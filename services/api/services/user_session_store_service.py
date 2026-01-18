# 代碼功能說明: UserSession 存儲服務 - 提供用戶會話的 CRUD 操作
# 創建日期: 2026-01-17 18:07 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:07 UTC+8

"""UserSession Store Service

提供用戶會話的 CRUD 操作，包括創建、查詢、更新、終止會話等功能。
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.user_session import UserSessionCreate, UserSessionModel, UserSessionUpdate

logger = logging.getLogger(__name__)

USER_SESSIONS_COLLECTION = "user_sessions"


def _document_to_model(doc: Dict[str, Any]) -> UserSessionModel:
    """將 ArangoDB document 轉換為 UserSessionModel"""
    return UserSessionModel(
        id=doc.get("_key"),
        session_id=doc.get("session_id"),
        user_id=doc.get("user_id"),
        access_token=doc.get("access_token"),
        refresh_token=doc.get("refresh_token"),
        ip_address=doc.get("ip_address"),
        user_agent=doc.get("user_agent"),
        device_info=doc.get("device_info", {}),
        login_at=(
            datetime.fromisoformat(doc["login_at"]) if doc.get("login_at") else datetime.utcnow()
        ),
        last_activity_at=(
            datetime.fromisoformat(doc["last_activity_at"])
            if doc.get("last_activity_at")
            else datetime.utcnow()
        ),
        expires_at=(
            datetime.fromisoformat(doc["expires_at"])
            if doc.get("expires_at")
            else datetime.utcnow()
        ),
        is_active=doc.get("is_active", True),
    )


class UserSessionStoreService:
    """UserSession 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 UserSession Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(USER_SESSIONS_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(USER_SESSIONS_COLLECTION)

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

        # session_id 唯一索引
        session_id_fields = ("session_id",)
        if session_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["session_id"],
                    "unique": True,
                    "name": "idx_user_sessions_session_id",
                }
            )

        # user_id 索引
        user_id_fields = ("user_id",)
        if user_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id"],
                    "name": "idx_user_sessions_user_id",
                }
            )

        # user_id + is_active 複合索引
        user_active_fields = ("user_id", "is_active")
        if user_active_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id", "is_active"],
                    "name": "idx_user_sessions_user_active",
                }
            )

        # expires_at TTL 索引（自動清理過期會話）
        expires_at_fields = ("expires_at",)
        if expires_at_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "ttl",
                    "fields": ["expires_at"],
                    "expireAfter": 0,  # 過期後立即清理
                    "name": "idx_user_sessions_expires_at_ttl",
                }
            )

    def create_session(self, session_data: UserSessionCreate) -> UserSessionModel:
        """
        創建用戶會話

        Args:
            session_data: 會話創建數據

        Returns:
            創建的會話模型

        Raises:
            ValueError: 如果會話 ID 已存在
        """
        # 檢查會話 ID 是否已存在
        existing = self._collection.find({"session_id": session_data.session_id}, limit=1)
        if existing:
            raise ValueError(f"Session ID '{session_data.session_id}' already exists")

        now = datetime.utcnow().isoformat()
        doc_key = f"session_{uuid.uuid4().hex[:12]}"
        doc: Dict[str, Any] = {
            "_key": doc_key,
            "session_id": session_data.session_id,
            "user_id": session_data.user_id,
            "access_token": session_data.access_token,
            "refresh_token": session_data.refresh_token,
            "ip_address": session_data.ip_address,
            "user_agent": session_data.user_agent,
            "device_info": session_data.device_info,
            "login_at": now,
            "last_activity_at": now,
            "expires_at": session_data.expires_at.isoformat(),
            "is_active": True,
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                f"User session created: session_id={session_data.session_id}, user_id={session_data.user_id}"
            )
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                f"Failed to create user session: session_id={session_data.session_id}, error={str(exc)}"
            )
            raise

    def get_session(self, session_id: str) -> Optional[UserSessionModel]:
        """
        獲取用戶會話

        Args:
            session_id: 會話 ID

        Returns:
            會話模型，如果不存在則返回 None
        """
        results = self._collection.find({"session_id": session_id}, limit=1)
        if not results:
            return None
        return _document_to_model(results[0])

    def list_user_sessions(
        self,
        user_id: str,
        include_inactive: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[List[UserSessionModel], int]:
        """
        列出用戶會話

        Args:
            user_id: 用戶 ID
            include_inactive: 是否包含未活躍的會話
            limit: 限制返回數量
            offset: 偏移量（用於分頁）

        Returns:
            (會話列表, 總數)
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 構建 AQL 查詢
        aql = "FOR doc IN user_sessions"
        bind_vars: Dict[str, Any] = {"user_id": user_id}

        # 構建過濾條件
        filters = ["doc.user_id == @user_id"]
        if not include_inactive:
            filters.append("doc.is_active == true")

        if filters:
            aql += " FILTER " + " AND ".join(filters)

        # 計算總數
        count_aql = aql + " COLLECT WITH COUNT INTO total RETURN total"
        try:
            count_cursor = self._client.db.aql.execute(count_aql, bind_vars=bind_vars)
            total = list(count_cursor)[0] if count_cursor else 0
        except Exception:
            total = 0

        # 排序和分頁
        aql += " SORT doc.login_at DESC"
        if limit:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit

        aql += " RETURN doc"

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            results = list(cursor)
            return ([_document_to_model(doc) for doc in results], total)
        except Exception as e:
            self._logger.error(
                f"Failed to list user sessions: user_id={user_id}, error={e}", exc_info=True
            )
            return ([], 0)

    def list_all_active_sessions(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> tuple[List[UserSessionModel], int]:
        """
        列出所有活躍會話（僅 Super Admin 可調用）

        Args:
            limit: 限制返回數量
            offset: 偏移量（用於分頁）

        Returns:
            (會話列表, 總數)
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 構建 AQL 查詢
        aql = "FOR doc IN user_sessions FILTER doc.is_active == true"
        bind_vars: Dict[str, Any] = {}

        # 計算總數
        count_aql = aql + " COLLECT WITH COUNT INTO total RETURN total"
        try:
            count_cursor = self._client.db.aql.execute(count_aql, bind_vars=bind_vars)
            total = list(count_cursor)[0] if count_cursor else 0
        except Exception:
            total = 0

        # 排序和分頁
        aql += " SORT doc.login_at DESC"
        if limit:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit

        aql += " RETURN doc"

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            results = list(cursor)
            return ([_document_to_model(doc) for doc in results], total)
        except Exception as e:
            self._logger.error(f"Failed to list all active sessions: error={e}", exc_info=True)
            return ([], 0)

    def update_session(
        self, session_id: str, session_data: UserSessionUpdate
    ) -> Optional[UserSessionModel]:
        """
        更新用戶會話

        Args:
            session_id: 會話 ID
            session_data: 會話更新數據

        Returns:
            更新後的會話模型，如果會話不存在則返回 None
        """
        results = self._collection.find({"session_id": session_id}, limit=1)
        if not results:
            return None

        existing = results[0]

        # 構建更新文檔
        update_doc: Dict[str, Any] = {}

        if session_data.last_activity_at is not None:
            update_doc["last_activity_at"] = session_data.last_activity_at.isoformat()
        if session_data.is_active is not None:
            update_doc["is_active"] = session_data.is_active

        if not update_doc:
            # 沒有需要更新的內容
            return _document_to_model(existing)

        try:
            self._collection.update({"_key": existing["_key"], **update_doc})
            self._logger.info(f"User session updated: session_id={session_id}")
            return self.get_session(session_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to update user session: session_id={session_id}, error={str(exc)}"
            )
            raise

    def terminate_session(self, session_id: str) -> bool:
        """
        終止用戶會話

        Args:
            session_id: 會話 ID

        Returns:
            是否成功終止
        """
        results = self._collection.find({"session_id": session_id}, limit=1)
        if not results:
            return False

        existing = results[0]

        try:
            self._collection.update(
                {
                    "_key": existing["_key"],
                    "is_active": False,
                    "last_activity_at": datetime.utcnow().isoformat(),
                }
            )
            self._logger.info(f"User session terminated: session_id={session_id}")
            return True
        except Exception as exc:
            self._logger.error(
                f"Failed to terminate user session: session_id={session_id}, error={str(exc)}"
            )
            raise

    def terminate_user_sessions(
        self, user_id: str, exclude_session_id: Optional[str] = None
    ) -> int:
        """
        終止用戶的所有會話

        Args:
            user_id: 用戶 ID
            exclude_session_id: 要排除的會話 ID（可選，用於保留當前會話）

        Returns:
            終止的會話數量
        """
        filters: Dict[str, Any] = {"user_id": user_id, "is_active": True}
        sessions = self._collection.find(filters)

        terminated_count = 0
        for session in sessions:
            if exclude_session_id and session.get("session_id") == exclude_session_id:
                continue

            try:
                self._collection.update(
                    {
                        "_key": session["_key"],
                        "is_active": False,
                        "last_activity_at": datetime.utcnow().isoformat(),
                    }
                )
                terminated_count += 1
            except Exception as exc:
                self._logger.error(
                    f"Failed to terminate user session: session_id={session.get('session_id')}, error={str(exc)}"
                )

        self._logger.info(f"User sessions terminated: user_id={user_id}, count={terminated_count}")
        return terminated_count

    def update_activity(self, session_id: str) -> bool:
        """
        更新會話活動時間

        Args:
            session_id: 會話 ID

        Returns:
            是否成功更新
        """
        results = self._collection.find({"session_id": session_id}, limit=1)
        if not results:
            return False

        existing = results[0]

        try:
            self._collection.update(
                {
                    "_key": existing["_key"],
                    "last_activity_at": datetime.utcnow().isoformat(),
                }
            )
            return True
        except Exception as exc:
            self._logger.warning(
                f"Failed to update session activity: session_id={session_id}, error={str(exc)}"
            )
            return False


def get_user_session_store_service(
    client: Optional[ArangoDBClient] = None,
) -> UserSessionStoreService:
    """
    獲取 UserSession Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        UserSessionStoreService 實例
    """
    global _service
    if _service is None:
        _service = UserSessionStoreService(client)
    return _service


_service: Optional[UserSessionStoreService] = None
