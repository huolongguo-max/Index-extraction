"""
Apple 风格 PyQt6 桌面置顶悬浮窗（完整版）
==========================================
纯展示层 — 仅通过 HTTP + SSE 与后端通信，不耦合业务逻辑。

能力矩阵:
  窗口: 无边框 | 全局置顶(可切换) | 任意拖拽 | 四边缩放 | 最小化到托盘
  数据: SSE 实时推送 | 自定义指标选择 | 可调字体大小
  操作: 手动刷新按钮(触发后端采集) | 系统托盘菜单
  设置: 开机自启 | 置顶开关 | 字体大小 | 指标筛选
  容错: 断线自动重连(指数退避) | 离线状态提示 | 程序不闪退
  行为: 关闭悬浮窗 → 隐藏到托盘，不终止后端采集服务

设计: 苹果简约风格 — 玻璃态背景 + Apple 系统色 + SF Pro 排版
"""

import sys
import os
import json
import time
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGraphicsDropShadowEffect, QFrame,
    QSystemTrayIcon, QMenu, QSlider, QCheckBox, QScrollArea,
    QSizePolicy, QSpacerItem, QLineEdit,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QRect, QSize, QSettings,
    pyqtSignal, QObject, QThread,
)
from PyQt6.QtGui import (
    QFont, QColor, QIcon, QAction, QPixmap, QPainter, QMouseEvent,
)

# 项目根路径
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from config.settings import (
    DESKTOP_WINDOW_WIDTH, DESKTOP_WINDOW_HEIGHT, DESKTOP_WINDOW_POSITION,
    DESKTOP_WINDOW_OPACITY, DESKTOP_REFRESH_INTERVAL,
    VITE_API_BASE_URL, APP_NAME,
)
from utils.log_utils import setup_logger, get_logger
from window.styles import (
    colors as c, spacing as s, radius as r, typography as t, motion as m,
    generate_global_stylesheet,
)
from window.components.glass_card import GlassCard
from window.components.status_indicator import StatusDot, ConnectionBadge, KPIStat
from window.components.data_table import AppleTable

setup_logger(name="window")
logger = get_logger()

# ================================================================
# SSE 客户端（增强版 — 心跳保活 + 分级重试 + 日志抑制）
# ================================================================

class SSEClient(QObject):
    data_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool, str)

    # 客户端读取超时 = 心跳间隔的 2.3 倍 + 余量，避免误判超时
    _CONNECT_TIMEOUT = 5      # 秒 — TCP 连接超时
    _READ_TIMEOUT = 40        # 秒 — 闲置读取超时（后端心跳 15s，40s > 2×15s）

    def __init__(self, url: str = f"{VITE_API_BASE_URL}/api/sse/stream"):
        super().__init__()
        self._url = url
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._reconnect_count = 0
        self._consecutive_fails = 0
        self._consecutive_timeouts = 0   # 连续超时计数（用于抑制日志）
        self._last_event_time = 0.0       # 最近收到事件的时间戳
        self._last_connect_time = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    def start(self):
        self._running = True
        self._reconnect_count = 0
        self._consecutive_fails = 0
        self._consecutive_timeouts = 0
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(f"SSE 客户端启动: {self._url} (read_timeout={self._READ_TIMEOUT}s)")

    def stop(self):
        self._running = False
        self._connected = False

    def _backoff(self) -> float:
        """指数退避：1s → 2s → 4s → ... → max 30s"""
        return min(1.0 * (2 ** self._reconnect_count), 30.0)

    def _listen(self):
        import requests as req_lib

        while self._running:
            try:
                resp = req_lib.get(
                    self._url,
                    headers={"Accept": "text/event-stream"},
                    stream=True,
                    timeout=(self._CONNECT_TIMEOUT, self._READ_TIMEOUT),
                )
                # 连接成功
                self._connected = True
                self._reconnect_count = 0
                self._consecutive_fails = 0
                self._consecutive_timeouts = 0
                self._last_event_time = time.time()
                self._last_connect_time = time.time()
                self.connection_changed.emit(True, "已连接")
                logger.debug("SSE 连接成功")

                for line in resp.iter_lines(decode_unicode=True):
                    if not self._running:
                        break
                    if line and line.startswith("data: "):
                        try:
                            self._last_event_time = time.time()
                            data = json.loads(line[6:])
                            event_type = data.get("type", "")
                            # 心跳事件静默处理 — 不发 signal，不复写日志
                            if event_type == "heartbeat":
                                continue
                            self.data_received.emit(data)
                        except json.JSONDecodeError:
                            pass

            except req_lib.exceptions.ReadTimeout:
                # 读取超时 — 非致命，可能后端空闲
                if self._running:
                    self._connected = False
                    self._consecutive_timeouts += 1
                    self._consecutive_fails += 1
                    self._reconnect_count = min(self._reconnect_count + 1, 3)  # 慢退避
                    delay = self._backoff()

                    # 日志抑制：每 5 次超时才打印一次，其余用 DEBUG
                    if self._consecutive_timeouts % 5 == 1:
                        logger.info(
                            f"SSE 空闲超时（连续 {self._consecutive_timeouts} 次）| "
                            f"等待 {delay:.0f}s"
                        )
                    else:
                        logger.debug(f"SSE read timeout, sleeping {delay:.0f}s")

                    self.connection_changed.emit(
                        False,
                        f"等待数据中…（{self._consecutive_timeouts}）",
                    )
                    time.sleep(delay)

            except req_lib.exceptions.ConnectionError as e:
                # 连接失败 — 后端不可达
                if self._running:
                    self._connected = False
                    self._consecutive_fails += 1
                    self._consecutive_timeouts = 0
                    self._reconnect_count += 1
                    delay = self._backoff()
                    logger.warning(
                        f"SSE 连接失败: {e} | "
                        f"重试 #{self._reconnect_count} | 等待 {delay:.0f}s"
                    )
                    self.connection_changed.emit(
                        False,
                        f"后端不可达（重试 #{self._reconnect_count}，{delay:.0f}s）",
                    )
                    time.sleep(delay)

            except req_lib.RequestException as e:
                # 其他网络异常
                if self._running:
                    self._connected = False
                    self._consecutive_fails += 1
                    self._consecutive_timeouts = 0
                    self._reconnect_count += 1
                    delay = self._backoff()
                    logger.warning(
                        f"SSE 异常: {type(e).__name__}: {e} | "
                        f"重试 #{self._reconnect_count} | 等待 {delay:.0f}s"
                    )
                    self.connection_changed.emit(False, f"网络异常 — {delay:.0f}s 后重试")
                    time.sleep(delay)


