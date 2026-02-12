# 代碼功能說明: SQL 執行器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""SQL 執行器

職責：
- 執行 Oracle SQL
- 管理連線池
- 處理超時和錯誤
"""

import os
import logging
import time
from typing import Dict, Any, List, Optional

from .config import get_config, SchemaDrivenQueryConfig, OracleConfig

logger = logging.getLogger(__name__)


class SQLExecutor:
    """
    SQL 執行器

    支援 Oracle 資料庫
    """

    def __init__(
        self,
        config: Optional[SchemaDrivenQueryConfig] = None,
        oracle_config: Optional[OracleConfig] = None,
    ):
        self.config = config or get_config()
        self.oracle_config = oracle_config or self.config.oracle

        # 設定環境變數
        self._setup_env()

        # 連線池
        self._connection = None

    def _setup_env(self):
        """設定環境變數"""
        lib_path = self.oracle_config.lib_path
        libaio_path = self.oracle_config.libaio_path

        if "LD_LIBRARY_PATH" in os.environ:
            if lib_path not in os.environ["LD_LIBRARY_PATH"]:
                os.environ["LD_LIBRARY_PATH"] = (
                    f"{lib_path}:{libaio_path}:{os.environ['LD_LIBRARY_PATH']}"
                )
        else:
            os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{libaio_path}"

    def _get_connection(self):
        """獲取連線"""
        import oracledb

        if self._connection is None:
            oracledb.init_oracle_client(lib_dir=self.oracle_config.lib_path)

            self._connection = oracledb.connect(
                user=self.oracle_config.user,
                password=self.oracle_config.password,
                dsn=self.oracle_config.dsn,
            )

            logger.info(f"Connected to Oracle: {self.oracle_config.dsn}")

        return self._connection

    def execute(self, sql: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        執行 SQL

        Args:
            sql: SQL 語句
            timeout: 超時時間（秒）

        Returns:
            Dict: 執行結果
        """
        timeout = timeout or self.config.default_timeout

        start_time = time.time()

        try:
            connection = self._get_connection()
            cursor = connection.cursor()

            # 執行查詢
            cursor.execute(sql)

            # 獲取欄位名稱
            columns = [col[0] for col in cursor.description]

            # 獲取結果
            rows = cursor.fetchall()

            # 轉換為 Dict
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # 處理 Oracle DATE 類型
                    if hasattr(value, "strftime"):
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    row_dict[col] = value
                data.append(row_dict)

            execution_time = int((time.time() - start_time) * 1000)

            logger.info(f"SQL executed: {len(data)} rows, {execution_time}ms")

            return {
                "data": data,
                "row_count": len(data),
                "execution_time_ms": execution_time,
                "columns": columns,
            }

        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise SQLExecutionError(str(e), sql)

    def execute_many(
        self, sql: str, params_list: List[Dict], batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        批量執行 SQL

        Args:
            sql: SQL 模板
            params_list: 參數列表
            batch_size: 批次大小

        Returns:
            Dict: 執行結果
        """
        start_time = time.time()

        try:
            connection = self._get_connection()
            cursor = connection.cursor()

            total_rows = 0

            for i in range(0, len(params_list), batch_size):
                batch = params_list[i : i + batch_size]
                cursor.executemany(sql, batch)
                total_rows += cursor.rowcount

            connection.commit()

            execution_time = int((time.time() - start_time) * 1000)

            return {"row_count": total_rows, "execution_time_ms": execution_time}

        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise SQLExecutionError(str(e), sql)

    def close(self):
        """關閉連線"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SQLExecutionError(Exception):
    """SQL 執行錯誤"""

    def __init__(self, message: str, sql: str):
        self.message = message
        self.sql = sql
        super().__init__(f"SQL Execution Error: {message}\nSQL: {sql}")


class ExecutorFactory:
    """執行器工廠

    支援動態切換資料來源：
    - "ORACLE": SQLExecutor
    - "DUCKDB": DuckDBExecutor
    """

    def __init__(self, config: Optional[SchemaDrivenQueryConfig] = None):
        self.config = config or get_config()
        self._executors = {}

    def get_executor(self, datasource: Optional[str] = None) -> Any:
        """
        獲取執行器實例

        Args:
            datasource: 資料來源 ("ORACLE" 或 "DUCKDB")
                       若為 None，則使用 config.datasource

        Returns:
            執行器實例
        """
        datasource = datasource or self.config.datasource
        datasource = datasource.upper()

        logger.info(
            f"ExecutorFactory.get_executor(): datasource={datasource}, config.datasource={self.config.datasource}"
        )

        if datasource not in self._executors:
            self._executors[datasource] = self._create_executor(datasource)

        return self._executors[datasource]

    def _create_executor(self, datasource: str) -> Any:
        """創建指定類型的執行器"""
        if datasource == "DUCKDB":
            from .duckdb_executor import DuckDBExecutor

            return DuckDBExecutor(
                config=self.config.duckdb,
                s3_config=self.config.duckdb.s3,
            )

        elif datasource == "ORACLE":
            return SQLExecutor(config=self.config)

        else:
            raise ValueError(f"Unknown datasource: {datasource}")

    def execute(
        self, sql: str, datasource: Optional[str] = None, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """執行查詢"""
        executor = self.get_executor(datasource)
        return executor.execute(sql, timeout)

    def close_all(self):
        """關閉所有執行器"""
        for executor in self._executors.values():
            if hasattr(executor, "close"):
                executor.close()
        self._executors.clear()

    def validate_connection(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """驗證連線"""
        executor = self.get_executor(datasource)

        if hasattr(executor, "validate_connection"):
            return executor.validate_connection()

        return {"status": "healthy", "datasource": datasource or self.config.datasource}


def get_executor(
    datasource: Optional[str] = None, config: Optional[SchemaDrivenQueryConfig] = None
) -> Any:
    """
    獲取執行器實例

    Args:
        datasource: 資料來源 ("ORACLE" 或 "DUCKDB")
        config: 配置

    Returns:
        執行器實例
    """
    factory = ExecutorFactory(config=config)
    return factory.get_executor(datasource)
