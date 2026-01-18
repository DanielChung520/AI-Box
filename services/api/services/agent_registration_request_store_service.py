# 代碼功能說明: AgentRegistrationRequest 存儲服務 - 提供 Agent 申請的 CRUD 操作
# 創建日期: 2026-01-17 18:27 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:27 UTC+8

"""AgentRegistrationRequest Store Service

提供 Agent 註冊申請的 CRUD 操作，包括創建、查詢、更新、審查批准等功能。
"""

from __future__ import annotations

import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.agent_registration_request import (
    AgentConfigRequest,
    AgentRegistrationRequestCreate,
    AgentRegistrationRequestModel,
    AgentRegistrationRequestUpdate,
    AgentRegistrationStatus,
    ApplicantInfo,
    RequestedPermissions,
    ReviewInfo,
    SecretInfo,
)

logger = logging.getLogger(__name__)

AGENT_REGISTRATION_REQUESTS_COLLECTION = "agent_registration_requests"


def _generate_secret_id() -> str:
    """生成 Secret ID

    格式：aibox-{timestamp}-{random_hex}
    例如：aibox-1768374372-b7fd8d2d
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(4)  # 8 個字符
    return f"aibox-{timestamp}-{random_hex}"


def _generate_secret_key() -> str:
    """生成 Secret Key

    使用 secrets.token_urlsafe 生成 64 字符的隨機字符串
    """
    # 生成 48 字節（會產生約 64 個字符的 base64 字符串）
    return secrets.token_urlsafe(48)


def _hash_secret_key(secret_key: str) -> str:
    """使用 bcrypt 哈希 Secret Key

    Args:
        secret_key: 明文 Secret Key

    Returns:
        bcrypt 哈希後的 Secret Key
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret_key.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _document_to_model(doc: Dict[str, Any]) -> AgentRegistrationRequestModel:
    """將 ArangoDB document 轉換為 AgentRegistrationRequestModel"""
    # 確保必需字段存在
    request_id = doc.get("request_id")
    agent_id = doc.get("agent_id")
    agent_name = doc.get("agent_name")

    if not request_id or not agent_id or not agent_name:
        raise ValueError("Missing required fields: request_id, agent_id, or agent_name")

    return AgentRegistrationRequestModel(
        id=doc.get("_key"),
        request_id=request_id,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_description=doc.get("agent_description"),
        applicant_info=ApplicantInfo(**doc.get("applicant_info", {})),
        agent_config=AgentConfigRequest(**doc.get("agent_config", {})),
        requested_permissions=RequestedPermissions(**doc.get("requested_permissions", {})),
        status=AgentRegistrationStatus(doc.get("status", "pending")),
        secret_info=SecretInfo(
            secret_id=doc.get("secret_info", {}).get("secret_id"),
            secret_key_hash=doc.get("secret_info", {}).get("secret_key_hash"),
            issued_at=(
                datetime.fromisoformat(doc.get("secret_info", {}).get("issued_at"))
                if doc.get("secret_info", {}).get("issued_at")
                else None
            ),
            expires_at=(
                datetime.fromisoformat(doc.get("secret_info", {}).get("expires_at"))
                if doc.get("secret_info", {}).get("expires_at")
                else None
            ),
        ),
        review_info=ReviewInfo(
            reviewed_by=doc.get("review_info", {}).get("reviewed_by"),
            reviewed_at=(
                datetime.fromisoformat(doc.get("review_info", {}).get("reviewed_at"))
                if doc.get("review_info", {}).get("reviewed_at")
                else None
            ),
            review_notes=doc.get("review_info", {}).get("review_notes"),
            rejection_reason=doc.get("review_info", {}).get("rejection_reason"),
        ),
        tenant_id=doc.get("tenant_id"),
        created_at=(
            datetime.fromisoformat(doc["created_at"])
            if doc.get("created_at")
            else datetime.utcnow()
        ),
        updated_at=(
            datetime.fromisoformat(doc["updated_at"])
            if doc.get("updated_at")
            else datetime.utcnow()
        ),
        metadata=doc.get("metadata", {}),
    )


