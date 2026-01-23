# 代碼功能說明: SeaweedFS 變更提案服務 - 存儲和管理變更提案
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 變更提案服務 - 使用 SeaweedFS 存儲變更提案"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from botocore.exceptions import ClientError

from services.api.models.change_proposal import ChangeProposal, ChangeProposalCreate, ProposalStatus
from services.api.services.governance.seaweedfs_log_service import _get_seaweedfs_storage
from storage.s3_storage import S3FileStorage

logger = structlog.get_logger(__name__)


class SeaweedFSChangeProposalService:
    """SeaweedFS 變更提案服務"""

    def __init__(self, storage: Optional[S3FileStorage] = None):
        """
        初始化 SeaweedFS 變更提案服務

        Args:
            storage: S3FileStorage 實例（如果不提供則自動創建）
        """
        self.storage = storage or _get_seaweedfs_storage()
        self.bucket = "bucket-change-proposals"
        self.logger = logger.bind(service="SeaweedFSChangeProposalService", bucket=self.bucket)

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

    def _get_proposal_file_path(
        self, proposal_type: str, resource_id: Optional[str], proposal_id: str
    ) -> str:
        """
        生成提案文件路徑

        Args:
            proposal_type: 提案類型
            resource_id: 資源 ID（可選）
            proposal_id: 提案 ID

        Returns:
            文件路徑（例如：proposals/config_update/{resource_id}/{proposal_id}.json）
        """
        resource_dir = resource_id or "global"
        return f"proposals/{proposal_type}/{resource_dir}/{proposal_id}.json"

    async def create_proposal(self, proposal_data: ChangeProposalCreate) -> str:
        """
        創建變更提案

        Args:
            proposal_data: 變更提案創建請求

        Returns:
            提案 ID
        """
        # 1. 生成提案 ID
        timestamp_ms = int(time.time() * 1000)
        resource_part = proposal_data.resource_id or "global"
        proposal_id = f"{proposal_data.proposal_type}_{resource_part}_{timestamp_ms}"

        # 2. 生成提案文件路徑
        file_path = self._get_proposal_file_path(
            proposal_data.proposal_type, proposal_data.resource_id, proposal_id
        )

        # 3. 創建提案記錄
        proposal_record = ChangeProposal(
            proposal_id=proposal_id,
            proposal_type=proposal_data.proposal_type,
            resource_id=proposal_data.resource_id,
            proposed_by=proposal_data.proposed_by,
            status=ProposalStatus.PENDING,
            proposal_data=proposal_data.proposal_data,
            approval_required=proposal_data.approval_required,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 4. 保存到 SeaweedFS
        try:
            content = json.dumps(proposal_record.dict(), ensure_ascii=False, default=str).encode(
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
                "Proposal created",
                proposal_id=proposal_id,
                proposal_type=proposal_data.proposal_type,
                resource_id=proposal_data.resource_id,
            )
            return proposal_id
        except ClientError as e:
            self.logger.error(
                "Failed to create proposal",
                proposal_id=proposal_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to create proposal: {e}") from e

    async def _get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取提案（內部方法，通過搜索找到提案文件）

        Args:
            proposal_id: 提案 ID

        Returns:
            提案數據，如果不存在則返回 None
        """
        # 搜索所有 proposals 目錄
        prefix = "proposals/"
        try:
            paginator = self.storage.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if key.endswith(f"{proposal_id}.json"):
                            try:
                                response = self.storage.s3_client.get_object(
                                    Bucket=self.bucket, Key=key
                                )
                                content = response["Body"].read()
                                return json.loads(content.decode("utf-8"))
                            except (ClientError, json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to read proposal file",
                                    key=key,
                                    error=str(e),
                                )
                                continue
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                self.logger.error(
                    "Failed to search for proposal",
                    proposal_id=proposal_id,
                    error=str(e),
                )

        return None

    async def get_proposal(self, proposal_id: str) -> Optional[ChangeProposal]:
        """
        獲取提案詳情

        Args:
            proposal_id: 提案 ID

        Returns:
            變更提案，如果不存在則返回 None
        """
        proposal_data = await self._get_proposal(proposal_id)
        if proposal_data:
            return ChangeProposal(**proposal_data)
        return None

    async def approve_proposal(self, proposal_id: str, approved_by: str) -> bool:
        """
        審批提案（狀態更新 + 應用到 ArangoDB）

        Args:
            proposal_id: 提案 ID
            approved_by: 審批者（用戶 ID）

        Returns:
            是否成功
        """
        proposal_data = await self._get_proposal(proposal_id)
        if not proposal_data:
            self.logger.warning("Proposal not found", proposal_id=proposal_id)
            return False

        # 1. 更新提案狀態
        proposal_data["status"] = ProposalStatus.APPROVED.value
        proposal_data["approved_by"] = approved_by
        proposal_data["approved_at"] = datetime.utcnow().isoformat() + "Z"
        proposal_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        # 2. 保存更新後的提案
        proposal = ChangeProposal(**proposal_data)
        file_path = self._get_proposal_file_path(
            proposal.proposal_type, proposal.resource_id, proposal_id
        )

        try:
            content = json.dumps(proposal.dict(), ensure_ascii=False, default=str).encode("utf-8")
            self.storage.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=content,
                ContentType="application/json",
                ContentEncoding="utf-8",
            )

            # 3. 應用到 ArangoDB（Active State）
            await self._apply_proposal_to_arangodb(proposal)

            self.logger.info(
                "Proposal approved",
                proposal_id=proposal_id,
                approved_by=approved_by,
            )
            return True
        except ClientError as e:
            self.logger.error(
                "Failed to approve proposal",
                proposal_id=proposal_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to approve proposal: {e}") from e

    async def reject_proposal(self, proposal_id: str, rejected_by: str, reason: str) -> bool:
        """
        拒絕提案

        Args:
            proposal_id: 提案 ID
            rejected_by: 拒絕者（用戶 ID）
            reason: 拒絕原因

        Returns:
            是否成功
        """
        proposal_data = await self._get_proposal(proposal_id)
        if not proposal_data:
            self.logger.warning("Proposal not found", proposal_id=proposal_id)
            return False

        # 1. 更新提案狀態
        proposal_data["status"] = ProposalStatus.REJECTED.value
        proposal_data["rejected_by"] = rejected_by
        proposal_data["rejected_at"] = datetime.utcnow().isoformat() + "Z"
        proposal_data["rejection_reason"] = reason
        proposal_data["updated_at"] = datetime.utcnow().isoformat() + "Z"

        # 2. 保存更新後的提案
        proposal = ChangeProposal(**proposal_data)
        file_path = self._get_proposal_file_path(
            proposal.proposal_type, proposal.resource_id, proposal_id
        )

        try:
            content = json.dumps(proposal.dict(), ensure_ascii=False, default=str).encode("utf-8")
            self.storage.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=content,
                ContentType="application/json",
                ContentEncoding="utf-8",
            )

            self.logger.info(
                "Proposal rejected",
                proposal_id=proposal_id,
                rejected_by=rejected_by,
                reason=reason,
            )
            return True
        except ClientError as e:
            self.logger.error(
                "Failed to reject proposal",
                proposal_id=proposal_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to reject proposal: {e}") from e

    async def list_proposals(
        self,
        proposal_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[ProposalStatus] = None,
        limit: int = 100,
    ) -> List[ChangeProposal]:
        """
        列出提案列表

        Args:
            proposal_type: 提案類型（可選）
            resource_id: 資源 ID（可選）
            status: 提案狀態（可選）
            limit: 返回數量限制

        Returns:
            提案列表（按創建時間降序排列）
        """
        prefix = "proposals/"
        if proposal_type:
            prefix = f"proposals/{proposal_type}/"
            if resource_id:
                prefix = f"proposals/{proposal_type}/{resource_id}/"

        proposals: List[ChangeProposal] = []

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
                                proposal_data = json.loads(content.decode("utf-8"))
                                proposal = ChangeProposal(**proposal_data)

                                # 過濾條件
                                if resource_id and proposal.resource_id != resource_id:
                                    continue
                                if status and proposal.status != status:
                                    continue

                                proposals.append(proposal)
                            except (ClientError, json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to read proposal file",
                                    key=key,
                                    error=str(e),
                                )
                                continue

            # 按創建時間降序排序
            proposals.sort(key=lambda x: x.created_at, reverse=True)
            return proposals[:limit]
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                return []
            self.logger.error(
                "Failed to list proposals",
                error=str(e),
            )
            raise RuntimeError(f"Failed to list proposals: {e}") from e

    async def _apply_proposal_to_arangodb(self, proposal: ChangeProposal) -> None:
        """
        應用提案到 ArangoDB（Active State）

        Args:
            proposal: 變更提案
        """
        # 這裡需要根據提案類型應用到對應的服務
        # 例如：config_update -> ConfigStoreService, ontology_update -> OntologyStoreService
        # 這是一個簡化實現，實際應該根據 proposal_type 調用對應的服務方法

        self.logger.info(
            "Applying proposal to ArangoDB",
            proposal_id=proposal.proposal_id,
            proposal_type=proposal.proposal_type,
            resource_id=proposal.resource_id,
        )

        # TODO: 根據提案類型實現具體的應用邏輯
        # 例如：
        # if proposal.proposal_type == "config_update":
        #     from services.api.services.config_store_service import get_config_store_service
        #     service = get_config_store_service()
        #     service.save_config(...)
        # elif proposal.proposal_type == "ontology_update":
        #     from services.api.services.ontology_store_service import get_ontology_store_service
        #     service = get_ontology_store_service()
        #     service.save_ontology(...)

        # 目前僅記錄日誌，實際應用邏輯需要在具體服務中實現
