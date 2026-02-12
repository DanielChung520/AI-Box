# 代碼功能說明: SQL 渲染器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""
SQL Renderer

功能：
- 將 Canonical SQL 渲染為特定系統的 SQL
- 自動轉換表名/欄位名
- 處理 Parquet 路徑
- 支持多 SQL 方言

使用示例：
    renderer = SQLRenderer(
        schema=loader.load_system("tiptop_erp"),
        convention=NamingConvention.TIPTOP
    )

    # 渲染表名
    renderer.render_table("item_master")  # "ima_file"

    # 渲染欄位名
    renderer.render_column("item_master", "item_code")  # "ima01"

    # 渲染 Parquet 路徑
    renderer.render_parquet_path("item_master")
    # "s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet"
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .schema_loader import NamingConvention, SystemMetadata
from .schema_resolver import SchemaResolver


class SQLDialect(Enum):
    """SQL 方言"""

    DUCKDB = "duckdb"
    ORACLE = "oracle"
    MYSQL = "mysql"
    HANA = "hana"
    POSTGRESQL = "postgresql"


@dataclass
class DialectConfig:
    """方言配置"""

    dialect: SQLDialect
    path_format: str
    hive_partitioning: bool = True
    limit_keyword: str = "LIMIT"
    concat_operator: str = "||"
    date_function: str = "CAST({col} AS DATE)"


class SQLRenderer:
    """
    SQL 渲染器

    職責：
    1. 將 Canonical SQL 渲染為特定系統的 SQL
    2. 自動轉換表名/欄位名
    3. 處理 Parquet 路徑
    4. 支持多 SQL 方言
    """

    _DIALECT_CONFIGS: Dict[SQLDialect, DialectConfig] = {
        SQLDialect.DUCKDB: DialectConfig(
            dialect=SQLDialect.DUCKDB,
            path_format="s3://{bucket}/raw/v1/{table}/year=*/month=*/data.parquet",
            hive_partitioning=True,
            limit_keyword="LIMIT",
            concat_operator="||",
            date_function="CAST({col} AS DATE)",
        ),
        SQLDialect.ORACLE: DialectConfig(
            dialect=SQLDialect.ORACLE,
            path_format="{schema}.{table}",
            hive_partitioning=False,
            limit_keyword="ROWNUM <= {n}",
            concat_operator="||",
            date_function="TO_DATE({col}, 'YYYY-MM-DD')",
        ),
        SQLDialect.HANA: DialectConfig(
            dialect=SQLDialect.HANA,
            path_format="{schema}.{table}",
            hive_partitioning=False,
            limit_keyword="LIMIT {n}",
            concat_operator="||",
            date_function="TO_DATE({col})",
        ),
    }

    def __init__(
        self,
        system_metadata: SystemMetadata,
        convention: NamingConvention,
        dialect: SQLDialect = SQLDialect.DUCKDB,
        bucket: Optional[str] = None,
    ):
        self.system = system_metadata
        self.convention = convention
        self.dialect = dialect
        self.bucket = bucket or system_metadata.bucket
        self.resolver = SchemaResolver(system_metadata)

        self.dialect_config = self._DIALECT_CONFIGS.get(
            dialect, self._DIALECT_CONFIGS[SQLDialect.DUCKDB]
        )

    def render_table(self, canonical_name: str) -> str:
        """渲染表名"""
        return self.resolver.get_table_name(canonical_name, self.convention)

    def render_table_source(self, canonical_name: str, alias: Optional[str] = None) -> str:
        """
        渲染表格來源（SQL FROM 子句）
        """
        table_name = self.render_table(canonical_name)

        if self.dialect == SQLDialect.DUCKDB:
            path = self.render_parquet_path(canonical_name)
            source = f"read_parquet('{path}', hive_partitioning=true)"
        else:
            source = table_name

        if alias:
            return f"{source} AS {alias}"
        return source

    def render_tablesources(
        self, canonical_names: List[str], aliases: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """批量渲染表格來源"""
        result = []
        aliases = aliases or {}

        for name in canonical_names:
            alias = aliases.get(name)
            result.append(self.render_table_source(name, alias))

        return result

    def render_column(
        self, table_name: str, canonical_column_id: str, alias: Optional[str] = None
    ) -> str:
        """
        渲染欄位名
        """
        column_name = self.resolver.get_column_name(
            table_name, canonical_column_id, self.convention
        )

        return column_name

    def render_select_clause(
        self, selections: List[Dict[str, str]], aliases: Optional[Dict[str, str]] = None
    ) -> str:
        """
        渲染 SELECT 子句
        """
        parts = []

        for sel in selections:
            table = sel["table"]
            column = sel["column"]
            alias = sel.get("alias")

            col_expr = self.render_column(table, column)

            table_alias = aliases.get(table, table)
            col_expr = f"{table_alias}.{col_expr}"

            if alias:
                col_expr += f" AS {alias}"

            parts.append(col_expr)

        return ", ".join(parts)

    def render_parquet_path(self, canonical_table_name: str) -> str:
        """
        渲染 Parquet 路徑
        """
        if self.dialect != SQLDialect.DUCKDB:
            raise ValueError("Parquet path only supported for DUCKDB")

        table_name = self.render_table(canonical_table_name)

        return self.dialect_config.path_format.format(
            bucket=self.bucket,
            table=table_name,
        )

    def render_join(
        self,
        from_table: str,
        to_table: str,
        join_type: str = "LEFT JOIN",
        aliases: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        渲染 JOIN 子句
        """
        join_info = self.resolver.get_join_condition(from_table, to_table)
        if not join_info:
            raise ValueError(f"No join condition between {from_table} and {to_table}")

        from_src = self.render_table_source(from_table)
        to_src = self.render_table_source(to_table)

        from_col = self.resolver.get_column_name(
            from_table, join_info["from_column"], self.convention
        )
        to_col = self.resolver.get_column_name(to_table, join_info["to_column"], self.convention)

        from_alias = aliases.get(from_table, "t1") if aliases else "t1"
        to_alias = aliases.get(to_table, "t2") if aliases else "t2"

        condition = f"{from_alias}.{from_col} = {to_alias}.{to_col}"

        return f"{from_src} AS {from_alias} {join_type} {to_src} AS {to_alias} ON {condition}"

    def render_simple_select(
        self, table: str, columns: List[str], where_clause: Optional[str] = None, limit: int = 10
    ) -> str:
        """
        渲染簡單的 SELECT 語句
        """
        from_clause = self.render_table_source(table, "t")

        col_parts = []
        for col in columns:
            col_expr = self.render_column(table, col)
            col_parts.append(f"t.{col_expr}")

        select_clause = ", ".join(col_parts)

        sql = f"SELECT {select_clause} FROM {from_clause}"

        if where_clause:
            sql += f" WHERE {where_clause}"

        if limit:
            sql += f" LIMIT {limit}"

        return sql
