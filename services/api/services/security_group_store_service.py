# 代碼功能說明: 安全群組存儲服務
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 19:41 UTC+8

"""Security Group Store Service

提供安全群組的 CRUD 操作和規則驗證。
"""

from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.security_group import (
    SecurityGroupCreate,
    SecurityGroupModel,
    SecurityGroupUpdate,
)

logger = structlog.get_logger(__name__)

SECURITY_GROUPS_COLLECTION = "security_groups"


class SecurityGroupStoreService:
    """安全群組存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化安全群組存儲服務

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(SECURITY_GROUPS_COLLECTION)
        self._collection = ArangoCollection(collection)

        # 創建索引
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        try:
            if not self._collection.has_index("idx_groups_tenant_active"):
                self._collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["tenant_id", "is_active"],
                    },
                    name="idx_groups_tenant_active",
                )
            if not self._collection.has_index("idx_groups_group_id"):
                self._collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["group_id"],
                        "unique": True,
                    },
                    name="idx_groups_group_id",
                )
        except Exception as e:
            self._logger.warning(f"Failed to create indexes: {str(e)}")

    def create_security_group(self, group: SecurityGroupCreate) -> SecurityGroupModel:
        """
        創建安全群組

        Args:
            group: 安全群組創建數據

        Returns:
            創建的安全群組
        """
        now = datetime.utcnow()

        doc = {
            "_key": group.group_id,
            "group_id": group.group_id,
            "group_name": group.group_name,
            "description": group.description,
            "tenant_id": group.tenant_id,
            "rules": group.rules.model_dump(mode="json"),
            "users": group.users,
            "is_active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self._collection.insert(doc, overwrite=True)

        self._logger.info(f"Security group created: group_id={group.group_id}")

        return self._document_to_model(doc)

    def get_security_group(self, group_id: str) -> Optional[SecurityGroupModel]:
        """
        獲取安全群組

        Args:
            group_id: 群組 ID

        Returns:
            安全群組，如果不存在則返回 None
        """
        doc = self._collection.get(group_id)

        if doc is None:
            return None

        return self._document_to_model(doc)

    def list_security_groups(
        self,
        tenant_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[SecurityGroupModel]:
        """
        列出安全群組

        Args:
            tenant_id: 租戶 ID 過濾（可選）
            is_active: 是否啟用過濾（可選）
            limit: 限制返回數量（可選）

        Returns:
            安全群組列表
        """
        filters: Dict[str, Any] = {}
        if tenant_id is not None:
            filters["tenant_id"] = tenant_id
        if is_active is not None:
            filters["is_active"] = is_active

        docs = self._collection.find(filters, limit=limit)

        groups = []
        for doc in docs:
            try:
                groups.append(self._document_to_model(doc))
            except Exception as e:
                self._logger.warning(
                    f"Failed to parse security group: group_id={doc.get('group_id')}, error={str(e)}"
                )

        return groups

    def update_security_group(
        self, group_id: str, updates: SecurityGroupUpdate
    ) -> Optional[SecurityGroupModel]:
        """
        更新安全群組

        Args:
            group_id: 群組 ID
            updates: 更新字段

        Returns:
            更新後的安全群組，如果不存在則返回 None
        """
        doc = self._collection.get(group_id)

        if doc is None:
            return None

        # 更新字段
        if updates.group_name is not None:
            doc["group_name"] = updates.group_name
        if updates.description is not None:
            doc["description"] = updates.description
        if updates.rules is not None:
            doc["rules"] = updates.rules.model_dump(mode="json")
        if updates.users is not None:
            doc["users"] = updates.users
        if updates.is_active is not None:
            doc["is_active"] = updates.is_active

        doc["updated_at"] = datetime.utcnow().isoformat()

        self._collection.update(group_id, doc)

        self._logger.info(f"Security group updated: group_id={group_id}")

        return self._document_to_model(doc)

    def delete_security_group(self, group_id: str) -> bool:
        """
        刪除安全群組

        Args:
            group_id: 群組 ID

        Returns:
            是否成功刪除
        """
        try:
            self._collection.delete(group_id)
            self._logger.info(f"Security group deleted: group_id={group_id}")
            return True
        except Exception as e:
            self._logger.error(
                f"Failed to delete security group: group_id={group_id}, error={str(e)}"
            )
            return False

    def add_user_to_group(self, group_id: str, user_id: str) -> Optional[SecurityGroupModel]:
        """
        將用戶添加到安全群組

        Args:
            group_id: 群組 ID
            user_id: 用戶 ID

        Returns:
            更新後的安全群組，如果不存在則返回 None
        """
        doc = self._collection.get(group_id)

        if doc is None:
            return None

        users = doc.get("users", [])
        if user_id not in users:
            users.append(user_id)
            doc["users"] = users
            doc["updated_at"] = datetime.utcnow().isoformat()
            self._collection.update(group_id, doc)

            self._logger.info(
                f"User added to security group: group_id={group_id}, user_id={user_id}"
            )

        return self._document_to_model(doc)

    def remove_user_from_group(self, group_id: str, user_id: str) -> Optional[SecurityGroupModel]:
        """
        從安全群組移除用戶

        Args:
            group_id: 群組 ID
            user_id: 用戶 ID

        Returns:
            更新後的安全群組，如果不存在則返回 None
        """
        doc = self._collection.get(group_id)

        if doc is None:
            return None

        users = doc.get("users", [])
        if user_id in users:
            users.remove(user_id)
            doc["users"] = users
            doc["updated_at"] = datetime.utcnow().isoformat()
            self._collection.update(group_id, doc)

            self._logger.info(
                f"User removed from security group: group_id={group_id}, user_id={user_id}"
            )

        return self._document_to_model(doc)

    def check_ip_access(self, group: SecurityGroupModel, ip_address: str) -> bool:
        """
        檢查 IP 地址是否可以訪問

        Args:
            group: 安全群組
            ip_address: IP 地址

        Returns:
            是否允許訪問
        """
        # 檢查黑名單
        for blacklisted in group.rules.ip_blacklist:
            try:
                if self._ip_in_cidr(ip_address, blacklisted):
                    return False
            except Exception:
                continue

        # 檢查白名單（如果有白名單，必須在白名單中）
        if group.rules.ip_whitelist:
            for whitelisted in group.rules.ip_whitelist:
                try:
                    if self._ip_in_cidr(ip_address, whitelisted):
                        return True
                except Exception:
                    continue
            return False  # 有白名單但不在白名單中

        return True  # 沒有白名單或黑名單，允許訪問

    def check_time_access(self, group: SecurityGroupModel, current_time: datetime) -> bool:
        """
        檢查當前時間是否允許訪問

        Args:
            group: 安全群組
            current_time: 當前時間

        Returns:
            是否允許訪問
        """
        if not group.rules.allowed_time_ranges:
            return True  # 沒有時間限制

        current_time_only = current_time.time()
        current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        day_map = {
            0: "mon",
            1: "tue",
            2: "wed",
            3: "thu",
            4: "fri",
            5: "sat",
            6: "sun",
        }
        current_day = day_map[current_weekday]

        for time_range in group.rules.allowed_time_ranges:
            days = time_range.get("days", [])
            if current_day not in days:
                continue

            start_str = time_range.get("start", "00:00")
            end_str = time_range.get("end", "23:59")

            try:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()

                if start_time <= current_time_only <= end_time:
                    return True
            except Exception:
                continue

        return False  # 不在任何允許的時間範圍內

    def _ip_in_cidr(self, ip: str, cidr: str) -> bool:
        """檢查 IP 是否在 CIDR 範圍內"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            network = ipaddress.ip_network(cidr, strict=False)
            return ip_obj in network
        except Exception:
            return False

    def _document_to_model(self, doc: Dict[str, Any]) -> SecurityGroupModel:
        """將文檔轉換為模型"""
        from services.api.models.security_group import SecurityGroupRules

        return SecurityGroupModel(
            id=doc["_key"],
            group_id=doc["group_id"],
            group_name=doc["group_name"],
            description=doc.get("description"),
            tenant_id=doc.get("tenant_id"),
            rules=SecurityGroupRules(**doc.get("rules", {})),
            users=doc.get("users", []),
            is_active=doc.get("is_active", True),
            created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
            updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        )


# 單例模式
_service: Optional[SecurityGroupStoreService] = None


def get_security_group_store_service() -> SecurityGroupStoreService:
    """獲取 SecurityGroupStoreService 實例（單例模式）"""
    global _service
    if _service is None:
        _service = SecurityGroupStoreService()
    return _service
