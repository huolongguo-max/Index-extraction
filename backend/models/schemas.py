"""
Pydantic v2 数据模型定义
严格禁止零散参数定义，所有接口参数统一使用 Pydantic 模型接收
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ==================== RPA 抓取请求模型 ====================

class RPATaskRequest(BaseModel):
    """RPA 抓取任务请求"""
    url: str = Field(..., description="目标网页地址")
    rule_name: str = Field(..., description="XPath 规则名称（对应 xpath_rules.json 中的 rule.name）")
    max_rows: Optional[int] = Field(default=None, ge=1, description="最大抓取行数，留空则全部抓取")
    max_pages: Optional[int] = Field(default=None, ge=1, description="最大翻页数，留空则使用规则配置")
    extra_headers: Optional[dict[str, str]] = Field(default=None, description="自定义请求头")


class RPATaskStatusRequest(BaseModel):
    """RPA 任务状态查询"""
    task_id: str = Field(..., description="任务唯一标识")


# ==================== 浏览器控制请求模型 ====================

class BrowserNavigateRequest(BaseModel):
    """浏览器导航请求"""
    url: str = Field(..., description="目标 URL")


class BrowserExecuteRequest(BaseModel):
    """浏览器执行脚本请求"""
    script: str = Field(..., description="JavaScript 代码")


# ==================== 数据缓存请求模型 ====================

class CacheQueryRequest(BaseModel):
    """缓存数据查询"""
    task_id: Optional[str] = Field(default=None, description="任务 ID")
    rule_name: Optional[str] = Field(default=None, description="规则名称")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


# ==================== RPA 响应数据模型 ====================

class TableCellData(BaseModel):
    """表格单元格数据"""
    row_index: int = Field(..., description="行号")
    col_name: str = Field(..., description="列名")
    value: Any = Field(default=None, description="单元格值")


class TableRowData(BaseModel):
    """表格行数据"""
    row_index: int = Field(..., description="行号")
    cells: dict[str, Any] = Field(default_factory=dict, description="该行所有列数据 {列名: 值}")


class RPATaskResult(BaseModel):
    """RPA 任务结果"""
    task_id: str = Field(..., description="任务 ID")
    status: str = Field(..., description="状态: pending / running / completed / failed")
    url: str = Field(..., description="目标 URL")
    rule_name: str = Field(..., description="使用的规则名称")
    total_rows: int = Field(default=0, description="总行数")
    total_pages: int = Field(default=0, description="总页数")
    data: list[dict[str, Any]] = Field(default_factory=list, description="抓取数据")
    error_msg: Optional[str] = Field(default=None, description="错误信息")
    created_at: Optional[datetime] = Field(default=None, description="任务创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="任务完成时间")


# ==================== XPath 规则模型 ====================

class XPathColumnRule(BaseModel):
    """XPath 列规则"""
    name: str = Field(..., description="列名")
    header_xpath: str = Field(..., description="表头 XPath")
    cell_xpath_template: str = Field(..., description="单元格 XPath 模板")
    data_type: str = Field(default="string", description="数据类型: string | number | date")


class XPathRule(BaseModel):
    """XPath 抓取规则"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(default=None, description="规则描述")
    url_pattern: str = Field(..., description="URL 匹配模式")
    table_container: str = Field(..., description="表格容器 XPath")
    row_xpath: str = Field(..., description="行 XPath")
    columns: list[XPathColumnRule] = Field(..., description="列规则列表")
    pagination: Optional[dict] = Field(default=None, description="翻页配置")


# ==================== 通用分页模型 ====================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: list[Any] = Field(default_factory=list, description="数据项")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="当前页")
    page_size: int = Field(default=20, description="每页条数")
    total_pages: int = Field(default=0, description="总页数")
