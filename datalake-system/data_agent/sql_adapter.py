# 代碼功能說明: SQL 資料庫適配器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
#
# 職責:
# - 隔離資料庫差異
# - 未來替換資料庫只需新增 Adapter
# - Data-Agent 無需知道底層資料庫

"""SQL Adapter 介面 - 資料庫抽象化層

架構原則:
┌─────────────────────────────────────────────────┐
│              Data-Agent (抽象化層)               │
├─────────────────────────────────────────────────┤
│  Query → RAG → LLM → SQL → Adapter.execute()   │
│                              │                  │
│                              ▼                  │
│              ┌─────────────────────────┐       │
│              │   SQLAdapter 介面      │       │
│              ├─────────────────────────┤       │
│              │ DuckDBAdapter │ OracleAdapter │       │
│              └─────────────────────────┘       │
└─────────────────────────────────────────────────┘
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SQLResult:
    """SQL 執行結果"""

    success: bool
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    sql_query: str = ""
    error: Optional[str] = None


class SQLAdapter(ABC):
    """SQL Adapter 介面 - 所有資料庫適配器必須實作此介面"""

    @property
    @abstractmethod
    def dialect_name(self) -> str:
        """資料庫名稱（如 'duckdb', 'oracle', 'mysql'）"""
        pass

    @abstractmethod
    def table_source(self, table: str, schema: Optional[str] = None) -> str:
        """生成表格來源語法"""
        pass

    @abstractmethod
    def cast(self, expr: str, type: str) -> str:
        """生成 CAST 表達式"""
        pass

    @abstractmethod
    def concat(self, *args: str) -> str:
        """生成字串拼接"""
        pass

    @abstractmethod
    def like(self, field: str, pattern: str) -> str:
        """生成 LIKE 條件"""
        pass

    @abstractmethod
    def sum(self, field: str, alias: Optional[str] = None) -> str:
        """生成 SUM 聚合"""
        pass

    @abstractmethod
    def count(self, field: str = "*", alias: Optional[str] = None) -> str:
        """生成 COUNT 聚合"""
        pass

    @abstractmethod
    def join(
        self,
        left_table: str,
        right_table: str,
        left_field: str,
        right_field: str,
        join_type: str = "LEFT",
    ) -> str:
        """生成 JOIN 語法"""
        pass

    @abstractmethod
    def limit(self, count: int) -> str:
        """生成 LIMIT 子句"""
        pass

    @abstractmethod
    def execute(self, sql_query: str) -> SQLResult:
        """執行 SQL 查詢"""
        pass


class DuckDBAdapter(SQLAdapter):
    """DuckDB 適配器 - 支援 S3 Parquet 存儲"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.s3_endpoint = self.config.get("s3_endpoint") or "http://localhost:8334"
        self.bucket = self.config.get("bucket") or "tiptop-raw"
        self._connection: Any = None

    @property
    def dialect_name(self) -> str:
        return "duckdb"

    def _ensure_connection(self):
        if self._connection is None:
            import duckdb

            self._connection = duckdb.connect(database=":memory:")
            access_key = self.config.get("s3_access_key") or "admin"
            secret_key = self.config.get("s3_secret_key") or "admin123"
            self._connection.execute(f"""
                CREATE SECRET IF NOT EXISTS s3_secret
                TYPE S3
                ENDPOINT '{self.s3_endpoint}'
                ACCESS_KEY '{access_key}'
                SECRET_KEY '{secret_key}'
                USE_SSL false
            """)

    def table_source(self, table: str, schema: Optional[str] = None) -> str:
        return f"read_parquet('s3://{self.bucket}/raw/v1/{table}/year=*/month=*/data.parquet', hive_partitioning=true)"

    def cast(self, expr: str, type: str) -> str:
        type_map = {"V": "VARCHAR", "N": "DOUBLE", "D": "DATE"}
        return f"CAST({expr} AS {type_map.get(type, type)})"

    def concat(self, *args: str) -> str:
        return f"CONCAT({', '.join(args)})"

    def like(self, field: str, pattern: str) -> str:
        return f"{field} LIKE '{pattern}'"

    def sum(self, field: str, alias: Optional[str] = None) -> str:
        result = f"SUM({field})"
        if alias:
            result += f" AS {alias}"
        return result

    def count(self, field: str = "*", alias: Optional[str] = None) -> str:
        result = f"COUNT({field})"
        if alias:
            result += f" AS {alias}"
        return result

    def join(
        self,
        left_table: str,
        right_table: str,
        left_field: str,
        right_field: str,
        join_type: str = "LEFT",
    ) -> str:
        left_src = self.table_source(left_table)
        right_src = self.table_source(right_table)
        return f"{left_src} AS t1 {join_type} JOIN {right_src} AS t2 ON t1.{left_field} = t2.{right_field}"

    def limit(self, count: int) -> str:
        return f"LIMIT {count}"

    def execute(self, sql_query: str) -> SQLResult:
        try:
            self._ensure_connection()
            result = self._connection.execute(sql_query)
            rows = result.fetchall()
            columns = [desc[0] for desc in result.description] if result.description else []
            data = [dict(zip(columns, row)) for row in rows]
            return SQLResult(success=True, rows=data, row_count=len(data), sql_query=sql_query)
        except Exception as e:
            return SQLResult(success=False, error=str(e), sql_query=sql_query)


