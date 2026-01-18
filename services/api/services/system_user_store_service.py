# 代碼功能說明: SystemUser 存儲服務 - 提供 SystemUser 的 CRUD 操作
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""SystemUser Store Service

提供 SystemUser 的 CRUD 操作，包括創建、查詢、更新、刪除、密碼重置等功能。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import bcrypt
import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.system_user import SystemUserCreate, SystemUserModel, SystemUserUpdate

logger = structlog.get_logger(__name__)

SYSTEM_USERS_COLLECTION = "system_users"


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


def _document_to_model(doc: Dict[str, Any]) -> SystemUserModel:
    """將 ArangoDB document 轉換為 SystemUserModel"""
    return SystemUserModel(
        id=doc.get("_key"),
        user_id=doc.get("user_id"),
        username=doc.get("username"),
        email=doc.get("email"),
        password_hash=doc.get("password_hash"),  # 不返回給客戶端，但模型需要
        roles=doc.get("roles", []),
        permissions=doc.get("permissions", []),
        is_active=doc.get("is_active", True),
        is_system_user=doc.get("is_system_user", True),
        security_level=doc.get("security_level", "highest"),
        created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
        updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        metadata=doc.get("metadata", {}),
    )


class SystemUserStoreService:
    """SystemUser 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 SystemUser Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(SYSTEM_USERS_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(SYSTEM_USERS_COLLECTION)

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
                    "name": "idx_system_users_user_id",
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
                    "name": "idx_system_users_username",
                }
            )

        # is_active 索引
        is_active_fields = ("is_active",)
        if is_active_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["is_active"],
                    "name": "idx_system_users_is_active",
                }
            )

    def create_system_user(self, user_data: SystemUserCreate) -> SystemUserModel:
        """
        創建系統用戶

        Args:
            user_data: 用戶創建數據

        Returns:
            創建的用戶模型

        Raises:
            ValueError: 如果用戶 ID 或用戶名已存在
        """
        # 檢查用戶 ID 是否已存在
        existing_by_id = self._collection.get(user_data.user_id)
        if existing_by_id:
            raise ValueError(f"User ID '{user_data.user_id}' already exists")

        # 檢查用戶名是否已存在
        existing_by_username = self._collection.find({"username": user_data.username}, limit=1)
        if existing_by_username:
            raise ValueError(f"Username '{user_data.username}' already exists")

        # 哈希密碼
        password_hash = _hash_password(user_data.password)

        now = datetime.utcnow().isoformat()
        doc: Dict[str, Any] = {
            "_key": user_data.user_id,
            "user_id": user_data.user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "roles": user_data.roles or ["system_admin"],
            "permissions": user_data.permissions or ["*"],
            "is_active": user_data.is_active,
            "is_system_user": True,
            "security_level": user_data.security_level,
            "created_at": now,
            "updated_at": now,
            "metadata": user_data.metadata or {},
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                f"System user created: user_id={user_data.user_id}, username={user_data.username}"
            )
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                f"Failed to create system user: user_id={user_data.user_id}, error={str(exc)}"
            )
            raise

    def get_system_user(self, user_id: str) -> Optional[SystemUserModel]:
        """
        獲取系統用戶

        Args:
            user_id: 用戶 ID

        Returns:
            用戶模型，如果不存在則返回 None
        """
        doc = self._collection.get(user_id)
        if doc is None:
            return None
        return _document_to_model(doc)

    def get_system_user_by_username(self, username: str) -> Optional[SystemUserModel]:
        """
        根據用戶名獲取系統用戶

        Args:
            username: 用戶名

        Returns:
            用戶模型，如果不存在則返回 None
        """
        results = self._collection.find({"username": username}, limit=1)
        if not results:
            return None
        return _document_to_model(results[0])

    def list_system_users(
        self, include_inactive: bool = False, limit: Optional[int] = None
    ) -> List[SystemUserModel]:
        """
        列出所有系統用戶

        Args:
            include_inactive: 是否包含未啟用的用戶
            limit: 限制返回數量

        Returns:
            用戶列表
        """
        filters: Dict[str, Any] = {}
        if not include_inactive:
            filters["is_active"] = True

        results = self._collection.find(filters, limit=limit)
        return [_document_to_model(doc) for doc in results]

    def update_system_user(
        self, user_id: str, user_data: SystemUserUpdate
    ) -> Optional[SystemUserModel]:
        """
        更新系統用戶

        Args:
            user_id: 用戶 ID
            user_data: 用戶更新數據

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None

        Raises:
            ValueError: 如果嘗試修改默認 systemAdmin 的某些字段
        """
        existing = self._collection.get(user_id)
        if existing is None:
            return None

        # 禁止修改默認 systemAdmin 的某些字段
        if user_id == "systemAdmin":
            if user_data.is_active is False:
                raise ValueError("Cannot deactivate default systemAdmin user")
            if user_data.roles and "system_admin" not in user_data.roles:
                raise ValueError("Cannot remove system_admin role from default systemAdmin user")

        # 檢查用戶名唯一性（如果更新用戶名）
        if user_data.username and user_data.username != existing.get("username"):
            existing_by_username = self._collection.find({"username": user_data.username}, limit=1)
            if existing_by_username and existing_by_username[0].get("_key") != user_id:
                raise ValueError(f"Username '{user_data.username}' already exists")

        # 構建更新文檔
        update_doc: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if user_data.username is not None:
            update_doc["username"] = user_data.username
        if user_data.email is not None:
            update_doc["email"] = user_data.email
        if user_data.roles is not None:
            update_doc["roles"] = user_data.roles
        if user_data.permissions is not None:
            update_doc["permissions"] = user_data.permissions
        if user_data.is_active is not None:
            update_doc["is_active"] = user_data.is_active
        if user_data.security_level is not None:
            update_doc["security_level"] = user_data.security_level
        if user_data.metadata is not None:
            # 合併元數據
            existing_metadata = existing.get("metadata", {})
            existing_metadata.update(user_data.metadata)
            update_doc["metadata"] = existing_metadata

        try:
            self._collection.update({"_key": user_id, **update_doc})
            self._logger.info(f"System user updated: user_id={user_id}")
            return self.get_system_user(user_id)
        except Exception as exc:
            self._logger.error(f"Failed to update system user: user_id={user_id}, error={str(exc)}")
            raise

    def delete_system_user(self, user_id: str) -> bool:
        """
        刪除系統用戶（軟刪除）

        Args:
            user_id: 用戶 ID

        Returns:
            是否成功刪除

        Raises:
            ValueError: 如果嘗試刪除默認 systemAdmin
        """
        if user_id == "systemAdmin":
            raise ValueError("Cannot delete default systemAdmin user")

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
            self._logger.info(f"System user deleted (soft): user_id={user_id}")
            return True
        except Exception as exc:
            self._logger.error(f"Failed to delete system user: user_id={user_id}, error={str(exc)}")
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
            self._logger.info(f"Password reset for system user: user_id={user_id}")
            return True
        except Exception as exc:
            self._logger.error(
                f"Failed to reset password for system user: user_id={user_id}, error={str(exc)}"
            )
            raise

    def toggle_active(self, user_id: str) -> Optional[SystemUserModel]:
        """
        切換用戶啟用狀態

        Args:
            user_id: 用戶 ID

        Returns:
            更新後的用戶模型，如果用戶不存在則返回 None

        Raises:
            ValueError: 如果嘗試禁用默認 systemAdmin
        """
        if user_id == "systemAdmin":
            raise ValueError("Cannot deactivate default systemAdmin user")

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
                f"System user active status toggled: user_id={user_id}, is_active={new_active_status}"
            )
            return self.get_system_user(user_id)
        except Exception as exc:
            self._logger.error(
                f"Failed to toggle active status for system user: user_id={user_id}, error={str(exc)}"
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
        user = self.get_system_user(user_id)
        if user is None or user.password_hash is None:
            return False
        return _verify_password(password, user.password_hash)


def get_system_user_store_service(
    client: Optional[ArangoDBClient] = None,
) -> SystemUserStoreService:
    """
    獲取 SystemUser Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        SystemUserStoreService 實例
    """
    global _service
    if _service is None:
        _service = SystemUserStoreService(client)
    return _service


_service: Optional[SystemUserStoreService] = None