# ================================================================
# 边缘大小调整检测器
# ================================================================

class EdgeGrip:
    """窗口边缘拖拽缩放检测"""

    MARGIN = 6  # 边缘检测宽度 (px)

    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4
    TOP_LEFT = 5
    TOP_RIGHT = 6
    BOTTOM_LEFT = 7
    BOTTOM_RIGHT = 8

    CURSORS = {
        LEFT: Qt.CursorShape.SizeHorCursor,
        RIGHT: Qt.CursorShape.SizeHorCursor,
        TOP: Qt.CursorShape.SizeVerCursor,
        BOTTOM: Qt.CursorShape.SizeVerCursor,
        TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
        BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
        TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
        BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    }

    @classmethod
    def detect(cls, pos: QPoint, rect: QRect) -> tuple[int, Qt.CursorShape | None]:
        """检测鼠标在窗口边缘的位置"""
        x, y = pos.x(), pos.y()
        rw, rh = rect.width(), rect.height()
        on_left = x <= cls.MARGIN
        on_right = x >= rw - cls.MARGIN
        on_top = y <= cls.MARGIN
        on_bottom = y >= rh - cls.MARGIN

        if on_left and on_top:
            return cls.TOP_LEFT, cls.CURSORS.get(cls.TOP_LEFT)
        if on_right and on_top:
            return cls.TOP_RIGHT, cls.CURSORS.get(cls.TOP_RIGHT)
        if on_left and on_bottom:
            return cls.BOTTOM_LEFT, cls.CURSORS.get(cls.BOTTOM_LEFT)
        if on_right and on_bottom:
            return cls.BOTTOM_RIGHT, cls.CURSORS.get(cls.BOTTOM_RIGHT)
        if on_left:
            return cls.LEFT, cls.CURSORS.get(cls.LEFT)
        if on_right:
            return cls.RIGHT, cls.CURSORS.get(cls.RIGHT)
        if on_top:
            return cls.TOP, cls.CURSORS.get(cls.TOP)
        if on_bottom:
            return cls.BOTTOM, cls.CURSORS.get(cls.BOTTOM)
        return cls.NONE, None


# ================================================================
# 标题栏（增强版 — 三键功能齐全 + 设置入口）
# ================================================================

