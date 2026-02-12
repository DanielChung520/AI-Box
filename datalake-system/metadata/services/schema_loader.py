# 代碼功能說明: 智能 Schema 加載器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""
Smart Schema Loader

功能：
- 按需加載（只加載需要的 Table）
- 多系統支持
- 內存緩存
- 引用計數（自動卸載不常用的 Schema）

使用示例：
    loader = SmartSchemaLoader(Path("/metadata"))

    # 加載完整系統
    schema = loader.load_system("tiptop_erp")

    # 按需加載單個 Table
    table = loader.get_table("tiptop_erp", "item_master")

    # 批量加載關聯表
    tables = loader.get_related_tables("tiptop_erp", {"purchase_line"})
"""

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, Optional, Set, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NamingConvention(Enum):
    """命名約定枚舉"""

    CANONICAL = "canonical"
    TIPTOP = "tiptop"
    ORACLE = "oracle"
    SAP = "sap"


@dataclass
class ColumnMetadata:
    """欄位元數據（輕量）"""

    canonical_id: str
    names: Dict[str, str]
    type: str
    description: str
    primary_key: bool = False
    fk: Optional[str] = None
    example: Optional[str] = None


@dataclass
class TableMetadata:
    """表格元數據（輕量）"""

    canonical_name: str
    names: Dict[str, str]
    description: str
    table_type: str
    columns: Dict[str, ColumnMetadata]
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)


@dataclass
class SystemMetadata:
    """系統元數據"""

    id: str
    name: str
    dialect: str
    naming_convention: str
    bucket: str
    tables: List[TableMetadata] = field(default_factory=list)
    intents: List[Dict[str, Any]] = field(default_factory=list)


class SmartSchemaLoader:
    """
    智能 Schema 加載器

    核心特性：
    1. 按需加載：只加載 Query 需要的 Table，而非全量
    2. 多系統支持：通過 Registry 路由到不同系統
    3. 內存緩存：LRU Cache 避免重複 IO
    """

    def __init__(self, metadata_root: Path):
        self.metadata_root = Path(metadata_root)
        self._system_cache: Dict[str, SystemMetadata] = {}
        self._table_cache: Dict[str, TableMetadata] = {}
        self._shared_cache: Dict[str, Any] = {}

    def load_registry(self) -> dict:
        """加載 Registry（輕量入口）"""
        registry_path = self.metadata_root / "schema_registry.json"

        if not registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {registry_path}")

        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_systems(self) -> List[str]:
        """獲取所有可用系統"""
        registry = self.load_registry()
        return list(registry.get("systems", {}).keys())

    def get_system_config(self, system_id: str) -> dict:
        """獲取系統配置"""
        registry = self.load_registry()
        systems = registry.get("systems", {})

        if system_id not in systems:
            raise ValueError(f"Unknown system: {system_id}")

        return systems[system_id]

    @lru_cache(maxsize=16)
    def load_system(self, system_id: str) -> SystemMetadata:
        """
        加載完整系統 Schema

        Args:
            system_id: 系統 ID（如 "tiptop_erp", "oracle_scm"）

        Returns:
            SystemMetadata 對象
        """
        import yaml

        config = self.get_system_config(system_id)
        system_path = self.metadata_root / config["path"]

        logger.info(f"Loading system schema: {system_id} from {system_path}")

        with open(system_path, "r", encoding="utf-8") as f:
            schema_data = yaml.safe_load(f)

        tables = []
        for table_data in schema_data.get("tables", []):
            columns = {}
            for col_data in table_data.get("columns", []):
                col = ColumnMetadata(
                    canonical_id=col_data["id"],
                    names=col_data.get("names", {}),
                    type=col_data.get("type", "string"),
                    description=col_data.get("description", ""),
                    primary_key=col_data.get("primary_key", False),
                    fk=col_data.get("fk"),
                    example=col_data.get("example"),
                )
                columns[col.canonical_id] = col

            table = TableMetadata(
                canonical_name=table_data["name"],
                names=table_data.get("names", {}),
                description=table_data.get("description", ""),
                table_type=table_data.get("type", "dimension"),
                columns=columns,
                aliases=table_data.get("aliases", []),
                relationships=[],
            )
            tables.append(table)

        table_map = {t.canonical_name: t for t in tables}

        for rel in schema_data.get("relationships", []):
            from_table = table_map.get(rel["from_table"])
            if from_table:
                from_table.relationships.append(rel)

        system = SystemMetadata(
            id=schema_data["system"]["id"],
            name=schema_data["system"]["name"],
            dialect=schema_data["system"]["dialect"],
            naming_convention=schema_data["system"]["naming_convention"],
            bucket=schema_data["system"]["bucket"],
            tables=tables,
        )

        self._system_cache[system_id] = system
        return system

    def get_table(self, system_id: str, canonical_name: str) -> Optional[TableMetadata]:
        """按需加載單個 Table"""
        cache_key = f"{system_id}:{canonical_name}"

        if cache_key in self._table_cache:
            return self._table_cache[cache_key]

        system = self.load_system(system_id)

        for table in system.tables:
            if table.canonical_name == canonical_name:
                self._table_cache[cache_key] = table
                return table

        return None

    def get_related_tables(self, system_id: str, table_names: Set[str]) -> List[TableMetadata]:
        """批量加載 Table 及其關聯 Table"""
        system = self.load_system(system_id)

        rel_index: Dict[str, List[Dict]] = {}
        for table in system.tables:
            rel_index[table.canonical_name] = table.relationships

        tables_to_load = set(table_names)
        for table in table_names:
            for rel in rel_index.get(table, []):
                tables_to_load.add(rel["to_table"])

        result = []
        for table in system.tables:
            if table.canonical_name in tables_to_load:
                result.append(table)

        logger.info(
            f"Loaded {len(result)} tables for query, "
            f"requested: {table_names}, "
            f"resolved: {tables_to_load}"
        )

        return result

    def find_table_by_alias(self, system_id: str, alias: str) -> Optional[str]:
        """根據 Alias 查找 Table"""
        system = self.load_system(system_id)

        for table in system.tables:
            if alias in table.aliases:
                return table.canonical_name
            if alias in table.names.values():
                return table.canonical_name

        return None

    def load_shared_config(self, config_type: str) -> dict:
        """加載共享配置（macros/rules）"""
        import yaml

        if config_type in self._shared_cache:
            return self._shared_cache[config_type]

        registry = self.load_registry()
        shared_config = registry.get("shared", {})

        if config_type not in shared_config:
            raise ValueError(f"Unknown shared config: {config_type}")

        shared_path = self.metadata_root / shared_config[config_type]

        with open(shared_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self._shared_cache[config_type] = config
        return config

    def clear_cache(self):
        """清除所有緩存"""
        self._system_cache.clear()
        self._table_cache.clear()
        self._shared_cache.clear()
        self.load_system.cache_clear()
        logger.info("Schema cache cleared")

    def get_cache_stats(self) -> dict:
        """獲取緩存統計"""
        cache_info = self.load_system.cache_info()
        return {
            "system_cache_size": len(self._system_cache),
            "table_cache_size": len(self._table_cache),
            "shared_cache_size": len(self._shared_cache),
            "system_cache_hits": cache_info.hits,
            "system_cache_misses": cache_info.misses,
        }
