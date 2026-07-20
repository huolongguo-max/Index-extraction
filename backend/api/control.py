"""
控制接口 — 手动触发 / 全局调度 / 浏览器模式

端点:
  POST /api/control/trigger/{rule_id}     手动立即执行单次采集
  POST /api/control/scheduler/start       全局启动调度
  POST /api/control/scheduler/stop        全局停止调度
  POST /api/control/browser/mode          切换浏览器显示模式 (headless/gui)

接口层与业务层严格分离 — 所有逻辑委托至 scheduler / scraper / browser_manager。
"""

from fastapi import APIRouter, HTTPException

from backend.core.response import resp
from backend.api.schemas import BrowserModeRequest
from backend.services.rpa.rule_manager import rule_manager
from backend.services.rpa import scheduler, scraper
from backend.services.window_manager import window_manager

# browser_manager 依赖 selenium，环境未安装时降级
try:
    from utils.browser_utils import browser_manager
    _HAS_BROWSER = True
except ImportError:
    browser_manager = None  # type: ignore
    _HAS_BROWSER = False

from utils.log_utils import get_logger

logger = get_logger()
router = APIRouter(prefix="/api/control", tags=["采集控制"])


# ================================================================
# 手动触发采集
# ================================================================

@router.post("/trigger/{rule_id}", summary="手动执行单次采集")
async def trigger_fetch(rule_id: str):
    """
    立即触发单次采集（不改变规则的定时调度）

    适用场景:
      - 「立即刷新」按钮
      - 手动测试规则
      - 调试
    """
    rule = rule_manager.get(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"规则不存在: {rule_id}")

    if scraper is None:
        raise HTTPException(status_code=503, detail="采集引擎未安装（缺少 selenium）")

    # 同步采集在后台线程执行，避免阻塞接口响应
    import threading

    result_container = {}

    def _run():
        try:
            res = scraper.run(rule)
            result_container["result"] = res

            # 采集完成后 → SSE 广播
            from backend.api.sse_manager import sse_manager
            if res.status == "ok":
                sse_manager.broadcast_update(
                    rule_id=rule_id,
                    rule_name=rule.rule_name,
                    rows=res.rows,
                    row_count=res.row_count,
                )
            else:
                sse_manager.broadcast_error(rule_id=rule_id, error_msg=res.error or "未知错误")

            # 广播调度器最新状态
            if scheduler:
                snap = scheduler.snapshot()
                sse_manager.broadcast_status(snap.model_dump())

        except Exception as exc:
            result_container["error"] = str(exc)
            logger.error(f"[API] trigger 异常: {exc}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=60)  # 最多等 60 秒（Chrome 首次启动较慢）

    if "result" in result_container:
        res = result_container["result"]
        if res.status == "ok":
            return resp.success(
                data={
                    "rule_id": rule_id,
                    "rule_name": rule.rule_name,
                    "row_count": res.row_count,
                    "elapsed_seconds": res.elapsed_seconds,
                    "rows": res.rows,
                    "debug_log": res.debug_log,
                },
                msg=f"采集完成，共 {res.row_count} 行",
            )
        else:
            return resp.error(
                msg=f"采集失败: {res.error}",
                data={"debug_log": res.debug_log},
            )

    if "error" in result_container:
        return resp.error(msg=f"采集异常: {result_container['error']}")

    return resp.error(msg="采集超时（60s），Chrome 首次启动可能较慢，请稍后重试")


# ================================================================
# 全局调度控制
# ================================================================

@router.post("/scheduler/start", summary="启动全局采集调度")
async def start_scheduler():
    """启动后台定时采集调度器"""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="调度器不可用（缺少 selenium）")

    if scheduler.is_running:
        return resp.success(
            data=scheduler.snapshot().model_dump(),
            msg="调度器已在运行中",
        )

    scheduler.start()
    snap = scheduler.snapshot()
    return resp.success(data=snap.model_dump(), msg="调度器已启动")


@router.post("/scheduler/stop", summary="停止全局采集调度")
async def stop_scheduler():
    """停止后台定时采集调度器"""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="调度器不可用（缺少 selenium）")

    if not scheduler.is_running:
        return resp.success(msg="调度器未在运行")

    scheduler.stop()
    return resp.success(msg="调度器已停止")


# ================================================================
# 浏览器模式切换
# ================================================================

@router.post("/browser/mode", summary="切换浏览器显示模式")
async def switch_browser_mode(req: BrowserModeRequest):
    """
    切换 Chrome 浏览器显示模式

    - headless: 后台静默运行（生产环境）
    - gui: 前台可见窗口（开发调试）
    """
    if not _HAS_BROWSER:
        raise HTTPException(status_code=503, detail="浏览器驱动未安装（缺少 selenium）")

    try:
        browser_manager.switch_mode(req.mode)
        return resp.success(
            data={"mode": req.mode},
            msg=f"浏览器已切换为 {req.mode} 模式",
        )
    except Exception as exc:
        return resp.error(msg=f"切换失败: {exc}")


# ================================================================
# 悬浮窗控制
# ================================================================

@router.post("/window/start", summary="启动桌面悬浮窗")
async def start_window():
    """启动 PyQt6 桌面悬浮窗子进程"""
    ok = window_manager.start()
    if ok:
        return resp.success(
            data={"pid": window_manager.pid, "running": True},
            msg="悬浮窗已启动",
        )
    return resp.error(msg="悬浮窗启动失败，请查看服务端日志")


@router.post("/window/stop", summary="停止桌面悬浮窗")
async def stop_window():
    """停止 PyQt6 桌面悬浮窗子进程"""
    window_manager.stop()
    return resp.success(data={"running": False}, msg="悬浮窗已停止")


@router.post("/window/restart", summary="重启桌面悬浮窗")
async def restart_window():
    """重启 PyQt6 桌面悬浮窗"""
    ok = window_manager.restart()
    if ok:
        return resp.success(
            data={"pid": window_manager.pid, "running": True},
            msg="悬浮窗已重启",
        )
    return resp.error(msg="悬浮窗重启失败")


@router.get("/window/status", summary="悬浮窗运行状态")
async def window_status():
    """查询悬浮窗运行状态"""
    return resp.success(
        data={
            "running": window_manager.is_running,
            "pid": window_manager.pid,
            "uptime_seconds": round(window_manager.uptime_seconds, 1),
        },
        msg="查询成功",
    )
