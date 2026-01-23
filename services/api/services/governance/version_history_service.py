# 代碼功能說明: SeaweedFS 版本歷史服務 - 存儲配置和 Ontology 的版本歷史
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 版本歷史服務 - 使用 SeaweedFS 存儲版本歷史記錄"""

import json
from datetime import datetime
from typing import List, Optional

import structlog
from botocore.exceptions import ClientError

from services.api.models.version_history import VersionHistory, VersionHistoryCreate
from services.api.services.governance.seaweedfs_log_service import _get_seaweedfs_storage
from storage.s3_storage import S3FileStorage

logger = structlog.get_logger(__name__)


class SeaweedFSVersionHistoryService:
    """SeaweedFS 版本歷史服務"""

    def __init__(self, storage: Optional[S3FileStorage] = None):
        """
        初始化 SeaweedFS 版本歷史服務

        Args:
            storage: S3FileStorage 實例（如果不提供則自動創建）
        """
        self.storage = storage or _get_seaweedfs_storage()
        self.bucket = "bucket-version-history"
        self.logger = logger.bind(service="SeaweedFSVersionHistoryService", bucket=self.bucket)

        # 確保 Bucket 存在
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """確保 Bucket 存在"""
        try:
            self.storage.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.debug("Bucket already exists", bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                try:
                    self.storage.s3_client.create_bucket(Bucket=self.bucket)
                    self.logger.info("Bucket created", bucket=self.bucket)
                except ClientError as create_error:
                    self.logger.error(
                        "Failed to create bucket",
                        bucket=self.bucket,
                        error=str(create_error),
                    )
                    raise
            else:
                self.logger.error(
                    "Failed to check bucket existence",
                    bucket=self.bucket,
                    error=str(e),
                )
                raise

    def _get_version_file_path(self, resource_type: str, resource_id: str, version: int) -> str:
        """
        生成版本文件路徑

        Args:
            resource_type: 資源類型
            resource_id: 資源 ID
            version: 版本號

        Returns:
            文件路徑（例如：versions/ontologies/{resource_id}/v{version}.json）
        """
        return f"versions/{resource_type}/{resource_id}/v{version}.json"

    async def _get_next_version(self, resource_type: str, resource_id: str) -> int:
        """
        獲取下一個版本號

        Args:
            resource_type: 資源類型
            resource_id: 資源 ID

        Returns:
            下一個版本號
        """
        prefix = f"versions/{resource_type}/{resource_id}/"
        max_version = 0

        try:
            paginator = self.storage.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        # 從文件路徑提取版本號：versions/{resource_type}/{resource_id}/v{version}.json
                        if key.endswith(".json"):
                            version_str = key.split("/")[-1][1:-5]  # 移除 "v" 前綴和 ".json" 後綴
                            try:
                                version = int(version_str)
                                if version > max_version:
                                    max_version = version
                            except ValueError:
                                continue
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                self.logger.warning(
                    "Failed to list versions",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    error=str(e),
                )

        return max_version + 1

    async def create_version(self, version_data: VersionHistoryCreate) -> int:
        """
        創建版本記錄

        Args:
            version_data: 版本歷史創建請求

        Returns:
            版本號
        """
        # 1. 獲取當前版本號
        version = await self._get_next_version(version_data.resource_type, version_data.resource_id)

        # 2. 生成版本文件路徑
        file_path = self._get_version_file_path(
            version_data.resource_type, version_data.resource_id, version
        )

        # 3. 創建版本記錄
        version_record = VersionHistory(
            resource_type=version_data.resource_type,
            resource_id=version_data.resource_id,
            version=version,
            change_type=version_data.change_type,
            changed_by=version_data.changed_by,
            change_summary=version_data.change_summary,
            previous_version=version_data.previous_version,
            current_version=version_data.current_version,
            created_at=datetime.utcnow(),
        )

        # 4. 保存到 SeaweedFS
        try:
            content = json.dumps(version_record.dict(), ensure_ascii=False, default=str).encode(
                "utf-8"
            )
            self.storage.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=content,
                ContentType="application/json",
                ContentEncoding="utf-8",
            )
            self.logger.info(
                "Version created",
                resource_type=version_data.resource_type,
                resource_id=version_data.resource_id,
                version=version,
            )
            return version
        except ClientError as e:
            self.logger.error(
                "Failed to create version",
                resource_type=version_data.resource_type,
                resource_id=version_data.resource_id,
                version=version,
                error=str(e),
            )
            raise RuntimeError(f"Failed to create version: {e}") from e

    async def get_version_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100,
    ) -> List[VersionHistory]:
        """
        獲取版本歷史列表

        Args:
            resource_type: 資源類型
            resource_id: 資源 ID
            limit: 返回數量限制

        Returns:
            版本歷史列表（按版本號降序排列）
        """
        prefix = f"versions/{resource_type}/{resource_id}/"
        versions: List[VersionHistory] = []

        try:
            paginator = self.storage.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if key.endswith(".json"):
                            try:
                                response = self.storage.s3_client.get_object(
                                    Bucket=self.bucket, Key=key
                                )
                                content = response["Body"].read()
                                version_data = json.loads(content.decode("utf-8"))
                                versions.append(VersionHistory(**version_data))
                            except (ClientError, json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to read version file",
                                    key=key,
                                    error=str(e),
                                )
                                continue

            # 按版本號降序排序
            versions.sort(key=lambda x: x.version, reverse=True)
            return versions[:limit]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                return []
            self.logger.error(
                "Failed to get version history",
                resource_type=resource_type,
                resource_id=resource_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get version history: {e}") from e

    async def get_version(
        self,
        resource_type: str,
        resource_id: str,
        version: int,
    ) -> Optional[VersionHistory]:
        """
        獲取特定版本

        Args:
            resource_type: 資源類型
            resource_id: 資源 ID
            version: 版本號

        Returns:
            版本歷史記錄，如果不存在則返回 None
        """
        file_path = self._get_version_file_path(resource_type, resource_id, version)

        try:
            response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
            content = response["Body"].read()
            version_data = json.loads(content.decode("utf-8"))
            return VersionHistory(**version_data)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                return None
            self.logger.error(
                "Failed to get version",
                resource_type=resource_type,
                resource_id=resource_id,
                version=version,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get version: {e}") from e
