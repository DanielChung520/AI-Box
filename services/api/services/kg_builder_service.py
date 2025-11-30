# 代碼功能說明: 知識圖譜構建服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""知識圖譜構建服務 - 實現三元組到圖譜的轉換、實體和關係的創建/更新"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog
import hashlib

from database.arangodb import ArangoDBClient
from services.api.models.triple_models import Triple

logger = structlog.get_logger(__name__)

# 實體和關係集合名稱
ENTITIES_COLLECTION = "entities"
RELATIONS_COLLECTION = "relations"


class KGBuilderService:
    """知識圖譜構建服務主類"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        self.client = client or ArangoDBClient()
        self._ensure_collections()

    def _ensure_collections(self):
        """確保集合存在"""
        if self.client is None:
            raise RuntimeError("ArangoDB client is not initialized")
        if self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")

        if not self.client.db.has_collection(ENTITIES_COLLECTION):
            self.client.db.create_collection(ENTITIES_COLLECTION)
            # 創建索引
            collection = self.client.db.collection(ENTITIES_COLLECTION)
            collection.add_index({"type": "persistent", "fields": ["type"]})
            collection.add_index({"type": "persistent", "fields": ["name"]})
            collection.add_index({"type": "persistent", "fields": ["tags[*]"]})

        if not self.client.db.has_collection(RELATIONS_COLLECTION):
            self.client.db.create_collection(RELATIONS_COLLECTION, edge=True)
            # 創建索引
            collection = self.client.db.collection(RELATIONS_COLLECTION)
            collection.add_index({"type": "persistent", "fields": ["type"]})
            collection.add_index({"type": "persistent", "fields": ["weight"]})

    def _generate_entity_key(self, text: str, entity_type: str) -> str:
        """生成實體鍵（用於去重）"""
        # 使用文本和類型的哈希作為鍵
        key_str = f"{entity_type}:{text}"
        key_hash = hashlib.md5(key_str.encode("utf-8")).hexdigest()[:16]
        return f"{entity_type.lower()}_{key_hash}"

    def _find_or_create_entity(
        self, text: str, entity_type: str, start: int, end: int
    ) -> str:
        """查找或創建實體（實體去重）"""
        if self.client is None or self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")
        entity_key = self._generate_entity_key(text, entity_type)
        collection = self.client.db.collection(ENTITIES_COLLECTION)

        # 嘗試查找現有實體
        try:
            existing = collection.get(entity_key)
            if existing:
                # 更新實體（合併信息）
                update_data = {
                    "_key": entity_key,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                collection.update(update_data)
                return f"{ENTITIES_COLLECTION}/{entity_key}"
        except Exception:
            pass

        # 創建新實體
        entity_doc = {
            "_key": entity_key,
            "type": entity_type,
            "name": text,
            "text": text,
            "start": start,
            "end": end,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection.insert(entity_doc)
        return f"{ENTITIES_COLLECTION}/{entity_key}"

    def _find_or_create_relation(
        self,
        from_vertex: str,
        to_vertex: str,
        relation_type: str,
        confidence: float,
        context: str,
    ) -> Optional[str]:
        """查找或創建關係（關係去重）"""
        if self.client is None or self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")
        # 生成關係鍵
        key_str = f"{from_vertex}:{relation_type}:{to_vertex}"
        relation_key = hashlib.md5(key_str.encode("utf-8")).hexdigest()[:16]

        collection = self.client.db.collection(RELATIONS_COLLECTION)

        # 嘗試查找現有關係
        try:
            existing_result = collection.get(relation_key)
            # 處理可能的異步結果
            if isinstance(existing_result, dict):
                existing = existing_result
            else:
                existing = None
            if existing:
                # 更新關係（合併信息，取較高置信度）
                update_data = {
                    "_key": relation_key,
                    "confidence": max(existing.get("confidence", 0), confidence),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                collection.update(update_data)
                return f"{RELATIONS_COLLECTION}/{relation_key}"
        except Exception:
            pass

        # 創建新關係
        relation_doc = {
            "_key": relation_key,
            "_from": from_vertex,
            "_to": to_vertex,
            "type": relation_type,
            "confidence": confidence,
            "context": context,
            "weight": confidence,  # 使用置信度作為權重
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection.insert(relation_doc)
        return f"{RELATIONS_COLLECTION}/{relation_key}"

    async def build_from_triples(self, triples: List[Triple]) -> Dict:
        """從三元組構建知識圖譜"""
        entities_created = 0
        entities_updated = 0
        relations_created = 0
        relations_updated = 0

        for triple in triples:
            try:
                # 創建或更新主體實體
                subject_id = self._find_or_create_entity(
                    triple.subject.text,
                    triple.subject.type,
                    triple.subject.start,
                    triple.subject.end,
                )
                entities_created += 1

                # 創建或更新客體實體
                object_id = self._find_or_create_entity(
                    triple.object.text,
                    triple.object.type,
                    triple.object.start,
                    triple.object.end,
                )
                entities_created += 1

                # 創建或更新關係
                relation_id = self._find_or_create_relation(
                    subject_id,
                    object_id,
                    triple.relation.type,
                    triple.confidence,
                    triple.context,
                )
                if relation_id:
                    relations_created += 1

            except Exception as e:
                logger.error("kg_build_triple_failed", error=str(e), triple=triple)

        return {
            "entities_created": entities_created,
            "entities_updated": entities_updated,
            "relations_created": relations_created,
            "relations_updated": relations_updated,
            "total_triples": len(triples),
        }

    async def build_from_triples_batch(self, triples_list: List[List[Triple]]) -> Dict:
        """批量從三元組構建知識圖譜"""
        total_entities_created = 0
        total_relations_created = 0
        total_triples = 0

        for triples in triples_list:
            result = await self.build_from_triples(triples)
            total_entities_created += result["entities_created"]
            total_relations_created += result["relations_created"]
            total_triples += result["total_triples"]

        return {
            "entities_created": total_entities_created,
            "relations_created": total_relations_created,
            "total_triples": total_triples,
            "batches_processed": len(triples_list),
        }

    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """查詢實體"""
        if self.client.db is None:
            return None
        try:
            collection = self.client.db.collection(ENTITIES_COLLECTION)
            result = collection.get(entity_id.split("/")[-1])
            # 處理可能的異步結果
            if isinstance(result, dict):
                return result
            return None
        except Exception:
            return None

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        """查詢實體列表"""
        if self.client is None or self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")

        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")
        aql = f"FOR doc IN {ENTITIES_COLLECTION}"
        bind_vars: Dict[str, Any] = {}

        if entity_type:
            aql += " FILTER doc.type == @entity_type"
            bind_vars["entity_type"] = entity_type

        aql += " LIMIT @offset, @limit"
        bind_vars["offset"] = offset
        bind_vars["limit"] = limit

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        return list(cursor) if cursor else []  # type: ignore[arg-type]

    def get_entity_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """獲取實體的鄰居節點"""
        from database.arangodb import queries as kg_queries

        return kg_queries.fetch_neighbors(
            self.client, entity_id, relation_types=relation_types, limit=limit
        )

    def get_entity_subgraph(
        self, entity_id: str, max_depth: int = 2, limit: int = 50
    ) -> List[Dict]:
        """獲取實體的 N 度關係子圖"""
        from database.arangodb import queries as kg_queries

        return kg_queries.fetch_subgraph(
            self.client, entity_id, max_depth=max_depth, limit=limit
        )
