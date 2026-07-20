"""
API 层 Pydantic v2 请求/响应校验模型
严格禁止零散参数 — 所有接口入参通过 Pydantic 模型接收
"""

from typing import Optional
from pydantic import BaseModel, Field


# ================================================================
# 规则管理 — 请求模型
# ================================================================

class RuleCreateRequest(BaseModel):
    """新增规则请求"""
    rule_name: str = Field(..., min_length=1, max_length=128)
    target_url: str = Field(..., min_length=5)
    row_keyword: str = Field(..., min_length=1, max_length=256)
    target_headers: list[str] = Field(..., min_length=1)
    refresh_mode: str = Field(default="interval")
    table_type: str = Field(default="div")
    interval_seconds: int = Field(default=60, ge=5)
    enabled: bool = Field(default=True)
    auto_click_button: bool = Field(default=False)
    button_text: Optional[str] = Field(default=None)
    row_xpath: str = Field(default="//div[contains(@class, 'table-row')]")
    header_row_xpath: str = Field(default="//div[contains(@class, 'table-header')]")
    cell_tag: str = Field(default="div")
    cell_class: Optional[str] = Field(default=None)
    max_pages: int = Field(default=1, ge=1)


class RuleUpdateRequest(BaseModel):
    """编辑规则请求 — 所有字段可选"""
    rule_name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    target_url: Optional[str] = Field(default=None, min_length=5)
    row_keyword: Optional[str] = Field(default=None, min_length=1, max_length=256)
    target_headers: Optional[list[str]] = Field(default=None, min_length=1)
    refresh_mode: Optional[str] = Field(default=None)
    table_type: Optional[str] = Field(default=None)
    interval_seconds: Optional[int] = Field(default=None, ge=5)
    enabled: Optional[bool] = Field(default=None)
    auto_click_button: Optional[bool] = Field(default=None)
    button_text: Optional[str] = Field(default=None)
    row_xpath: Optional[str] = Field(default=None)
    header_row_xpath: Optional[str] = Field(default=None)
    cell_tag: Optional[str] = Field(default=None)
    cell_class: Optional[str] = Field(default=None)
    max_pages: Optional[int] = Field(default=None, ge=1)


class RuleIdRequest(BaseModel):
    """规则 ID 请求（用于启用/停用/删除/触发的路径参数 fallback）"""
    rule_id: str = Field(..., min_length=1)


# ================================================================
# 控制类 — 请求模型
# ================================================================

class BrowserModeRequest(BaseModel):
    """切换浏览器模式请求"""
    mode: str = Field(..., pattern="^(headless|gui)$")


class TriggerRequest(BaseModel):
    """手动触发采集请求"""
    rule_id: str = Field(..., min_length=1)


# ================================================================
# 数据查询 — 请求模型
# ================================================================

class LogQueryRequest(BaseModel):
    """日志查询请求"""
    rule_id: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
