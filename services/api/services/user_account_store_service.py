# 代碼功能說明: UserAccount 存儲服務 - 提供用戶賬號的 CRUD 操作
# 創建日期: 2026-01-17 17:33 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:33 UTC+8

"""UserAccount Store Service

提供用戶賬號的 CRUD 操作，包括創建、查詢、更新、刪除、密碼重置等功能。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import bcrypt
import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.user_account import UserAccountCreate, UserAccountModel, UserAccountUpdate

logger = structlog.get_logger(__name__)

USER_ACCOUNTS_COLLECTION = "user_accounts"


def _hash_password(password: str) -> str:
    """使用 bcrypt 哈希密碼

    Args:
        password: 明文密碼

    Returns:
        bcrypt 哈希後的密碼
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    """驗證密碼

    Args:
        password: 明文密碼
        password_hash: bcrypt 哈希密碼

    Returns:
        是否匹配
    """
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _document_to_model(doc: Dict[str, Any]) -> UserAccountModel:
    """將 ArangoDB document 轉換為 UserAccountModel"""
    return UserAccountModel(
        id=doc.get("_key"),
        user_id=doc.get("user_id"),
        username=doc.get("username"),
        email=doc.get("email"),
        password_hash=doc.get("password_hash"),  # 不返回給客戶端，但模型需要
        tenant_id=doc.get("tenant_id"),
        roles=doc.get("roles", []),
        permissions=doc.get("permissions", []),
        is_active=doc.get("is_active", True),
        is_system_user=doc.get("is_system_user", False),
        created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
        updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        last_login_at=(
            datetime.fromisoformat(doc["last_login_at"]) if doc.get("last_login_at") else None
        ),
        login_count=doc.get("login_count", 0),
        metadata=doc.get("metadata", {}),
    )


