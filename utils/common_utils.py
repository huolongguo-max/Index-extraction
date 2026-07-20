"""
通用工具 — 数字清洗 + 异常重试 + 零业务逻辑

职责（纯工具层）：
  1. 数字清洗：去千分位逗号、中文数字、货币符号 → 标准 float / int
  2. 异常重试装饰器：可配置次数、间隔、指数退避、异常白名单
  3. 仅提供纯函数 / 装饰器，不触碰任何业务

可被 backend/、desktop/ 直接复用。
"""

import re
import time
import asyncio
from functools import wraps
from typing import Callable, Optional, Type, Union


# ================================================================
# 数字清洗
# ================================================================

# 匹配包含数字、千分位逗号、货币符号、中文数字的字符串
_NUM_PATTERN = re.compile(r'[\d,.\-+]+')

# 常见货币符号 & 单位前缀
_CURRENCY_SYMBOLS = r'[\$\€\¥\£\₹\₩\฿\₫\₪]'

# 不参与数字解析的纯文本（如 "暂无"、"N/A"）
_NON_NUMERIC_MARKERS = re.compile(
    r'^(?:—|-{1,3}|/|n/?a|none|暂无(?:数据)?|无(?:数据)?|空|null)$',
    re.IGNORECASE,
)


def clean_number(
    value: str,
    *,
    as_type: str = "auto",
    default=None,
) -> Union[int, float, str, None]:
    """
    清洗数字字符串 → 标准数值

    处理内容（按顺序）：
      1. 去中文数字前缀 / 后缀
      2. 去货币符号 ¥ $ € £
      3. 去千分位逗号 1,234,567 → 1234567
      4. 去度量单位 % ‰
      5. 识别正负号

    Args:
        value:    待清洗文本，如 "¥1,234.56万", "-5.6%", "1.2k"
        as_type:  "auto" 自动判断 int/float；"int" 强制整型；"float" 强制浮点
        default:  解析失败时返回的默认值

    Returns:
        int / float / default

    Examples:
        >>> clean_number("¥1,234.56")
        1234.56
        >>> clean_number("-3,000")
        -3000
        >>> clean_number("暂无数据", default=0)
        0
        >>> clean_number("1,234.56万")
        1234.56
        >>> clean_number("N/A", default=None)
        None
    """
    if value is None:
        return default

    text = str(value).strip()

    if not text or _NON_NUMERIC_MARKERS.match(text):
        return default

    # 1) 移除中文数字单位（万/亿/千/百/十）
    chinese_unit_scale = {
        "万": 10_000,
        "亿": 100_000_000,
        "千万": 10_000_000,
        "百万": 1_000_000,
        "十万": 100_000,
        "千": 1_000,
        "百": 100,
    }
    multiplier = 1
    for unit, scale in sorted(chinese_unit_scale.items(), key=lambda x: -len(x[0])):
        if unit in text:
            multiplier = scale
            text = text.replace(unit, "")
            break

    # 2) 取最后一个数字组（防止前缀文字干扰）
    match = re.findall(r'[\-\+]?[\d,]+(?:\.\d+)?', text)
    if not match:
        return default

    # 取匹配组中最长的（最可能是正经数值）
    num_str = max(match, key=len)

    # 3) 去千分位逗号
    num_str = num_str.replace(",", "")

    # 4) 转数值
    try:
        if "." in num_str:
            result = float(num_str) * multiplier
        else:
            result = int(num_str) * multiplier
    except (ValueError, OverflowError):
        return default

    # 5) 检查百分比符号
    if "%" in text or "％" in text:
        result = result / 100.0

    # 6) 类型控制
    if as_type == "int":
        return int(result)
    if as_type == "float":
        return float(result)
    # auto: 如果是整数则返回 int
    if isinstance(result, float) and result == int(result) and "." not in num_str:
        return int(result)
    return result


def clean_number_batch(
    values: list[str],
    *,
    as_type: str = "auto",
    default=0,
) -> list:
    """
    批量清洗数字

    Args:
        values: 待清洗文本列表
        as_type: "auto" | "int" | "float"
        default: 单条失败时的默认值

    Returns:
        list[Union[int, float]]
    """
    return [clean_number(v, as_type=as_type, default=default) for v in values]


def is_numeric(value: str) -> bool:
    """快速判断字符串是否可解析为数字"""
    result = clean_number(value, default=None)
    return result is not None and isinstance(result, (int, float))


