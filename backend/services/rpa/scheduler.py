"""
RPA 后台定时采集调度器

职责（纯业务层）：
  - 多规则按各自间隔独立循环执行
  - 采集任务在后台线程运行，与主服务互不阻塞
  - 单规则失败不影响其他规则，自动下一轮重试
  - 支持启停、快照监控

不依赖接口层、不依赖前端、不依赖桌面端。
"""

import time
import threading
from datetime import datetime
from typing import Optional

from backend.models.rpa_models import ScrapeRule, SchedulerSnapshot
from backend.services.rpa.rule_manager import rule_manager
from backend.services.rpa.scraper import scraper
from utils.log_utils import get_logger

logger = get_logger()


class Scheduler:
    """
    后台定时调度器

    工作原理:
      - 一条规则 → 一个 Timer 线程
      - 每条规则按自己的 interval_seconds 独立循环
      - 启用/停用规则时自动注册/注销对应定时器
      - 所有定时器共享线程池，互不阻塞

    用法:
        sched = Scheduler()

        # 启动调度（自动加载所有已启用规则）
        sched.start()

        # 运行时快照
        snap = sched.snapshot()

        # 优雅停止
        sched.stop()
    """

    def __init__(self):
        # rule_id → threading.Timer（每条规则一个定时器）
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

        # 运行状态
        self._running = False
        self._started_at: Optional[datetime] = None

        # 统计
        self._total_runs = 0
        self._total_ok = 0
        self._total_fail = 0

    # ================================================================
    # 生命周期
    # ================================================================

    def start(self):
        """启动调度器 — 注册所有已启用规则的定时器"""
        if self._running:
            logger.warning("调度器已在运行中")
            return

        self._running = True
        self._started_at = datetime.now()

        for rule in rule_manager.list_enabled():
            if self._should_schedule(rule):
                self._schedule_rule(rule)

        logger.info(
            f"[SCHEDULER:START] 已启动 | "
            f"启用规则: {rule_manager.count_enabled()}/{rule_manager.count()}"
        )

    def stop(self):
        """停止调度器 — 取消所有定时器"""
        self._running = False

        with self._lock:
            for rule_id, timer in self._timers.items():
                timer.cancel()
            self._timers.clear()

        logger.info(
            f"[SCHEDULER:STOP] 已停止 | "
            f"总执行: {self._total_runs} | "
            f"成功: {self._total_ok} | 失败: {self._total_fail}"
        )

    @property
    def is_running(self) -> bool:
        return self._running

    # ================================================================
    # 调度判断
    # ================================================================

    @staticmethod
    def _should_schedule(rule: ScrapeRule) -> bool:
        """手动刷新模式的规则不加入自动调度"""
        if not rule.enabled:
            return False
        if rule.refresh_mode == "manual":
            return False
        return True

    # ================================================================
    # 定时器注册 / 注销
    # ================================================================

    def _schedule_rule(self, rule: ScrapeRule):
        """
        为单条规则注册下一次定时执行

        每次执行完毕后递归调用自身，实现无限循环。
        """
        if not self._running:
            return

        interval = max(rule.interval_seconds, 5)  # 最小 5 秒

        timer = threading.Timer(interval, self._execute_and_reschedule, args=(rule.rule_id,))
        timer.daemon = True  # 主线程退出时自动清理

        with self._lock:
            # 取消旧定时器（如果存在）
            old = self._timers.pop(rule.rule_id, None)
            if old:
                old.cancel()
            self._timers[rule.rule_id] = timer

        timer.start()
        logger.debug(f"[TIMER] 注册 rule={rule.rule_id} interval={interval}s")

    def _cancel_rule(self, rule_id: str):
        """取消某条规则的定时器"""
        with self._lock:
            timer = self._timers.pop(rule_id, None)
            if timer:
                timer.cancel()
                logger.debug(f"[TIMER] 取消 rule={rule_id}")

    # ================================================================
    # 定时执行回调
    # ================================================================

    def _execute_and_reschedule(self, rule_id: str):
        """
        定时器回调:
          1. 从规则管理器获取最新规则（可能已被编辑）
          2. 如果规则已停用或不存在，不再重调度
          3. 执行采集流水线
          4. 递归注册下一次定时器
        """
        if not self._running:
            return

        # 获取最新规则状态
        rule = rule_manager.get(rule_id)
        if rule is None:
            logger.warning(f"[SCHEDULER] 规则已删除，取消调度: {rule_id}")
            self._cancel_rule(rule_id)
            return

        if not self._should_schedule(rule):
            mode = rule.refresh_mode if rule.enabled else "disabled"
            logger.info(f"[SCHEDULER] 规则{mode}，取消自动调度: {rule.rule_name} ({rule_id})")
            self._cancel_rule(rule_id)
            return

        # ---- 执行采集 ----
        logger.info(f"[SCHEDULER:EXEC] rule={rule.rule_name} url={rule.target_url}")

        try:
            result = scraper.run(rule)
            self._total_runs += 1

            if result.status == "ok":
                self._total_ok += 1
            else:
                self._total_fail += 1

        except Exception as exc:
            # 最外层保护：即使 scraper 内部没兜住的异常也不会炸调度器
            self._total_runs += 1
            self._total_fail += 1
            logger.error(
                f"[SCHEDULER:CRASH] rule={rule.rule_name} — "
                f"未预期的异常: {type(exc).__name__}: {exc}"
            )
            # 仍然通知规则管理器
            rule_manager.record_run(
                rule_id=rule_id,
                status="fail",
                error=f"调度器级异常: {type(exc).__name__}: {exc}",
            )

        # ---- 重调度 ----
        self._schedule_rule(rule)

    # ================================================================
    # 动态新增 / 编辑 / 启停的调度联动
    # ================================================================

    def on_rule_added(self, rule: ScrapeRule):
        """规则新增回调 — 如果已启用则注册定时器"""
        if not self._running:
            return
        if rule.enabled:
            self._schedule_rule(rule)
            logger.info(f"[SCHEDULER] 新规则已加入调度: {rule.rule_name}")

    def on_rule_updated(self, rule_id: str):
        """规则编辑回调 — 重新加载规则并重设定时器"""
        if not self._running:
            return
        rule = rule_manager.get(rule_id)
        if rule is None:
            self._cancel_rule(rule_id)
            return
        self._cancel_rule(rule_id)
        if self._should_schedule(rule):
            self._schedule_rule(rule)

    def on_rule_enabled(self, rule_id: str):
        """规则启用回调 — 加入调度（仅 interval 模式）"""
        if not self._running:
            return
        rule = rule_manager.get(rule_id)
        if rule and self._should_schedule(rule):
            self._schedule_rule(rule)

    def on_rule_disabled(self, rule_id: str):
        """规则停用回调 — 移出调度"""
        self._cancel_rule(rule_id)

    def on_rule_removed(self, rule_id: str):
        """规则删除回调 — 移出调度"""
        self._cancel_rule(rule_id)

    # ================================================================
    # 手动触发单次采集（不改变定时器）
    # ================================================================

    def trigger_now(self, rule_id: str) -> bool:
        """
        立即触发一次采集（绕过定时器）

        常用于: "立即刷新" 按钮、手动测试

        Returns:
            True 采集成功
        """
        rule = rule_manager.get(rule_id)
        if rule is None:
            logger.warning(f"[TRIGGER] 规则不存在: {rule_id}")
            return False

        logger.info(f"[TRIGGER] 手动触发 rule={rule.rule_name}")
        result = scraper.run(rule)

        self._total_runs += 1
        if result.status == "ok":
            self._total_ok += 1
        else:
            self._total_fail += 1

        return result.status == "ok"

    # ================================================================
    # 运行时快照（监控用）
    # ================================================================

    def snapshot(self) -> SchedulerSnapshot:
        """获取调度器运行时快照"""
        with self._lock:
            active_timer_count = len(self._timers)

        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now() - self._started_at).total_seconds()

        # 规则详情
        rules_detail = []
        for rule in rule_manager.list_all():
            rules_detail.append({
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "enabled": rule.enabled,
                "interval": rule.interval_seconds,
                "last_run": rule.last_run_at.isoformat() if rule.last_run_at else None,
                "last_status": rule.last_status,
                "last_rows": rule.last_row_count,
            })

        return SchedulerSnapshot(
            active_rules=active_timer_count,
            running_tasks=active_timer_count,  # 简化：active timer ≈ running tasks
            total_runs=self._total_runs,
            total_ok=self._total_ok,
            total_fail=self._total_fail,
            rules_detail=rules_detail,
            uptime_seconds=round(uptime, 1),
        )


# ================================================================
# 全局单例
# ================================================================

scheduler = Scheduler()
