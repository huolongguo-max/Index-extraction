"""
Apple 风格 PyQt6 玻璃态悬浮窗
=================================
设计来源: ui-ux-pro-max data
- Style:     Glassmorphism (#3) + Bento Box Grid (#39) + Spatial UI (VisionOS)
- Colors:    Apple System Colors + Translucent Glass Surfaces
- Typography: Inter (SF Pro 风格替代)
- Motion:    Subtle micro-interactions (150-250ms, power1.out)
- UX:        Touch-friendly, focus-visible, reduced-motion support

视觉特征:
- 半透明玻璃背景 (frosted glass, blur equivalent)
- 圆角 18px 窗口圆角
- 微细白色描边
- 多层次投影模拟三维深度
- 无边框拖拽窗口
- 置顶悬浮 (WindowStaysOnTopHint)
"""

import sys
import os
import json
import threading
import requests
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGraphicsDropShadowEffect,
    QSizePolicy, QSpacerItem, QFrame,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation,
    QEasingCurve, pyqtSignal, QObject, QRect, QSize,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPainterPath,
    QLinearGradient, QMouseEvent, QEnterEvent,
)

# 项目根路径
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from config.settings import (
    DESKTOP_WINDOW_WIDTH,
    DESKTOP_WINDOW_HEIGHT,
    DESKTOP_WINDOW_POSITION,
    DESKTOP_WINDOW_OPACITY,
    DESKTOP_REFRESH_INTERVAL,
    VITE_API_BASE_URL,
    SSE_PUSH_INTERVAL,
    APP_NAME,
)
from utils.log_utils import setup_logger, get_logger

from window.styles import (
    colors, spacing, radius, typography, motion, shadow,
    generate_global_stylesheet,
)
from window.components.glass_card import GlassCard
from window.components.status_indicator import StatusDot, ConnectionBadge, KPIStat
from window.components.data_table import AppleTable

# 初始化日志
setup_logger(name="window")
logger = get_logger()


# ================================================================
# SSE 客户端 (后台线程 → Qt Signal 驱动)
# ================================================================

class SSEClient(QObject):
    """SSE 实时数据流接收器"""
    data_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(bool, str)  # is_connected, message

    def __init__(self, url: str = f"{VITE_API_BASE_URL}/api/sse/stream"):
        super().__init__()
        self._url = url
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(f"SSE 客户端启动: {self._url}")

    def stop(self):
        self._running = False
        self._connected = False
        logger.info("SSE 客户端已停止")

    def _listen(self):
        while self._running:
            try:
                resp = requests.get(
                    self._url,
                    headers={"Accept": "text/event-stream"},
                    stream=True,
                    timeout=(5, SSE_PUSH_INTERVAL + 10),
                )
                self._connected = True
                self.connection_changed.emit(True, "已连接")

                for line in resp.iter_lines(decode_unicode=True):
                    if not self._running:
                        break
                    if line and line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            self.data_received.emit(data)
                        except json.JSONDecodeError:
                            pass

            except requests.RequestException as e:
                if self._running:
                    self._connected = False
                    self.connection_changed.emit(False, f"连接异常: {str(e)[:40]}")
                    logger.warning(f"SSE 连接中断: {e}")
                    import time
                    time.sleep(3)  # 重连间隔

            self._connected = False


# ================================================================
# 自定义标题栏 (macOS 风格)
# ================================================================

