"""
本地存储工具 — JSON 文件读写 + SQLite 迁移接口

职责（纯工具层）：
  1. JSON 文件原子读写（采集数据缓存、规则持久化）
  2. 预留 SQLite 无缝迁移接口（与 JSON 相同的 CRUD 签名）
  3. 自动创建目录、文件锁防并发写

可被 backend/、desktop/ 直接复用，不依赖任何业务。
"""

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

from utils.log_utils import get_logger

logger = get_logger()


# ================================================================
# 抽象存储接口 — SQLite 迁移时只需实现此接口
# ================================================================

class IStorage(ABC):
    """统一存储接口：JSON 和 SQLite 均实现同样的 CRUD 签名"""

    @abstractmethod
    def read(self, key: str = "__all__") -> Any:
        """读取数据"""

    @abstractmethod
    def write(self, key: str, data: Any) -> None:
        """写入数据"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除数据"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查是否存在"""

    @abstractmethod
    def list_keys(self) -> list[str]:
        """列出所有 key"""


# ================================================================
# JSON 文件存储实现
# ================================================================

class JsonStorage(IStorage):
    """
    JSON 文件存储

    结构: { "key1": {...}, "key2": [...] }

    特性:
      - 原子写入（先写临时文件再 rename，防断电丢数据）
      - 线程锁防并发写
      - 自动创建父目录
      - 无第三方依赖

    用法:
        store = JsonStorage("static/cache/table_data.json")

        # 缓存采集数据
        store.write("task_20250101_001", {"rows": [...], "url": "..."})

        # 读取
        data = store.read("task_20250101_001")

        # 列出所有 key
        keys = store.list_keys()
    """

    def __init__(self, file_path: Union[str, Path]):
        self._file_path = Path(file_path)
        self._lock = threading.Lock()

    # ---- 路径 ----

    @property
    def file_path(self) -> Path:
        return self._file_path

    # ---- 底层原子操作 ----

    def _load(self) -> dict:
        """从文件加载全部数据（无锁 - 内部使用）"""
        if not self._file_path.exists():
            return {}

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(f"存储文件根类型异常，重置为空: {self._file_path}")
                return {}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"读取存储文件失败: {self._file_path} — {exc}")
            return {}

    def _dump(self, data: dict) -> None:
        """原子写入：写临时文件 → rename"""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._file_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 原子替换（POSIX rename 是原子的）
            os.replace(tmp_path, self._file_path)

        except OSError as exc:
            logger.error(f"写入存储文件失败: {self._file_path} — {exc}")
            # 清理临时文件
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    # ---- 接口实现 ----

    def read(self, key: str = "__all__") -> Any:
        """
        读取数据

        Args:
            key:  数据 key；"__all__" 返回 dict[str, Any]
        """
        with self._lock:
            all_data = self._load()
        if key == "__all__":
            return all_data
        return all_data.get(key, None)

    def write(self, key: str, data: Any) -> None:
        """写入数据（覆盖该 key）"""
        with self._lock:
            all_data = self._load()
            all_data[key] = data
            self._dump(all_data)
        logger.debug(f"存储写入: key='{key}'")

    def delete(self, key: str) -> None:
        """删除数据"""
        with self._lock:
            all_data = self._load()
            if key in all_data:
                del all_data[key]
                self._dump(all_data)
                logger.debug(f"存储删除: key='{key}'")

    def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        with self._lock:
            all_data = self._load()
        return key in all_data

    def list_keys(self) -> list[str]:
        """列出所有 key"""
        with self._lock:
            all_data = self._load()
        return list(all_data.keys())

    def clear(self) -> None:
        """清空所有数据"""
        with self._lock:
            self._dump({})
        logger.warning(f"存储已清空: {self._file_path}")


# ================================================================
# SQLite 占位实现 — 后续无缝切换只需替换 new SqliteStorage(...)
# ================================================================

class SqliteStorage(IStorage):
    """
    SQLite 存储实现（预留）

    接口与 JsonStorage 完全一致，后续迁移只需替换实例化即可。

    启用步骤：
        pip install aiosqlite   # (非必须，此处用同步示例)
        store = SqliteStorage("static/cache/data.db")

    当前为占位实现，待后续迭代补齐 SQL DDL。
    """

    def __init__(self, db_path: Union[str, Path]):
        self._db_path = Path(db_path)
        self._conn = None
        logger.info(f"SqliteStorage 占位创建: {self._db_path}（DDL 待实现）")

    def _ensure_table(self):
        """创建表（按业务需求后续补齐）"""
        pass

    def read(self, key: str = "__all__") -> Any:
        raise NotImplementedError("SQLite 存储尚未实现 — 请先使用 JsonStorage")

    def write(self, key: str, data: Any) -> None:
        raise NotImplementedError("SQLite 存储尚未实现 — 请先使用 JsonStorage")

    def delete(self, key: str) -> None:
        raise NotImplementedError("SQLite 存储尚未实现 — 请先使用 JsonStorage")

    def exists(self, key: str) -> bool:
        raise NotImplementedError("SQLite 存储尚未实现 — 请先使用 JsonStorage")

    def list_keys(self) -> list[str]:
        raise NotImplementedError("SQLite 存储尚未实现 — 请先使用 JsonStorage")


# ================================================================
# 便捷工厂
# ================================================================

def create_storage(backend: str = "json", **kwargs) -> IStorage:
    """
    统一存储工厂

    Args:
        backend: "json" | "sqlite"
        **kwargs: 传给具体存储实现的参数

    Returns:
        IStorage 实例
    """
    if backend == "json":
        return JsonStorage(kwargs.get("file_path", "static/cache/default.json"))
    elif backend == "sqlite":
        return SqliteStorage(kwargs.get("db_path", "static/cache/default.db"))
    else:
        raise ValueError(f"不支持的存储后端: {backend}（可选: json, sqlite）")


# ================================================================
# 默认便利实例（全局复用）
# ================================================================

# 采集数据缓存
data_store = JsonStorage("static/cache/table_data.json")

# XPath 规则缓存
rules_store = JsonStorage("static/cache/rules_cache.json")
