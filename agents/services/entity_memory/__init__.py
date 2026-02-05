# 代碼功能說明: Entity Memory 服務模組
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""Entity Memory 服務 - 長期實體記憶管理模組

提供實體記憶的存儲、檢索、提取和指代消解功能。
"""

from .models import (
    EntityType,
    EntityStatus,
    EntityMemory,
    EntityRelation,
    SessionContext,
    CoreferenceResolution,
    CoreferenceResult,
)

from .entity_storage import EntityStorage
from .entity_memory_service import EntityMemoryService, get_entity_memory_service
from .entity_extractor import EntityExtractor, get_entity_extractor

__all__ = [
    "EntityType",
    "EntityStatus",
    "EntityMemory",
    "EntityRelation",
    "SessionContext",
    "CoreferenceResolution",
    "CoreferenceResult",
    "EntityStorage",
    "EntityMemoryService",
    "get_entity_memory_service",
    "EntityExtractor",
    "get_entity_extractor",
]
