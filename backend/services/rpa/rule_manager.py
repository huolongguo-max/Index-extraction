"""
RPA 抓取规则全生命周期管理

职责（纯业务层）：
  - 新增 / 编辑 / 删除规则
  - 单条启用 / 停用
  - 每条规则独立存储，互不干扰
  - 规则持久化到 JSON，无缝预留 SQLite 迁移

不依赖接口层、不依赖展示层、不依赖桌面端。
后端 API 和桌面端可直接 import 调用。
"""

import threading
from typing import Optional

from backend.models.rpa_models import ScrapeRule
from utils.storage_utils import rules_store
from utils.log_utils import get_logger

logger = get_logger()


class RuleManager:
    """
    规则管理器 — 单例模式

    用法:
        mgr = RuleManager()

        # 新增
        rule = ScrapeRule(rule_name="示例", target_url="https://...",
                          row_keyword="张三", target_headers=["金额", "日期"])
        mgr.add(rule)

        # 编辑
        mgr.update("rule_id_xxx", {"interval_seconds": 30})

        # 启用/停用
        mgr.disable("rule_id_xxx")
        mgr.enable("rule_id_xxx")

        # 查询
        all_rules = mgr.list_all()
        active   = mgr.list_enabled()
        one      = mgr.get("rule_id_xxx")

        # 删除
        mgr.remove("rule_id_xxx")
    """

    # JSON 存储 key
    _STORAGE_KEY = "rpa_rules"

    def __init__(self):
        self._lock = threading.Lock()
        self._ensure_storage()

    # ================================================================
    # 底层持久化
    # ================================================================

    def _ensure_storage(self):
        """确保存储中存在规则数据集"""
        if not rules_store.exists(self._STORAGE_KEY):
            rules_store.write(self._STORAGE_KEY, {})
            logger.info("RPA 规则存储初始化完成")

    def _load(self) -> dict[str, dict]:
        """从存储加载所有规则（原始 dict）"""
        data = rules_store.read(self._STORAGE_KEY)
        return data or {}

    def _save(self, rules: dict[str, dict]) -> None:
        """将所有规则写回存储"""
        rules_store.write(self._STORAGE_KEY, rules)

    def _dict_to_rule(self, d: dict) -> ScrapeRule:
        """dict → ScrapeRule 模型"""
        return ScrapeRule(**d)

    def _rule_to_dict(self, rule: ScrapeRule) -> dict:
        """ScrapeRule 模型 → dict（排除 None）"""
        return rule.model_dump(exclude_none=True)

    # ================================================================
    # CRUD
    # ================================================================

    def add(self, rule: ScrapeRule) -> ScrapeRule:
        """
        新增规则

        Raises:
            ValueError: rule_id 已存在
        """
        with self._lock:
            rules = self._load()
            if rule.rule_id in rules:
                raise ValueError(f"规则 ID 已存在: {rule.rule_id}")

            rules[rule.rule_id] = self._rule_to_dict(rule)
            self._save(rules)

        logger.info(f"[RULE:ADD] id={rule.rule_id} name={rule.rule_name} "
                     f"url={rule.target_url} interval={rule.interval_seconds}s")
        return rule

    def update(self, rule_id: str, updates: dict) -> ScrapeRule:
        """
        编辑规则（部分更新）

        Args:
            rule_id: 规则 ID
            updates: 要更新的字段 dict，如 {"interval_seconds": 30, "enabled": False}

        Raises:
            KeyError: rule_id 不存在
        """
        with self._lock:
            rules = self._load()
            if rule_id not in rules:
                raise KeyError(f"规则不存在: {rule_id}")

            # merge
            current = rules[rule_id]
            current.update(updates)
            # 重新校验
            validated = ScrapeRule(**current)
            rules[rule_id] = self._rule_to_dict(validated)
            self._save(rules)

        logger.info(f"[RULE:UPDATE] id={rule_id} fields={list(updates.keys())}")
        return validated

    def remove(self, rule_id: str) -> None:
        """
        删除规则

        Raises:
            KeyError: rule_id 不存在
        """
        with self._lock:
            rules = self._load()
            if rule_id not in rules:
                raise KeyError(f"规则不存在: {rule_id}")

            name = rules[rule_id].get("rule_name", "")
            del rules[rule_id]
            self._save(rules)

        logger.info(f"[RULE:DELETE] id={rule_id} name={name}")

    # ================================================================
    # 查询
    # ================================================================

    def get(self, rule_id: str) -> Optional[ScrapeRule]:
        """根据 ID 获取单条规则"""
        with self._lock:
            rules = self._load()
            data = rules.get(rule_id)
            return self._dict_to_rule(data) if data else None

    def list_all(self) -> list[ScrapeRule]:
        """获取所有规则"""
        with self._lock:
            rules = self._load()
            return [self._dict_to_rule(d) for d in rules.values()]

    def list_enabled(self) -> list[ScrapeRule]:
        """获取所有已启用的规则"""
        return [r for r in self.list_all() if r.enabled]

    def list_disabled(self) -> list[ScrapeRule]:
        """获取所有已停用的规则"""
        return [r for r in self.list_all() if not r.enabled]

    # ================================================================
    # 启用 / 停用
    # ================================================================

    def enable(self, rule_id: str) -> ScrapeRule:
        """启用规则"""
        rule = self.update(rule_id, {"enabled": True})
        logger.info(f"[RULE:ENABLE] id={rule_id} name={rule.rule_name}")
        return rule

    def disable(self, rule_id: str) -> ScrapeRule:
        """停用规则"""
        rule = self.update(rule_id, {"enabled": False})
        logger.info(f"[RULE:DISABLE] id={rule_id} name={rule.rule_name}")
        return rule

    def toggle(self, rule_id: str) -> ScrapeRule:
        """切换启用/停用状态"""
        rule = self.get(rule_id)
        if rule is None:
            raise KeyError(f"规则不存在: {rule_id}")
        if rule.enabled:
            return self.disable(rule_id)
        else:
            return self.enable(rule_id)

    # ================================================================
    # 运行时元数据更新（采集器调用）
    # ================================================================

    def record_run(
        self,
        rule_id: str,
        status: str,
        row_count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """
        记录规则最近一次运行结果（由采集器回调）

        Args:
            rule_id:   规则 ID
            status:    "ok" | "fail"
            row_count: 采集到的行数
            error:     错误信息（status=fail 时）
        """
        from datetime import datetime
        updates = {
            "last_run_at": datetime.now().isoformat(),
            "last_status": status,
            "last_row_count": row_count,
            "last_error": error,
        }
        try:
            self.update(rule_id, updates)
        except KeyError:
            logger.warning(f"record_run 时规则已不存在: {rule_id}")

    # ================================================================
    # 便捷方法
    # ================================================================

    def count(self) -> int:
        """总规则数"""
        with self._lock:
            return len(self._load())

    def count_enabled(self) -> int:
        """已启用规则数"""
        return len(self.list_enabled())


# ================================================================
# 全局单例
# ================================================================

rule_manager = RuleManager()
