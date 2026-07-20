"""
Index-extraction Apple 玻璃态悬浮窗 — 启动入口

用法:
    python window/main.py
    python -m window.main

行为:
  - 关闭悬浮窗 → 隐藏到系统托盘（采集服务继续运行）
  - 右键托盘 → 退出程序 才真正停止
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import QApplication

from config.settings import APP_NAME
from window.floating_window import FloatingWindow
from utils.log_utils import setup_logger, get_logger


def main():
    setup_logger(name="window")
    logger = get_logger()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，退到托盘

    window = FloatingWindow()
    window.show()

    logger.info("🚀 悬浮窗 v2.0 已启动（关闭窗口将隐藏到托盘）")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
