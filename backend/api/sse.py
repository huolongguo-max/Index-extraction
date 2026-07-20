"""
SSE 实时推送接口

端点:
  GET /api/sse/stream     SSE 实时数据流（text/event-stream）

每次采集完成后，调度器 / 手动触发接口会向所有订阅端推送：
  - type: update    → 最新采集数据
  - type: status    → 调度器运行状态
  - type: heartbeat → 心跳保活
  - type: error     → 采集异常通知

SSE 推送不阻塞主服务运行 — 基于 asyncio.Queue 实现异步广播。
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.api.sse_manager import sse_manager
from backend.core.response import sse
from config.settings import SSE_HEARTBEAT_INTERVAL

router = APIRouter(prefix="/api/sse", tags=["实时推送"])


@router.get("/stream", summary="SSE 实时数据流")
async def sse_stream(request: Request):
    """
    SSE (Server-Sent Events) 实时数据流端点

    客户端连接后将持续接收:
      - update:    每次采集完成后的最新数据
      - status:    调度器运行状态快照
      - heartbeat: 每 15 秒一次心跳
      - error:     采集异常通知

    用法（前端）:
        const evtSource = new EventSource('/api/sse/stream');
        evtSource.addEventListener('message', (e) => {
            const { type, payload } = JSON.parse(e.data);
            if (type === 'update') updateTable(payload);
        });

    桌面端:
        requests.get('/api/sse/stream', stream=True)
    """
    async def generator():
        async for data in sse_manager.event_generator(
            heartbeat_interval=SSE_HEARTBEAT_INTERVAL
        ):
            # 检查客户端是否断开连接
            if await request.is_disconnected():
                break
            yield data

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/clients", summary="SSE 客户端统计")
async def sse_clients():
    """查看当前 SSE 连接数"""
    from backend.core.response import resp
    return resp.success(
        data={"active_clients": sse_manager.client_count},
        msg=f"当前 {sse_manager.client_count} 个 SSE 客户端",
    )
