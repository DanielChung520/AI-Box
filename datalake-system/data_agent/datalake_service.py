# 代碼功能說明: Datalake 數據查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""Datalake 數據查詢服務實現

支持舊架構（.jsonl/.json）和新架構（.parquet）
整合 DuckDB 作為 SQL 查詢引擎
"""

import json
import os

# 導入 AI-Box 項目的模塊（datalake-system 在 AI-Box 項目中）
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
import structlog
from botocore.exceptions import ClientError
from io import BytesIO

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from dotenv import load_dotenv

from storage.s3_storage import S3FileStorage, SeaweedFSService
from .config_manager import get_config

# 加載環境變數（使用絕對路徑）
# datalake-system 在 AI-Box 項目中，需要指向 AI-Box 根目錄的 .env
base_dir = Path(__file__).resolve().parent.parent.parent  # AI-Box 根目錄
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = structlog.get_logger(__name__)


class DatalakeService:
    """Datalake 數據查詢服務"""

    def __init__(self) -> None:
        """初始化 Datalake 服務"""
        self._config = get_config()
        self._storage: Optional[S3FileStorage] = None
        self._logger = logger
        # 從配置讀取預設 bucket
        self._default_bucket = self._config.get_datalake_bucket()
        # 初始化 DuckDB
        self._duckdb_con = duckdb.connect(":memory:")
        self._configure_duckdb()

    def _get_storage(self) -> S3FileStorage:
        """獲取 S3 存儲實例"""
        if self._storage is None:
            endpoint = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8334")
            access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY", "admin")
            secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY", "admin123")
            use_ssl = os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"

            self._storage = S3FileStorage(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                use_ssl=use_ssl,
                service_type=SeaweedFSService.DATALAKE,
            )

        return self._storage

    def _configure_duckdb(self) -> None:
        """配置 DuckDB 的 S3 連接參數"""
        try:
            endpoint = (
                os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT", "localhost:8334")
                .replace("http://", "")
                .replace("https://", "")
            )
            access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY", "admin")
            secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY", "admin123")
            use_ssl = os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"
            max_memory = os.getenv("DATA_AGENT_DUCKDB_MAX_MEMORY", "4GB")

            self._duckdb_con.execute(f"""
                SET s3_endpoint = '{endpoint}';
                SET s3_access_key_id = '{access_key}';
                SET s3_secret_access_key = '{secret_key}';
                SET s3_use_ssl = {str(use_ssl).lower()};
                SET s3_url_style = 'path';
                SET max_memory = '{max_memory}';
            """)
            self._logger.info("DuckDB S3 配置完成", endpoint=endpoint, use_ssl=use_ssl)
        except Exception as e:
            self._logger.error("DuckDB 配置失敗", error=str(e))
            raise

    async def query(
        self,
        bucket: Optional[str] = None,
        key: str = "",
        query_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢 Datalake 數據

        Args:
            bucket: Bucket 名稱（如果不提供，使用預設 bucket）
            key: 數據鍵（文件路徑）或表名
            query_type: 查詢類型（exact/fuzzy/table）（可選，默認從配置讀取）
            filters: 過濾條件
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            查詢結果
        """
        try:
            # 從配置讀取默認值
            if bucket is None or bucket == "":
                bucket = self._default_bucket
            if query_type is None:
                query_type = self._config.get_datalake_query_type()

            storage = self._get_storage()

            # 根據查詢類型執行查詢
            if query_type == "exact":
                result = await self._query_exact(storage, bucket, key)
            elif query_type == "fuzzy":
                result = await self._query_fuzzy(storage, bucket, key, filters)
            elif query_type == "table":
                # 新架構：按表名查詢（使用新架構的路徑結構）
                result = await self._query_table(storage, bucket, key, filters)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported query_type: {query_type}",
                }

            # 應用過濾條件（如果提供）
            if filters and result.get("success"):
                result["rows"] = self._apply_filters(result.get("rows", []), filters)
                result["row_count"] = len(result["rows"])

            # 驗證數據（如果提供 Schema）
            if result.get("success"):
                schema = await self._get_schema_for_key(bucket, key)
                if schema:
                    validation = self._validate_data_against_schema(result.get("rows", []), schema)
                    result["validation"] = validation

            return result

        except Exception as e:
            self._logger.error("Datalake query failed", error=str(e), bucket=bucket, key=key)
            return {
                "success": False,
                "error": str(e),
            }

    async def _query_table(
        self,
        storage: S3FileStorage,
        bucket: str,
        table_name: str,
        filters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """按表名查詢（新架構：使用分區路徑結構）

        Args:
            storage: S3FileStorage 實例
            bucket: Bucket 名稱（如果不提供，使用預設 bucket）
            table_name: 表名（如：ima_file, img_file）
            filters: 過濾條件（可選）

        Returns:
            查詢結果
        """
        try:
            # 新架構路徑結構：raw/v1/{table_name}/year={year}/month={month}/data.parquet
            # 嘗試多個路徑（與 Dashboard 一致），因模擬數據可能在不同分區
            from datetime import datetime

            now = datetime.now()
            prefixes_to_try = [
                f"raw/v1/{table_name}/year={now.year}/month={now.month:02d}/",
                f"raw/v1/{table_name}/year={now.year - 1}/month=12/",
                f"raw/v1/{table_name}/year=2025/month=12/",
                f"raw/v1/{table_name}/year=2026/month=01/",
            ]
            # 去重並保持順序
            seen = set()
            unique_prefixes = []
            for p in prefixes_to_try:
                if p not in seen:
                    seen.add(p)
                    unique_prefixes.append(p)

            # 從配置讀取最大行數
            max_rows = self._config.get_datalake_max_rows()

            all_rows: List[Dict[str, Any]] = []
            year_month_prefix = ""

            for prefix in unique_prefixes:
                paginator = storage.s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

                for page in pages:
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            key = obj["Key"]
                            if key.endswith("/"):
                                continue
                            if key.endswith(".parquet"):
                                try:
                                    response = storage.s3_client.get_object(Bucket=bucket, Key=key)
                                    df = pd.read_parquet(BytesIO(response["Body"].read()))
                                    rows = df.to_dict("records")
                                    all_rows.extend(rows)
                                    year_month_prefix = prefix
                                    if len(all_rows) >= max_rows:
                                        break
                                except Exception as e:
                                    self._logger.warning(
                                        "Failed to read Parquet file",
                                        key=key,
                                        error=str(e),
                                    )
                                    continue
                    if len(all_rows) >= max_rows:
                        break
                if all_rows:
                    break

            all_rows = all_rows[:max_rows]

            return {
                "success": True,
                "rows": all_rows,
                "row_count": len(all_rows),
                "query_type": "table",
                "bucket": bucket,
                "table_name": table_name,
                "path_prefix": year_month_prefix or unique_prefixes[0],
                "max_rows": max_rows,
            }

        except Exception as e:
            self._logger.error("Table query failed", error=str(e), table_name=table_name)
            return {
                "success": False,
                "error": str(e),
            }

    async def _query_exact(
        self,
        storage: S3FileStorage,
        bucket: str,
        key: str,
    ) -> Dict[str, Any]:
        """精確查詢：讀取單個文件（支持舊架構）

        Args:
            storage: S3FileStorage 實例
            bucket: Bucket 名稱
            key: 數據鍵

        Returns:
            查詢結果
        """
        try:
            # 從 S3 讀取文件
            response = storage.s3_client.get_object(Bucket=bucket, Key=key)

            # 判斷文件類型
            if key.endswith(".parquet"):
                # 新架構：Parquet 文件
                df = pd.read_parquet(BytesIO(response["Body"].read()))
                data = df.to_dict("records")
            else:
                # 舊架構：JSON/JSONL 文件
                content = response["Body"].read().decode("utf-8")

                if key.endswith(".jsonl"):
                    data = []
                    for line in content.split("\n"):
                        if line.strip():
                            data.append(json.loads(line))
                else:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        data = [data]

            return {
                "success": True,
                "rows": data,
                "row_count": len(data),
                "query_type": "exact",
                "bucket": bucket,
                "key": key,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                return {
                    "success": False,
                    "error": f"File not found: {bucket}/{key}",
                }
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _query_fuzzy(
        self,
        storage: S3FileStorage,
        bucket: str,
        key_prefix: str,
        filters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """模糊查詢：列出目錄並過濾（支持舊架構）

        Args:
            storage: S3FileStorage 實例
            bucket: Bucket 名稱
            key_prefix: 鍵前綴（目錄路徑）
            filters: 過濾條件（可選）

        Returns:
            查詢結果
        """
        try:
            # 列出目錄下的所有文件
            response = storage.s3_client.list_objects_v2(Bucket=bucket, Prefix=key_prefix)

            all_rows: List[Dict[str, Any]] = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue

                try:
                    file_response = storage.s3_client.get_object(Bucket=bucket, Key=key)
                    content = file_response["Body"].read().decode("utf-8")

                    if key.endswith(".jsonl"):
                        for line in content.split("\n"):
                            if line.strip():
                                all_rows.append(json.loads(line))
                    else:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            all_rows.append(data)
                        elif isinstance(data, list):
                            all_rows.extend(data)
                except Exception as e:
                    self._logger.warning("Failed to read file", key=key, error=str(e))
                    continue

            return {
                "success": True,
                "rows": all_rows,
                "row_count": len(all_rows),
                "query_type": "fuzzy",
                "bucket": bucket,
                "key_prefix": key_prefix,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _apply_filters(
        self,
        rows: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """應用過濾條件

        Args:
            rows: 數據行列表
            filters: 過濾條件

        Returns:
            過濾後的數據行列表
        """
        filtered_rows = rows

        for field, condition in filters.items():
            if isinstance(condition, dict):
                if "gte" in condition:
                    filtered_rows = [
                        row
                        for row in filtered_rows
                        if field in row and row[field] >= condition["gte"]
                    ]
                if "lte" in condition:
                    filtered_rows = [
                        row
                        for row in filtered_rows
                        if field in row and row[field] <= condition["lte"]
                    ]
                if "gt" in condition:
                    filtered_rows = [
                        row
                        for row in filtered_rows
                        if field in row and row[field] > condition["gt"]
                    ]
                if "lt" in condition:
                    filtered_rows = [
                        row
                        for row in filtered_rows
                        if field in row and row[field] < condition["lt"]
                    ]
                if "in" in condition:
                    filtered_rows = [
                        row
                        for row in filtered_rows
                        if field in row and row[field] in condition["in"]
                    ]
            else:
                filtered_rows = [
                    row for row in filtered_rows if field in row and row[field] == condition
                ]

        return filtered_rows

    async def _get_schema_for_key(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """獲取對應 key 的 Schema

        Args:
            bucket: Bucket 名稱
            key: 數據鍵

        Returns:
            Schema 定義，如果不存在則返回 None
        """
        # 從 key 推斷 schema_id
        # 例如：parts/ABC-123.json -> part_schema
        # 這裡可以根據實際需求實現更複雜的邏輯
        # TODO: 未來實現時，從 key 提取前綴作為 schema_id，並通過 SchemaService 獲取
        # 實際實現中，可以通過依賴注入的方式獲取 SchemaService
        try:
            # 暫時返回 None，等待 SchemaService 集成
            pass
        except Exception:
            pass

        return None

    async def query_sql(
        self,
        sql_query: str,
        max_rows: Optional[int] = 10,
    ) -> Dict[str, Any]:
        """對 Datalake 數據查詢 SQL 查詢（使用 DuckDB）

        支援完整的 SQL 操作：
        - WHERE 條件
        - ORDER BY
        - LIMIT
        - 聚合函數：SUM, COUNT, AVG
        - GROUP BY
        - JOIN
        - 子查詢

        Args:
            sql_query: SQL 查詢語句
            max_rows: 最大返回行數（可選，默認 10）

        Returns:
            查詢結果
        """
        try:
            import re

            self._logger.info(f"SQL 查詢（DuckDB）: {sql_query[:200]}")

            # 提取表名（支持 img_file, ima_file, tlf_file 等）
            table_match = re.search(r"FROM\s+(\w+)", sql_query, re.IGNORECASE)
            if not table_match:
                return {
                    "success": False,
                    "error": f"無法解析 SQL 中的表名: {sql_query}",
                }

            table_name = table_match.group(1).strip()

            # 映射表名到實際的 S3 Parquet 路徑
            table_mapping = {
                "img_file": "img_file",
                "ima_file": "ima_file",
                "tlf_file": "tlf_file",
                "tlf_file_large": "tlf_file_large",
                "pmc_file": "pmc_file",
                "pmn_file": "pmn_file",
                "imd_file": "imd_file",
                "ime_file": "ime_file",
                # 新增表（2026-01 JP-PoC 擴展）
                "cmc_file": "cmc_file",
                "coptc_file": "coptc_file",
                "coptd_file": "coptd_file",
                "prc_file": "prc_file",
            }

            if table_name not in table_mapping:
                return {
                    "success": False,
                    "error": f"不支援的表名: {table_name}",
                }

            # 構建 Parquet 文件路徑
            parquet_path = (
                f"s3://{self._default_bucket}/raw/v1/{table_mapping[table_name]}/**/*.parquet"
            )

            # 使用簡單的字串分割方式來處理 FROM 子句
            # 找到 FROM 關鍵字的位置
            from_pos = sql_query.upper().find("FROM ")
            if from_pos == -1:
                return {"success": False, "error": "無法找到 FROM 子句"}

            # 使用正則表達式來正確處理 FROM 子句（支援多行 SQL）
            from_pattern = r"FROM\s+(\w+)(?:\s+(\w+))?(?=\s+(?:WHERE|GROUP|ORDER|HAVING|LIMIT|JOIN|LEFT|RIGHT|INNER|OUTER|$|\)))"
            from_match = re.search(from_pattern, sql_query, re.IGNORECASE)

            if not from_match:
                return {"success": False, "error": "無法解析 SQL 中的 FROM 子句"}

            table_name_in_sql = from_match.group(1)
            from_alias = from_match.group(2) if from_match.group(2) else None

            # 構建 Parquet 文件路徑
            parquet_path = (
                f"s3://{self._default_bucket}/raw/v1/{table_mapping[table_name]}/**/*.parquet"
            )

            # 替換 FROM 子句
            from_replacement = f"FROM read_parquet('{parquet_path}', hive_partitioning=true) t1"
            if from_alias:
                duckdb_query = re.sub(
                    from_pattern, from_replacement, sql_query, flags=re.IGNORECASE
                )
                # 替換別名引用為 t1
                duckdb_query = duckdb_query.replace(f"{from_alias}.", "t1.")
            else:
                duckdb_query = re.sub(
                    from_pattern, from_replacement, sql_query, flags=re.IGNORECASE
                )
            if from_alias:
                duckdb_query = duckdb_query.replace(f"{from_alias}.", "t1.")

            # 處理 JOIN（將多個表名替換為 Parquet 路徑）
            join_count = 2
            for table_key in table_mapping:
                if table_key == table_name:
                    continue
                # 查找包含此表名的 JOIN 語句
                join_pattern = (
                    r"(JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN)\s+"
                    + re.escape(table_key)
                    + r"(\s+\w+)?"
                )
                for match in re.finditer(join_pattern, duckdb_query, re.IGNORECASE):
                    join_type = match.group(1)
                    join_alias = match.group(2) if match.group(2) else table_key
                    join_parquet_path = f"s3://{self._default_bucket}/raw/v1/{table_mapping[table_key]}/**/*.parquet"
                    replacement = f"{join_type} read_parquet('{join_parquet_path}', hive_partitioning=true) t{join_count}"
                    duckdb_query = duckdb_query.replace(match.group(0), replacement)
                    # 替換別名引用
                    if join_alias and join_alias != table_key:
                        duckdb_query = duckdb_query.replace(f"{join_alias}.", f"t{join_count}.")
                    join_count += 1

            # 添加 LIMIT 子句（如果不存在）
            if "LIMIT" not in duckdb_query.upper():
                duckdb_query += f" LIMIT {max_rows}"

            self._logger.info(f"DuckDB 執行查詢: {duckdb_query[:500]}")

            # 執行查詢
            result = self._duckdb_con.execute(duckdb_query)

            # 獲取結果
            columns = [desc[0] for desc in result.description]
            rows_data = result.fetchall()

            # 轉換為字典列表
            rows = [dict(zip(columns, row)) for row in rows_data]

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "sql_query": sql_query,
                "duckdb_query": duckdb_query,
                "query_type": "sql_duckdb",
            }

        except Exception as e:
            self._logger.error(f"SQL query (DuckDB) failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

            table_name = table_match.group(1).strip()

            # 映射表名到實際的 S3 Parquet 路徑
            table_mapping = {
                "img_file": "img_file",
                "ima_file": "ima_file",
                "tlf_file": "tlf_file",
                "tlf_file_large": "tlf_file_large",
                "pmc_file": "pmc_file",
                "pmn_file": "pmn_file",
                "imd_file": "imd_file",
                "ime_file": "ime_file",
                # 新增表（2026-01 JP-PoC 擴展）
                "cmc_file": "cmc_file",
                "coptc_file": "coptc_file",
                "coptd_file": "coptd_file",
                "prc_file": "prc_file",
            }

            if table_name not in table_mapping:
                return {
                    "success": False,
                    "error": f"不支援的表名: {table_name}",
                }

            # 構建 Parquet 文件路徑
            parquet_path = (
                f"s3://{self._default_bucket}/raw/v1/{table_mapping[table_name]}/**/*.parquet"
            )

            # 將表名替換為 Parquet 文件路徑
            # 先檢查 FROM 子句後是否有別名
            from_match = re.search(
                r"FROM\s+" + re.escape(table_name) + r"(?:\s+(\w+))?", sql_query, re.IGNORECASE
            )

            # 檢查捕獲的別名是否是 SQL 關鍵字
            sql_keywords = [
                "WHERE",
                "GROUP",
                "ORDER",
                "HAVING",
                "LIMIT",
                "JOIN",
                "LEFT",
                "RIGHT",
                "INNER",
                "OUTER",
            ]
            from_alias = None
            if from_match and from_match.group(1):
                alias = from_match.group(1)
                if alias.upper() not in sql_keywords:
                    from_alias = alias

            # 構建主表的替換（不包含 FROM 關鍵字）
            from_replacement = f"read_parquet('{parquet_path}', hive_partitioning=true) t1"

            # 精確替換 FROM 子句（只替換第一個 FROM 子句）
            duckdb_query = re.sub(
                r"(FROM\s+)" + re.escape(table_name) + r"(\s+\w+)?",
                r"\1" + from_replacement,
                sql_query,
                flags=re.IGNORECASE,
                count=1,
            )

            from_alias = from_match.group(2) if from_match and from_match.group(2) else None

            # 構建主表的替換（不包含 FROM 關鍵字）
            from_replacement = f"read_parquet('{parquet_path}', hive_partitioning=true) t1"

            # 精確替換 FROM 子句（只替換第一個 FROM 子句）
            duckdb_query = re.sub(
                r"(FROM\s+)" + re.escape(table_name) + r"(\s+\w+)?",
                r"\1" + from_replacement,
                sql_query,
                flags=re.IGNORECASE,
                count=1,
            )

            # 替換主表別名引用為 t1
            if from_alias:
                # 替換所有的別名引用（如 i.img01 → t1.img01）
                duckdb_query = duckdb_query.replace(f"{from_alias}.", "t1.")
                # 替換 ON 條件中的別名
                duckdb_query = duckdb_query.replace(
                    r"ON\s+" + re.escape(from_alias) + r"\.",
                    "ON t1.",
                    duckdb_query,
                    flags=re.IGNORECASE,
                )

            # 精確替換 FROM 子句（只替換第一個 FROM 子句）
            duckdb_query = re.sub(
                r"(FROM\s+)" + re.escape(table_name) + r"(\s+\w+)?",
                r"\1" + from_replacement,
                sql_query,
                flags=re.IGNORECASE,
                count=1,
            )

            # 替換主表別名引用為 t1
            if from_alias:
                # 替換所有的別名引用（如 i.img01 → t1.img01）
                duckdb_query = duckdb_query.replace(f"{from_alias}.", "t1.")
                # 替換 ON 條件中的別名
                duckdb_query = re.sub(
                    r"ON\s+" + re.escape(from_alias) + r"\.",
                    "ON t1.",
                    duckdb_query,
                    flags=re.IGNORECASE,
                )

            # 替換主表別名引用為 t1
            if from_alias:
                # 替換所有的別名引用（如 i.img01 → t1.img01）
                duckdb_query = duckdb_query.replace(f"{from_alias}.", "t1.")
                # 替換 ON 條件中的別名
                duckdb_query = re.sub(
                    r"ON\s+" + re.escape(from_alias) + r"\.",
                    "ON t1.",
                    duckdb_query,
                    flags=re.IGNORECASE,
                )

            # 處理 JOIN（將多個表名替換為 Parquet 路徑）
            join_count = 2
            for table_key in table_mapping:
                if table_key == table_name:
                    continue
                # 查找包含此表名的 JOIN 語句
                join_pattern = (
                    r"(JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN)\s+"
                    + re.escape(table_key)
                    + r"(\s+\w+)?"
                )
                for match in re.finditer(join_pattern, duckdb_query, re.IGNORECASE):
                    join_type = match.group(1)
                    join_alias = match.group(2) if match.group(2) else table_key
                    join_parquet_path = f"s3://{self._default_bucket}/raw/v1/{table_mapping[table_key]}/**/*.parquet"
                    replacement = f"{join_type} read_parquet('{join_parquet_path}', hive_partitioning=true) t{join_count}"
                    duckdb_query = duckdb_query.replace(match.group(0), replacement)
                    # 替換別名引用
                    if join_alias and join_alias != table_key:
                        duckdb_query = duckdb_query.replace(f"{join_alias}.", f"t{join_count}.")
                    join_count += 1

            # 添加 LIMIT 子句（如果不存在）
            if "LIMIT" not in duckdb_query.upper():
                duckdb_query += f" LIMIT {max_rows}"

            self._logger.info(f"DuckDB 執行查詢: {duckdb_query[:500]}")

            # 執行查詢
            result = self._duckdb_con.execute(duckdb_query)

            # 獲取結果
            columns = [desc[0] for desc in result.description]
            rows_data = result.fetchall()

            # 轉換為字典列表
            rows = [dict(zip(columns, row)) for row in rows_data]

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "sql_query": sql_query,
                "duckdb_query": duckdb_query,
                "query_type": "sql_duckdb",
            }

        except Exception as e:
            self._logger.error(f"SQL query (DuckDB) failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    def _parse_where_clause(self, where_clause: str) -> list:
        """解析 WHERE 子句為條件列表

        Args:
            where_clause: WHERE 子句字符串

        Returns:
            條件列表：[{"column": "img02", "operator": "=", "value": "W01"}]
        """
        conditions = []

        # 簡單的 WHERE 條件解析
        import re

        pattern = r"(\w+)\s*(!=|>=|<=|>|<|LIKE|IN|NOT\s+IN)\s*([^\s)]+)"

        for match in re.finditer(pattern, where_clause):
            column = match.group(1)
            operator = match.group(2).strip()
            value_str = match.group(3).strip()

            # 處理字符串值
            if value_str.startswith("'") and value_str.endswith("'"):
                value = value_str[1:-1]
            elif value_str.startswith('"') and value_str.endswith('"'):
                value = value_str[1:-1]
            elif value_str.replace(".", "").isdigit():
                value = float(value_str)
            else:
                value = value_str

            # 處理 IN 操作符
            if operator.upper() in ["IN", "NOT IN"]:
                values = [
                    v.strip().strip("'\"")
                    for v in value_str[value_str.find("(") + 1 : value_str.rfind(")")].split(",")
                ]
                conditions.append(
                    {"column": column, "operator": operator.upper(), "values": values}
                )
            else:
                conditions.append({"column": column, "operator": operator, "value": value})

        return conditions

    def _validate_data_against_schema(
        self,
        rows: List[Dict[str, Any]],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """根據 Schema 驗證數據

        Args:
            rows: 數據行列表
            schema: Schema 定義

        Returns:
            驗證結果
        """
        # 這裡應該調用 SchemaService 的驗證方法
        # 為了避免循環依賴，暫時返回基本驗證結果
        return {
            "valid": True,
            "issues": [],
            "warnings": [],
        }
