"""
数据查询接口 — 最新数据、历史记录、运行日志

端点:
  GET  /api/data/latest?rule_id=xxx        最新采集数据
  GET  /api/data/history?rule_id=xxx       历史采集记录
  GET  /api/data/logs?rule_id=xxx&page=1   运行日志列表

接口层与业务层严格分离 — 只读，不改动任何业务状态。
"""

from fastapi import APIRouter, Query, HTTPException

from backend.core.response import resp
from backend.services.rpa.rule_manager import rule_manager
from backend.services.rpa import scheduler
from utils.storage_utils import data_store
from utils.log_utils import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/data", tags=["数据查询"])


# ================================================================
# 最新采集数据
# ================================================================

@router.get("/latest", summary="最新采集数据")
async def get_latest_data(rule_id: str | None = Query(default=None)):
    """
    获取最新采集数据

    - ?rule_id=xxx: 查询指定规则的最新数据
    - 无参数: 返回所有规则的最新数据
    """
    if rule_id:
        cache_key = f"rule_{rule_id}_latest"
        cached = data_store.read(cache_key)
        if not cached:
            return resp.success(
                data={"rule_id": rule_id, "rows": [], "row_count": 0},
                msg="暂无数据",
            )
        return resp.success(data=cached, msg="查询成功")

    # 无 rule_id → 返回所有规则的最新数据
    all_data = []
    for rule in rule_manager.list_all():
        cache_key = f"rule_{rule.rule_id}_latest"
        cached = data_store.read(cache_key)
        if cached:
            all_data.append({
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "row_count": cached.get("row_count", 0),
                "cached_at": cached.get("cached_at"),
            })

    return resp.success(
        data={"items": all_data, "total": len(all_data)},
        msg=f"共 {len(all_data)} 条规则有缓存数据",
    )


# ================================================================
# 历史采集记录
# ================================================================

@router.get("/history", summary="历史采集记录")
async def get_history(
    rule_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    获取历史采集记录

    数据来源：规则的 last_run_at / last_status / last_row_count
    以及缓存中存储的最近一次完整数据。
    """
    all_rules = rule_manager.list_all()

    # 过滤
    if rule_id:
        all_rules = [r for r in all_rules if r.rule_id == rule_id]
        if not all_rules:
            raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    # 构建记录列表
    records = []
    for rule in all_rules:
        cache_key = f"rule_{rule.rule_id}_latest"
        cached = data_store.read(cache_key)

        records.append({
            "rule_id": rule.rule_id,
            "rule_name": rule.rule_name,
            "target_url": rule.target_url,
            "last_run_at": rule.last_run_at.isoformat() if rule.last_run_at else None,
            "last_status": rule.last_status,
            "last_row_count": rule.last_row_count,
            "last_error": rule.last_error,
            "cached_at": cached.get("cached_at") if cached else None,
        })

    # 分页
    total = len(records)
    start = (page - 1) * page_size
    end = start + page_size
    paged = records[start:end]

    return resp.success(
        data={
            "items": paged,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
        msg="查询成功",
    )


# ================================================================
# 运行日志列表
# ================================================================

@router.get("/logs", summary="运行日志列表")
async def get_logs(
    rule_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """
    获取运行日志摘要

    基于规则管理器中的运行时元数据构建日志记录。
    后续可扩展为读取 loguru 日志文件进行全文检索。
    """
    all_rules = rule_manager.list_all()

    if rule_id:
        all_rules = [r for r in all_rules if r.rule_id == rule_id]

    logs = []
    for rule in all_rules:
        if rule.last_run_at:  # 只记录有运行历史的
            logs.append({
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "run_at": rule.last_run_at.isoformat() if rule.last_run_at else None,
                "status": rule.last_status,
                "row_count": rule.last_row_count,
                "error": rule.last_error,
            })

    # 按时间倒序
    logs.sort(key=lambda x: x.get("run_at") or "", reverse=True)

    total = len(logs)
    start = (page - 1) * page_size
    end = start + page_size

    return resp.success(
        data={
            "items": logs[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
        msg=f"共 {total} 条运行日志",
    )


# ================================================================
# 调度器快照
# ================================================================

@router.get("/status", summary="调度器运行状态")
async def get_scheduler_status():
    """获取后台调度器运行快照"""
    if scheduler is None:
        return resp.success(
            data={"active": False, "reason": "采集引擎未安装（缺少 selenium）"},
            msg="调度器不可用",
        )

    snap = scheduler.snapshot()
    return resp.success(data=snap.model_dump(), msg="查询成功")