class AgentRegistrationRequestStoreService:
    """AgentRegistrationRequest 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 AgentRegistrationRequest Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(AGENT_REGISTRATION_REQUESTS_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(AGENT_REGISTRATION_REQUESTS_COLLECTION)

        # 獲取現有索引
        indexes = collection.indexes()
        existing_index_fields = {
            (
                tuple(idx.get("fields", []))
                if isinstance(idx.get("fields"), list)
                else idx.get("fields")
            )
            for idx in indexes
        }

        # request_id 唯一索引
        request_id_fields = ("request_id",)
        if request_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["request_id"],
                    "unique": True,
                    "name": "idx_agent_requests_request_id",
                }
            )

        # agent_id 索引
        agent_id_fields = ("agent_id",)
        if agent_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["agent_id"],
                    "name": "idx_agent_requests_agent_id",
                }
            )

        # status 索引
        status_fields = ("status",)
        if status_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["status"],
                    "name": "idx_agent_requests_status",
                }
            )

        # tenant_id + status 複合索引
        tenant_status_fields = ("tenant_id", "status")
        if tenant_status_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "status"],
                    "name": "idx_agent_requests_tenant_status",
                }
            )

        # applicant_info.email 索引
        email_fields = ("applicant_info.email",)
        if email_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["applicant_info.email"],
                    "name": "idx_agent_requests_email",
                }
            )

        # created_at 索引（用於排序）
        created_at_fields = ("created_at",)
        if created_at_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["created_at"],
                    "name": "idx_agent_requests_created_at",
                }
            )

    def create_request(
        self,
        request_data: AgentRegistrationRequestCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AgentRegistrationRequestModel:
        """
        創建 Agent 註冊申請

        Args:
            request_data: 申請創建數據
            ip_address: 申請來源 IP 地址
            user_agent: User-Agent 字符串

        Returns:
            創建的申請模型

        Raises:
            ValueError: 如果 Agent ID 已存在待審核或已批准的申請
        """
        # 檢查是否已有相同 Agent ID 的待審核或已批准申請
        existing = self._collection.find(
            {
                "agent_id": request_data.agent_id,
                "status": {"$in": ["pending", "approved"]},
            },
            limit=1,
        )
        if existing:
            raise ValueError(
                f"Agent ID '{request_data.agent_id}' already has a pending or approved registration request"
            )

        # 生成 request_id
        request_id = f"req_{uuid.uuid4().hex[:12]}"

        now = datetime.utcnow().isoformat()
        doc_key = f"req_{uuid.uuid4().hex}"
        doc: Dict[str, Any] = {
            "_key": doc_key,
            "request_id": request_id,
            "agent_id": request_data.agent_id,
            "agent_name": request_data.agent_name,
            "agent_description": request_data.agent_description,
            "applicant_info": request_data.applicant_info.model_dump(),
            "agent_config": request_data.agent_config.model_dump(),
            "requested_permissions": request_data.requested_permissions.model_dump(),
            "status": AgentRegistrationStatus.PENDING.value,
            "secret_info": {
                "secret_id": None,
                "secret_key_hash": None,
                "issued_at": None,
                "expires_at": None,
            },
            "review_info": {
                "reviewed_by": None,
                "reviewed_at": None,
                "review_notes": None,
                "rejection_reason": None,
            },
            "tenant_id": request_data.tenant_id,
            "created_at": now,
            "updated_at": now,
            "metadata": {
                "ip_address": ip_address or "unknown",
                "user_agent": user_agent or "unknown",
            },
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                f"Agent registration request created: request_id={request_id}, agent_id={request_data.agent_id}"
            )
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                f"Failed to create agent registration request: agent_id={request_data.agent_id}, error={str(exc)}"
            )
            raise

    def get_request(self, request_id: str) -> Optional[AgentRegistrationRequestModel]:
        """
        獲取 Agent 註冊申請

        Args:
            request_id: 申請 ID

        Returns:
            申請模型，如果不存在則返回 None
        """
        results = self._collection.find({"request_id": request_id}, limit=1)
        if not results:
            return None
        return _document_to_model(results[0])

    def list_requests(
        self,
        status: Optional[AgentRegistrationStatus] = None,
        tenant_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> tuple[List[AgentRegistrationRequestModel], int]:
        """
        列出 Agent 註冊申請

        Args:
            status: 申請狀態過濾（可選）
            tenant_id: 租戶 ID 過濾（可選）
            limit: 限制返回數量
            offset: 偏移量（用於分頁）
            search: 搜索關鍵字（搜索 Agent 名稱、Agent ID、申請者郵箱）

        Returns:
            (申請列表, 總數)
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 構建 AQL 查詢
        aql = "FOR doc IN agent_registration_requests"
        bind_vars: Dict[str, Any] = {}

        # 構建過濾條件
        filters = []
        if status is not None:
            filters.append("doc.status == @status")
            bind_vars["status"] = status.value

        if tenant_id is not None:
            filters.append("doc.tenant_id == @tenant_id")
            bind_vars["tenant_id"] = tenant_id

        if search:
            filters.append(
                "(doc.agent_name LIKE @search OR doc.agent_id LIKE @search OR doc.applicant_info.email LIKE @search)"
            )
            bind_vars["search"] = f"%{search}%"

        if filters:
            aql += " FILTER " + " AND ".join(filters)

        # 計算總數
        count_aql = aql + " COLLECT WITH COUNT INTO total RETURN total"
        try:
            count_cursor = self._client.db.aql.execute(count_aql, bind_vars=bind_vars)
            count_results = [count for count in count_cursor] if count_cursor else []  # type: ignore[union-attr]
            total = count_results[0] if count_results else 0
        except Exception:
            total = 0

        # 排序和分頁
        aql += " SORT doc.created_at DESC"
        if limit:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit

        aql += " RETURN doc"

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            results = [doc for doc in cursor]  # type: ignore[union-attr]
            return ([_document_to_model(doc) for doc in results], total)
        except Exception as e:
            self._logger.error(
                f"Failed to list agent registration requests: error={e}", exc_info=True
            )
            return ([], 0)

    def update_request(
        self, request_id: str, request_data: AgentRegistrationRequestUpdate
    ) -> Optional[AgentRegistrationRequestModel]:
        """
        更新 Agent 註冊申請

        Args:
            request_id: 申請 ID
            request_data: 申請更新數據

        Returns:
            更新後的申請模型，如果申請不存在則返回 None
        """
        results = self._collection.find({"request_id": request_id}, limit=1)
        if not results:
            return None

        existing = results[0]

        # 只有 pending 狀態的申請可以更新
        if existing.get("status") != AgentRegistrationStatus.PENDING.value:
            raise ValueError(f"Cannot update request in status '{existing.get('status')}'")

        # 構建更新文檔
        update_doc: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if request_data.agent_name is not None:
            update_doc["agent_name"] = request_data.agent_name
        if request_data.agent_description is not None:
            update_doc["agent_description"] = request_data.agent_description
        if request_data.applicant_info is not None:
            update_doc["applicant_info"] = request_data.applicant_info.model_dump()
        if request_data.agent_config is not None:
            update_doc["agent_config"] = request_data.agent_config.model_dump()
        if request_data.requested_permissions is not None:
            update_doc["requested_permissions"] = request_data.requested_permissions.model_dump()

        try:
            self._collection.update({"_key": existing["_key"], **update_doc})
            self._logger.info(f"Agent registration request updated: request_id={request_id}")
            return self.get_request(request_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to update agent registration request: request_id={request_id}, error={str(exc)}"
            )
            raise

    def approve_request(
        self,
        request_id: str,
        reviewed_by: str,
        review_notes: Optional[str] = None,
        secret_expires_days: Optional[int] = None,
    ) -> tuple[AgentRegistrationRequestModel, str]:
        """
        批准 Agent 註冊申請

        Args:
            request_id: 申請 ID
            reviewed_by: 審查人 user_id
            review_notes: 審查意見
            secret_expires_days: Secret 過期天數（可選，None 表示永不過期）

        Returns:
            (更新後的申請模型, Secret Key 明文)

        Raises:
            ValueError: 如果申請不存在或狀態不是 pending
        """
        results = self._collection.find({"request_id": request_id}, limit=1)
        if not results:
            raise ValueError(f"Request '{request_id}' not found")

        existing = results[0]

        # 只有 pending 狀態的申請可以批准
        if existing.get("status") != AgentRegistrationStatus.PENDING.value:
            raise ValueError(f"Cannot approve request in status '{existing.get('status')}'")

        # 生成 Secret ID 和 Key
        secret_id = _generate_secret_id()
        secret_key = _generate_secret_key()
        secret_key_hash = _hash_secret_key(secret_key)

        now = datetime.utcnow()
        expires_at = None
        if secret_expires_days:
            expires_at = now + timedelta(days=secret_expires_days)

        # 更新申請
        update_doc: Dict[str, Any] = {
            "_key": existing["_key"],
            "status": AgentRegistrationStatus.APPROVED.value,
            "secret_info": {
                "secret_id": secret_id,
                "secret_key_hash": secret_key_hash,
                "issued_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
            "review_info": {
                "reviewed_by": reviewed_by,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "rejection_reason": None,
            },
            "updated_at": now.isoformat(),
        }

        try:
            self._collection.update(update_doc)
            self._logger.info(
                f"Agent registration request approved: request_id={request_id}, agent_id={existing.get('agent_id')}"
            )
            updated_request = self.get_request(request_id)
            if updated_request is None:
                raise RuntimeError(f"Failed to retrieve updated request: request_id={request_id}")
            return (updated_request, secret_key)
        except Exception as exc:
            self._logger.error(
                f"Failed to approve agent registration request: request_id={request_id}, error={str(exc)}"
            )
            raise

    def reject_request(
        self,
        request_id: str,
        reviewed_by: str,
        rejection_reason: str,
        review_notes: Optional[str] = None,
    ) -> Optional[AgentRegistrationRequestModel]:
        """
        拒絕 Agent 註冊申請

        Args:
            request_id: 申請 ID
            reviewed_by: 審查人 user_id
            rejection_reason: 拒絕原因
            review_notes: 審查意見

        Returns:
            更新後的申請模型，如果申請不存在則返回 None

        Raises:
            ValueError: 如果申請狀態不是 pending
        """
        results = self._collection.find({"request_id": request_id}, limit=1)
        if not results:
            return None

        existing = results[0]

        # 只有 pending 狀態的申請可以拒絕
        if existing.get("status") != AgentRegistrationStatus.PENDING.value:
            raise ValueError(f"Cannot reject request in status '{existing.get('status')}'")

        now = datetime.utcnow()

        # 更新申請
        update_doc: Dict[str, Any] = {
            "_key": existing["_key"],
            "status": AgentRegistrationStatus.REJECTED.value,
            "review_info": {
                "reviewed_by": reviewed_by,
                "reviewed_at": now.isoformat(),
                "review_notes": review_notes,
                "rejection_reason": rejection_reason,
            },
            "updated_at": now.isoformat(),
        }

        try:
            self._collection.update(update_doc)
            self._logger.info(
                f"Agent registration request rejected: request_id={request_id}, agent_id={existing.get('agent_id')}"
            )
            return self.get_request(request_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to reject agent registration request: request_id={request_id}, error={str(exc)}"
            )
            raise

    def revoke_request(
        self,
        request_id: str,
        revoked_by: str,
        revoke_reason: str,
    ) -> Optional[AgentRegistrationRequestModel]:
        """
        撤銷已批准的 Agent 註冊申請

        Args:
            request_id: 申請 ID
            revoked_by: 撤銷人 user_id
            revoke_reason: 撤銷原因

        Returns:
            更新後的申請模型，如果申請不存在則返回 None

        Raises:
            ValueError: 如果申請狀態不是 approved
        """
        results = self._collection.find({"request_id": request_id}, limit=1)
        if not results:
            return None

        existing = results[0]

        # 只有 approved 狀態的申請可以撤銷
        if existing.get("status") != AgentRegistrationStatus.APPROVED.value:
            raise ValueError(f"Cannot revoke request in status '{existing.get('status')}'")

        now = datetime.utcnow()

        # 更新申請
        update_doc: Dict[str, Any] = {
            "_key": existing["_key"],
            "status": AgentRegistrationStatus.REVOKED.value,
            "review_info": {
                "reviewed_by": revoked_by,
                "reviewed_at": now.isoformat(),
                "review_notes": existing.get("review_info", {}).get("review_notes"),
                "rejection_reason": revoke_reason,  # 使用 rejection_reason 字段存儲撤銷原因
            },
            "updated_at": now.isoformat(),
        }

        try:
            self._collection.update(update_doc)
            self._logger.info(
                f"Agent registration request revoked: request_id={request_id}, agent_id={existing.get('agent_id')}"
            )
            return self.get_request(request_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to revoke agent registration request: request_id={request_id}, error={str(exc)}"
            )
            raise


def get_agent_registration_request_store_service(
    client: Optional[ArangoDBClient] = None,
) -> AgentRegistrationRequestStoreService:
    """
    獲取 AgentRegistrationRequest Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        AgentRegistrationRequestStoreService 實例
    """
    global _service
    if _service is None:
        _service = AgentRegistrationRequestStoreService(client)
    return _service


_service: Optional[AgentRegistrationRequestStoreService] = None
