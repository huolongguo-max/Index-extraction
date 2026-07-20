"""
Index-extraction 公共工具库（纯工具层，零业务逻辑）

模块清单：
  browser_utils    — Chrome 驱动管理 + Vue 动态页面等待
  xpath_utils      — 行列交叉 XPath 固定模板生成器
  storage_utils    — JSON 文件读写 + SQLite 迁移接口
  log_utils        — loguru 统一日志 + RPA 采集日志封装
  common_utils     — 数字清洗 + 异常重试装饰器

使用方式：
  from utils.xpath_utils import xp             # 始终可用（纯 Python）
  from utils.log_utils import get_logger        # 始终可用
  from utils.common_utils import clean_number   # 始终可用
  from utils.storage_utils import data_store    # 始终可用
  from utils.browser_utils import browser_manager  # 需 selenium + webdriver-manager
"""

# ---- 始终可用的模块 ----
from utils.log_utils import setup_logger, get_logger, RPALogger, timed, timed_decorator
from utils.xpath_utils import XPathBuilder, XPathValidator, xp, xpath_validator
from utils.storage_utils import (
    IStorage, JsonStorage, SqliteStorage,
    create_storage, data_store, rules_store,
)
from utils.common_utils import (
    clean_number, clean_number_batch, is_numeric,
    safe_int, safe_float, retry, retry_async,
    sanitize_cell, sanitize_row, sanitize_rows,
)

# ---- 可选模块（依赖 selenium / PyQt6，环境未安装时静默跳过） ----
try:
    from utils.browser_utils import BrowserManager, browser_manager
    __all_browser__ = ["BrowserManager", "browser_manager"]
except ImportError:
    __all_browser__ = []

__all__ = [
    # log
    "setup_logger", "get_logger", "RPALogger", "timed", "timed_decorator",
    # xpath
    "XPathBuilder", "XPathValidator", "xp", "xpath_validator",
    # storage
    "IStorage", "JsonStorage", "SqliteStorage",
    "create_storage", "data_store", "rules_store",
    # common
    "clean_number", "clean_number_batch", "is_numeric",
    "safe_int", "safe_float", "retry", "retry_async",
    "sanitize_cell", "sanitize_row", "sanitize_rows",
] + __all_browser__
