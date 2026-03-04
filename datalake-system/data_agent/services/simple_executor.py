# 代碼功能說明: v5 簡化版 DuckDB 執行器（使用本地 DuckDB）
# 創建日期: 2026-03-02
# 創建人: Daniel Chung
# 用途: v5 端點使用，支援 summary/list 模式

"""SimpleDBExecutor - 簡化版 DuckDB 執行器

v5 專用執行器，支援：
- return_mode: summary / list
- summary: 聚合 + 前 10 筆 + 總數
- list: 最多 1000 筆 + 總數

使用本地 DuckDB 數據庫（與 V4 相同）
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

import duckdb

from data_agent.services.schema_driven_query.config import get_config

logger = logging.getLogger(__name__)

# 最大返回筆數限制
MAX_ROWS_LIMIT = 1000
SUMMARY_ROWS = 10


class SimpleDBExecutor:
    """簡化版 DuckDB 執行器"""

    def __init__(self):
        self.config = get_config()
        self.duckdb_config = self.config.duckdb

    def _get_connection(self):
        """建立 DuckDB 連線"""
        return duckdb.connect(
            database=self.duckdb_config.database,
            config={
                "temp_directory": self.duckdb_config.temp_directory,
                "memory_limit": self.duckdb_config.memory_limit,
                "worker_threads": self.duckdb_config.threads,
            },
        )

    def _strip_limit(self, sql: str) -> str:
        """移除 SQL 中的 LIMIT 子句"""
        return re.sub(r"LIMIT\s+\d+", "", sql, flags=re.IGNORECASE).strip().rstrip(";")

    def execute(
        self,
        sql: str,
        return_mode: str = "summary",
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """執行 SQL 查詢"""
        start_time = time.time()

        logger.debug(f"v5 executing SQL: {sql[:200]}...")

        try:
            connection = self._get_connection()
            connection.execute(f"SET memory_limit = '{self.duckdb_config.max_memory}'")

            if return_mode == "summary":
                result = self._execute_summary(connection, sql)
            else:
                result = self._execute_list(connection, sql)

            connection.close()

            execution_time = int((time.time() - start_time) * 1000)
            result["execution_time_ms"] = execution_time

            logger.info(f"v5 executed: {result['row_count']} rows, {execution_time}ms")
            return result

        except Exception as e:
            logger.error(f"v5 execution failed: {e}")
            raise SimpleDBExecutionError(str(e), sql)

    def _execute_summary(self, connection, sql: str) -> Dict[str, Any]:
        """執行 summary 模式"""
        sql_upper = sql.upper()
        has_aggregation = any(
            kw in sql_upper for kw in ["GROUP BY", "SUM(", "COUNT(", "AVG(", "MAX(", "MIN("]
        )

        if has_aggregation:
            cursor = connection.cursor()
            cursor.execute(sql)
            data, columns = self._fetch_results(cursor)
            total = len(data)
            if "LIMIT" in sql_upper:
                count_sql = self._strip_limit(sql)
                count_sql = f"SELECT COUNT(*) as _total FROM ({count_sql}) _sub"
                try:
                    cursor.execute(count_sql)
                    total = cursor.fetchone()[0]
                except Exception:
                    pass
        else:
            aggregation_sql = self._add_aggregation(sql)
            cursor = connection.cursor()
            cursor.execute(aggregation_sql)
            agg_data, agg_columns = self._fetch_results(cursor)

            limit_sql = self._strip_limit(sql) + f" LIMIT {SUMMARY_ROWS}"
            cursor.execute(limit_sql)
            raw_data, raw_columns = self._fetch_results(cursor)

            total = self._get_total_count(connection, sql)
            data = agg_data + raw_data
            columns = agg_columns if agg_columns else raw_columns

        return {
            "data": data,
            "row_count": len(data),
            "columns": columns if columns else [],
            "pagination": {
                "displayed": len(data),
                "total": total,
            },
        }

    def _execute_list(self, connection, sql: str) -> Dict[str, Any]:
        """執行 list 模式"""
        sql_no_limit = self._strip_limit(sql)
        limit_sql = sql_no_limit + f" LIMIT {MAX_ROWS_LIMIT}"

        cursor = connection.cursor()
        cursor.execute(limit_sql)
        data, columns = self._fetch_results(cursor)

        total = self._get_total_count(connection, sql)

        return {
            "data": data,
            "row_count": len(data),
            "columns": columns if columns else [],
            "pagination": {
                "displayed": len(data),
                "total": total,
            },
        }

    def _add_aggregation(self, sql: str) -> str:
        """為 SQL 添加聚合查詢"""
        sql = sql.strip().rstrip(";")
        select_match = re.match(r"SELECT\s+(.+?)\s+FROM", sql, re.IGNORECASE)
        if select_match:
            select_part = select_match.group(1).strip()
            if select_part == "*":
                where_match = re.search(r"WHERE\s+(\w+)\s*=\s*'([^']+)'", sql, re.IGNORECASE)
                if where_match:
                    column = where_match.group(1)
                    return sql.replace(
                        "SELECT *",
                        f"SELECT {column}, COUNT(*) as record_count",
                        1,
                    )
        return f"SELECT COUNT(*) as total_count FROM ({sql}) _sub"

    def _get_total_count(self, connection, sql: str) -> int:
        """計算總數"""
        count_sql = self._strip_limit(sql)
        count_sql = f"SELECT COUNT(*) as _total FROM ({count_sql}) _sub"

        try:
            cursor = connection.cursor()
            cursor.execute(count_sql)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.warning(f"Failed to get total count: {e}")
            return 0

    def _fetch_results(self, cursor) -> tuple[List[Dict[str, Any]], List[str]]:
        """獲取查詢結果"""
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

            return data, columns

        return [], []


class SimpleDBExecutionError(Exception):
    def __init__(self, message: str, sql: str):
        self.message = message
        self.sql = sql
        super().__init__(f"SimpleDB Execution Error: {message}\nSQL: {sql}")


_executor: Optional[SimpleDBExecutor] = None


def get_simple_executor() -> SimpleDBExecutor:
    global _executor
    if _executor is None:
        _executor = SimpleDBExecutor()
    return _executor