class OracleAdapter(SQLAdapter):
    """Oracle 適配器 - 未來擴展"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @property
    def dialect_name(self) -> str:
        return "oracle"

    def table_source(self, table: str, schema: Optional[str] = None) -> str:
        schema_prefix = f"{schema}." if schema else ""
        return f"{schema_prefix}{table.upper()}"

    def cast(self, expr: str, type: str) -> str:
        return f"CAST({expr} AS {type})"

    def concat(self, *args: str) -> str:
        return " || ".join(args)

    def like(self, field: str, pattern: str) -> str:
        return f"{field} LIKE '{pattern}'"

    def sum(self, field: str, alias: Optional[str] = None) -> str:
        result = f"SUM({field})"
        if alias:
            result += f" {alias}"
        return result

    def count(self, field: str = "*", alias: Optional[str] = None) -> str:
        result = f"COUNT({field})"
        if alias:
            result += f" {alias}"
        return result

    def join(
        self,
        left_table: str,
        right_table: str,
        left_field: str,
        right_field: str,
        join_type: str = "LEFT",
    ) -> str:
        left_src = self.table_source(left_table)
        right_src = self.table_source(right_table)
        return f"{left_src} t1 {join_type} JOIN {right_src} t2 ON t1.{left_field.upper()} = t2.{right_field.upper()}"

    def limit(self, count: int) -> str:
        return f"ROWNUM <= {count}"

    def execute(self, sql_query: str) -> SQLResult:
        return SQLResult(success=False, error="Oracle adapter not implemented yet")


class MySQLAdapter(SQLAdapter):
    """MySQL 適配器 - 未來擴展"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @property
    def dialect_name(self) -> str:
        return "mysql"

    def table_source(self, table: str, schema: Optional[str] = None) -> str:
        schema_prefix = f"{schema}." if schema else ""
        return f"`{schema_prefix}{table}`"

    def cast(self, expr: str, type: str) -> str:
        return f"CAST({expr} AS {type})"

    def concat(self, *args: str) -> str:
        return f"CONCAT({', '.join(args)})"

    def like(self, field: str, pattern: str) -> str:
        return f"{field} LIKE '{pattern}'"

    def sum(self, field: str, alias: Optional[str] = None) -> str:
        result = f"SUM({field})"
        if alias:
            result += f" AS `{alias}`"
        return result

    def count(self, field: str = "*", alias: Optional[str] = None) -> str:
        result = f"COUNT({field})"
        if alias:
            result += f" AS `{alias}`"
        return result

    def join(
        self,
        left_table: str,
        right_table: str,
        left_field: str,
        right_field: str,
        join_type: str = "LEFT",
    ) -> str:
        left_src = self.table_source(left_table)
        right_src = self.table_source(right_table)
        return f"{left_src} AS t1 {join_type} JOIN {right_src} AS t2 ON t1.`{left_field}` = t2.`{right_field}`"

    def limit(self, count: int) -> str:
        return f"LIMIT {count}"

    def execute(self, sql_query: str) -> SQLResult:
        return SQLResult(success=False, error="MySQL adapter not implemented yet")


class SQLAdapterFactory:
    """SQL Adapter 工廠"""

    _adapters: Dict[str, type] = {
        "duckdb": DuckDBAdapter,
        "oracle": OracleAdapter,
        "mysql": MySQLAdapter,
    }

    @classmethod
    def create(cls, dialect: str, config: Optional[Dict[str, Any]] = None) -> SQLAdapter:
        adapter_class = cls._adapters.get(dialect.lower())
        if not adapter_class:
            raise ValueError(f"不支援的資料庫類型: {dialect}")
        return adapter_class(config)

    @classmethod
    def register(cls, dialect: str, adapter_class: type):
        cls._adapters[dialect.lower()] = adapter_class

    @classmethod
    def supported_dialects(cls) -> List[str]:
        return list(cls._adapters.keys())
