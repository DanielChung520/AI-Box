# 代碼功能說明: Entity Memory 數據模型
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""Entity Memory 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class EntityType(str, Enum):
    """實體類型枚舉"""

    ENTITY_NOUN = "entity_noun"  # 名詞實體（所有需要長期記憶的名詞）


class EntityStatus(str, Enum):
    """實體狀態枚舉"""

    ACTIVE = "active"  # 活躍
    ARCHIVED = "archived"  # 歸檔
    REVIEW = "review"  # 待審核


class EntityMemory(BaseModel):
    """
    實體記憶數據模型（存儲到 Qdrant）

    用於長期追蹤和管理對話中出現的重要實體名詞。
    """

    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_value: str = Field(..., description="實體名稱（如 'AI-Box'）")
    entity_type: EntityType = Field(default=EntityType.ENTITY_NOUN)
    user_id: str = Field(..., description="所屬用戶 ID")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: EntityStatus = Field(default=EntityStatus.ACTIVE)
    first_mentioned: datetime = Field(default_factory=datetime.utcnow)
    last_mentioned: datetime = Field(default_factory=datetime.utcnow)
    mention_count: int = Field(default=0, ge=0)
    vector: Optional[List[float]] = Field(default=None, description="實體向量表示")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    related_entities: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """自定義 model_dump"""
        data = super().model_dump(*args, **kwargs)
        for field_name in ["started_at", "last_activity"]:
            if field_name in data and isinstance(data[field_name], datetime):
                data[field_name] = data[field_name].isoformat()
        return data


class EntityRelation(BaseModel):
    """
    實體關係數據模型（存儲到 ArangoDB）

    用於追蹤實體之間的關聯關係。
    """

    relation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str = Field(..., description="源實體 ID")
    target_entity_id: str = Field(..., description="目標實體 ID")
    relation_type: str = Field(default="related", description="關係類型")
    description: Optional[str] = Field(default=None, description="關係描述")
    user_id: str = Field(..., description="所屬用戶 ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class SessionContext(BaseModel):
    """
    會話上下文數據模型（存儲到 Redis）

    用於追蹤會話內的實體引用和指代關係。
    """

    session_id: str = Field(..., description="會話 ID")
    user_id: str = Field(..., description="用戶 ID")
    mentioned_entities: List[str] = Field(
        default_factory=list, description="會話中提到的實體 ID 列表"
    )
    last_referred_entity: Optional[str] = Field(
        default=None, description="最後被指代詞引用的實體 ID"
    )
    coreference_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="指代消解歷史記錄"
    )
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class CoreferenceResolution(BaseModel):
    """指代消解結果"""

    original_text: str = Field(..., description="原始指代詞（如 '它'）")
    resolved_text: str = Field(..., description="消解後的實體（如 'AI-Box'）")
    entity_id: Optional[str] = Field(default=None, description="實體 ID（如果存在）")
    source: str = Field(
        default="inference", description="來源: 'session' | 'long_term' | 'inference'"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CoreferenceResult(BaseModel):
    """指代消解完整結果"""

    original_query: str = Field(..., description="原始查詢")
    resolved_query: str = Field(..., description="消解後的查詢")
    resolutions: List[CoreferenceResolution] = Field(
        default_factory=list, description="指代消解列表"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    entities_found: List[str] = Field(default_factory=list)


class EntitySearchResult(BaseModel):
    """實體搜索結果（含分數）"""

    entity: EntityMemory
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="vector", description="來源: 'vector' | 'exact' | 'type_filter'")


EntityMemory.model_rebuild()
EntityRelation.model_rebuild()
SessionContext.model_rebuild()
CoreferenceResolution.model_rebuild()
CoreferenceResult.model_rebuild()
EntitySearchResult.model_rebuild()