class AppleTitleBar(QWidget):
    minimize_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._drag_start: Optional[QPoint] = None
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        # 关闭按钮（红色 — 隐藏到托盘）
        close_btn = QPushButton()
        close_btn.setFixedSize(12, 12)
        close_btn.setToolTip("隐藏到托盘")
        close_btn.setStyleSheet("""QPushButton{background:#FF5F57;border:none;border-radius:6px}QPushButton:hover{background:#FF3B30}""")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

        # 最小化按钮（黄色 — 最小化到托盘）
        min_btn = QPushButton()
        min_btn.setFixedSize(12, 12)
        min_btn.setToolTip("最小化到托盘")
        min_btn.setStyleSheet("""QPushButton{background:#FFBD2E;border:none;border-radius:6px}QPushButton:hover{background:#FF9F0A}""")
        min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(min_btn)

        # 设置按钮（绿色 — 打开设置面板）
        set_btn = QPushButton()
        set_btn.setFixedSize(12, 12)
        set_btn.setToolTip("设置")
        set_btn.setStyleSheet("""QPushButton{background:#28C840;border:none;border-radius:6px}QPushButton:hover{background:#1DAF30}""")
        set_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(set_btn)

        layout.addSpacing(6)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color:{c.text_secondary};font-size:11px;font-weight:600;background:transparent")
        layout.addWidget(title_label)
        layout.addStretch()

        # 右侧连接状态
        self._badge = ConnectionBadge(status="grey", label="离线")
        layout.addWidget(self._badge)

    @property
    def badge(self) -> ConnectionBadge:
        return self._badge

    def _on_close(self):
        """红色按钮 — 隐藏窗口（退到托盘）"""
        win = self.window()
        if win:
            win.hide()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            w = self.window()
            if w:
                w.move(w.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start = None
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # 双击标题栏 → 切换置顶
        w = self.window()
        if w and hasattr(w, 'toggle_always_on_top'):
            w.toggle_always_on_top()


# ================================================================
# 设置面板（弹出式）
# ================================================================

class SettingsPanel(QWidget):
    """悬浮窗设置面板 — 指标选择 / 字体大小 / 开机自启 / 置顶"""

    font_size_changed = pyqtSignal(int)
    metrics_changed = pyqtSignal(list)
    auto_start_toggled = pyqtSignal(bool)
    always_on_top_toggled = pyqtSignal(bool)
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._font_size = 11
        self._auto_start = False
        self._on_top = True
        self._available_headers: list[str] = []
        self._selected_headers: set[str] = set()

        self.setFixedWidth(260)
        self._build_ui()
        self._apply_style()

        # 加载持久化设置
        self._settings = QSettings("IndexExtraction", "FloatingWindow")
        self._font_size = int(self._settings.value("font_size", 11))
        self._auto_start = bool(self._settings.value("auto_start", False) == "true")
        self._on_top = bool(self._settings.value("always_on_top", True) != "false")
        loaded_headers = self._settings.value("selected_headers", "")
        if loaded_headers:
            self._selected_headers = set(loaded_headers.split(","))
        self._sync_controls_from_state()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 标题
        title = QLabel("设置")
        title.setStyleSheet(f"font-size:12px;font-weight:700;color:{c.text_primary};background:transparent")
        layout.addWidget(title)

        # === 字体大小 ===
        fs_label = QLabel(f"字体大小: {self._font_size}pt")
        fs_label.setStyleSheet(f"font-size:10px;color:{c.text_secondary};background:transparent")
        layout.addWidget(fs_label)
        self._font_label = fs_label

        self._font_slider = QSlider(Qt.Orientation.Horizontal)
        self._font_slider.setRange(8, 22)
        self._font_slider.setValue(self._font_size)
        self._font_slider.setStyleSheet(self._slider_style())
        self._font_slider.valueChanged.connect(self._on_font_slider)
        self._font_slider.setFixedHeight(20)
        layout.addWidget(self._font_slider)

        # === 置顶开关 ===
        self._on_top_cb = QCheckBox("窗口置顶")
        self._on_top_cb.setChecked(self._on_top)
        self._on_top_cb.setStyleSheet(self._checkbox_style())
        self._on_top_cb.toggled.connect(self._on_top_toggle)
        layout.addWidget(self._on_top_cb)

        # === 开机自启 ===
        self._auto_start_cb = QCheckBox("开机自启")
        self._auto_start_cb.setChecked(self._auto_start)
        self._auto_start_cb.setStyleSheet(self._checkbox_style())
        self._auto_start_cb.toggled.connect(self._on_auto_start_toggle)
        layout.addWidget(self._auto_start_cb)

        # === 指标选择 ===
        metrics_label = QLabel("显示指标")
        metrics_label.setStyleSheet(f"font-size:10px;font-weight:600;color:{c.text_secondary};background:transparent")
        layout.addWidget(metrics_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(140)
        scroll.setStyleSheet(f"background:transparent;border:1px solid {c.separator};border-radius:8px")
        self._metrics_container = QWidget()
        self._metrics_container.setStyleSheet("background:transparent")
        self._metrics_layout = QVBoxLayout(self._metrics_container)
        self._metrics_layout.setContentsMargins(8, 4, 8, 4)
        self._metrics_layout.setSpacing(1)
        self._metrics_layout.addStretch()
        scroll.setWidget(self._metrics_container)
        layout.addWidget(scroll)

        self._metric_checkboxes: dict[str, QCheckBox] = {}

        # === 关闭按钮 ===
        close_btn = QPushButton("完成")
        close_btn.setStyleSheet(f"""
            QPushButton{{background:{c.system_blue};color:#FFF;border:none;border-radius:6px;padding:6px;font-size:11px;font-weight:600}}
            QPushButton:hover{{background:{c.system_blue_light}}}
        """)
        close_btn.clicked.connect(self._on_done)
        layout.addWidget(close_btn)

    def _apply_style(self):
        self.setStyleSheet(f"""
            SettingsPanel{{background:{c.glass_bg_elevated};border:0.5px solid {c.border_glass};border-radius:14px}}
        """)

    def _checkbox_style(self):
        return f"""QCheckBox{{color:{c.text_secondary};font-size:11px;background:transparent;spacing:8px}}
                   QCheckBox::indicator{{width:16px;height:16px;border-radius:4px;border:1px solid {c.separator};background:transparent}}
                   QCheckBox::indicator:checked{{background:{c.system_blue};border-color:{c.system_blue}}}"""

    def _slider_style(self):
        return f"""QSlider::groove:horizontal{{background:{c.fill_secondary};height:4px;border-radius:2px}}
                   QSlider::handle:horizontal{{background:{c.system_blue};width:14px;height:14px;margin:-5px 0;border-radius:7px}}
                   QSlider::sub-page:horizontal{{background:{c.system_blue};border-radius:2px}}"""

    def set_available_headers(self, headers: list[str]):
        """根据后端数据动态构建指标选择列表"""
        self._available_headers = headers
        # 清除旧项
        for cb in list(self._metric_checkboxes.values()):
            self._metrics_layout.removeWidget(cb)
            cb.deleteLater()
        self._metric_checkboxes.clear()

        for h in headers:
            cb = QCheckBox(h)
            cb.setChecked(h in self._selected_headers if self._selected_headers else True)
            cb.setStyleSheet(self._checkbox_style())
            cb.toggled.connect(self._emit_metrics)
            self._metrics_layout.insertWidget(self._metrics_layout.count() - 1, cb)
            self._metric_checkboxes[h] = cb

    def _sync_controls_from_state(self):
        self._font_slider.setValue(self._font_size)
        self._font_label.setText(f"字体大小: {self._font_size}pt")
        self._on_top_cb.setChecked(self._on_top)
        self._auto_start_cb.setChecked(self._auto_start)

    def _on_font_slider(self, val: int):
        self._font_size = val
        self._font_label.setText(f"字体大小: {val}pt")
        self._settings.setValue("font_size", val)
        self.font_size_changed.emit(val)

    def _on_top_toggle(self, checked: bool):
        self._on_top = checked
        self._settings.setValue("always_on_top", "true" if checked else "false")
        self.always_on_top_toggled.emit(checked)

    def _on_auto_start_toggle(self, checked: bool):
        self._auto_start = checked
        self._settings.setValue("auto_start", "true" if checked else "false")
        self._set_auto_start_os(checked)
        self.auto_start_toggled.emit(checked)

    def _set_auto_start_os(self, enable: bool):
        """写入系统开机自启（macOS LaunchAgent / Linux autostart / Windows Startup）"""
        try:
            if sys.platform == "darwin":
                plist_dir = Path.home() / "Library/LaunchAgents"
                plist_dir.mkdir(parents=True, exist_ok=True)
                plist_path = plist_dir / "com.indexextraction.floatingwindow.plist"
                if enable:
                    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
    <key>Label</key><string>com.indexextraction.floatingwindow</string>
    <key>ProgramArguments</key><array><string>{sys.executable}</string>
    <string>{ROOT_DIR}/window/main.py</string></array>
    <key>RunAtLoad</key><true/>
</dict></plist>"""
                    plist_path.write_text(plist)
                else:
                    plist_path.unlink(missing_ok=True)

            elif sys.platform == "linux":
                autostart_dir = Path.home() / ".config/autostart"
                autostart_dir.mkdir(parents=True, exist_ok=True)
                desktop_file = autostart_dir / "index-extraction.desktop"
                if enable:
                    desktop_file.write_text(f"""[Desktop Entry]
Type=Application
Name=Index-extraction
Exec={sys.executable} {ROOT_DIR}/window/main.py
X-GNOME-Autostart-enabled=true
""")
                else:
                    desktop_file.unlink(missing_ok=True)

            elif sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE,
                )
                if enable:
                    winreg.SetValueEx(key, "IndexExtraction", 0, winreg.REG_SZ,
                                      f'"{sys.executable}" "{ROOT_DIR}/window/main.py"')
                else:
                    try:
                        winreg.DeleteValue(key, "IndexExtraction")
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(key)

        except Exception as exc:
            logger.warning(f"设置开机自启失败: {exc}")

    def _emit_metrics(self):
        selected = [h for h, cb in self._metric_checkboxes.items() if cb.isChecked()]
        self._settings.setValue("selected_headers", ",".join(selected))
        self.metrics_changed.emit(selected)

    def _on_done(self):
        self._emit_metrics()
        self.close_requested.emit()
        self.hide()

    @property
    def selected_headers(self) -> list[str]:
        return [h for h, cb in self._metric_checkboxes.items() if cb.isChecked()]


# ================================================================
# 主悬浮窗（完整版）
# ================================================================

class FloatingWindow(QWidget):
    """Apple 风格玻璃态悬浮窗 — Index-extraction 核心展示端"""

    def __init__(self):
        super().__init__()
        self._sse_client: Optional[SSEClient] = None
        self._data_cache: list[dict] = []
        self._is_connected = False
        self._on_top = True
        self._font_size = 11
        self._selected_headers: list[str] = []
        self._resize_edge = EdgeGrip.NONE
        self._drag_start: Optional[QPoint] = None
        self._resize_start_geom: Optional[QRect] = None
        self._resize_start_pos: Optional[QPoint] = None
        self._settings_panel: Optional[SettingsPanel] = None
        self._offline_banner: Optional[QWidget] = None
        self._tray: Optional[QSystemTrayIcon] = None

        # 加载持久化设置
        self._qsettings = QSettings("IndexExtraction", "FloatingWindow")

        self._init_window()
        self._init_ui()
        self._init_tray()
        self._init_sse()
        self._apply_style()

        # 恢复设置
        self._load_persisted_settings()

        logger.info("悬浮窗 v2.0 初始化完成")

    # ================================================================
    # 窗口初始化
    # ================================================================

    def _init_window(self):
        self.setWindowTitle(f"{APP_NAME} — 数据悬浮窗")
        self.resize(DESKTOP_WINDOW_WIDTH, DESKTOP_WINDOW_HEIGHT)
        self.setMinimumSize(280, 360)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(DESKTOP_WINDOW_OPACITY)
        x, y = DESKTOP_WINDOW_POSITION
        self.move(QPoint(x, y))
        self.setMouseTracking(True)  # 边缘缩放需要

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # === 玻璃态容器 ===
        self._container = QWidget()
        self._container.setObjectName("glass")
        self._container.setStyleSheet(f"""
            QWidget#glass{{background:{c.glass_bg_primary};border:0.5px solid {c.border_glass};border-radius:{r.xxl}px}}
        """)
        shadow = QGraphicsDropShadowEffect(self._container)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 80))
        self._container.setGraphicsEffect(shadow)

        cl = QVBoxLayout(self._container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # === 标题栏 ===
        self._title_bar = AppleTitleBar(title="Index-extraction")
        self._title_bar.minimize_clicked.connect(self._on_minimize)
        self._title_bar.settings_clicked.connect(self._open_settings)
        cl.addWidget(self._title_bar)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"border:none;border-top:0.5px solid {c.separator}")
        sep.setFixedHeight(1)
        cl.addWidget(sep)

        # === 离线横幅（默认隐藏） ===
        self._offline_banner = QWidget()
        self._offline_banner.setStyleSheet(f"background:{c.system_orange}20;border-bottom:0.5px solid {c.separator}")
        obl = QHBoxLayout(self._offline_banner)
        obl.setContentsMargins(12, 4, 12, 4)
        self._offline_label = QLabel("离线模式 — 正在重连...")
        self._offline_label.setStyleSheet(f"color:{c.system_orange};font-size:10px;font-weight:500;background:transparent")
        obl.addWidget(self._offline_label)
        obl.addStretch()
        self._offline_banner.hide()
        cl.addWidget(self._offline_banner)

        # === 主内容滚动区 ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{background:transparent;border:none}}")
        self._content = QWidget()
        self._content.setStyleSheet("background:transparent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(14, 10, 14, 12)
        self._content_layout.setSpacing(8)
        scroll.setWidget(self._content)

        # -- KPI 行 --
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(8)
        self._kpi_total = KPIStat(value="--", label="总行数")
        self._kpi_pages = KPIStat(value="--", label="总页数")
        self._kpi_status = KPIStat(value="--", label="状态")
        self._kpi_row.addWidget(self._kpi_total)
        self._kpi_row.addWidget(self._kpi_pages)
        self._kpi_row.addWidget(self._kpi_status)
        self._content_layout.addLayout(self._kpi_row)

        # -- 操作按钮行 --
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._refresh_btn = QPushButton("⟳ 手动刷新")
        self._refresh_btn.setStyleSheet(f"""
            QPushButton{{background:{c.fill_primary};color:{c.system_blue};border:none;border-radius:8px;padding:6px 12px;font-size:11px;font-weight:600}}
            QPushButton:hover{{background:{c.fill_secondary}}}
            QPushButton:pressed{{background:{c.fill_primary};color:{c.system_blue_dark}}}
        """)
        self._refresh_btn.clicked.connect(self._manual_refresh)
        btn_row.addWidget(self._refresh_btn)

        btn_row.addStretch()
        self._refresh_status = QLabel("")
        self._refresh_status.setStyleSheet(f"color:{c.text_tertiary};font-size:10px;background:transparent")
        btn_row.addWidget(self._refresh_status)
        self._content_layout.addLayout(btn_row)

        # -- 数据表格 --
        table_card = GlassCard(title="实时数据", level="secondary")
        self._data_table = AppleTable()
        table_card.add_widget(self._data_table)
        self._content_layout.addWidget(table_card, stretch=1)

        # -- 底部状态栏 --
        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 0, 0, 0)
        self._footer_time = QLabel("等待数据...")
        self._footer_time.setStyleSheet(f"color:{c.text_quaternary};font-size:9px;background:transparent")
        fl.addWidget(self._footer_time)
        fl.addStretch()
        self._footer_count = QLabel("")
        self._footer_count.setStyleSheet(f"color:{c.text_quaternary};font-size:9px;background:transparent")
        fl.addWidget(self._footer_count)
        self._content_layout.addWidget(footer)

        cl.addWidget(scroll)
        root.addWidget(self._container)

    def _init_tray(self):
        """系统托盘 — 关闭窗口不退出程序"""
        self._tray = QSystemTrayIcon(self)

        # 生成简单图标
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(c.system_blue))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 4, 28, 24, 6, 6)
        painter.setBrush(QColor(255, 255, 255, 60))
        painter.drawRoundedRect(6, 14, 10, 10, 2, 2)
        painter.drawRoundedRect(18, 14, 10, 10, 2, 2)
        painter.end()
        self._tray.setIcon(QIcon(pix))
        self._tray.setToolTip(f"{APP_NAME} — 数据悬浮窗")

        menu = QMenu()
        show_action = menu.addAction("显示悬浮窗")
        show_action.triggered.connect(self._show_from_tray)
        menu.addSeparator()
        refresh_action = menu.addAction("手动刷新")
        refresh_action.triggered.connect(self._manual_refresh)
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(self._open_settings)
        menu.addSeparator()
        quit_action = menu.addAction("退出程序")
        quit_action.triggered.connect(self._quit_app)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _init_sse(self):
        self._sse_client = SSEClient()
        self._sse_client.data_received.connect(self._on_sse_data)
        self._sse_client.connection_changed.connect(self._on_connection_change)
        self._sse_client.start()

    def _apply_style(self):
        self.setStyleSheet(generate_global_stylesheet())

    def _load_persisted_settings(self):
        """从 QSettings 恢复设置"""
        self._font_size = int(self._qsettings.value("font_size", 11))
        self._on_top = bool(self._qsettings.value("always_on_top", True) != "false")
        loaded = self._qsettings.value("selected_headers", "")
        self._selected_headers = loaded.split(",") if loaded else []
        self._apply_font_size()
        self._apply_on_top()

    # ================================================================
    # SSE 事件处理
    # ================================================================

    def _on_sse_data(self, data: dict):
        event_type = data.get("type", "")
        payload = data.get("payload", {})

        if event_type == "update":
            rows = payload.get("data", [])
            if rows:
                self._data_cache = rows
                self._update_table(rows)
            self._update_kpis(payload)
            self._refresh_status.setText("")
            now = datetime.now().strftime("%H:%M:%S")
            self._footer_time.setText(f"更新于 {now}")

        elif event_type == "heartbeat":
            self._footer_time.setText(f"心跳 {datetime.now().strftime('%H:%M:%S')}")

    def _on_connection_change(self, is_connected: bool, msg: str):
        self._is_connected = is_connected
        if is_connected:
            self._title_bar.badge.set_status("在线", "green")
            self._offline_banner.hide()
            self._refresh_btn.setEnabled(True)
        else:
            self._title_bar.badge.set_status("离线", "red")
            self._offline_label.setText(msg)
            self._offline_banner.show()
            self._refresh_btn.setEnabled(False)

    # ================================================================
    # 数据展示
    # ================================================================

    def _update_table(self, rows: list[dict]):
        if not rows:
            self._data_table.populate_data(["提示"], [])
            self._footer_count.setText("0 行")
            return

        all_headers = list(rows[0].keys())

        # 过滤指标
        if self._selected_headers:
            visible = [h for h in self._selected_headers if h in all_headers]
        else:
            visible = all_headers

        if not visible:
            visible = all_headers[:1]

        # 更新设置面板的可用指标列表
        if self._settings_panel and self._settings_panel.isVisible():
            self._settings_panel.set_available_headers(all_headers)

        # 过滤数据
        filtered = [{h: row.get(h, "") for h in visible} for row in rows]
        self._data_table.populate_data(visible, filtered)
        self._footer_count.setText(f"{len(rows)} 行 × {len(visible)} 列")

    def _update_kpis(self, payload: dict):
        def _set_kpi(kpi: KPIStat, val):
            kpi._value = str(val)
            from PyQt6.QtWidgets import QLabel
            lbl = kpi.findChild(QLabel)
            if lbl and lbl.font().pixelSize() >= 20:
                lbl.setText(str(val))

        total_rows = payload.get("total_rows")
        total_pages = payload.get("total_pages")
        status = payload.get("status")

        if total_rows is not None:
            _set_kpi(self._kpi_total, total_rows)
        if total_pages is not None:
            _set_kpi(self._kpi_pages, total_pages)
        if status:
            _set_kpi(self._kpi_status, status)

    # ================================================================
    # 手动刷新（HTTP POST 触发后端采集）
    # ================================================================

    def _manual_refresh(self):
        """点击手动刷新 → 触发后端 /api/control/trigger"""
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⟳ 请求中...")
        self._refresh_status.setText("正在触发采集...")

        def _do():
            try:
                # 获取所有已启用规则的第一个 rule_id
                rules_resp = requests.get(
                    f"{VITE_API_BASE_URL}/api/rules?enabled=true", timeout=5
                )
                rules_data = rules_resp.json()
                items = rules_data.get("data", {}).get("items", [])

                if not items:
                    self._refresh_status.setText("⚠️ 无已启用规则")
                    return

                triggered = 0
                for item in items[:5]:  # 最多触发 5 条
                    try:
                        resp = requests.post(
                            f"{VITE_API_BASE_URL}/api/control/trigger/{item['rule_id']}",
                            timeout=15,
                        )
                        if resp.status_code == 200:
                            triggered += 1
                    except Exception:
                        pass

                if triggered:
                    self._refresh_status.setText(f"✅ 已触发 {triggered} 条规则采集")
                else:
                    self._refresh_status.setText("⚠️ 触发失败")

            except requests.RequestException as e:
                self._refresh_status.setText(f"❌ 请求异常: {str(e)[:30]}")
                logger.warning(f"手动刷新失败: {e}")
            except Exception as exc:
                self._refresh_status.setText(f"❌ 异常: {str(exc)[:30]}")

        threading.Thread(target=_do, daemon=True).start()

        def _restore():
            self._refresh_btn.setEnabled(True)
            self._refresh_btn.setText("⟳ 手动刷新")

        QTimer.singleShot(2000, _restore)

    # ================================================================
    # 设置面板
    # ================================================================

    def _open_settings(self):
        if self._settings_panel is None:
            self._settings_panel = SettingsPanel(self)
            self._settings_panel.font_size_changed.connect(self._on_font_size_changed)
            self._settings_panel.metrics_changed.connect(self._on_metrics_changed)
            self._settings_panel.always_on_top_toggled.connect(self._on_top_toggled)
            self._settings_panel.close_requested.connect(self._settings_panel.hide)

        # 更新可用指标
        if self._data_cache:
            headers = list(self._data_cache[0].keys())
            self._settings_panel.set_available_headers(headers)

        # 在标题栏绿色按钮下方弹出
        pos = self.mapToGlobal(QPoint(30, 44))
        self._settings_panel.move(pos)
        self._settings_panel.show()

    def _on_font_size_changed(self, size: int):
        self._font_size = size
        self._apply_font_size()

    def _apply_font_size(self):
        self._data_table.setFont(QFont("", self._font_size))
        self._data_table.setStyleSheet(
            self._data_table.styleSheet().replace(
                "font-size: 12px", f"font-size: {self._font_size}px"
            )
        )
        # Force refresh
        if self._data_cache:
            self._update_table(self._data_cache)

    def _on_metrics_changed(self, headers: list):
        self._selected_headers = headers
        if self._data_cache:
            self._update_table(self._data_cache)

    def _on_top_toggled(self, checked: bool):
        self._on_top = checked
        self._apply_on_top()

    def _apply_on_top(self):
        """动态切换窗口置顶"""
        flags = self.windowFlags()
        if self._on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()  # 需要重新 show 才能生效

    def toggle_always_on_top(self):
        self._on_top = not self._on_top
        self._apply_on_top()
        if self._settings_panel:
            self._settings_panel._on_top = self._on_top
            self._settings_panel._on_top_cb.setChecked(self._on_top)

    # ================================================================
    # 托盘 & 最小化
    # ================================================================

    def _on_minimize(self):
        """黄色按钮 — 最小化到托盘"""
        self.hide()

    def _show_from_tray(self):
        """从托盘恢复显示"""
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """双击托盘图标 → 显示窗口"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _quit_app(self):
        """退出整个程序"""
        if self._sse_client:
            self._sse_client.stop()
        if self._tray:
            self._tray.hide()
        QApplication.instance().quit()
        logger.info("悬浮窗程序已退出")

    # ================================================================
    # 边缘缩放
    # ================================================================

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            edge, cursor = EdgeGrip.detect(event.pos(), self.rect())
            if edge != EdgeGrip.NONE:
                self._resize_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return
            # 否则可能是拖拽
            child = self.childAt(event.pos())
            if child in (self._container, self._content, self._data_table):
                self._drag_start = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._resize_edge != EdgeGrip.NONE and self._resize_start_geom:
            self._do_resize(event)
            return
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.move(self.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            return
        # 更新光标
        edge, cursor = EdgeGrip.detect(event.pos(), self.rect())
        self.setCursor(cursor if cursor else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._resize_edge = EdgeGrip.NONE
        self._resize_start_geom = None
        self._resize_start_pos = None
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _do_resize(self, event: QMouseEvent):
        geom = QRect(self._resize_start_geom)
        delta = event.globalPosition().toPoint() - self._resize_start_pos
        e = self._resize_edge
        min_w, min_h = 280, 360

        if e in (EdgeGrip.LEFT, EdgeGrip.TOP_LEFT, EdgeGrip.BOTTOM_LEFT):
            new_w = geom.width() - delta.x()
            if new_w >= min_w:
                geom.setLeft(geom.left() + delta.x())
        if e in (EdgeGrip.RIGHT, EdgeGrip.TOP_RIGHT, EdgeGrip.BOTTOM_RIGHT):
            new_w = geom.width() + delta.x()
            if new_w >= min_w:
                geom.setRight(geom.right() + delta.x())
        if e in (EdgeGrip.TOP, EdgeGrip.TOP_LEFT, EdgeGrip.TOP_RIGHT):
            new_h = geom.height() - delta.y()
            if new_h >= min_h:
                geom.setTop(geom.top() + delta.y())
        if e in (EdgeGrip.BOTTOM, EdgeGrip.BOTTOM_LEFT, EdgeGrip.BOTTOM_RIGHT):
            new_h = geom.height() + delta.y()
            if new_h >= min_h:
                geom.setBottom(geom.bottom() + delta.y())

        self.setGeometry(geom)

    # ================================================================
    # 鼠标渐变效果
    # ================================================================

    def enterEvent(self, event):
        self.setWindowOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setWindowOpacity(DESKTOP_WINDOW_OPACITY)
        super().leaveEvent(event)

    # ================================================================
    # 生命周期
    # ================================================================

    def closeEvent(self, event):
        """关闭 → 隐藏到托盘（不退出程序）"""
        if self._tray and self._tray.isVisible():
            self.hide()
            event.ignore()  # 不真正关闭
            self._tray.showMessage(
                "Index-extraction",
                "悬浮窗已隐藏到托盘，采集服务继续运行",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            if self._sse_client:
                self._sse_client.stop()
            event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        logger.debug(f"悬浮窗显示: {self.width()}x{self.height()}")
