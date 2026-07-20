"""
日志工具 — 基于 loguru 统一日志格式

职责（纯工具层）：
  1. 初始化 loguru 全局 logger（控制台彩色 + 文件持久化）
  2. 统一日志格式：时间 | 级别 | 模块:函数:行号 | 消息
  3. 自动记录采集成败、异常原因、运行耗时
  4. 错误日志单独归档，支持自动 rotation / retention

可被 backend/、desktop/ 直接复用。
"""

import sys
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable

from loguru import logger

from config.settings import (
    LOG_LEVEL,
    LOG_DIR,
    LOG_MAX_SIZE,
    LOG_RETENTION_DAYS,
)

# ---- 控制台 / 文件日志格式 ----
_FMT_CONSOLE = (
    "<green>[{time:HH:mm:ss}]</green> "
    "<level>[{level:^7}]</level> "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)

_FMT_FILE = (
    "[{time:YYYY-MM-DD HH:mm:ss.SSS}] "
    "[{level:^7}] "
    "[{module}:{function}:{line}] "
    "{message}"
)

# 标记是否已初始化（避免重复配置）
_initialized = False


# ================================================================
# 初始化
# ================================================================

def setup_logger(
    name: str = "index_extraction",
    log_level: str = LOG_LEVEL,
    log_dir: str = LOG_DIR,
) -> None:
    """
    初始化 loguru 全局日志器

    输出目标:
      1. 控制台 stderr — 彩色、简洁
      2. 全量日志文件 — 默认 10MB rotation / 7 天保留
      3. 错误日志文件 — ERROR 级别独立归档，30 天保留

    Args:
        name:      模块名（rpa / api / desktop / window）
        log_level: DEBUG | INFO | WARNING | ERROR
        log_dir:   日志存储目录
    """
    global _initialized
    if _initialized:
        return

    # 清空默认 handler
    logger.remove()

    # ---- 控制台 ----
    logger.add(
        sys.stderr,
        format=_FMT_CONSOLE,
        level=log_level,
        colorize=True,
    )

    # ---- 全量文件 ----
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path / f"{name}.log",
        format=_FMT_FILE,
        level=log_level,
        rotation=f"{LOG_MAX_SIZE} MB",
        retention=f"{LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
    )

    # ---- 错误文件 ----
    logger.add(
        log_path / f"{name}_error.log",
        format=_FMT_FILE,
        level="ERROR",
        rotation=f"{LOG_MAX_SIZE} MB",
        retention=f"{LOG_RETENTION_DAYS * 4} days",
        compression="zip",
        encoding="utf-8",
    )

    # ---- 运行日志（仅 INFO，正常审计追踪） ----
    logger.add(
        log_path / f"{name}_ops.log",
        format=_FMT_FILE,
        level="INFO",
        rotation=f"{LOG_MAX_SIZE * 2} MB",
        retention=f"{LOG_RETENTION_DAYS} days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: record["level"].name == "INFO",
    )

    _initialized = True
    logger.info(f"日志系统就绪 | 模块: {name} | 级别: {log_level} | 路径: {log_path}")


def get_logger():
    """获取全局 logger 实例"""
    return logger


# ================================================================
# RPA 专用日志记录器 — 封装采集成败 / 异常 / 耗时
# ================================================================

class RPALogger:
    """
    RPA 采集日志统一封装

    记录维度:
      - 采集成功 → INFO（含耗时、行数）
      - 采集失败 → ERROR（含异常原因）
      - 浏览器异常 → ERROR
      - 接口报错 → ERROR
    """

    @staticmethod
    def fetch_success(url: str, row_count: int, elapsed: float, rule_name: str = ""):
        """采集成功日志"""
        logger.info(
            f"[RPA:OK] url={url} | rule={rule_name} | "
            f"rows={row_count} | elapsed={elapsed:.2f}s"
        )

    @staticmethod
    def fetch_failure(url: str, reason: str, rule_name: str = ""):
        """采集失败日志"""
        logger.error(
            f"[RPA:FAIL] url={url} | rule={rule_name} | reason={reason}"
        )

    @staticmethod
    def browser_error(context: str, exc: Exception):
        """浏览器异常日志"""
        logger.error(f"[BROWSER] {context} — {type(exc).__name__}: {exc}")

    @staticmethod
    def api_error(endpoint: str, status_code: int, detail: str = ""):
        """接口报错日志"""
        logger.error(
            f"[API:{status_code}] {endpoint} — {detail}"
        )

    @staticmethod
    def xpath_not_found(xpath: str, url: str = ""):
        """XPath 未匹配到元素"""
        logger.warning(f"[XPATH:NOMATCH] url={url} | xpath={xpath}")


# ================================================================
# 耗时上下文管理器（with 块自动计时）
# ================================================================

@contextmanager
def timed(operation: str = "操作"):
    """
    耗时统计上下文管理器

    用法:
        with timed("表格抓取"):
            do_rpa_fetch()

        # 自动输出: [TIMED] 表格抓取 — 2.35s
    """
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info(f"[TIMED] {operation} — {elapsed:.2f}s")


def timed_decorator(operation: str = ""):
    """
    耗时统计装饰器

    用法:
        @timed_decorator("数据提取")
        def extract_data(url):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            label = operation or func.__name__
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(f"[TIMED] {label} — {elapsed:.2f}s")
                return result
            except Exception:
                elapsed = time.perf_counter() - start
                logger.error(f"[TIMED:FAIL] {label} — {elapsed:.2f}s")
                raise
        return wrapper
    return decorator


# ================================================================
# 预初始化（import 时自动配置）
# ================================================================

setup_logger()
