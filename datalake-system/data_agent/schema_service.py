# 代碼功能說明: Schema 管理服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Schema 管理服務實現"""

import json
import os

# 導入 AI-Box 項目的模塊（datalake-system 在 AI-Box 項目中）
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
import structlog
from botocore.exceptions import ClientError

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from dotenv import load_dotenv

from storage.s3_storage import S3FileStorage, SeaweedFSService

# 加載環境變數（使用絕對路徑）
# datalake-system 在 AI-Box 項目中，需要指向 AI-Box 根目錄的 .env
base_dir = Path(__file__).resolve().parent.parent.parent  # AI-Box 根目錄
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = structlog.get_logger(__name__)


class SchemaService:
    """Schema 管理服務"""

    def __init__(self) -> None:
        """初始化 Schema 服務"""
        self._storage: Optional[S3FileStorage] = None
        self._bucket = "bucket-datalake-schema"
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
        schema_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """創建 Schema

        Args:
            schema_id: Schema ID
            data: Schema 數據
            user_id: 用戶 ID（可選）
            tenant_id: 租戶 ID（可選）

        Returns:
            創建結果
        """
        # 驗證 JSON Schema 格式
        json_schema = data.get("json_schema")
        if not json_schema:
            return {
                "success": False,
                "error": "Missing json_schema field",
            }

        # 驗證 JSON Schema 語法
        validation = self._validate_json_schema(json_schema)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid JSON Schema: {validation['error']}",
            }

        try:
            storage = self._get_storage()
            key = f"{schema_id}.json"

            # 保存到 SeaweedFS
            storage.s3_client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                ContentType="application/json",
                ContentEncoding="utf-8",
            )

            self._logger.info(
                "Schema created",
                schema_id=schema_id,
                bucket=self._bucket,
                key=key,
            )

            return {
                "success": True,
                "schema_id": schema_id,
                "key": key,
            }

        except Exception as e:
            self._logger.error("Failed to create schema", schema_id=schema_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def get(self, schema_id: str) -> Dict[str, Any]:
        """查詢 Schema

        Args:
            schema_id: Schema ID

        Returns:
            查詢結果
        """
        try:
            storage = self._get_storage()
            key = f"{schema_id}.json"

            # 從 SeaweedFS 讀取
            response = storage.s3_client.get_object(Bucket=self._bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            return {
                "success": True,
                "schema": data,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey" or error_code == "404":
                return {
                    "success": False,
                    "error": f"Schema not found: {schema_id}",
                }
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            self._logger.error("Failed to get schema", schema_id=schema_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def validate_data(
        self,
        data: List[Dict[str, Any]],
        schema_id: str,
    ) -> Dict[str, Any]:
        """根據 Schema 驗證數據

        Args:
            data: 待驗證數據（可以是空列表）
            schema_id: Schema ID

        Returns:
            驗證結果
        """
        # 獲取 Schema
        schema_result = await self.get(schema_id)
        if not schema_result.get("success"):
            return {
                "success": False,
                "error": f"Schema not found: {schema_id}",
            }

        schema = schema_result["schema"]
        json_schema = schema.get("json_schema", {})

        # 如果數據為空列表，視為有效（沒有數據需要驗證）
        if not data:
            return {
                "success": True,
                "valid": True,
                "issues": [],
                "validated_count": 0,
                "invalid_count": 0,
                "message": "Empty data list is valid (no data to validate)",
            }

        # 驗證數據
        validator = jsonschema.Draft7Validator(json_schema)
        issues: List[Dict[str, Any]] = []

        for i, row in enumerate(data):
            errors = list(validator.iter_errors(row))
            if errors:
                for error in errors:
                    issues.append(
                        {
                            "row": i + 1,
                            "field": ".".join(str(x) for x in error.path),
                            "message": error.message,
                            "value": error.instance,
                        }
                    )

        return {
            "success": True,
            "valid": len(issues) == 0,
            "issues": issues,
            "validated_count": len(data),
            "invalid_count": len(issues),
        }

    def _validate_json_schema(self, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """驗證 JSON Schema 語法

        Args:
            json_schema: JSON Schema 定義

        Returns:
            驗證結果
        """
        try:
            # 基本結構檢查
            if not isinstance(json_schema, dict):
                return {
                    "valid": False,
                    "error": "JSON Schema must be a dictionary",
                }

            # 檢查是否有 $schema 字段（推薦但不強制）
            # 檢查是否有 type 字段（對於對象類型 Schema 是必需的）
            if "type" not in json_schema:
                # 如果沒有 type，檢查是否有其他有效的 Schema 結構
                if (
                    "$ref" not in json_schema
                    and "anyOf" not in json_schema
                    and "oneOf" not in json_schema
                ):
                    return {
                        "valid": False,
                        "error": "JSON Schema must have 'type' field or use '$ref', 'anyOf', or 'oneOf'",
                    }

            # 使用 jsonschema 驗證
            jsonschema.Draft7Validator.check_schema(json_schema)
            return {
                "valid": True,
            }
        except jsonschema.SchemaError as e:
            return {
                "valid": False,
                "error": str(e),
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }
