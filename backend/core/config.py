"""
FastAPI 后端配置
从全局 config/settings.py 加载，统一管理所有后端配置项
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保跨模块导入
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import (
    APP_NAME,
    APP_ENV,
    DEBUG,
    BACKEND_PORT,
    BACKEND_HOST,
    BACKEND_RELOAD,
    BACKEND_WORKERS,
    RPA_MAX_RETRIES,
    RPA_RETRY_INTERVAL,
    RPA_XPATH_CONFIG_PATH,
    RPA_FETCH_TIMEOUT,
    RPA_CACHE_FILE_PATH,
    SSE_HEARTBEAT_INTERVAL,
    SSE_PUSH_INTERVAL,
)

__all__ = [
    "APP_NAME",
    "APP_ENV",
    "DEBUG",
    "BACKEND_PORT",
    "BACKEND_HOST",
    "BACKEND_RELOAD",
    "BACKEND_WORKERS",
    "RPA_MAX_RETRIES",
    "RPA_RETRY_INTERVAL",
    "RPA_XPATH_CONFIG_PATH",
    "RPA_FETCH_TIMEOUT",
    "RPA_CACHE_FILE_PATH",
    "SSE_HEARTBEAT_INTERVAL",
    "SSE_PUSH_INTERVAL",
]
