"""
SSE 实时推送管理器

职责:
  - 维护所有 SSE 订阅端连接
  - 每次采集完成后，向所有订阅端广播最新数据与运行状态
  - 线程安全：调度器在后台线程触发 → asyncio 安全投递
  - 心跳保活，自动清理断连客户端

纯基础设施层，不包含业务逻辑。
"""

import asyncio
import json
import time
from typing import Optional

from utils.log_utils import get_logger

logger = get_logger()


class SSEManager:
    """
    SSE 连接管理器（单例）

    工作原理:
      1. 客户端 GET /api/sse/stream → 创建 asyncio.Queue 并注册
      2. 调度器/采集器完成 → broadcast(event) → 投递到所有 Queue
      3. 每个 SSE 端点异步从自己的 Queue 读取 → yield 给客户端

    线程安全:
      broadcast() 可从后台线程调用，内部通过
      asyncio.run_coroutine_threadsafe 安全投递到 event loop。
    """

    def __init__(self):
        # 活跃客户端队列集合
        self._queues: set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._total_broadcasts: int = 0
        self._active_since: float = 0.0

    # ================================================================
    # 客户端管理
    # ================================================================

    @property
    def client_count(self) -> int:
        return len(self._queues)

    def register(self) -> asyncio.Queue:
        """
        注册新 SSE 客户端

        Returns:
            专属 asyncio.Queue，客户端从此队列读取事件
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)

        if self._loop is None:
            self._loop = asyncio.get_running_loop()
            self._active_since = time.time()

        self._queues.add(queue)
        logger.info(f"[SSE] 客户端连接 (活跃: {len(self._queues)})")
        return queue

    def unregister(self, queue: asyncio.Queue):
        """注销 SSE 客户端"""
        self._queues.discard(queue)
        # 清空队列残留
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        logger.info(f"[SSE] 客户端断开 (活跃: {len(self._queues)})")

    # ================================================================
    # 广播（可从任意线程调用）
    # ================================================================

    def broadcast(self, event_type: str, payload: dict):
        """
        向所有已连接客户端广播事件

        Args:
            event_type: "update" | "status" | "heartbeat" | "error"
            payload:    事件负载数据

        线程安全：可在调度器后台线程中直接调用。
        """
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }

        if self._loop and self._loop.is_running():
            # 从非 asyncio 线程投递
            asyncio.run_coroutine_threadsafe(
                self._abroadcast_to_all(event), self._loop
            )
        else:
            logger.warning("[SSE] event loop 未就绪，跳过广播")

    async def _abroadcast_to_all(self, event: dict):
        """异步广播到所有队列（在 event loop 内执行）"""
        dead_queues = set()
        self._total_broadcasts += 1

        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # 客户端消费太慢，丢弃最旧事件腾出空间
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    dead_queues.add(queue)
                    logger.warning("[SSE] 客户端队列异常，标记移除")

        # 清理死队列
        for q in dead_queues:
            self.unregister(q)

    # ================================================================
    # 快捷广播
    # ================================================================

    def broadcast_update(self, rule_id: str, rule_name: str, rows: list, row_count: int):
        """广播数据更新事件"""
        self.broadcast("update", {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "data": rows,
            "row_count": row_count,
        })

    def broadcast_status(self, scheduler_snapshot: dict):
        """广播调度器状态"""
        self.broadcast("status", scheduler_snapshot)

    def broadcast_error(self, rule_id: str, error_msg: str):
        """广播错误事件"""
        self.broadcast("error", {
            "rule_id": rule_id,
            "msg": error_msg,
        })

    def broadcast_heartbeat(self):
        """广播心跳"""
        self.broadcast("heartbeat", {
            "active_clients": len(self._queues),
            "total_broadcasts": self._total_broadcasts,
        })

    # ================================================================
    # SSE 端点生成器
    # ================================================================

    async def event_generator(self, heartbeat_interval: int = 15):
        """
        异步生成器 — 每个 SSE 客户端调用一次

        行为:
          - 持续从该客户端的 Queue 读取事件 → yield SSE 格式
          - 每隔 heartbeat_interval 秒发送心跳
          - 客户端断开时自动清理

        Args:
            heartbeat_interval: 心跳间隔秒数
        """
        queue = self.register()
        try:
            while True:
                try:
                    # 等待事件，超时则发心跳
                    event = await asyncio.wait_for(
                        queue.get(), timeout=heartbeat_interval
                    )
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                except asyncio.TimeoutError:
                    # 心跳
                    heartbeat = {
                        "type": "heartbeat",
                        "payload": {"active_clients": len(self._queues)},
                        "timestamp": time.time(),
                    }
                    yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.debug("[SSE] 客户端连接取消")
        finally:
            self.unregister(queue)


# ================================================================
# 全局单例
# ================================================================

sse_manager = SSEManager()
