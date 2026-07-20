"""
RPA 数据抓取接口
提供抓取任务创建、状态查询、结果获取、XPath 规则管理
严格 Restful 规范：GET 查、POST 新增、PUT 修改、DELETE 删除
"""

from fastapi import APIRouter, Query
from backend.core.response import resp
from backend.models.schemas import (
    RPATaskRequest,
    RPATaskStatusRequest,
    RPATaskResult,
)

router = APIRouter(prefix="/api/rpa", tags=["RPA 数据抓取"])


@router.post("/fetch", summary="创建 RPA 抓取任务")
async def create_fetch_task(req: RPATaskRequest):
    """
    创建 RPA 数据抓取任务
    - url: 目标网页地址
    - rule_name: XPath 规则名称
    - max_rows: 最大抓取行数（可选）
    - max_pages: 最大翻页数（可选）
    """
    # TODO: 调用 RPA 抓取服务
    return resp.success(
        data={"task_id": "placeholder-task-id"},
        msg="抓取任务已创建",
    )


@router.get("/task/{task_id}", summary="查询抓取任务状态")
async def get_task_status(task_id: str):
    """
    根据任务 ID 查询抓取状态和结果
    """
    # TODO: 从缓存/数据库读取任务状态
    return resp.success(
        data={
            "task_id": task_id,
            "status": "pending",
            "data": [],
        },
        msg="查询成功",
    )


@router.get("/tasks", summary="获取所有抓取任务列表")
async def list_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
):
    """
    分页获取历史抓取任务列表
    """
    # TODO: 从缓存/数据库读取
    return resp.success(
        data={
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
        },
        msg="查询成功",
    )


@router.delete("/task/{task_id}", summary="删除抓取任务记录")
async def delete_task(task_id: str):
    """
    删除指定抓取任务及其缓存数据
    """
    # TODO: 清理任务记录和缓存
    return resp.success(msg=f"任务 {task_id} 已删除")


@router.get("/rules", summary="获取 XPath 抓取规则列表")
async def get_xpath_rules():
    """
    获取所有已配置的 XPath 抓取规则
    """
    # TODO: 从 xpath_rules.json 加载
    return resp.success(data=[], msg="查询成功")


@router.put("/rules", summary="更新 XPath 抓取规则")
async def update_xpath_rule():
    """
    更新或新增 XPath 抓取规则
    """
    # TODO: 写入 xpath_rules.json
    return resp.success(msg="规则已更新")
