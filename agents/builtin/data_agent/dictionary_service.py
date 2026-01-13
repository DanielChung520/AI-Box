# 代碼功能說明: 數據字典管理服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""數據字典管理服務實現"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from storage.s3_storage import S3FileStorage, SeaweedFSService

# 加載環境變數（使用絕對路徑）
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = structlog.get_logger(__name__)


class DictionaryService:
    """數據字典管理服務"""

    def __init__(self) -> None:
        """初始化數據字典服務"""
        self._storage: Optional[S3FileStorage] = None
        self._bucket = "bucket-datalake-dictionary"
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

            # 確保 bucket 存在
            self._storage._ensure_bucket_exists(self._bucket)

        return self._storage

    async def create(
        self,
        dictionary_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """創建數據字典

        Args:
            dictionary_id: 數據字典 ID
            data: 數據字典數據
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            創建結果
        """
        # 驗證數據結構
        validation = self._validate_dictionary_data(data)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid dictionary data: {validation['error']}",
            }

        try:
            storage = self._get_storage()
            key = f"{dictionary_id}.json"

            # 保存到 SeaweedFS
            storage.s3_client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                ContentType="application/json",
            )

            self._logger.info(
                "Dictionary created",
                dictionary_id=dictionary_id,
                bucket=self._bucket,
                key=key,
            )

            return {
                "success": True,
                "dictionary_id": dictionary_id,
                "key": key,
            }

        except Exception as e:
            self._logger.error(
                "Failed to create dictionary", dictionary_id=dictionary_id, error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def get(self, dictionary_id: str) -> Dict[str, Any]:
        """查詢數據字典

        Args:
            dictionary_id: 數據字典 ID

        Returns:
            查詢結果
        """
        try:
            storage = self._get_storage()
            key = f"{dictionary_id}.json"

            # 從 SeaweedFS 讀取
            response = storage.s3_client.get_object(Bucket=self._bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            return {
                "success": True,
                "dictionary": data,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                return {
                    "success": False,
                    "error": f"Dictionary not found: {dictionary_id}",
                }
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            self._logger.error(
                "Failed to get dictionary", dictionary_id=dictionary_id, error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def update(
        self,
        dictionary_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新數據字典

        Args:
            dictionary_id: 數據字典 ID
            data: 更新的數據字典數據
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            更新結果
        """
        # 驗證數據結構
        validation = self._validate_dictionary_data(data)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid dictionary data: {validation['error']}",
            }

        try:
            storage = self._get_storage()
            key = f"{dictionary_id}.json"

            # 檢查字典是否存在
            try:
                storage.s3_client.head_object(Bucket=self._bucket, Key=key)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404" or error_code == "NoSuchKey":
                    return {
                        "success": False,
                        "error": f"Dictionary not found: {dictionary_id}",
                    }
                raise

            # 更新數據字典
            storage.s3_client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                ContentType="application/json",
            )

            self._logger.info(
                "Dictionary updated",
                dictionary_id=dictionary_id,
                bucket=self._bucket,
                key=key,
            )

            return {
                "success": True,
                "dictionary_id": dictionary_id,
                "key": key,
            }

        except Exception as e:
            self._logger.error(
                "Failed to update dictionary", dictionary_id=dictionary_id, error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
            }

    def _validate_dictionary_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證數據字典結構

        Args:
            data: 數據字典數據

        Returns:
            驗證結果
        """
        required_fields = ["dictionary_id", "name", "version", "tables"]
        for field in required_fields:
            if field not in data:
                return {
                    "valid": False,
                    "error": f"Missing required field: {field}",
                }

        # 驗證 tables 結構
        if not isinstance(data["tables"], list):
            return {
                "valid": False,
                "error": "tables must be a list",
            }

        return {
            "valid": True,
        }
