# 代碼功能說明: KA-Agent 專用存儲適配器 (SeaweedFS)
# 創建日期: 2026-01-25
# 創建人: Daniel Chung

import boto3
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class KAStorageAdapter:
    """KA-Agent 專用存儲適配器，對接 SeaweedFS S3 接口"""

    def __init__(self, endpoint: str = "http://localhost:8334", bucket: str = "knowledge-assets"):
        self.endpoint = endpoint
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        """確保資產桶存在"""
        try:
            self.s3.create_bucket(Bucket=self.bucket)
        except self.s3.exceptions.BucketAlreadyExists:
            pass
        except self.s3.exceptions.BucketAlreadyOwnedByYou:
            pass
        except Exception as e:
            logger.error(f"Failed to ensure bucket {self.bucket}: {e}")

    async def upload_asset_spec(self, ka_id: str, version: str, spec: Dict[str, Any]) -> str:
        """上傳知識資產規格說明 (JSON)"""
        key = f"assets/{ka_id}/{version}/ka_spec.json"
        try:
            body = json.dumps(spec, ensure_ascii=False, indent=2).encode("utf-8")
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=body)
            return f"{self.endpoint}/{self.bucket}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload KA spec for {ka_id}: {e}")
            raise

    async def upload_data_blob(self, ka_id: str, version: str, filename: str, data: bytes) -> str:
        """上傳二進位數據（如 Parquet 或 PDF 快照）"""
        key = f"assets/{ka_id}/{version}/data/{filename}"
        try:
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
            return f"{self.endpoint}/{self.bucket}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload data blob {filename} for {ka_id}: {e}")
            raise
