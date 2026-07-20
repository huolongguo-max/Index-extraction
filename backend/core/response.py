"""
全局统一接口返回格式
强制所有接口遵守，支持普通 JSON 响应和 SSE 数据流

返回格式:
    {
        "code": 200,    # 200=成功 / 500=失败
        "msg": "xxx",   # 提示信息
        "data": {}       # 业务数据
    }

SSE 格式: text/event-stream
    data: {"type": "update", "payload": {...}}

"""

from typing import Any, Optional, AsyncGenerator
import json
import asyncio
from fastapi.responses import StreamingResponse
from loguru import logger


class ResponseCode:
    """统一响应码"""
    SUCCESS = 200
    ERROR = 500


class UnifiedResponse:
    """JSON 标准响应"""

    @staticmethod
    def success(data: Any = None, msg: str = "success") -> dict:
        """请求成功"""
        return {
            "code": ResponseCode.SUCCESS,
            "msg": msg,
            "data": data,
        }

    @staticmethod
    def error(msg: str = "error", data: Any = None, code: int = ResponseCode.ERROR) -> dict:
        """请求失败（浏览器异常、抓取失败、接口报错）"""
        logger.error(f"[{code}] {msg}")
        return {
            "code": code,
            "msg": msg,
            "data": data,
        }

    @staticmethod
    def rpa_fetch_success(data: Any, count: int = 0) -> dict:
        """RPA 抓取成功专用"""
        msg = f"抓取成功，共 {count} 条数据" if count else "抓取成功"
        return UnifiedResponse.success(data=data, msg=msg)

    @staticmethod
    def rpa_fetch_error(error_detail: str) -> dict:
        """RPA 抓取失败专用"""
        logger.error(f"RPA 抓取失败: {error_detail}")
        return UnifiedResponse.error(
            msg=f"抓取失败: {error_detail}",
            code=ResponseCode.ERROR,
        )


class SSEResponse:
    """SSE (Server-Sent Events) 实时数据流"""

    @staticmethod
    async def event_stream(
        data_generator: AsyncGenerator,
        heartbeat_interval: int = 15,
    ) -> AsyncGenerator[str, None]:
        """
        标准 SSE 流式响应
        用于悬浮窗实时刷新数据

        Args:
            data_generator: 异步数据生成器
            heartbeat_interval: 心跳间隔（秒）
        """
        try:
            async for payload in data_generator:
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info("SSE 连接已取消")
        except Exception as e:
            logger.error(f"SSE 数据流异常: {e}")
            error_payload = {
                "type": "error",
                "msg": str(e),
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    @staticmethod
    def response(data_generator: AsyncGenerator, heartbeat_interval: int = 15) -> StreamingResponse:
        """创建 SSE StreamingResponse"""
        return StreamingResponse(
            SSEResponse.event_stream(data_generator, heartbeat_interval),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )


# 便捷出口
resp = UnifiedResponse()
sse = SSEResponse()
