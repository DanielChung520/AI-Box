# 代碼功能說明: Schema 解析器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""
Schema Resolver

功能：
- 處理多系統表名/欄位名映射
- 根據命名約定轉換名稱
- 支持動態切換系統

使用示例：
    loader = SmartSchemaLoader(Path("/metadata"))
    resolver = SchemaResolver(loader.load_system("tiptop_erp"))

    # Canonical → TiTop
    resolver.get_table_name("item_master", NamingConvention.TIPTOP)  # "ima_file"

    # Canonical → Oracle
    resolver.get_column_name("item_master", "item_code", NamingConvention.ORACLE)  # "INVENTORY_ITEM_ID"
"""

from typing import Dict, Optional, List
from dataclasses import dataclass

from .schema_loader import NamingConvention, SystemMetadata, TableMetadata


@dataclass
class ColumnMapping:
    """欄位映射"""

    canonical_id: str
    names: Dict[str, str]


class SchemaResolver:
    """
    Schema 解析器

    職責：
    1. 處理多系統表名/欄位名映射
    2. 根據命名約定轉換名稱
    3. 支持動態切換系統
    """

    def __init__(self, system_metadata: SystemMetadata):
        self.system = system_metadata

        self._table_index: Dict[str, TableMetadata] = {}
        self._column_index: Dict[str, Dict[str, ColumnMapping]] = {}
        self._alias_index: Dict[str, str] = {}

        self._build_indexes()

    def _build_indexes(self):
        """建立索引"""
        for table in self.system.tables:
            self._table_index[table.canonical_name] = table

            self._column_index[table.canonical_name] = {}
            for col_id, col in table.columns.items():
                self._column_index[table.canonical_name][col_id] = ColumnMapping(
                    canonical_id=col.canonical_id,
                    names=col.names,
                )

            for alias in table.aliases:
                self._alias_index[alias.lower()] = table.canonical_name

    def get_table_name(self, canonical_name: str, convention: NamingConvention) -> str:
        """
        獲取指定約定的表名

        Args:
            canonical_name: 規範名稱（如 "item_master"）
            convention: 目標命名約定

        Returns:
            轉換後的表名（如 "ima_file" 或 "MTL_SYSTEM_ITEMS_B"）
        """
        table = self._table_index.get(canonical_name)
        if not table:
            raise ValueError(f"Unknown table: {canonical_name}")

        if convention == NamingConvention.CANONICAL:
            return canonical_name

        system_name = convention.value
        return table.names.get(system_name, canonical_name)

    def get_table_names(
        self, canonical_names: List[str], convention: NamingConvention
    ) -> List[str]:
        """批量轉換表名"""
        return [self.get_table_name(name, convention) for name in canonical_names]

    def get_column_name(
        self, table_name: str, canonical_column_id: str, convention: NamingConvention
    ) -> str:
        """
        獲取指定約定的欄位名
        """
        table = self._table_index.get(table_name)
        if not table:
            for t in self._table_index.values():
                if table_name in t.names.values():
                    table = t
                    break

        if not table:
            raise ValueError(f"Unknown table: {table_name}")

        columns = self._column_index.get(table.canonical_name, {})
        column = columns.get(canonical_column_id)

        if not column:
            return canonical_column_id

        if convention == NamingConvention.CANONICAL:
            return canonical_column_id

        system_name = convention.value
        return column.names.get(system_name, canonical_column_id)

    def find_table_by_alias(self, alias: str) -> Optional[str]:
        """根據 Alias 查找 Table"""
        return self._alias_index.get(alias.lower())

    def find_table(
        self, name: str, source_convention: Optional[NamingConvention] = None
    ) -> Optional[str]:
        """
        根據名稱查找 Table（支持模糊匹配）
        """
        if source_convention:
            for canonical, table in self._table_index.items():
                if table.names.get(source_convention.value) == name:
                    return canonical

        for canonical, table in self._table_index.items():
            if name in table.names.values():
                return canonical

        return self.find_table_by_alias(name)

    def get_relationships(self, table_name: str) -> List[dict]:
        """獲取表格的關聯關係"""
        table = self._table_index.get(table_name)
        if not table:
            return []
        return table.relationships

    def get_join_condition(self, from_table: str, to_table: str) -> Optional[dict]:
        """
        獲取兩個表格的 JOIN 條件
        """
        table = self._table_index.get(from_table)
        if not table:
            return None

        for rel in table.relationships:
            if rel.get("to_table") == to_table:
                return {
                    "from_column": rel["from_column"],
                    "to_column": rel["to_column"],
                    "join_type": rel.get("join_type", "LEFT JOIN"),
                    "description": rel.get("description", ""),
                    "warning": rel.get("warning"),
                }

        return None
