# 代碼功能說明: Qdrant 存儲適配器 - AAM 長期記憶向量存儲
# 創建日期: 2026-02-02
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-02

"""
Qdrant 存儲適配器 - 提供 AAM 長期記憶的向量存儲和檢索功能

功能特點:
- User Isolation: 按 user_id 隔離記憶，防止跨用戶污染
- 向量相似度搜索: 使用 all-mpnet-base-v2 embedding
- 去重檢測: 防止重複記憶
- 衝突檢測: 檢測並處理衝突記憶
- 熱度追蹤: 記錄訪問次數，支持熱度排序
- 時效性管理: 支持記憶歸檔和清理
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
    DatetimeRange,
)

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

from .models import Memory

logger = logging.getLogger(__name__)


class MemoryConflict:
    """記憶衝突報告"""

    def __init__(
        self,
        existing_memory: Memory,
        new_confidence: float,
        similarity: float,
        suggested_action: str = "overwrite",
    ):
        self.existing_memory = existing_memory
        self.new_confidence = new_confidence
        self.similarity = similarity
        self.suggested_action = suggested_action


class QdrantAdapter:
    """Qdrant 存儲 AAM 長期適配器 -記憶"""

    COLLECTION_NAME = "aam_entities"
    VECTOR_SIZE = 768

    ENTITY_TYPE_PART_NUMBER = "part_number"
    ENTITY_TYPE_TLF19 = "tlf19"
    ENTITY_TYPE_INTENT = "intent"
    ENTITY_TYPE_PREFERENCE = "preference"
    ENTITY_TYPE_CONTEXT = "context"

    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_REVIEW = "review"

    def __init__(
        self,
        qdrant_client: Optional["QdrantClient"] = None,
        collection_name: str = "aam_entities",
    ):
        self._client: Optional["QdrantClient"] = qdrant_client
        self.collection_name = collection_name
        self._embedding_model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(host="localhost", port=6333)
            logger.info("Created local Qdrant client")

        self._init_embedding_model()
        self._ensure_collection()
        self._initialized = True

    def _init_embedding_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer("all-mpnet-base-v2")
            logger.info("Initialized embedding model: all-mpnet-base-v2")
        except ImportError as e:
            logger.error(f"Failed to import sentence-transformers: {e}")
            raise RuntimeError(
                "sentence-transformers is required for QdrantAdapter. "
                "Install it with: pip install sentence-transformers"
            )

    def _ensure_collection(self) -> None:
        self._ensure_initialized()
        assert self._client is not None, "Qdrant client is not initialized"

        try:
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                from qdrant_client.models import VectorParams, Distance

                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def _encode_text(self, text: str) -> List[float]:
        self._ensure_initialized()
        assert self._embedding_model is not None, "Embedding model is not initialized"
        return self._embedding_model.encode(text).tolist()

    def _memory_to_payload(self, memory: Memory) -> Dict[str, Any]:
        payload = memory.to_dict()
        payload["_key"] = memory.memory_id
        return payload

    def _payload_to_memory(self, payload: Dict[str, Any]) -> Memory:
        payload.pop("_key", None)
        return Memory.from_dict(payload)

    def store(self, memory: Memory) -> bool:
        try:
            self._ensure_initialized()
            assert self._client is not None

            existing = self.retrieve(memory.memory_id)
            if existing is not None:
                return self.update(memory)

            vector = self._encode_text(memory.content)
            payload = self._memory_to_payload(memory)

            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=memory.memory_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            logger.debug(f"Stored memory: {memory.memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store memory: {e}", exc_info=True)
            return False

    def retrieve(self, memory_id: str) -> Optional[Memory]:
        try:
            self._ensure_initialized()
            assert self._client is not None

            points = self._client.retrieve(
                collection_name=self.collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                return None

            return self._payload_to_memory(points[0].payload)

        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}", exc_info=True)
            return None

    def update(self, memory: Memory) -> bool:
        try:
            self._ensure_initialized()
            assert self._client is not None

            existing = self.retrieve(memory.memory_id)
            if existing is None:
                logger.warning(f"Memory not found for update: {memory.memory_id}")
                return False

            from datetime import datetime
            memory.updated_at = datetime.now()

            vector = self._encode_text(memory.content)
            payload = self._memory_to_payload(memory)

            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=memory.memory_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            logger.debug(f"Updated memory: {memory.memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update memory: {e}", exc_info=True)
            return False

    def delete(self, memory_id: str) -> bool:
        try:
            self._ensure_initialized()
            assert self._client is not None

            self._client.delete(
                collection_name=self.collection_name,
                points=[memory_id],
            )

            logger.debug(f"Deleted memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str,
        user_id: str,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> List[Memory]:
        try:
            self._ensure_initialized()
            assert self._client is not None

            query_vector = self._encode_text(query)

            must_conditions: List[FieldCondition] = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ]

            if entity_type:
                must_conditions.append(
                    FieldCondition(key="entity_type", match=MatchValue(value=entity_type))
                )

            if status:
                must_conditions.append(
                    FieldCondition(key="status", match=MatchValue(value=status))
                )

            if min_confidence > 0:
                must_conditions.append(
                    FieldCondition(key="confidence", range=Range(gte=min_confidence))
                )

            search_filter = Filter(must=must_conditions)

            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            memories = []
            for hit in results:
                payload = hit.payload
                payload["relevance_score"] = hit.score
                memories.append(self._payload_to_memory(payload))

            return memories

        except Exception as e:
            logger.error(f"Failed to search memories: {e}", exc_info=True)
            return []

    def find_by_exact_match(
        self,
        user_id: str,
        entity_type: str,
        entity_value: str,
    ) -> Optional[Memory]:
        try:
            self._ensure_initialized()
            assert self._client is not None

            results = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="entity_type", match=MatchValue(value=entity_type)),
                        FieldCondition(key="entity_value", match=MatchValue(value=entity_value)),
                        FieldCondition(key="status", match=MatchValue(value=self.STATUS_ACTIVE)),
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            if results[0]:
                return self._payload_to_memory(results[0][0].payload)

            return None

        except Exception as e:
            logger.error(f"Failed to find by exact match: {e}", exc_info=True)
            return None

    def get_user_entities(
        self,
        user_id: str,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        try:
            self._ensure_initialized()
            assert self._client is not None

            must_conditions: List[FieldCondition] = [
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            ]

            if entity_type:
                must_conditions.append(
                    FieldCondition(key="entity_type", match=MatchValue(value=entity_type))
                )

            if status:
                must_conditions.append(
                    FieldCondition(key="status", match=MatchValue(value=status))
                )

            results = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(must=must_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            memories = []
            for point in results[0]:
                memories.append(self._payload_to_memory(point.payload))

            return memories

        except Exception as e:
            logger.error(f"Failed to get user entities: {e}", exc_info=True)
            return []

    def detect_conflicts(
        self,
        user_id: str,
        entity_type: str,
        new_value: str,
        new_confidence: float,
    ) -> List[MemoryConflict]:
        try:
            self._ensure_initialized()

            existing_entities = self.get_user_entities(
                user_id=user_id,
                entity_type=entity_type,
                status=self.STATUS_ACTIVE,
                limit=50,
            )

            if not existing_entities:
                return []

            new_vector = self._encode_text(new_value)
            conflicts = []

            for existing in existing_entities:
                existing_vector = self._encode_text(existing.content)
                similarity = self._cosine_similarity(new_vector, existing_vector)

                if 0.85 < similarity < 1.0:
                    suggested_action = (
                        "overwrite" if new_confidence > existing.confidence else "ignore"
                    )

                    conflicts.append(
                        MemoryConflict(
                            existing_memory=existing,
                            new_confidence=new_confidence,
                            similarity=similarity,
                            suggested_action=suggested_action,
                        )
                    )

            return conflicts

        except Exception as e:
            logger.error(f"Failed to detect conflicts: {e}", exc_info=True)
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """計算餘弦相似度"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(float(a) * float(a) for a in vec1))
        norm2 = math.sqrt(sum(float(b) * float(b) for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def update_access(self, memory_id: str) -> bool:
        try:
            self._ensure_initialized()

            memory = self.retrieve(memory_id)
            if memory is None:
                return False

            from datetime import datetime
            memory.access_count += 1
            memory.accessed_at = datetime.now()

            return self.update(memory)

        except Exception as e:
            logger.error(f"Failed to update access: {e}", exc_info=True)
            return False

    def find_low_hotness(
        self,
        user_id: str,
        max_access: int = 3,
        older_than_days: int = 90,
    ) -> List[Memory]:
        try:
            self._ensure_initialized()
            assert self._client is not None

            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=older_than_days)

            results = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="status", match=MatchValue(value=self.STATUS_ACTIVE)),
                        FieldCondition(
                            key="created_at",
                            range=DatetimeRange(lt=cutoff_date.isoformat()),
                        ),
                    ]
                ),
                limit=100,
                with_payload=True,
                with_vectors=False,
            )

            low_hotness = []
            for point in results[0]:
                memory = self._payload_to_memory(point.payload)
                if memory.access_count <= max_access:
                    low_hotness.append(memory)

            return low_hotness

        except Exception as e:
            logger.error(f"Failed to find low hotness: {e}", exc_info=True)
            return []

    def archive_memory(self, memory_id: str) -> bool:
        try:
            self._ensure_initialized()

            memory = self.retrieve(memory_id)
            if memory is None:
                return False

            memory.status = self.STATUS_ARCHIVED

            from datetime import datetime
            memory.updated_at = datetime.now()

            return self.update(memory)

        except Exception as e:
            logger.error(f"Failed to archive memory: {e}", exc_info=True)
            return False

    def mark_for_review(self, memory_id: str, reason: str) -> bool:
        try:
            self._ensure_initialized()

            memory = self.retrieve(memory_id)
            if memory is None:
                return False

            memory.status = self.STATUS_REVIEW
            memory.metadata["review_reason"] = reason

            from datetime import datetime
            memory.updated_at = datetime.now()

            return self.update(memory)

        except Exception as e:
            logger.error(f"Failed to mark for review: {e}", exc_info=True)
            return False

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        try:
            self._ensure_initialized()

            entities = self.get_user_entities(user_id=user_id, limit=1000)

            stats = {
                "total_count": len(entities),
                "by_entity_type": {},
                "by_status": {},
                "avg_confidence": 0.0,
                "total_access_count": 0,
            }

            confidence_sum = 0.0
            access_sum = 0

            for entity in entities:
                et = entity.entity_type
                stats["by_entity_type"][et] = stats["by_entity_type"].get(et, 0) + 1

                st = entity.status
                stats["by_status"][st] = stats["by_status"].get(st, 0) + 1

                confidence_sum += entity.confidence
                access_sum += entity.access_count

            if entities:
                stats["avg_confidence"] = confidence_sum / len(entities)
                stats["total_access_count"] = access_sum

            return stats

        except Exception as e:
            logger.error(f"Failed to get user stats: {e}", exc_info=True)
            return {}


def create_qdrant_adapter() -> QdrantAdapter:
    """創建 QdrantAdapter 實例"""
    return QdrantAdapter()
