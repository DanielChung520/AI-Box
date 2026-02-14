# 代碼功能說明: DuckDB SQL 執行器
# 創建日期: 2026-02-12
# 創建人: Daniel Chung
# 用途: 執行 DuckDB/S3 Parquet 查詢

"""DuckDBExecutor

職責：
- 執行 DuckDB SQL 查詢
- 連接 S3 (SeaweedFS)
- 管理連線和錯誤處理
- 查詢結果快取
"""

import logging
import time
import re
import hashlib
from typing import Any, Dict, List, Optional
from collections import OrderedDict
from threading import Lock

import duckdb

from .config import DuckDBConfig, S3Config

logger = logging.getLogger(__name__)


class QueryResultCache:
    """查詢結果快取"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: OrderedDict = OrderedDict()
        self.lock = Lock()

    def _make_key(self, sql: str) -> str:
        return hashlib.md5(sql.encode("utf-8")).hexdigest()

    def get(self, sql: str) -> Optional[Dict]:
        with self.lock:
            key = self._make_key(sql)
            if key not in self.cache:
                return None

            entry = self.cache[key]
            if time.time() - entry["timestamp"] > self.ttl:
                del self.cache[key]
                return None

            self.cache.move_to_end(key)
            logger.info(f"Query result cache hit")
            return entry["data"]

    def set(self, sql: str, data: Dict):
        with self.lock:
            key = self._make_key(sql)
            if key in self.cache:
                del self.cache[key]
            elif len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            self.cache[key] = {"data": data, "timestamp": time.time()}


_query_result_cache = QueryResultCache(max_size=50, ttl_seconds=600)


def parse_time_range_from_sql(sql: str) -> tuple[Optional[str], Optional[str]]:
    """從 SQL 中解析 TIME_RANGE，返回 (year, month)"""
    import re

    # 匹配 BETWEEN '2026-01-01' AND '2026-02-01' 格式
    match = re.search(
        r"BETWEEN\s+'(\d{4})-(\d{2})-(\d{2})'\s+AND\s+'(\d{4})-(\d{2})-(\d{2})'", sql, re.IGNORECASE
    )
    if match:
        return match.group(1), match.group(2)  # year, month

    # 匹配 BETWEEN 2026-01-01 AND 2026-02-01 格式
    match = re.search(
        r"BETWEEN\s+(\d{4})-(\d{2})-(\d{2})\s+AND\s+(\d{4})-(\d{2})-(\d{2})", sql, re.IGNORECASE
    )
    if match:
        return match.group(1), match.group(2)

    return None, None


class S3PathMapper:
    """Oracle Table → S3 Parquet Path 映射"""

    TABLE_S3_PATH = {
        "INAG_T": "s3://tiptop-raw/raw/v1/tiptop_jp/INAG_T/year=*/month=*/data.parquet",
        "SFAA_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFAA_T/year=*/month=*/data.parquet",
        "SFCA_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFCA_T/year=*/month=*/data.parquet",
        "SFCB_T": "s3://tiptop-raw/raw/v1/tiptop_jp/SFCB_T/year=*/month=*/data.parquet",
        "XMDG_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDG_T/year=*/month=*/data.parquet",
        "XMDH_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDH_T/year=*/month=*/data.parquet",
        "XMDT_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDT_T/year=*/month=*/data.parquet",
        "XMDU_T": "s3://tiptop-raw/raw/v1/tiptop_jp/XMDU_T/year=*/month=*/data.parquet",
    }

    def __init__(self, s3_config: S3Config):
        self.s3_config = s3_config

    def map_table(self, table_name: str) -> str:
        """將 Table 名稱映射為 S3 Parquet 路徑"""
        if table_name in self.TABLE_S3_PATH:
            base_path = self.TABLE_S3_PATH[table_name]
            bucket = self.s3_config.bucket
            s3_path = base_path.replace("s3://tiptop-raw", f"s3://{bucket}")
            return s3_path
        return table_name

    def map_sql(self, sql: str) -> str:
        """將 SQL 中的 Table 名稱替換為 S3 Parquet 路徑"""
        import re

        for table_name in self.TABLE_S3_PATH:
            s3_path = self.map_table(table_name)
            read_parquet_func = f"read_parquet('{s3_path}') AS _{table_name.lower().rstrip('_t')}"

            # Handle FROM clause with comma-separated tables (implicit JOIN)
            sql = re.sub(
                rf"(?i)(FROM\s+)({table_name})(?=\s*[,)])",
                rf"\1{read_parquet_func}",
                sql,
            )

            # Handle FROM clause with alias
            sql = re.sub(
                rf"(?i)(FROM\s+)({table_name})(\s+(?:AS\s+)?([a-zA-Z0-9_]+))",
                rf"\1{read_parquet_func} \4",
                sql,
            )

            # Handle FROM clause with quoted table name
            sql = re.sub(
                rf'(?i)(FROM\s+)("{table_name}")(\s+(?:AS\s+)?([a-zA-Z0-9_]+))',
                rf"\1{read_parquet_func} \4",
                sql,
            )

            # Handle FROM clause WITHOUT alias (standalone table) - 添加別名
            sql = re.sub(
                rf"(?i)(FROM\s+)({table_name})(?=\s+(?:INNER|LEFT|RIGHT|OUTER|CROSS|WHERE|GROUP|ORDER|LIMIT|HAVING|$|and|OR))",
                rf"\1{read_parquet_func}",
                sql,
            )

            # Handle FROM clause without alias at end of statement - 添加別名
            sql = re.sub(rf"(?i)(FROM\s+)({table_name})(?=\s*$)", rf"\1{read_parquet_func}", sql)

            # Handle comma-separated table in FROM (e.g., "FROM INAG_T, SFCA_T")
            sql = re.sub(
                rf"(?i)(,\s*){table_name}(?=\s*[,)])",
                rf", {read_parquet_func}",
                sql,
            )
            sql = re.sub(
                rf"(?i)(,\s*){table_name}(?=\s+(?:WHERE|GROUP|ORDER|LIMIT|HAVING|$))",
                rf", {read_parquet_func}",
                sql,
            )

            # Handle JOIN clause with alias
            sql = re.sub(
                rf"(?i)(JOIN\s+)({table_name})(\s+(?:AS\s+)?([a-zA-Z0-9_]+))",
                rf"\1{read_parquet_func} \4",
                sql,
            )

            # Handle JOIN clause with quoted table name
            sql = re.sub(
                rf'(?i)(JOIN\s+)("{table_name}")(\s+(?:AS\s+)?([a-zA-Z0-9_]+))',
                rf"\1{read_parquet_func} \4",
                sql,
            )

            # Handle JOIN clause WITHOUT alias - 添加別名
            sql = re.sub(
                rf"(?i)(JOIN\s+)({table_name})(?=\s+(?:INNER|LEFT|RIGHT|OUTER|CROSS|WHERE|GROUP|ORDER|LIMIT|ON|and|OR|$))",
                rf"\1{read_parquet_func}",
                sql,
            )

            # Handle JOIN clause without alias at end
            sql = re.sub(
                rf"(?i)(JOIN\s+)({table_name})(?=\s*$)",
                rf"\1{read_parquet_func}",
                sql,
            )

        # 解析 TIME_RANGE 並優化 S3 路徑
        year, month = parse_time_range_from_sql(sql)
        if year and month:
            logger.info(f"Applying TIME_RANGE filter: year={year}, month={month}")
            # 將 year=*/month=* 替換為特定的 year/month
            sql = re.sub(r"year=\*/month=\*", f"year={year}/month={month:02d}", sql)

        return sql


class DuckDBExecutor:
    """DuckDB SQL 執行器"""

    def __init__(
        self,
        config: Optional[DuckDBConfig] = None,
        s3_config: Optional[S3Config] = None,
    ):
        self.config = config or DuckDBConfig()
        self.s3_config = s3_config or self.config.s3
        self._connection = None
        self._path_mapper = S3PathMapper(self.s3_config)

    def _map_sql(self, sql: str) -> str:
        """映射 SQL 中的 Table 為 S3 Path，並優化 TIME_RANGE"""
        # 先映射表格
        mapped_sql = self._path_mapper.map_sql(sql)

        # 解析 TIME_RANGE 並優化 S3 路徑
        year, month = parse_time_range_from_sql(mapped_sql)
        if year and month:
            logger.info(f"Applying TIME_RANGE optimization: year={year}, month={month}")
            # 將 year=*/month=* 替換為特定的 year/month
            mapped_sql = re.sub(r"year=\*/month=\*", f"year={year}/month={month:02d}", mapped_sql)

        # 添加預設 LIMIT（如果沒有的話）
        if "LIMIT" not in mapped_sql.upper():
            mapped_sql = mapped_sql.strip().rstrip(";") + " LIMIT 100"

        return mapped_sql

    def execute(self, sql: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        執行 SQL 查詢

        Args:
            sql: SQL 語句
            timeout: 超時時間（秒）

        Returns:
            Dict: 執行結果
        """
        start_time = time.time()

        try:
            import duckdb

            try:
                default_conn = duckdb.default_connection()
                if default_conn is not None:
                    try:
                        default_conn.close()
                    except Exception:
                        pass
            except Exception:
                pass

            connection = duckdb.connect(
                database=":memory:",
                config={
                    "s3_endpoint": self.s3_config.endpoint_host,
                    "s3_access_key_id": self.s3_config.access_key,
                    "s3_secret_access_key": self.s3_config.secret_key,
                    "s3_region": self.s3_config.region,
                    "s3_use_ssl": str(self.s3_config.use_ssl).lower(),
                    "s3_url_style": self.s3_config.url_style,
                    "temp_directory": self.config.temp_directory,
                    "memory_limit": self.config.memory_limit,
                    "worker_threads": self.config.threads,
                },
            )

            # 設定工作記憶體（使用正確的 DuckDB 參數名稱）
            connection.execute(f"SET memory_limit = '{self.config.max_memory}'")

            mapped_sql = self._map_sql(sql)
            logger.debug(f"Executing mapped SQL: {mapped_sql[:200]}...")

            cursor = connection.cursor()
            cursor.execute(mapped_sql)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if hasattr(value, "strftime"):
                            value = value.strftime("%Y-%m-%d %H:%M:%S")
                        row_dict[col] = value
                    data.append(row_dict)
            else:
                columns = []
                data = []

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(f"DuckDB executed: {len(data)} rows, {execution_time}ms")

            connection.close()

            return {
                "data": data,
                "row_count": len(data),
                "execution_time_ms": execution_time,
                "columns": columns,
            }

        except Exception as e:
            logger.error(f"DuckDB execution failed: {e}")
            raise DuckDBExecutionError(str(e), sql)

    def validate_connection(self) -> Dict[str, Any]:
        """驗證 S3 連線"""
        try:
            result = self.execute("SELECT 1")
            return {
                "status": "healthy",
                "duckdb": True,
                "s3_endpoint": self.s3_config.endpoint,
                "s3_bucket": self.s3_config.bucket,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def close(self):
        """關閉連線"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DuckDBExecutionError(Exception):
    """DuckDB 執行錯誤"""

    def __init__(self, message: str, sql: str):
        self.message = message
        self.sql = sql
        super().__init__(f"DuckDB Execution Error: {message}\nSQL: {sql}")


def get_duckdb_executor(
    config: Optional[DuckDBConfig] = None,
) -> DuckDBExecutor:
    """獲取 DuckDBExecutor 實例"""
    return DuckDBExecutor(config=config)
