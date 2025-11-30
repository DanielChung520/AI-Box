# 代碼功能說明: 安全相關數據模型
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:30 (UTC+8)

"""安全相關數據模型定義。"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class Permission(str, Enum):
    """權限枚舉 - 預定義常用權限"""

    # 通用權限
    ALL = "*"  # 超級管理員權限

    # Agent 相關權限
    AGENT_VIEW = "agent:view"
    AGENT_EXECUTE = "agent:execute"
    AGENT_MANAGE = "agent:manage"

    # Task 相關權限
    TASK_VIEW = "task:view"
    TASK_CREATE = "task:create"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"

    # LLM 相關權限
    LLM_GENERATE = "llm:generate"
    LLM_CHAT = "llm:chat"
    LLM_EMBEDDING = "llm:embedding"

    # ChromaDB 相關權限
    CHROMADB_READ = "chromadb:read"
    CHROMADB_WRITE = "chromadb:write"

    # ArangoDB 相關權限
    ARANGODB_READ = "arangodb:read"
    ARANGODB_WRITE = "arangodb:write"


class Role(str, Enum):
    """角色枚舉 - 預定義常用角色"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    DEVELOPER = "developer"


@dataclass
class User:
    """用戶模型 - 表示認證後的用戶信息"""

    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化後處理"""
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}

    def has_role(self, role: str) -> bool:
        """檢查用戶是否擁有指定角色"""
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """檢查用戶是否擁有指定權限"""
        # ALL 權限表示擁有所有權限
        if Permission.ALL.value in self.permissions:
            return True
        return permission in self.permissions

    def has_any_permission(self, *permissions: str) -> bool:
        """檢查用戶是否擁有任意一個指定權限"""
        return any(self.has_permission(perm) for perm in permissions)

    def has_all_permissions(self, *permissions: str) -> bool:
        """檢查用戶是否擁有所有指定權限"""
        return all(self.has_permission(perm) for perm in permissions)

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }

    @classmethod
    def create_dev_user(cls) -> "User":
        """創建開發模式下的默認用戶"""
        return cls(
            user_id="dev_user",
            username="development_user",
            email="dev@ai-box.local",
            roles=[Role.ADMIN.value],
            permissions=[Permission.ALL.value],
            is_active=True,
            metadata={"mode": "development", "bypass_auth": True},
        )
