"""
Index-extraction PyQt6 桌面悬浮窗
置顶悬浮窗口，通过 SSE 实时接收后端抓取数据并展示
"""

import sys
import json
import threading
import requests
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStatusBar,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPoint,
    pyqtSignal,
    QObject,
)
from PyQt6.QtGui import QFont, QIcon, QAction

# 项目根目录
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import (
    DESKTOP_WINDOW_WIDTH,
    DESKTOP_WINDOW_HEIGHT,
    DESKTOP_WINDOW_POSITION,
    DESKTOP_WINDOW_OPACITY,
    DESKTOP_REFRESH_INTERVAL,
    VITE_API_BASE_URL,
    SSE_PUSH_INTERVAL,
)
from utils.log_utils import setup_logger, get_logger

# 初始化日志
setup_logger(name="desktop")
logger = get_logger()


class SSEClient(QObject):
    """SSE 数据流客户端（PyQt6 信号驱动）"""
    data_received = pyqtSignal(dict)
    connection_error = pyqtSignal(str)

    def __init__(self, url: str = f"{VITE_API_BASE_URL}/api/sse/stream"):
        super().__init__()
        self.url = url
        self._running = False
        self._thread = None

    def start(self):
        """启动 SSE 监听线程"""
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info(f"SSE 客户端已启动: {self.url}")

    def stop(self):
        """停止 SSE 监听"""
        self._running = False
        logger.info("SSE 客户端已停止")

    def _listen(self):
        """SSE 长连接监听（后台线程）"""
        while self._running:
            try:
                response = requests.get(
                    self.url,
                    headers={"Accept": "text/event-stream"},
                    stream=True,
                    timeout=(10, SSE_PUSH_INTERVAL + 5),
                )
                for line in response.iter_lines():
                    if not self._running:
                        break
                    if line and line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            self.data_received.emit(data)
                        except json.JSONDecodeError as e:
                            logger.warning(f"SSE 数据解析失败: {e}")

            except requests.RequestException as e:
                if self._running:
                    logger.error(f"SSE 连接异常: {e}")
                    self.connection_error.emit(str(e))
                    # 重连等待
                    import time
                    time.sleep(3)


class FloatingWindow(QMainWindow):
    """PyQt6 悬浮置顶窗口"""

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._init_sse()
        self._init_timer()

    def _init_ui(self):
        """初始化悬浮窗 UI"""
        self.setWindowTitle("Index-extraction 数据悬浮窗")
        self.setFixedSize(DESKTOP_WINDOW_WIDTH, DESKTOP_WINDOW_HEIGHT)

        # 置顶 + 无边框 + 透明背景
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(DESKTOP_WINDOW_OPACITY)

        # 移动到默认位置
        x, y = DESKTOP_WINDOW_POSITION
        self.move(QPoint(x, y))

        # 中央容器
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 30, 220);
                border-radius: 12px;
                color: #e0e0e0;
                font-family: 'SF Pro Display', 'Helvetica Neue', sans-serif;
            }
        """)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题栏（可拖拽移动）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("📊 数据提取结果")
        title_label.setFont(QFont("", 13, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                color: #888;
            }
            QPushButton:hover {
                color: #fff;
                background: rgba(255, 80, 80, 150);
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)

        layout.addWidget(title_bar)

        # 状态标签
        self.status_label = QLabel("等待数据连接...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding: 4px 0;")
        layout.addWidget(self.status_label)

        # 数据表格
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["等待数据..."])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(40, 40, 40, 180);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 6px;
                gridline-color: rgba(255, 255, 255, 10);
                font-size: 11px;
            }
            QHeaderView::section {
                background: rgba(60, 60, 60, 200);
                border: none;
                padding: 4px;
                font-weight: bold;
                color: #ccc;
            }
        """)
        layout.addWidget(self.table)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #888; font-size: 10px;")
        self.status_bar.showMessage("就绪")
        self.setStatusBar(self.status_bar)

        logger.info("悬浮窗 UI 初始化完成")

    def _init_sse(self):
        """初始化 SSE 数据流客户端"""
        self.sse_client = SSEClient()
        self.sse_client.data_received.connect(self._on_data_received)
        self.sse_client.connection_error.connect(self._on_connection_error)
        self.sse_client.start()

    def _init_timer(self):
        """初始化刷新定时器"""
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(DESKTOP_REFRESH_INTERVAL * 1000)

    def _on_data_received(self, data: dict):
        """处理 SSE 推送数据"""
        event_type = data.get("type", "unknown")
        payload = data.get("payload", {})

        if event_type == "update":
            rows = payload.get("data", [])
            if rows:
                self._update_table(rows)
            self.status_label.setText(
                f"✅ 已连接 | 数据: {len(rows)} 行 | "
                f"{datetime.now().strftime('%H:%M:%S')}"
            )
        elif event_type == "error":
            self.status_label.setText(f"❌ 错误: {payload.get('msg', '未知错误')}")
        elif event_type == "heartbeat":
            self.status_label.setText(f"💓 心跳 | {datetime.now().strftime('%H:%M:%S')}")

    def _on_connection_error(self, error_msg: str):
        """处理 SSE 连接错误"""
        self.status_label.setText(f"⚠️ 连接断开: {error_msg[:50]}...")

    def _update_table(self, rows: list):
        """更新悬浮窗表格数据"""
        if not rows:
            self.table.setRowCount(0)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["暂无数据"])
            return

        # 获取列名（从第一条数据提取）
        columns = list(rows[0].keys())
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            for col_idx, col_name in enumerate(columns):
                value = row_data.get(col_name, "")
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

        self.status_bar.showMessage(f"共 {len(rows)} 行数据")

    def _refresh_status(self):
        """定时刷新状态"""
        pass  # 由 SSE 事件驱动，此处仅做周期性检查

    # 支持拖拽移动窗口
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_start_position'):
            self.move(event.globalPosition().toPoint() - self._drag_start_position)
            event.accept()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.sse_client.stop()
        logger.info("悬浮窗已关闭")
        event.accept()


def main():
    """启动桌面悬浮窗"""
    app = QApplication(sys.argv)
    app.setApplicationName("Index-extraction 悬浮窗")

    # 系统托盘（可选）
    window = FloatingWindow()
    window.show()

    logger.info("桌面悬浮窗已启动")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