class AppleTitleBar(QWidget):
    """
    macOS 风格标题栏
    - 左侧: 红黄绿 交通灯按钮 (仅显示关闭)
    - 中间: 窗口标题
    - 右侧: 状态徽章
    """

    close_clicked = pyqtSignal()

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._drag_start: Optional[QPoint] = None
        self.setFixedHeight(44)  # Apple 标题栏标准高度

        layout = QHBoxLayout(self)
        layout.setContentsMargins(spacing.lg, 0, spacing.lg, 0)
        layout.setSpacing(spacing.md)

        # 关闭按钮 (红色交通灯)
        close_btn = QPushButton()
        close_btn.setFixedSize(12, 12)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #FF5F57;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #FF3B30;
            }
        """)
        close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(close_btn)

        # 最小化按钮 (黄色交通灯 - 装饰)
        min_btn = QPushButton()
        min_btn.setFixedSize(12, 12)
        min_btn.setStyleSheet("""
            QPushButton {
                background: #FFBD2E;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #FF9F0A;
            }
        """)
        layout.addWidget(min_btn)

        # 最大化按钮 (绿色交通灯 - 装饰)
        max_btn = QPushButton()
        max_btn.setFixedSize(12, 12)
        max_btn.setStyleSheet("""
            QPushButton {
                background: #28C840;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #1DAF30;
            }
        """)
        layout.addWidget(max_btn)

        layout.addSpacing(spacing.md)

        # 标题
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors.text_secondary};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        layout.addWidget(self._title_label)

        layout.addStretch()

        # 右侧连接状态
        self._badge = ConnectionBadge(status="grey", label="未连接")
        layout.addWidget(self._badge)

    @property
    def badge(self) -> ConnectionBadge:
        return self._badge

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            window = self.window()
            if window:
                window.move(window.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start = None
        event.accept()


# ================================================================
# 主悬浮窗 (Apple Glassmorphism)
# ================================================================

class AppleFloatingWindow(QWidget):
    """
    Apple 风格玻璃态悬浮窗

    设计参数 (来源: ui-ux-pro-max):
    - Glassmorphism: 半透明背景 + 白色描边 + 模糊效果模拟
    - Bento Box: 模块化卡片布局
    - Spatial UI: 深度投影 + 层次感
    - Apple 微交互: ≤2px 悬浮偏移, 150-250ms 过渡
    """

    window_closed = pyqtSignal()
    window_minimized = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._sse_client: Optional[SSEClient] = None
        self._data_cache: list[dict] = []
        self._is_connected = False

        self._init_window()
        self._init_ui()
        self._init_sse()
        self._apply_global_style()

        logger.info("Apple 玻璃态悬浮窗初始化完成")

    # ============ 窗口初始化 ============

    def _init_window(self):
        """窗口基础配置 — 无边框 + 置顶 + 玻璃态"""
        self.setWindowTitle(f"{APP_NAME} — 数据悬浮窗")

        # 窗口尺寸
        self.setFixedSize(DESKTOP_WINDOW_WIDTH, DESKTOP_WINDOW_HEIGHT)
        self.setMinimumSize(320, 400)

        # 窗口标志: 无边框 + 置顶 + 工具窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # 透明背景 (允许自定义绘制实现玻璃态)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 窗口透明度
        self.setWindowOpacity(DESKTOP_WINDOW_OPACITY)

        # 初始位置
        x, y = DESKTOP_WINDOW_POSITION
        self.move(QPoint(x, y))

    def _init_ui(self):
        """构建 Apple 风格 UI 布局"""
        # 根布局
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # === 内容容器 (带圆角 + 玻璃态背景) ===
        self._container = QWidget()
        self._container.setObjectName("glassContainer")
        self._container.setStyleSheet(f"""
            QWidget#glassContainer {{
                background: {colors.glass_bg_primary};
                border: 0.5px solid {colors.border_glass};
                border-radius: {radius.xxl}px;
            }}
        """)

        # 添加容器投影 (Qt 模拟多层阴影)
        self._add_container_shadow()

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # === 标题栏 ===
        self._title_bar = AppleTitleBar(title="Index-extraction")
        self._title_bar.close_clicked.connect(self.hide)
        container_layout.addWidget(self._title_bar)

        # === 分隔线 ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"border: none; border-top: 0.5px solid {colors.separator};")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)

        # === 主内容区域 (可滚动) ===
        self._content_area = QWidget()
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(
            spacing.lg, spacing.md, spacing.lg, spacing.lg
        )
        self._content_layout.setSpacing(spacing.lg)

        # -- KPI 数据卡片行 (Bento 小卡片) --
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(spacing.lg)

        self._kpi_total = KPIStat(value="--", label="总行数")
        self._kpi_pages = KPIStat(value="--", label="页数")
        self._kpi_status = KPIStat(value="--", label="任务状态")

        self._kpi_row.addWidget(self._kpi_total)
        self._kpi_row.addWidget(self._kpi_pages)
        self._kpi_row.addWidget(self._kpi_status)
        self._content_layout.addLayout(self._kpi_row)

        # -- 数据表格区域 --
        table_card = GlassCard(title="抓取数据", level="secondary")
        self._data_table = AppleTable()
        table_card.add_widget(self._data_table)
        self._content_layout.addWidget(table_card, stretch=1)

        # -- 底部状态栏 --
        self._footer = QWidget()
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        self._update_time_label = QLabel("等待数据...")
        self._update_time_label.setStyleSheet(f"""
            color: {colors.text_quaternary};
            font-size: 10px;
            background: transparent;
        """)
        footer_layout.addWidget(self._update_time_label)
        footer_layout.addStretch()

        row_count_label = QLabel("Index-extraction v1.0")
        row_count_label.setStyleSheet(f"""
            color: {colors.text_quaternary};
            font-size: 10px;
            background: transparent;
        """)
        footer_layout.addWidget(row_count_label)

        self._content_layout.addWidget(self._footer)

        container_layout.addWidget(self._content_area)

        self._root_layout.addWidget(self._container)

    def _add_container_shadow(self):
        """为容器添加多层投影效果 (Apple 深度系统)"""
        shadow_effect = QGraphicsDropShadowEffect(self._container)
        shadow_effect.setBlurRadius(30)
        shadow_effect.setOffset(0, 8)
        shadow_effect.setColor(QColor(0, 0, 0, 80))
        self._container.setGraphicsEffect(shadow_effect)

    def _init_sse(self):
        """初始化 SSE 连接"""
        self._sse_client = SSEClient()
        self._sse_client.data_received.connect(self._on_sse_data)
        self._sse_client.connection_changed.connect(self._on_connection_change)
        self._sse_client.start()

    def _apply_global_style(self):
        """应用全局 QSS 样式表"""
        self.setStyleSheet(generate_global_stylesheet())

    # ============ SSE 事件处理 ============

    def _on_sse_data(self, data: dict):
        """处理 SSE 推送数据"""
        event_type = data.get("type", "unknown")
        payload = data.get("payload", {})

        if event_type == "update":
            rows = payload.get("data", [])
            if rows:
                self._update_table_data(rows)
                self._data_cache = rows
            self._update_kpi(payload)

            now = datetime.now().strftime("%H:%M:%S")
            self._update_time_label.setText(f"更新于 {now}")

        elif event_type == "heartbeat":
            now = datetime.now().strftime("%H:%M:%S")
            self._update_time_label.setText(f"心跳 {now}")

        elif event_type == "error":
            logger.warning(f"SSE 数据错误: {payload.get('msg', '')}")

    def _on_connection_change(self, is_connected: bool, msg: str):
        """处理连接状态变化"""
        self._is_connected = is_connected

        if is_connected:
            self._title_bar.badge.set_status("已连接", "green")
        else:
            self._title_bar.badge.set_status("未连接", "red")

    # ============ 数据展示更新 ============

    def _update_table_data(self, rows: list[dict]):
        """更新数据表格"""
        if not rows:
            self._data_table.populate_data(["提示"], [])
            return
        columns = list(rows[0].keys())
        self._data_table.populate_data(columns, rows)

    def _update_kpi(self, payload: dict):
        """更新 KPI 卡片"""
        total_rows = payload.get("total_rows")
        total_pages = payload.get("total_pages")
        status = payload.get("status", "--")

        if total_rows is not None:
            self._kpi_total._value = str(total_rows)
            # 动态更新 KPI 值
            for i in range(self._kpi_total.layout().count()):
                w = self._kpi_total.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.font().pixelSize() >= 20:
                    w.setText(str(total_rows))

        if total_pages is not None:
            self._kpi_pages._value = str(total_pages)
            for i in range(self._kpi_pages.layout().count()):
                w = self._kpi_pages.layout().itemAt(i).widget()
                if isinstance(w, QLabel) and w.font().pixelSize() >= 20:
                    w.setText(str(total_pages))

    # ============ 拖拽 & 交互 ============

    def mousePressEvent(self, event: QMouseEvent):
        """点击窗口内部空白区域可拖拽 (Apple 风格)"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 只在点击容器空白区域时拖拽
            child = self.childAt(event.pos())
            if child is self._container or child is self._content_area:
                self._drag_start = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if hasattr(self, '_drag_start') and self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.move(self.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_start = None
        event.accept()

    def enterEvent(self, event: QEnterEvent):
        """鼠标进入窗口 — 轻微高亮效果"""
        self.setWindowOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开窗口 — 恢复透明度"""
        self.setWindowOpacity(DESKTOP_WINDOW_OPACITY)
        super().leaveEvent(event)

    # ============ 生命周期 ============

    def closeEvent(self, event):
        """关闭窗口时清理 SSE 连接"""
        if self._sse_client:
            self._sse_client.stop()
        self.window_closed.emit()
        logger.info("Apple 玻璃态悬浮窗已关闭")
        event.accept()

    def showEvent(self, event):
        """首次显示时记录"""
        super().showEvent(event)
        logger.info(f"悬浮窗显示 | 尺寸: {self.width()}x{self.height()} | 位置: {self.pos().x()},{self.pos().y()}")


# ================================================================
# 启动入口
# ================================================================

def main():
    """启动 Apple 风格玻璃态悬浮窗"""
    app = QApplication(sys.argv)
    app.setApplicationName(f"{APP_NAME} — Apple Glass Window")
    app.setQuitOnLastWindowClosed(False)  # macOS 风格：关闭窗口不退出

    window = AppleFloatingWindow()
    window.show()

    logger.info("🚀 Apple 玻璃态悬浮窗已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
