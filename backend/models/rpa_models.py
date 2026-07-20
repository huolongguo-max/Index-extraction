"""
RPA 抓取规则 Pydantic v2 数据模型
严格禁止零散参数定义，所有字段通过 Pydantic 模型统一校验
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


# ================================================================
# 抓取规则模型（核心）
# ================================================================

class ScrapeRule(BaseModel):
    """
    单条抓取规则 — 全生命周期独立管理

    固定字段：
      - target_url:         目标网页地址
      - row_keyword:        行关键词（用于定位目标行）
      - target_headers:     待采集表头列表（列名集合）
      - interval_seconds:   刷新间隔秒数
      - auto_click_button:  是否需要自动点击按钮（可选配置按钮文字）
      - enabled:            启用/停用开关
    """

    # ---- 身份标识 ----
    rule_id: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="规则唯一标识",
    )
    rule_name: str = Field(
        ..., min_length=1, max_length=128,
        description="规则名称（人类可读）",
    )

    # ---- 目标 & 定位 ----
    target_url: str = Field(
        ..., min_length=5,
        description="目标网页地址",
    )
    row_keyword: str = Field(
        ..., min_length=1, max_length=256,
        description="行关键词（用于在表格中定位目标行，例如公司名/产品名）",
    )
    target_headers: list[str] = Field(
        ..., min_length=1,
        description="待采集表头列表（列名，如 ['金额', '日期', '状态']）",
    )

    # ---- 表格结构类型 ----
    table_type: str = Field(
        default="div",
        description="表格结构类型: div=DIY结构, table=标准HTML表格",
    )

    # ---- 可选 XPath 容器自定义 ----
    row_xpath: str = Field(
        default="//div[contains(@class, 'table-row')]",
        description="行容器 XPath 基础表达式",
    )
    header_row_xpath: str = Field(
        default="//div[contains(@class, 'table-header')]",
        description="表头行容器 XPath",
    )
    cell_tag: str = Field(
        default="div",
        description="单元格标签名",
    )
    cell_class: Optional[str] = Field(
        default=None,
        description="单元格 CSS class（可选，用于 contains(@class, ...) 定位）",
    )

    # ---- 调度参数 ----
    refresh_mode: str = Field(
        default="interval",
        description="刷新模式: interval=定时刷新, manual=手动刷新",
    )
    interval_seconds: int = Field(
        default=60, ge=5,
        description="刷新间隔（秒），仅 refresh_mode=interval 时生效",
    )
    enabled: bool = Field(
        default=True,
        description="是否启用此规则",
    )

    # ---- 交互参数 ----
    auto_click_button: bool = Field(
        default=False,
        description="是否在页面加载后自动点击指定按钮",
    )
    button_text: Optional[str] = Field(
        default=None,
        description="自动点击的按钮文字（auto_click_button=True 时必填）",
    )

    # ---- 翻页 ----
    max_pages: int = Field(
        default=1, ge=1,
        description="最大翻页数，1 = 仅首页",
    )

    # ---- 运行时元数据（由调度器/采集器维护，用户不直接设置） ----
    last_run_at: Optional[datetime] = Field(default=None, description="上次执行时间")
    last_status: Optional[str] = Field(default=None, description="上次执行状态: ok / fail")
    last_row_count: int = Field(default=0, description="上次采集行数")
    last_error: Optional[str] = Field(default=None, description="上次错误信息")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="规则创建时间",
    )

    @field_validator("button_text")
    @classmethod
    def check_button_text(cls, v, info):
        """auto_click_button=True 时 button_text 不能为空"""
        if info.data.get("auto_click_button") and not v:
            raise ValueError("auto_click_button=True 时 button_text 不能为空")
        return v

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("target_url 必须以 http:// 或 https:// 开头")
        # 基本的 URL 格式检查
        if len(v) < 10 or "." not in v.split("://", 1)[-1]:
            raise ValueError("target_url 格式无效，请提供完整网址")
        return v

    @field_validator("row_keyword")
    @classmethod
    def validate_keyword(cls, v):
        """禁止包含 XPath 分隔符的 keyword（会导致表达式解析异常）"""
        dangerous = ("'", '"', "//", "[", "]")
        for ch in dangerous:
            if ch in v:
                raise ValueError(
                    f"row_keyword 不能包含 '{ch}' 字符（会导致 XPath 解析异常），"
                    f"请简化关键词"
                )
        return v.strip()

    @field_validator("target_headers")
    @classmethod
    def validate_headers(cls, v):
        """表头列表校验"""
        if not v:
            raise ValueError("target_headers 不能为空")
        # 去重警告（不阻止，只去重）
        seen = set()
        deduped = []
        for h in v:
            h = h.strip()
            if h and h not in seen:
                seen.add(h)
                deduped.append(h)
        if len(deduped) < len(v):
            # 有重复 — 自动去重
            pass
        if not deduped:
            raise ValueError("target_headers 去重后为空")
        return deduped

    @field_validator("table_type")
    @classmethod
    def validate_table_type(cls, v):
        if v not in ("div", "table"):
            raise ValueError("table_type 必须为 div 或 table")
        return v

    @field_validator("refresh_mode")
    @classmethod
    def validate_refresh_mode(cls, v):
        if v not in ("interval", "manual"):
            raise ValueError("refresh_mode 必须为 interval 或 manual")
        return v

    @field_validator("interval_seconds")
    @classmethod
    def validate_interval(cls, v):
        """刷新间隔合理性检查"""
        if v < 5:
            raise ValueError("interval_seconds 不能小于 5 秒（过于频繁会触发反爬）")
        if v > 86400:
            raise ValueError("interval_seconds 不能超过 86400 秒（24小时）")
        return v


# ================================================================
# 采集结果模型
# ================================================================

class ScrapeResult(BaseModel):
    """单次采集结果"""
    rule_id: str
    rule_name: str
    target_url: str
    status: str = "ok"           # ok | fail
    row_count: int = 0
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    debug_log: list[str] = Field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    elapsed_seconds: float = 0.0


# ================================================================
# 运行时快照（供调度器监控）
# ================================================================

class SchedulerSnapshot(BaseModel):
    """调度器运行时快照"""
    active_rules: int = 0
    running_tasks: int = 0
    total_runs: int = 0
    total_ok: int = 0
    total_fail: int = 0
    rules_detail: list[dict[str, Any]] = Field(default_factory=list)
    uptime_seconds: float = 0.0
