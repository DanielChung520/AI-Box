# -*- coding: utf-8 -*-
"""
Data-Agent-JP SQL 生成器

功能：
- 根據 Query AST 生成 Oracle SQL
- 處理 dialect 差異
- 支援 LIMIT 和 OFFSET 分頁
- 新增 SQL 快取

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-14
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional
from collections import OrderedDict

from .models import QueryAST

logger = logging.getLogger(__name__)


class SQLCache:
    """SQL 生成快取"""

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()

    def _make_key(self, key_str: str) -> str:
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def get(self, intent: str, params) -> Optional[str]:
        key = self._make_key(f"{intent}:{params}")
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, intent: str, params, sql: str):
        key = self._make_key(f"{intent}:{params}")
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = sql

    @property
    def size(self) -> int:
        return len(self.cache)


_sql_cache = SQLCache(max_size=500)


class SQLGenerator:
    """
    SQL 生成器

    支援：
    - Oracle dialect
    - DuckDB dialect
    - MySQL dialect
    - LIMIT / OFFSET 分頁
    """

    DIALECT_ORACLE = "ORACLE"
    DIALECT_DUCKDB = "DUCKDB"
    DIALECT_MYSQL = "MYSQL"

    def __init__(self, dialect: str = "ORACLE"):
        self.dialect = dialect

    def generate(self, ast: QueryAST) -> str:
        """
        生成 SQL

        Args:
            ast: Query AST

        Returns:
            str: SQL 語句
        """
        if not ast.select:
            raise ValueError("No SELECT clause")

        if not ast.from_tables:
            raise ValueError("No FROM clause")

        sql_parts = []

        # SELECT
        select_clause = self._build_select(ast.select)
        sql_parts.append(f"SELECT {select_clause}")

        # FROM
        from_clause = ", ".join(ast.from_tables)
        sql_parts.append(f"FROM {from_clause}")

        # WHERE
        if ast.where_conditions:
            where_clause = self._build_where(ast.where_conditions)
            sql_parts.append(f"WHERE {where_clause}")

        # Oracle ROWNUM (必須在 GROUP BY 之前)
        if self.dialect == self.DIALECT_ORACLE and ast.limit:
            if ast.where_conditions:
                sql_parts.append(f"AND ROWNUM <= {ast.limit}")
            else:
                sql_parts.append(f"WHERE ROWNUM <= {ast.limit}")

        # GROUP BY
        if ast.group_by:
            group_by_clause = ", ".join(ast.group_by)
            sql_parts.append(f"GROUP BY {group_by_clause}")

        # ORDER BY
        if ast.order_by:
            order_by_clause = ", ".join(ast.order_by)
            sql_parts.append(f"ORDER BY {order_by_clause}")

        # LIMIT / OFFSET (for DuckDB / MySQL)
        if self.dialect != self.DIALECT_ORACLE:
            if ast.limit:
                sql_parts.append(f"LIMIT {ast.limit}")
            if ast.offset:
                sql_parts.append(f"OFFSET {ast.offset}")

        sql = "\n".join(sql_parts)
        logger.debug(f"Generated SQL: {sql[:200]}...")

        return sql

    def _build_select(self, select_items: List[Dict[str, str]]) -> str:
        """建構 SELECT 子句"""
        items = []
        for item in select_items:
            expr = item.get("expr", "")
            alias = item.get("alias")
            if alias:
                items.append(f"{expr} AS {alias}")
            else:
                items.append(expr)
        return ", ".join(items)

    def _build_where(self, conditions: List[Dict[str, Any]]) -> str:
        """建構 WHERE 子句"""
        conditions_sql = []

        for cond in conditions:
            column = cond.get("column", "")
            operator = cond.get("operator", "=")
            value = cond.get("value")

            # 處理 NULL
            if value is None:
                op_sql = "IS NULL" if operator == "=" else "IS NOT NULL"
                conditions_sql.append(f"{column} {op_sql}")
            # 處理 BETWEEN（日期範圍）- 使用字串比較
            elif isinstance(value, dict) and value.get("type") == "BETWEEN":
                # 提取日期字串（去掉引號）
                start_val = value.get("start", "").strip("'\"")
                end_val = value.get("end", "").strip("'\"")
                # 將日期轉換為 YYYYMMDD 格式進行字串比較
                start_str = start_val.replace("-", "").replace("/", "")
                end_str = end_val.replace("-", "").replace("/", "")
                # 使用字串 BETWEEN 進行比較
                conditions_sql.append(f"{column} BETWEEN '{start_str}' AND '{end_str}'")
            # 處理 IN
            elif isinstance(value, list):
                values_str = ", ".join([self._quote_value(v) for v in value])
                conditions_sql.append(f"{column} IN ({values_str})")
            # 處理 LIKE
            elif operator.upper() == "LIKE":
                conditions_sql.append(f"{column} LIKE '{value}'")
            # 處理一般運算符
            else:
                conditions_sql.append(f"{column} {operator} {self._quote_value(value)}")

        return " AND ".join(conditions_sql)

    def _quote_value(self, value: Any) -> str:
        """引用值"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif value is None:
            return "NULL"
        else:
            return str(value)