# ================================================================
# 异常重试装饰器
# ================================================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    异常重试装饰器（同步版）

    用法:
        @retry(max_attempts=3, delay=1, backoff=2, exceptions=(TimeoutException,))
        def fetch_url(url):
            ...

    行为:
      - 第 1 次失败: 等待 1s
      - 第 2 次失败: 等待 2s (delay × backoff)
      - 第 3 次失败: 抛出异常

    Args:
        max_attempts:  最大尝试次数（含首次）
        delay:         首次重试间隔（秒）
        backoff:       退避乘数（≥ 1.0）
        exceptions:    触发重试的异常类型白名单
        on_retry:      重试回调 (attempt, exception, delay) -> None
    """
    if backoff < 1.0:
        raise ValueError("backoff 不能小于 1.0")
    if max_attempts < 1:
        raise ValueError("max_attempts 不能小于 1")

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from utils.log_utils import get_logger
            _log = get_logger()

            current_delay = delay
            last_exc = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        _log.error(
                            f"[RETRY:EXHAUSTED] {func.__name__} "
                            f"失败 {max_attempts}/{max_attempts} — {exc}"
                        )
                        raise

                    _log.warning(
                        f"[RETRY:{attempt}/{max_attempts}] {func.__name__} "
                        f"— {type(exc).__name__}: {exc} | "
                        f"等待 {current_delay:.1f}s"
                    )

                    if on_retry:
                        on_retry(attempt, exc, current_delay)

                    time.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不可达
            raise last_exc

        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    异常重试装饰器（异步版）

    用法:
        @retry_async(max_attempts=3, delay=1)
        async def fetch_async():
            ...
    """
    if backoff < 1.0:
        raise ValueError("backoff 不能小于 1.0")
    if max_attempts < 1:
        raise ValueError("max_attempts 不能小于 1")

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from utils.log_utils import get_logger
            _log = get_logger()

            current_delay = delay
            last_exc = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        _log.error(
                            f"[RETRY:EXHAUSTED] {func.__name__} "
                            f"失败 {max_attempts}/{max_attempts} — {exc}"
                        )
                        raise

                    _log.warning(
                        f"[RETRY:{attempt}/{max_attempts}] {func.__name__} "
                        f"— {type(exc).__name__}: {exc} | "
                        f"等待 {current_delay:.1f}s"
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            raise last_exc

        return wrapper
    return decorator


# ================================================================
# 便捷函数
# ================================================================

def safe_int(value, default: int = 0) -> int:
    """安全转 int（失败返回 default）"""
    result = clean_number(value, as_type="int", default=None)
    return result if result is not None else default


def safe_float(value, default: float = 0.0) -> float:
    """安全转 float（失败返回 default）"""
    result = clean_number(value, as_type="float", default=None)
    return result if result is not None else default


# ================================================================
# 数据消毒 — 确保前端/悬浮窗不会收到异常值导致展示错乱
# ================================================================

# 常见的"脏"值，应统一转为空字符串
_DIRTY_VALUES = frozenset({
    None, "None", "null", "NULL", "undefined",
    "NaN", "nan", "N/A", "n/a", "N/a",
    "—", "-", "--", "---",
    "暂无", "无", "空",
})

# 异常数字边界
_MAX_SAFE_DISPLAY = 9_999_999_999_999  # 超过此值视为异常
_MIN_SAFE_DISPLAY = -999_999_999_999


def sanitize_cell(value) -> str:
    """
    单个单元格值消毒 → 安全字符串

    处理:
      - None / NaN / "undefined" → ""
      - float('inf') → ""
      - 超长字符串截断
      - 异常大数 → ""
    """
    if value is None:
        return ""

    if isinstance(value, float):
        import math
        if math.isnan(value) or math.isinf(value):
            return ""
        if value > _MAX_SAFE_DISPLAY or value < _MIN_SAFE_DISPLAY:
            return ""

    if isinstance(value, str):
        stripped = value.strip()
        if stripped in _DIRTY_VALUES:
            return ""
        # 超长截断
        if len(stripped) > 1000:
            return stripped[:997] + "..."
        return stripped

    # int / bool / others → str
    s = str(value).strip()
    if s in _DIRTY_VALUES:
        return ""
    return s


def sanitize_row(row: dict) -> dict:
    """
    整行数据消毒

    确保每一列的值都是前端可直接展示的安全值（非 None、非 NaN）。
    """
    return {k: sanitize_cell(v) for k, v in row.items()}


def sanitize_rows(rows: list[dict]) -> list[dict]:
    """批量行消毒"""
    return [sanitize_row(r) for r in rows]
