# 代碼功能說明: Entity Memory 存儲層
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""Entity Memory 存儲層 - Qdrant + ArangoDB + Redis"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
)

from database.qdrant.client import get_qdrant_client

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from database.arangodb.client import ArangoDBClient

    ARANGODB_AVAILABLE = True
except ImportError:
    ARANGODB_AVAILABLE = False
    ArangoDBClient = None

from .models import (
    EntityMemory,
    EntityRelation,
    SessionContext,
    EntityType,
    EntityStatus,
)

logger = logging.getLogger(__name__)

# 配置常數
QDRANT_COLLECTION_NAME = "ai_box_entity_memory"
QDRANT_VECTOR_SIZE = 384  # nomic-embed-text 維度

REDIS_SESSION_PREFIX = "entity_session:"
REDIS_SESSION_TTL = 24 * 60 * 60  # 24 小時

# ArangoDB 配置
ARANGODB_COLLECTION_RELATIONS = "entity_relations"


class EntityStorage:
    """實體存儲層"""

    def __init__(
        self,
        qdrant_client: Optional[QdrantClient] = None,
        redis_client: Optional["redis.Redis"] = None,
        arangodb_client: Optional[Any] = None,
    ):
        self._qdrant_client = qdrant_client
        self._redis_client = redis_client
        self._arangodb_client = arangodb_client
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """確保存儲層已初始化"""
        if self._initialized:
            return

        # 初始化 Qdrant
        if self._qdrant_client is None:
            try:
                self._qdrant_client = get_qdrant_client()
                self._ensure_qdrant_collection()
            except Exception as e:
                logger.warning(f"Qdrant not available, using fallback: {e}")

        # 初始化 Redis
        if self._redis_client is None and REDIS_AVAILABLE:
            try:
                from database.redis.client import get_redis_client

                self._redis_client = get_redis_client()
            except Exception as e:
                logger.warning(f"Redis not available, session cache disabled: {e}")

        # 初始化 ArangoDB
        if self._arangodb_client is None:
            if ARANGODB_AVAILABLE and ArangoDBClient:
                try:
                    self._arangodb_client = ArangoDBClient()
                    self._ensure_arangodb_collection()
                except Exception as e:
                    logger.warning(f"ArangoDB not available, entity relations disabled: {e}")
            else:
                logger.warning("ArangoDB client not available, entity relations disabled")

        self._initialized = True

    def _ensure_qdrant_collection(self) -> None:
        """確保 Qdrant Collection 存在"""
        if self._qdrant_client is None:
            return

        try:
            collections = self._qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if QDRANT_COLLECTION_NAME not in collection_names:
                logger.info(f"Creating Qdrant collection: {QDRANT_COLLECTION_NAME}")
                self._qdrant_client.create_collection(
                    collection_name=QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=QDRANT_VECTOR_SIZE,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Qdrant collection created: {QDRANT_COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

    def _ensure_arangodb_collection(self) -> None:
        """確保 ArangoDB Collection 存在"""
        if self._arangodb_client is None:
            return

        try:
            db = self._arangodb_client.db
            if not db.has_collection(ARANGODB_COLLECTION_RELATIONS):
                db.create_collection(ARANGODB_COLLECTION_RELATIONS)
                logger.info(f"ArangoDB collection created: {ARANGODB_COLLECTION_RELATIONS}")
        except Exception as e:
            logger.error(f"Failed to ensure ArangoDB collection: {e}")

    # ==================== 實體操作 ====================

    async def store_entity(self, entity: EntityMemory) -> bool:
        """
        存儲實體到長期記憶

        Args:
            entity: 實體數據對象

        Returns:
            是否存儲成功
        """
        self._ensure_initialized()

        try:
            # 準備 payload
            payload = {
                "entity_value": entity.entity_value,
                "entity_type": entity.entity_type.value,
                "user_id": entity.user_id,
                "confidence": entity.confidence,
                "status": entity.status.value,
                "first_mentioned": entity.first_mentioned.isoformat(),
                "last_mentioned": entity.last_mentioned.isoformat(),
                "mention_count": entity.mention_count,
                "attributes": json.dumps(entity.attributes),
                "related_entities": json.dumps(entity.related_entities),
            }

            if self._qdrant_client is not None:
                point = PointStruct(
                    id=entity.entity_id,
                    vector=entity.vector or [0.0] * QDRANT_VECTOR_SIZE,
                    payload=payload,
                )
                self._qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=[point],
                )
                logger.info(f"Entity stored: {entity.entity_id} - {entity.entity_value}")
                return True
            else:
                logger.warning("Qdrant not available, cannot store entity")
                return False

        except Exception as e:
            logger.error(f"Failed to store entity: {e}", exc_info=True)
            return False

    async def get_entity(
        self,
        entity_id: str,
        user_id: str,
    ) -> Optional[EntityMemory]:
        """
        根據 ID 獲取實體

        Args:
            entity_id: 實體 ID
            user_id: 用戶 ID

        Returns:
            實體對象或 None
        """
        self._ensure_initialized()

        try:
            if self._qdrant_client is None:
                return None

            points = self._qdrant_client.retrieve(
                collection_name=QDRANT_COLLECTION_NAME,
                ids=[entity_id],
                with_payload=True,
            )

            if not points:
                return None

            point = points[0]
            payload = point.payload
            point_id = str(point.id)  # 轉換為字串

            # 驗證 user_id
            if payload.get("user_id") != user_id:
                return None

            # 處理 vector
            point_vector = point.vector
            if point_vector is not None and isinstance(point_vector, dict):
                # 如果 vector 是 dict，取第一個值（或其他處理方式）
                vector_values = list(point_vector.values())
                vector = vector_values[0] if vector_values else None
            else:
                vector = point_vector

            return EntityMemory(
                entity_id=point_id,
                entity_value=payload.get("entity_value", ""),
                entity_type=EntityType(payload.get("entity_type", "entity_noun")),
                user_id=payload.get("user_id", ""),
                confidence=payload.get("confidence", 1.0),
                status=EntityStatus(payload.get("status", "active")),
                first_mentioned=datetime.fromisoformat(
                    payload.get("first_mentioned", datetime.utcnow().isoformat())
                ),
                last_mentioned=datetime.fromisoformat(
                    payload.get("last_mentioned", datetime.utcnow().isoformat())
                ),
                mention_count=payload.get("mention_count", 0),
                vector=vector,
                attributes=json.loads(payload.get("attributes", "{}")),
                related_entities=json.loads(payload.get("related_entities", "[]")),
            )

        except Exception as e:
            logger.error(f"Failed to get entity: {e}", exc_info=True)
            return None

    async def get_entity_by_value(
        self,
        entity_value: str,
        user_id: str,
    ) -> Optional[EntityMemory]:
        """
        根據實體名稱精確查找

        Args:
            entity_value: 實體名稱
            user_id: 用戶 ID

        Returns:
            實體對象或 None
        """
        self._ensure_initialized()

        try:
            if self._qdrant_client is None:
                return None

            points = self._qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="entity_value", match=MatchValue(value=entity_value)),
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
                limit=1,
                with_payload=True,
            )[0]

            if not points:
                return None

            point = points[0]
            payload = point.payload

            return EntityMemory(
                entity_id=point.id,
                entity_value=payload.get("entity_value", ""),
                entity_type=EntityType(payload.get("entity_type", "entity_noun")),
                user_id=payload.get("user_id", ""),
                confidence=payload.get("confidence", 1.0),
                status=EntityStatus(payload.get("status", "active")),
                first_mentioned=datetime.fromisoformat(
                    payload.get("first_mentioned", datetime.utcnow().isoformat())
                ),
                last_mentioned=datetime.fromisoformat(
                    payload.get("last_mentioned", datetime.utcnow().isoformat())
                ),
                mention_count=payload.get("mention_count", 0),
                vector=point.vector,
                attributes=json.loads(payload.get("attributes", "{}")),
                related_entities=json.loads(payload.get("related_entities", "[]")),
            )

        except Exception as e:
            logger.error(f"Failed to get entity by value: {e}", exc_info=True)
            return None

    async def search_entities(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> List[EntityMemory]:
        """
        搜索實體（精確匹配）

        Args:
            query: 搜索查詢（實體名稱）
            user_id: 用戶 ID
            limit: 返回數量限制

        Returns:
            匹配的實體列表
        """
        self._ensure_initialized()

        results = []

        try:
            if self._qdrant_client is None:
                return results

            # 使用 scroll 進行過濾查詢
            points, _ = self._qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
                limit=limit * 2,  # 獲取更多結果以便過濾
                with_payload=True,
            )

            query_lower = query.lower()
            for point in points:
                payload = point.payload
                entity_value = payload.get("entity_value", "")

                # 精確匹配或包含匹配
                if (
                    entity_value.lower() == query_lower
                    or query_lower in entity_value.lower()
                    or entity_value.lower() in query_lower
                ):
                    results.append(
                        EntityMemory(
                            entity_id=point.id,
                            entity_value=entity_value,
                            entity_type=EntityType(payload.get("entity_type", "entity_noun")),
                            user_id=payload.get("user_id", ""),
                            confidence=payload.get("confidence", 1.0),
                            status=EntityStatus(payload.get("status", "active")),
                            first_mentioned=datetime.fromisoformat(
                                payload.get("first_mentioned", datetime.utcnow().isoformat())
                            ),
                            last_mentioned=datetime.fromisoformat(
                                payload.get("last_mentioned", datetime.utcnow().isoformat())
                            ),
                            mention_count=payload.get("mention_count", 0),
                            vector=point.vector,
                            attributes=json.loads(payload.get("attributes", "{}")),
                            related_entities=json.loads(payload.get("related_entities", "[]")),
                        )
                    )

                if len(results) >= limit:
                    break

        except Exception as e:
            logger.error(f"Failed to search entities: {e}", exc_info=True)

        return results

    async def update_entity_mention(
        self,
        entity_id: str,
        user_id: str,
    ) -> bool:
        """
        更新實體提及時間和次數

        Args:
            entity_id: 實體 ID
            user_id: 用戶 ID

        Returns:
            是否更新成功
        """
        self._ensure_initialized()

        try:
            entity = await self.get_entity(entity_id, user_id)
            if entity is None:
                return False

            # 更新字段
            entity.last_mentioned = datetime.utcnow()
            entity.mention_count += 1

            # 存儲更新後的實體
            return await self.store_entity(entity)

        except Exception as e:
            logger.error(f"Failed to update entity mention: {e}", exc_info=True)
            return False

    async def list_user_entities(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[EntityMemory]:
        """
        列出用戶的所有實體

        Args:
            user_id: 用戶 ID
            limit: 返回數量限制

        Returns:
            實體列表
        """
        self._ensure_initialized()

        results = []

        try:
            if self._qdrant_client is None:
                return results

            points, _ = self._qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
                limit=limit,
                with_payload=True,
            )

            for point in points:
                payload = point.payload
                results.append(
                    EntityMemory(
                        entity_id=point.id,
                        entity_value=payload.get("entity_value", ""),
                        entity_type=EntityType(payload.get("entity_type", "entity_noun")),
                        user_id=payload.get("user_id", ""),
                        confidence=payload.get("confidence", 1.0),
                        status=EntityStatus(payload.get("status", "active")),
                        first_mentioned=datetime.fromisoformat(
                            payload.get("first_mentioned", datetime.utcnow().isoformat())
                        ),
                        last_mentioned=datetime.fromisoformat(
                            payload.get("last_mentioned", datetime.utcnow().isoformat())
                        ),
                        mention_count=payload.get("mention_count", 0),
                        vector=point.vector,
                        attributes=json.loads(payload.get("attributes", "{}")),
                        related_entities=json.loads(payload.get("related_entities", "[]")),
                    )
                )

        except Exception as e:
            logger.error(f"Failed to list user entities: {e}", exc_info=True)

        return results

    # ==================== 向量搜尋 ====================

    async def search_entities_by_vector(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[EntityMemory]:
        """
        向量搜尋實體

        Args:
            query_vector: 查詢向量
            user_id: 用戶 ID
            limit: 返回數量限制
            score_threshold: 相似度閾值

        Returns:
            匹配的實體列表（按相似度排序）
        """
        self._ensure_initialized()

        results = []

        try:
            if self._qdrant_client is None:
                return results

            search_result = self._qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                    ]
                ),
                limit=limit,
                score_threshold=score_threshold,
            )

            for point in search_result:
                payload = point.payload
                results.append(
                    EntityMemory(
                        entity_id=point.id,
                        entity_value=payload.get("entity_value", ""),
                        entity_type=EntityType(payload.get("entity_type", "entity_noun")),
                        user_id=payload.get("user_id", ""),
                        confidence=payload.get("confidence", 1.0),
                        status=EntityStatus(payload.get("status", "active")),
                        first_mentioned=datetime.fromisoformat(
                            payload.get("first_mentioned", datetime.utcnow().isoformat())
                        ),
                        last_mentioned=datetime.fromisoformat(
                            payload.get("last_mentioned", datetime.utcnow().isoformat())
                        ),
                        mention_count=payload.get("mention_count", 0),
                        vector=point.vector,
                        attributes=json.loads(payload.get("attributes", "{}")),
                        related_entities=json.loads(payload.get("related_entities", "[]")),
                    )
                )

            logger.info(f"Vector search found {len(results)} entities")

        except Exception as e:
            logger.error(f"Failed to search entities by vector: {e}", exc_info=True)

        return results

    async def hybrid_search_entities(
        self,
        query: str,
        query_vector: Optional[List[float]],
        user_id: str,
        limit: int = 10,
        exact_match_weight: float = 1.0,
        vector_match_weight: float = 0.8,
    ) -> List[EntityMemory]:
        """
        混合搜尋：結合精確匹配和向量搜尋

        策略：
        1. 獲取精確匹配結果
        2. 獲取向量化搜尋結果（如果提供向量）
        3. 使用 RRF（Ranked Retrieval Fusion）合併排名

        Args:
            query: 查詢文本
            query_vector: 查詢向量（可選）
            user_id: 用戶 ID
            limit: 返回數量限制
            exact_match_weight: 精確匹配權重
            vector_match_weight: 向量匹配權重

        Returns:
            合併後的實體列表
        """
        self._ensure_initialized()

        # Step 1: 精確匹配
        exact_results = await self.search_entities(query, user_id, limit=limit)

        # Step 2: 向量搜尋（如果提供向量）
        vector_results = []
        if query_vector is not None:
            vector_results = await self.search_entities_by_vector(
                query_vector, user_id, limit=limit
            )

        # Step 3: 合併結果（RRF 融合）
        entity_map: Dict[str, EntityMemory] = {}
        rrf_scores: Dict[str, float] = {}

        for rank, entity in enumerate(exact_results):
            entity_id = entity.entity_id
            if entity_id not in entity_map:
                entity_map[entity_id] = entity
            rrf_scores[entity_id] = rrf_scores.get(entity_id, 0) + (exact_match_weight / (rank + 1))

        for rank, entity in enumerate(vector_results):
            entity_id = entity.entity_id
            if entity_id not in entity_map:
                entity_map[entity_id] = entity
            rrf_scores[entity_id] = rrf_scores.get(entity_id, 0) + (
                vector_match_weight / (rank + 1)
            )

        # Step 4: 按 RRF 分數排序
        sorted_entity_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Step 5: 返回 top N
        final_results = []
        for entity_id in sorted_entity_ids[:limit]:
            final_results.append(entity_map[entity_id])

        logger.info(f"Hybrid search found {len(final_results)} entities")
        return final_results

    # ==================== 關係操作 ====================

    async def store_relation(self, relation: EntityRelation) -> bool:
        """存儲實體關係"""
        self._ensure_initialized()

        try:
            if self._arangodb_client is None:
                logger.warning("ArangoDB not available, cannot store relation")
                return False

            db = self._arangodb_client.db
            collection = db.collection(ARANGODB_COLLECTION_RELATIONS)

            document = {
                "_key": relation.relation_id,
                "source_entity_id": relation.source_entity_id,
                "target_entity_id": relation.target_entity_id,
                "relation_type": relation.relation_type,
                "description": relation.description,
                "user_id": relation.user_id,
                "created_at": relation.created_at.isoformat(),
                "updated_at": relation.updated_at.isoformat(),
                "confidence": relation.confidence,
            }

            collection.insert(document)
            logger.info(f"Relation stored: {relation.relation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store relation: {e}", exc_info=True)
            return False

    async def get_related_entities(
        self,
        entity_id: str,
        user_id: str,
    ) -> List[str]:
        """
        獲取關聯的實體 ID 列表

        Args:
            entity_id: 源實體 ID
            user_id: 用戶 ID

        Returns:
            關聯的實體 ID 列表
        """
        self._ensure_initialized()

        try:
            if self._arangodb_client is None:
                return []

            db = self._arangodb_client.db
            collection = db.collection(ARANGODB_COLLECTION_RELATIONS)

            # 查詢源實體的所有關係
            results = collection.find(
                {
                    "_key": entity_id,
                    "user_id": user_id,
                }
            )

            related_ids = []
            for doc in results:
                related_ids.append(doc.get("target_entity_id", ""))

            return related_ids

        except Exception as e:
            logger.error(f"Failed to get related entities: {e}", exc_info=True)
            return []

    # ==================== 會話上下文操作 ====================

    def _get_session_key(self, session_id: str) -> str:
        """生成會話上下文 Redis Key"""
        return f"{REDIS_SESSION_PREFIX}{session_id}"

    async def store_session_context(
        self,
        session_id: str,
        context: SessionContext,
    ) -> bool:
        """存儲會話上下文"""
        self._ensure_initialized()

        try:
            if self._redis_client is None:
                logger.warning("Redis not available, cannot store session context")
                return False

            key = self._get_session_key(session_id)
            data = context.model_dump()

            # 轉換 datetime 為 ISO 格式
            for field in ["started_at", "last_activity"]:
                if field in data and isinstance(data[field], datetime):
                    data[field] = data[field].isoformat()

            # 存儲到 Redis
            self._redis_client.setex(
                key,
                REDIS_SESSION_TTL,
                json.dumps(data),
            )
            logger.info(f"Session context stored: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store session context: {e}", exc_info=True)
            return False

    async def get_session_context(
        self,
        session_id: str,
    ) -> Optional[SessionContext]:
        """獲取會話上下文"""
        self._ensure_initialized()

        try:
            if self._redis_client is None:
                return None

            key = self._get_session_key(session_id)
            data = self._redis_client.get(key)

            if not data:
                return None

            context_dict = json.loads(data)
            context = SessionContext(**context_dict)

            # 更新最後活動時間
            context.last_activity = datetime.utcnow()
            await self.store_session_context(session_id, context)

            return context

        except Exception as e:
            logger.error(f"Failed to get session context: {e}", exc_info=True)
            return None

    async def add_entity_to_session(
        self,
        session_id: str,
        entity_id: str,
    ) -> bool:
        """
        將實體添加到會話

        Args:
            session_id: 會話 ID
            entity_id: 實體 ID

        Returns:
            是否添加成功
        """
        try:
            context = await self.get_session_context(session_id)
            if context is None:
                context = SessionContext(
                    session_id=session_id,
                    user_id="",  # 會在後續存儲時設置
                )

            if entity_id not in context.mentioned_entities:
                context.mentioned_entities.append(entity_id)
                context.last_referred_entity = entity_id

            return await self.store_session_context(session_id, context)

        except Exception as e:
            logger.error(f"Failed to add entity to session: {e}", exc_info=True)
            return False

    async def set_last_referred_entity(
        self,
        session_id: str,
        entity_id: str,
    ) -> bool:
        """
        設置最後被引用的實體

        Args:
            session_id: 會話 ID
            entity_id: 實體 ID

        Returns:
            是否設置成功
        """
        try:
            context = await self.get_session_context(session_id)
            if context is None:
                context = SessionContext(
                    session_id=session_id,
                    user_id="",
                )

            context.last_referred_entity = entity_id
            return await self.store_session_context(session_id, context)

        except Exception as e:
            logger.error(f"Failed to set last referred entity: {e}", exc_info=True)
            return False

    async def get_session_entities(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[str]:
        """
        獲取會話中提到的實體 ID 列表（按順序）

        Args:
            session_id: 會話 ID
            limit: 返回數量限制

        Returns:
            實體 ID 列表（最近提到的在前）
        """
        context = await self.get_session_context(session_id)
        if context is None:
            return []

        # 返回最近提到的實體
        return context.mentioned_entities[-limit:][::-1]


# 全局存儲實例
_entity_storage: Optional[EntityStorage] = None


def get_entity_storage() -> EntityStorage:
    """獲取 Entity Storage 實例（單例模式）"""
    global _entity_storage
    if _entity_storage is None:
        _entity_storage = EntityStorage()
    return _entity_storage


def reset_entity_storage() -> None:
    """重置 Entity Storage 實例（主要用於測試）"""
    global _entity_storage
    _entity_storage = None