class UserAccountStoreService:
    """UserAccount 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 UserAccount Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(USER_ACCOUNTS_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(USER_ACCOUNTS_COLLECTION)

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

        # user_id 唯一索引
        user_id_fields = ("user_id",)
        if user_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["user_id"],
                    "unique": True,
                    "name": "idx_user_accounts_user_id",
                }
            )

        # username 唯一索引
        username_fields = ("username",)
        if username_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["username"],
                    "unique": True,
                    "name": "idx_user_accounts_username",
                }
            )

        # email 唯一索引
        email_fields = ("email",)
        if email_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["email"],
                    "unique": True,
                    "name": "idx_user_accounts_email",
                }
            )

        # tenant_id 索引
        tenant_id_fields = ("tenant_id",)
        if tenant_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id"],
                    "name": "idx_user_accounts_tenant_id",
                }
            )

        # is_active 索引
        is_active_fields = ("is_active",)
        if is_active_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["is_active"],
                    "name": "idx_user_accounts_is_active",
                }
            )

        # tenant_id + is_active 複合索引（用於租戶查詢）
        tenant_active_fields = ("tenant_id", "is_active")
        if tenant_active_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "is_active"],
                    "name": "idx_user_accounts_tenant_active",
                }
            )

    def create_user_account(self, user_data: UserAccountCreate) -> UserAccountModel:
        """
        創建用戶賬號

        Args:
            user_data: 用戶創建數據

        Returns:
            創建的用戶模型

        Raises:
            ValueError: 如果用戶 ID、用戶名或郵箱已存在
        """
        # 生成 user_id（如果未提供）
        user_id = user_data.user_id or f"user_{uuid.uuid4().hex[:12]}"

        # 檢查用戶 ID 是否已存在
        existing_by_id = self._collection.get(user_id)
        if existing_by_id:
            raise ValueError(f"User ID '{user_id}' already exists")

        # 檢查用戶名是否已存在
        existing_by_username = self._collection.find({"username": user_data.username}, limit=1)
        if existing_by_username:
            raise ValueError(f"Username '{user_data.username}' already exists")

        # 檢查郵箱是否已存在
        existing_by_email = self._collection.find({"email": user_data.email}, limit=1)
        if existing_by_email:
            raise ValueError(f"Email '{user_data.email}' already exists")

        # 哈希密碼
        password_hash = _hash_password(user_data.password)

        now = datetime.utcnow().isoformat()
        doc: Dict[str, Any] = {
            "_key": user_id,
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "tenant_id": user_data.tenant_id,
            "roles": user_data.roles or ["user"],
            "permissions": user_data.permissions or [],
            "is_active": user_data.is_active,
            "is_system_user": False,
            "created_at": now,
            "updated_at": now,
            "last_login_at": None,
            "login_count": 0,
            "metadata": user_data.metadata or {},
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                f"User account created: user_id={user_id}, username={user_data.username}"
            )
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                f"Failed to create user account: user_id={user_id}, error={str(exc)}"
            )
            raise

    def get_user_account(self, user_id: str) -> Optional[UserAccountModel]:
        """
        獲取用戶賬號

        Args:
            user_id: 用戶 ID

        Returns:
            用戶模型，如果不存在則返回 None
        """
        doc = self._collection.get(user_id)
        if doc is None:
            return None
        return _document_to_model(doc)

    def get_user_account_by_username(self, username: str) -> Optional[UserAccountModel]:
        """
        根據用戶名獲取用戶賬號

        Args:
            username: 用戶名

        Returns:
            用戶模型，如果不存在則返回 None
        """
        results = self._collection.find({"username": username}, limit=1)
        if not results:
            return None
        return _document_to_model(results[0])

    def get_user_account_by_email(self, email: str) -> Optional[UserAccountModel]:
        """
        根據郵箱獲取用戶賬號

        Args:
            email: 郵箱地址

        Returns:
            用戶模型，如果不存在則返回 None
        """
        results = self._collection.find({"email": email}, limit=1)
        if not results:
            return None
        return _document_to_model(results[0])

    def list_user_accounts(
        self,
        tenant_id: Optional[str] = None,
        include_inactive: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> tuple[List[UserAccountModel], int]:
        """
        列出用戶賬號

        Args:
            tenant_id: 租戶 ID（可選，None 表示所有租戶）
            include_inactive: 是否包含未啟用的用戶
            limit: 限制返回數量
            offset: 偏移量（用於分頁）
            search: 搜索關鍵字（搜索用戶名或郵箱）

        Returns:
            (用戶列表, 總數)
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 構建 AQL 查詢
        aql = "FOR doc IN user_accounts"
        bind_vars: Dict[str, Any] = {}

        # 構建過濾條件
        filters = []
        if tenant_id is not None:
            filters.append("doc.tenant_id == @tenant_id")
            bind_vars["tenant_id"] = tenant_id

        if not include_inactive:
            filters.append("doc.is_active == true")

        if search:
            filters.append("(doc.username LIKE @search OR doc.email LIKE @search)")
            bind_vars["search"] = f"%{search}%"

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
        aql += " SORT doc.created_at DESC"
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
            self._logger.error(f"Failed to list user accounts: {e}", exc_info=True)
            return ([], 0)

    def update_user_account(
        self, user_id: str, user_data: UserAccountUpdate
    ) -> Optional[UserAccountModel]:
        """
        更新用戶賬號

        Args:
            user_id: 用戶 ID
            user_data: 用戶更新數據

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None

        Raises:
            ValueError: 如果用戶名或郵箱已被其他用戶使用
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return None

        # 檢查用戶名唯一性（如果更新用戶名）
        if user_data.username and user_data.username != existing.get("username"):
            existing_by_username = self._collection.find({"username": user_data.username}, limit=1)
            if existing_by_username and existing_by_username[0].get("_key") != user_id:
                raise ValueError(f"Username '{user_data.username}' already exists")

        # 檢查郵箱唯一性（如果更新郵箱）
        if user_data.email and user_data.email != existing.get("email"):
            existing_by_email = self._collection.find({"email": user_data.email}, limit=1)
            if existing_by_email and existing_by_email[0].get("_key") != user_id:
                raise ValueError(f"Email '{user_data.email}' already exists")

        # 構建更新文檔
        update_doc: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if user_data.username is not None:
            update_doc["username"] = user_data.username
        if user_data.email is not None:
            update_doc["email"] = user_data.email
        if user_data.tenant_id is not None:
            update_doc["tenant_id"] = user_data.tenant_id
        if user_data.roles is not None:
            update_doc["roles"] = user_data.roles
        if user_data.permissions is not None:
            update_doc["permissions"] = user_data.permissions
        if user_data.is_active is not None:
            update_doc["is_active"] = user_data.is_active
        if user_data.metadata is not None:
            # 合併元數據
            existing_metadata = existing.get("metadata", {})
            existing_metadata.update(user_data.metadata)
            update_doc["metadata"] = existing_metadata

        try:
            self._collection.update({"_key": user_id, **update_doc})
            self._logger.info(f"User account updated: user_id={user_id}")
            return self.get_user_account(user_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to update user account: user_id={user_id}, error={str(exc)}"
            )
            raise

    def delete_user_account(self, user_id: str) -> bool:
        """
        刪除用戶賬號（軟刪除）

        Args:
            user_id: 用戶 ID

        Returns:
            是否成功刪除
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return False

        # 軟刪除：設置 is_active = False
        try:
            self._collection.update(
                {
                    "_key": user_id,
                    "is_active": False,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            self._logger.info(f"User account deleted (soft): user_id={user_id}")
            return True
        except Exception as exc:
            self._logger.error(
                f"Failed to delete user account: user_id={user_id}, error={str(exc)}"
            )
            raise

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        重置密碼

        Args:
            user_id: 用戶 ID
            new_password: 新密碼（明文）

        Returns:
            是否成功重置
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return False

        # 哈希新密碼
        password_hash = _hash_password(new_password)

        try:
            self._collection.update(
                {
                    "_key": user_id,
                    "password_hash": password_hash,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            self._logger.info(f"Password reset for user account: user_id={user_id}")
            return True
        except Exception as exc:
            self._logger.error(
                f"Failed to reset password for user account: user_id={user_id}, error={str(exc)}"
            )
            raise

    def toggle_active(self, user_id: str) -> Optional[UserAccountModel]:
        """
        切換用戶啟用狀態

        Args:
            user_id: 用戶 ID

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return None

        new_active_status = not existing.get("is_active", True)

        try:
            self._collection.update(
                {
                    "_key": user_id,
                    "is_active": new_active_status,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            self._logger.info(
                f"User account active status toggled: user_id={user_id}, is_active={new_active_status}"
            )
            return self.get_user_account(user_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to toggle active status for user account: user_id={user_id}, error={str(exc)}"
            )
            raise

    def verify_password(self, user_id: str, password: str) -> bool:
        """
        驗證用戶密碼

        Args:
            user_id: 用戶 ID
            password: 明文密碼

        Returns:
            是否匹配
        """
        user = self.get_user_account(user_id)
        if user is None or user.password_hash is None:
            return False
        return _verify_password(password, user.password_hash)

    def update_login_info(self, user_id: str) -> None:
        """
        更新登錄信息

        Args:
            user_id: 用戶 ID
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return

        try:
            now = datetime.utcnow().isoformat()
            login_count = existing.get("login_count", 0) + 1
            self._collection.update(
                {
                    "_key": user_id,
                    "last_login_at": now,
                    "login_count": login_count,
                    "updated_at": now,
                }
            )
        except Exception as exc:
            self._logger.warning(
                f"Failed to update login info: user_id={user_id}, error={str(exc)}"
            )

    def assign_role(self, user_id: str, role_id: str) -> Optional[UserAccountModel]:
        """
        分配角色給用戶

        Args:
            user_id: 用戶 ID
            role_id: 角色 ID

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None
        """
        user = self.get_user_account(user_id)
        if user is None:
            return None

        if role_id not in user.roles:
            roles = user.roles + [role_id]
            return self.update_user_account(user_id, UserAccountUpdate(roles=roles))
        return user

    def revoke_role(self, user_id: str, role_id: str) -> Optional[UserAccountModel]:
        """
        撤銷用戶角色

        Args:
            user_id: 用戶 ID
            role_id: 角色 ID

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None
        """
        user = self.get_user_account(user_id)
        if user is None:
            return None

        if role_id in user.roles:
            roles = [r for r in user.roles if r != role_id]
            return self.update_user_account(user_id, UserAccountUpdate(roles=roles))
        return user


def get_user_account_store_service(
    client: Optional[ArangoDBClient] = None,
) -> UserAccountStoreService:
    """
    獲取 UserAccount Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        UserAccountStoreService 實例
    """
    global _service
    if _service is None:
        _service = UserAccountStoreService(client)
    return _service


_service: Optional[UserAccountStoreService] = None
