"""
规则管理接口 — Restful CRUD + 启用/停用

端点:
  POST   /api/rules                 新增规则
  GET    /api/rules                 规则列表（支持 ?enabled=true/false 过滤）
  GET    /api/rules/{rule_id}       单条详情
  PUT    /api/rules/{rule_id}       编辑规则
  DELETE /api/rules/{rule_id}       删除规则
  POST   /api/rules/{rule_id}/enable    启用
  POST   /api/rules/{rule_id}/disable   停用
  POST   /api/rules/{rule_id}/toggle    切换启用/停用

接口层与业务层严格分离 — 所有逻辑委托至 rule_manager。
"""

from fastapi import APIRouter, Query, HTTPException

from backend.core.response import resp
from backend.api.schemas import RuleCreateRequest, RuleUpdateRequest
from backend.models.rpa_models import ScrapeRule
from backend.services.rpa.rule_manager import rule_manager
from backend.services.rpa import scheduler

router = APIRouter(prefix="/api/rules", tags=["规则管理"])


# ================================================================
# 新增
# ================================================================

@router.post("", summary="新增抓取规则", status_code=201)
async def create_rule(req: RuleCreateRequest):
    """
    新增一条抓取规则，自动生成 rule_id。

    必填: rule_name, target_url, row_keyword, target_headers
    可选: interval_seconds, enabled, auto_click_button, button_text ...
    """
    try:
        rule = ScrapeRule(**req.model_dump())
        created = rule_manager.add(rule)

        # 通知调度器
        if scheduler:
            scheduler.on_rule_added(created)

        return resp.success(
            data=created.model_dump(),
            msg=f"规则「{created.rule_name}」已创建",
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        return resp.error(msg=str(exc))


# ================================================================
# 列表
# ================================================================

@router.get("", summary="规则列表")
async def list_rules(enabled: str | None = Query(default=None, pattern="^(true|false)$")):
    """
    获取规则列表，支持 ?enabled=true 仅返回已启用规则
    """
    if enabled == "true":
        rules = rule_manager.list_enabled()
    elif enabled == "false":
        rules = rule_manager.list_disabled()
    else:
        rules = rule_manager.list_all()

    return resp.success(
        data={
            "items": [r.model_dump() for r in rules],
            "total": len(rules),
        },
        msg=f"共 {len(rules)} 条规则",
    )


# ================================================================
# 单条
# ================================================================

@router.get("/{rule_id}", summary="规则详情")
async def get_rule(rule_id: str):
    rule = rule_manager.get(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    return resp.success(data=rule.model_dump(), msg="查询成功")


# ================================================================
# 编辑
# ================================================================

@router.put("/{rule_id}", summary="编辑规则")
async def update_rule(rule_id: str, req: RuleUpdateRequest):
    """
    部分更新：只传需要修改的字段。

    示例: PUT /api/rules/abc123  {"interval_seconds": 30, "enabled": false}
    """
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="请至少提供一个要更新的字段")

    try:
        updated = rule_manager.update(rule_id, updates)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 通知调度器
    if scheduler:
        scheduler.on_rule_updated(rule_id)

    return resp.success(data=updated.model_dump(), msg="规则已更新")


# ================================================================
# 删除
# ================================================================

@router.delete("/{rule_id}", summary="删除规则")
async def delete_rule(rule_id: str):
    if rule_manager.get(rule_id) is None:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    rule_manager.remove(rule_id)

    # 通知调度器
    if scheduler:
        scheduler.on_rule_removed(rule_id)

    return resp.success(msg=f"规则 {rule_id} 已删除")


# ================================================================
# 启用 / 停用 / 切换
# ================================================================

@router.post("/{rule_id}/enable", summary="启用规则")
async def enable_rule(rule_id: str):
    try:
        rule = rule_manager.enable(rule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    if scheduler:
        scheduler.on_rule_enabled(rule_id)

    return resp.success(data=rule.model_dump(), msg=f"规则「{rule.rule_name}」已启用")


@router.post("/{rule_id}/disable", summary="停用规则")
async def disable_rule(rule_id: str):
    try:
        rule = rule_manager.disable(rule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    if scheduler:
        scheduler.on_rule_disabled(rule_id)

    return resp.success(data=rule.model_dump(), msg=f"规则「{rule.rule_name}」已停用")


@router.post("/{rule_id}/toggle", summary="切换启用/停用")
async def toggle_rule(rule_id: str):
    try:
        rule = rule_manager.toggle(rule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    if scheduler:
        scheduler.on_rule_updated(rule_id)

    status_text = "启用" if rule.enabled else "停用"
    return resp.success(data=rule.model_dump(), msg=f"规则「{rule.rule_name}」已{status_text}")
