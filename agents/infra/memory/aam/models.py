# 代碼功能說明: AAM 記憶數據模型
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 記憶數據模型定義"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class MemoryType(str, Enum):
    """記憶類型枚舉"""

    SHORT_TERM = "short_term"  # 短期記憶
    LONG_TERM = "long_term"  # 長期記憶


class MemoryPriority(str, Enum):
    """記憶優先級枚舉"""

    LOW = "low"  # 低優先級
    MEDIUM = "medium"  # 中優先級
    HIGH = "high"  # 高優先級
    CRITICAL = "critical"  # 關鍵優先級


@dataclass
class Memory:
    """記憶數據模型"""

    memory_id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority = MemoryPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accessed_at: Optional[datetime] = None
    access_count: int = 0
    relevance_score: float = 0.0  # 相關度分數（0.0-1.0）

    # Qdrant 擴展欄位
    user_id: str = ""  # 用於 User Isolation
    entity_type: str = ""  # 實體類型 (part_number, tlf19, etc.)
    entity_value: str = ""  # 實體值 (RM05-008, 101, etc.)
    confidence: float = 0.5  # 置信度 (0.0-1.0)
    status: str = "active"  # 狀態 (active, archived, review)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
            # Qdrant 擴展欄位
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "entity_value": self.entity_value,
            "confidence": self.confidence,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Memory:
        """從字典創建 Memory 對象"""
        return cls(
            memory_id=data["memory_id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            priority=MemoryPriority(data.get("priority", "medium")),
            metadata=data.get("metadata", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("created_at"), str)
                else data.get("created_at", datetime.now())
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if isinstance(data.get("updated_at"), str)
                else data.get("updated_at", datetime.now())
            ),
            accessed_at=(
                datetime.fromisoformat(data["accessed_at"])
                if isinstance(data.get("accessed_at"), str) and data.get("accessed_at")
                else None
            ),
            access_count=data.get("access_count", 0),
            relevance_score=data.get("relevance_score", 0.0),
            # Qdrant 擴展欄位
            user_id=data.get("user_id", ""),
            entity_type=data.get("entity_type", ""),
            entity_value=data.get("entity_value", ""),
            confidence=data.get("confidence", 0.5),
            status=data.get("status", "active"),
        )

    def update_access(self) -> None:
        """更新訪問信息"""
        self.accessed_at = datetime.now()
        self.access_count += 1
