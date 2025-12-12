# 代碼功能說明: 上下文管理數據模型
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""定義上下文管理相關的數據模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ContextMessage(BaseModel):
    """上下文消息數據模型。"""

    role: str = Field(description="消息角色（user, assistant, system）")
    content: str = Field(description="消息內容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息時間戳")
    agent_name: Optional[str] = Field(default=None, description="Agent 名稱")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


@dataclass
class ContextSession:
    """上下文會話數據模型。"""

    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self) -> None:
        """更新會話的更新時間。"""
        self.updated_at = datetime.now()


class ContextConfig(BaseModel):
    """上下文管理配置數據模型。"""

    redis_url: Optional[str] = Field(default=None, description="Redis 連接 URL")
    namespace: str = Field(default="agent_process:context", description="命名空間")
    ttl_seconds: int = Field(default=3600, ge=60, description="TTL 秒數")
    max_messages_per_session: int = Field(
        default=1000, ge=1, description="每個會話最大消息數"
    )
    enable_persistence: bool = Field(default=False, description="是否啟用持久化存儲")
    arangodb_collection: Optional[str] = Field(
        default=None, description="ArangoDB 集合名稱"
    )
