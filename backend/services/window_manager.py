"""
桌面悬浮窗进程管理器
负责启动/停止 PyQt6 悬浮窗子进程，供 API 层调用
"""

import sys
import os
import subprocess
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.log_utils import get_logger

logger = get_logger()


class WindowManager:
    """悬浮窗子进程管理器（单例）"""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._started_at: float = 0.0

    @property
    def is_running(self) -> bool:
        with self._lock:
            if self._process is None:
                return False
            poll = self._process.poll()
            return poll is None  # None means still running

    @property
    def pid(self) -> int | None:
        with self._lock:
            return self._process.pid if self._process else None

    @property
    def uptime_seconds(self) -> float:
        if not self.is_running:
            return 0.0
        return time.time() - self._started_at

    def start(self) -> bool:
        """
        启动悬浮窗子进程

        Returns:
            True 启动成功，False 已在运行或启动失败
        """
        with self._lock:
            if self._process and self._process.poll() is None:
                logger.info("悬浮窗已在运行中")
                return True

            try:
                main_py = ROOT_DIR / "window" / "main.py"
                env = os.environ.copy()
                env["PYTHONPATH"] = str(ROOT_DIR)

                self._process = subprocess.Popen(
                    [sys.executable, str(main_py)],
                    cwd=str(ROOT_DIR),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._started_at = time.time()
                logger.info(f"悬浮窗已启动 (PID={self._process.pid})")
                return True

            except Exception as exc:
                logger.error(f"启动悬浮窗失败: {exc}")
                self._process = None
                return False

    def stop(self) -> bool:
        """
        停止悬浮窗子进程

        Returns:
            True 停止成功
        """
        with self._lock:
            if self._process is None:
                return True

            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=2)
                logger.info("悬浮窗已停止")
            except Exception as exc:
                logger.error(f"停止悬浮窗失败: {exc}")
            finally:
                self._process = None
                self._started_at = 0.0

        return True

    def restart(self) -> bool:
        self.stop()
        time.sleep(0.5)
        return self.start()


# 全局单例
window_manager = WindowManager()
