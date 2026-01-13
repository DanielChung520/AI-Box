# 代碼功能說明: Datalake 數據查詢服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Datalake 數據查詢服務實現"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from storage.s3_storage import S3FileStorage, SeaweedFSService

# 加載環境變數（使用絕對路徑）
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = structlog.get_logger(__name__)


class DatalakeService:
    """Datalake 數據查詢服務"""

    def __init__(self) -> None:
        """初始化 Datalake 服務"""
        self._storage: Optional[S3FileStorage] = None
        self._logger = logger

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

    async def query(
        self,
        bucket: str,
        key: str,
        query_type: str = "exact",
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查詢 Datalake 數據

        Args:
            bucket: Bucket 名稱
            key: 數據鍵（文件路徑）
            query_type: 查詢類型（exact/fuzzy）
            filters: 過濾條件
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            查詢結果
        """
        try:
            storage = self._get_storage()

            # 根據查詢類型執行查詢
            if query_type == "exact":
                result = await self._query_exact(storage, bucket, key)
            elif query_type == "fuzzy":
                result = await self._query_fuzzy(storage, bucket, key, filters)
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

    async def _query_exact(
        self,
        storage: S3FileStorage,
        bucket: str,
        key: str,
    ) -> Dict[str, Any]:
        """精確查詢：讀取單個文件

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
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            # 如果是單個對象，轉換為列表
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
        """模糊查詢：列出目錄並過濾

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
                # 跳過目錄本身
                if key.endswith("/"):
                    continue

                # 讀取文件
                try:
                    file_response = storage.s3_client.get_object(Bucket=bucket, Key=key)
                    content = file_response["Body"].read().decode("utf-8")

                    # 如果是 JSONL 文件，逐行解析
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
                # 支持範圍查詢：{"gte": 10, "lte": 20}
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
                # 簡單等值匹配
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