class DuckDBSQLGenerator(SQLGenerator):
    """DuckDB SQL 生成器

    支援動態綁定（從 bindings.json 取得 S3 路徑）
    """

    def __init__(
        self,
        bucket: str = "tiptop-raw",
        dialect: Optional[str] = None,
        bindings: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect=self.DIALECT_DUCKDB)
        self.bucket = bucket
        self._bindings = bindings or {}

    def _get_table_path(self, table_name: str) -> Optional[str]:
        """從 bindings 動態取得表格路徑"""
        table_upper = table_name.upper()

        if self._bindings and table_upper in self._bindings:
            binding = self._bindings[table_upper].get("DUCKDB", {})
            s3_path = binding.get("s3_path")
            if s3_path:
                return s3_path
        return None

    def _is_mart_table(self, table_name: str) -> bool:
        """判斷是否為 mart 寬表"""
        return table_name.lower().startswith("mart_")

    def _build_from_clause(self, from_tables: List[str]) -> str:
        """建構 FROM 子句 (支援 S3 Path / DuckDB 寬表)"""
        mapped_tables = []
        for table in from_tables:
            table_upper = table.upper()

            # 優先從 bindings 取得路徑
            s3_path = self._get_table_path(table_upper)

            if s3_path:
                # 判斷是否為 DuckDB 寬表
                if self._is_mart_table(table):
                    mapped_tables.append(f"{table}")
                else:
                    path = s3_path.replace("s3://tiptop-raw", f"s3://{self.bucket}")
                    mapped_tables.append(f"read_parquet('{path}')")
            else:
                # Fallback: 使用表名作為 DuckDB 表格
                mapped_tables.append(table)
        return ", ".join(mapped_tables)

    def generate(self, ast: QueryAST) -> str:
        """生成 SQL (覆寫以支援 S3 Path)"""
        if not ast.select:
            raise ValueError("No SELECT clause")

        if not ast.from_tables:
            raise ValueError("No FROM clause")

        sql_parts = []

        select_clause = self._build_select(ast.select)
        sql_parts.append(f"SELECT {select_clause}")

        from_clause = self._build_from_clause(ast.from_tables)
        sql_parts.append(f"FROM {from_clause}")

        if ast.where_conditions:
            where_clause = self._build_where(ast.where_conditions)
            sql_parts.append(f"WHERE {where_clause}")

        if ast.group_by:
            group_by_clause = ", ".join(ast.group_by)
            sql_parts.append(f"GROUP BY {group_by_clause}")

        if ast.order_by:
            order_by_clause = ", ".join(ast.order_by)
            sql_parts.append(f"ORDER BY {order_by_clause}")

        if ast.limit:
            sql_parts.append(f"LIMIT {ast.limit}")
        if ast.offset:
            sql_parts.append(f"OFFSET {ast.offset}")

        sql = "\n".join(sql_parts)
        logger.debug(f"Generated DuckDB SQL: {sql[:200]}...")

        return sql


class MySQLSQLGenerator(SQLGenerator):
    """MySQL SQL 生成器"""

    def __init__(self, dialect: Optional[str] = None):
        super().__init__(dialect=self.DIALECT_MYSQL)


def get_sql_generator(dialect: str = "ORACLE") -> SQLGenerator:
    """
    獲取 SQL 生成器

    Args:
        dialect: SQL 方言 ("ORACLE", "DUCKDB", "MYSQL")

    Returns:
        SQLGenerator: 生成器實例
    """
    generators = {
        "ORACLE": SQLGenerator,
        "DUCKDB": DuckDBSQLGenerator,
        "MYSQL": MySQLSQLGenerator,
    }
    generator_class = generators.get(dialect, SQLGenerator)
    return generator_class(dialect=dialect)
