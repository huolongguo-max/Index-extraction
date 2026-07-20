"""
Pydantic v2 数据模型模块 - 统一管理所有请求/响应 Schema
"""

from backend.models.rpa_models import (
    ScrapeRule,
    ScrapeResult,
    SchedulerSnapshot,
)
from backend.models.schemas import (
    RPATaskRequest,
    RPATaskStatusRequest,
    RPATaskResult,
    BrowserNavigateRequest,
    BrowserExecuteRequest,
    CacheQueryRequest,
    TableCellData,
    TableRowData,
    XPathColumnRule,
    XPathRule,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # RPA 业务模型
    "ScrapeRule",
    "ScrapeResult",
    "SchedulerSnapshot",
    # 请求/响应模型
    "RPATaskRequest",
    "RPATaskStatusRequest",
    "RPATaskResult",
    "BrowserNavigateRequest",
    "BrowserExecuteRequest",
    "CacheQueryRequest",
    "TableCellData",
    "TableRowData",
    "XPathColumnRule",
    "XPathRule",
    "PaginationParams",
    "PaginatedResponse",
]
