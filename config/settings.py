"""
全局配置加载器
基于 python-dotenv 加载 .env 文件，统一管理所有配置项
禁止在业务代码中硬编码任何魔法数字、URL、超时时间
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# 根据环境变量加载对应 .env 文件
APP_ENV = os.getenv("APP_ENV", "development")
env_file_map = {
    "development": ROOT_DIR / ".env.development",
    "production": ROOT_DIR / ".env.production",
}
env_file = env_file_map.get(APP_ENV, ROOT_DIR / ".env.development")
load_dotenv(env_file, override=True)


def get_env(key: str, default=None, cast_type=None):
    """从环境变量获取配置值，支持类型转换"""
    value = os.getenv(key, default)
    if cast_type and value is not None:
        if cast_type == bool:
            return str(value).lower() in ("true", "1", "yes")
        return cast_type(value)
    return value


# ==================== 应用配置 ====================
APP_NAME = get_env("APP_NAME", "Index-extraction")
APP_ENV = get_env("APP_ENV", "development")
DEBUG = get_env("DEBUG", "false", bool)

# ==================== 前端配置 ====================
VITE_DEV_PORT = get_env("VITE_DEV_PORT", "5173", int)
VITE_DEV_HOST = get_env("VITE_DEV_HOST", "localhost")
VITE_API_BASE_URL = get_env("VITE_API_BASE_URL", "http://localhost:18000")

# ==================== 后端配置 ====================
BACKEND_PORT = get_env("BACKEND_PORT", "18000", int)
BACKEND_HOST = get_env("BACKEND_HOST", "0.0.0.0")
BACKEND_RELOAD = get_env("BACKEND_RELOAD", "true", bool)
BACKEND_WORKERS = get_env("BACKEND_WORKERS", "4", int)

# ==================== Chrome 浏览器配置 ====================
CHROME_MODE = get_env("CHROME_MODE", "headless")
CHROME_BINARY_PATH = get_env("CHROME_BINARY_PATH", "")
CHROME_PAGE_LOAD_TIMEOUT = get_env("CHROME_PAGE_LOAD_TIMEOUT", "30", int)
CHROME_ELEMENT_TIMEOUT = get_env("CHROME_ELEMENT_TIMEOUT", "10", int)
CHROME_WINDOW_SIZE = get_env("CHROME_WINDOW_SIZE", "1920,1080")
CHROME_CACHE_DIR = get_env("CHROME_CACHE_DIR", "./browser-cache")
CHROME_DISABLE_IMAGES = get_env("CHROME_DISABLE_IMAGES", "true", bool)

# ==================== RPA 抓取配置 ====================
RPA_MAX_RETRIES = get_env("RPA_MAX_RETRIES", "3", int)
RPA_RETRY_INTERVAL = get_env("RPA_RETRY_INTERVAL", "2", int)
RPA_XPATH_CONFIG_PATH = get_env("RPA_XPATH_CONFIG_PATH", "./config/xpath_rules.json")
RPA_FETCH_TIMEOUT = get_env("RPA_FETCH_TIMEOUT", "60", int)
RPA_CACHE_FILE_PATH = get_env("RPA_CACHE_FILE_PATH", "./static/cache/table_data.json")

# ==================== SSE 配置 ====================
SSE_HEARTBEAT_INTERVAL = get_env("SSE_HEARTBEAT_INTERVAL", "15", int)
SSE_PUSH_INTERVAL = get_env("SSE_PUSH_INTERVAL", "5", int)

# ==================== 桌面悬浮窗配置 ====================
DESKTOP_WINDOW_WIDTH = get_env("DESKTOP_WINDOW_WIDTH", "400", int)
DESKTOP_WINDOW_HEIGHT = get_env("DESKTOP_WINDOW_HEIGHT", "600", int)
# 解析位置坐标 "x,y"
_position = get_env("DESKTOP_WINDOW_POSITION", "100,100")
DESKTOP_WINDOW_POSITION = tuple(int(i) for i in _position.split(",")) if _position else (100, 100)
DESKTOP_WINDOW_OPACITY = get_env("DESKTOP_WINDOW_OPACITY", "0.95", float)
DESKTOP_REFRESH_INTERVAL = get_env("DESKTOP_REFRESH_INTERVAL", "3", int)

# ==================== 日志配置 ====================
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
LOG_DIR = get_env("LOG_DIR", "./logs")
LOG_MAX_SIZE = get_env("LOG_MAX_SIZE", "10", int)
LOG_RETENTION_DAYS = get_env("LOG_RETENTION_DAYS", "7", int)
