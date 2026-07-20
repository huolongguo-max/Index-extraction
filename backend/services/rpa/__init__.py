"""
RPA 抓取核心业务模块

子模块:
  rule_manager  — 规则全生命周期管理（CRUD + 启用/停用）
  scraper       — 标准采集流水线（load→click→wait→xpath→extract→clean→cache→log）
  scheduler     — 后台定时调度（多规则独立间隔、非阻塞）

使用方式（桌面端/API 层可直接调用）:
  from backend.services.rpa import rule_manager, scraper, scheduler

  # 规则管理
  rule = ScrapeRule(rule_name="示例", target_url="https://...",
                    row_keyword="张三", target_headers=["金额"])
  rule_manager.add(rule)

  # 手动采集
  result = scraper.run(rule)

  # 后台调度
  scheduler.start()
  scheduler.trigger_now(rule.rule_id)
  scheduler.stop()
"""

# ---- 始终可用的模块（纯 Python，零外部依赖） ----
from backend.services.rpa.rule_manager import rule_manager, RuleManager

# ---- 可选模块（依赖 selenium，环境未安装时静默跳过） ----
try:
    from backend.services.rpa.scraper import scraper, RPAScraper
    from backend.services.rpa.scheduler import scheduler, Scheduler
    __all_opt__ = ["scraper", "RPAScraper", "scheduler", "Scheduler"]
except ImportError as exc:
    import warnings
    warnings.warn(
        f"RPA 采集引擎/调度器不可用（缺少 selenium 或 webdriver-manager）: {exc}"
    )
    scraper = None       # type: ignore
    RPAScraper = None    # type: ignore
    scheduler = None     # type: ignore
    Scheduler = None     # type: ignore
    __all_opt__ = []

__all__ = [
    "rule_manager",
    "RuleManager",
] + __all_opt__
