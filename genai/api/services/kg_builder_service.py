# 代碼功能說明: 知識圖譜構建服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 13:55 (UTC+8)

"""知識圖譜構建服務 - 實現三元組到圖譜的轉換、實體和關係的創建/更新/清理"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient
from genai.api.models.triple_models import Triple

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
        self,
        text: str,
        entity_type: str,
        start: int,
        end: int,
        file_id: Optional[str] = None,
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
                # 更新實體（合併信息，添加file_id到file_ids數組）
                update_data = {
                    "_key": entity_key,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # 如果提供了file_id，添加到file_ids數組
                if file_id:
                    file_ids = existing.get("file_ids", [])
                    if file_id not in file_ids:
                        file_ids.append(file_id)
                        update_data["file_ids"] = file_ids
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

        # 如果提供了file_id，添加到文檔
        if file_id:
            entity_doc["file_id"] = file_id
            entity_doc["file_ids"] = [file_id]

        collection.insert(entity_doc)
        return f"{ENTITIES_COLLECTION}/{entity_key}"

    def _find_or_create_relation(
        self,
        from_vertex: str,
        to_vertex: str,
        relation_type: str,
        confidence: float,
        context: str,
        file_id: Optional[str] = None,
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
                # 如果提供了file_id，添加到file_ids數組
                if file_id:
                    file_ids = existing.get("file_ids", [])
                    if file_id not in file_ids:
                        file_ids.append(file_id)
                        update_data["file_ids"] = file_ids
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

        # 如果提供了file_id，添加到文檔
        if file_id:
            relation_doc["file_id"] = file_id
            relation_doc["file_ids"] = [file_id]

        collection.insert(relation_doc)
        return f"{RELATIONS_COLLECTION}/{relation_key}"

    async def build_from_triples(
        self,
        triples: List[Triple],
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict:
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
                    file_id=file_id,
                )
                entities_created += 1

                # 創建或更新客體實體
                object_id = self._find_or_create_entity(
                    triple.object.text,
                    triple.object.type,
                    triple.object.start,
                    triple.object.end,
                    file_id=file_id,
                )
                entities_created += 1

                # 創建或更新關係
                relation_id = self._find_or_create_relation(
                    subject_id,
                    object_id,
                    triple.relation.type,
                    triple.confidence,
                    triple.context,
                    file_id=file_id,
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

    def list_triples_by_file_id(
        self,
        file_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """依 file_id 查詢三元組（以 relations edge 為準，並回填 subject/object）。

        Args:
            file_id: 文件 ID
            limit: 回傳上限
            offset: 偏移量

        Returns:
            dict: { total: int, triples: List[Dict[str, Any]] }
        """
        if self.client is None or self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        safe_limit = max(0, int(limit))
        safe_offset = max(0, int(offset))

        # 兼容舊資料：若沒有 file_ids，則回退到 file_id 欄位
        query = """
        LET total = LENGTH(
            FOR r IN @@relations
                LET ids = (
                    r.file_ids != null ? r.file_ids :
                    (r.file_id != null ? [r.file_id] : [])
                )
                FILTER @file_id IN ids
                RETURN 1
        )

        LET items = (
            FOR r IN @@relations
                LET ids = (
                    r.file_ids != null ? r.file_ids :
                    (r.file_id != null ? [r.file_id] : [])
                )
                FILTER @file_id IN ids
                SORT r.updated_at DESC
                LIMIT @offset, @limit
                LET s = DOCUMENT(r._from)
                LET o = DOCUMENT(r._to)
                RETURN {
                    edge: KEEP(
                        r,
                        "_id",
                        "_key",
                        "_from",
                        "_to",
                        "type",
                        "confidence",
                        "context",
                        "created_at",
                        "updated_at",
                        "file_id",
                        "file_ids"
                    ),
                    subject: s == null ? null : KEEP(s, "_id", "_key", "type", "name", "file_id", "file_ids"),
                    object: o == null ? null : KEEP(o, "_id", "_key", "type", "name", "file_id", "file_ids")
                }
        )

        RETURN {
            total: total,
            items: items
        }
        """

        bind_vars: Dict[str, Any] = {
            "@relations": RELATIONS_COLLECTION,
            "file_id": file_id,
            "limit": safe_limit,
            "offset": safe_offset,
        }
        result = self.client.execute_aql(query, bind_vars=bind_vars)
        payload = (result.get("results") or [{}])[0]
        return {
            "total": int(payload.get("total", 0) or 0),
            "triples": payload.get("items", []) or [],
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def remove_file_associations(self, file_id: str) -> Dict[str, int]:
        """移除指定 file_id 在 KG（entities/relations）的關聯。

        規則：
        - relations: 將 file_id 從 file_ids 移除；若移除後 file_ids 為空則刪除該 edge。
        - entities: 將 file_id 從 file_ids 移除；若移除後 file_ids 為空且不再有任何關聯 edge，則刪除該 vertex。

        Returns:
            dict: {relations_deleted, relations_updated, entities_deleted, entities_updated}
        """
        if self.client is None or self.client.db is None:
            raise RuntimeError("數據庫連接未初始化")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        now_expr = "DATE_ISO8601(DATE_NOW())"

        # 1) 清理 relations
        rel_query = f"""
        LET targets = (
            FOR r IN @@relations
                LET ids = (
                    r.file_ids != null ? r.file_ids :
                    (r.file_id != null ? [r.file_id] : [])
                )
                FILTER @file_id IN ids
                LET new_ids = REMOVE_VALUE(ids, @file_id)
                RETURN {{ key: r._key, new_ids: new_ids }}
        )

        LET deleted = (
            FOR t IN targets
                FILTER LENGTH(t.new_ids) == 0
                REMOVE t.key IN @@relations
                RETURN 1
        )

        LET updated = (
            FOR t IN targets
                FILTER LENGTH(t.new_ids) > 0
                UPDATE t.key WITH {{
                    file_ids: t.new_ids,
                    file_id: FIRST(t.new_ids),
                    updated_at: {now_expr}
                }} IN @@relations
                RETURN 1
        )

        RETURN {{
            relations_deleted: LENGTH(deleted),
            relations_updated: LENGTH(updated)
        }}
        """
        rel_bind: Dict[str, Any] = {
            "@relations": RELATIONS_COLLECTION,
            "file_id": file_id,
        }
        rel_result = self.client.execute_aql(rel_query, bind_vars=rel_bind)
        rel_payload = (rel_result.get("results") or [{}])[0]
        relations_deleted = int(rel_payload.get("relations_deleted", 0) or 0)
        relations_updated = int(rel_payload.get("relations_updated", 0) or 0)

        # 2) 清理 entities（刪除前確認沒有任何關聯 edge）
        ent_query = f"""
        LET targets = (
            FOR e IN @@entities
                LET ids = (
                    e.file_ids != null ? e.file_ids :
                    (e.file_id != null ? [e.file_id] : [])
                )
                FILTER @file_id IN ids
                LET new_ids = REMOVE_VALUE(ids, @file_id)
                RETURN {{ key: e._key, id: e._id, new_ids: new_ids }}
        )

        LET deleted = (
            FOR t IN targets
                FILTER LENGTH(t.new_ids) == 0
                LET has_edge = LENGTH(
                    FOR r IN @@relations
                        FILTER r._from == t.id OR r._to == t.id
                        LIMIT 1
                        RETURN 1
                ) > 0
                FILTER has_edge == false
                REMOVE t.key IN @@entities
                RETURN 1
        )

        LET updated = (
            FOR t IN targets
                FILTER LENGTH(t.new_ids) > 0
                UPDATE t.key WITH {{
                    file_ids: t.new_ids,
                    file_id: FIRST(t.new_ids),
                    updated_at: {now_expr}
                }} IN @@entities
                RETURN 1
        )

        RETURN {{
            entities_deleted: LENGTH(deleted),
            entities_updated: LENGTH(updated)
        }}
        """
        ent_bind: Dict[str, Any] = {
            "@entities": ENTITIES_COLLECTION,
            "@relations": RELATIONS_COLLECTION,
            "file_id": file_id,
        }
        ent_result = self.client.execute_aql(ent_query, bind_vars=ent_bind)
        ent_payload = (ent_result.get("results") or [{}])[0]

        entities_deleted = int(ent_payload.get("entities_deleted", 0) or 0)
        entities_updated = int(ent_payload.get("entities_updated", 0) or 0)

        return {
            "relations_deleted": relations_deleted,
            "relations_updated": relations_updated,
            "entities_deleted": entities_deleted,
            "entities_updated": entities_updated,
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

        return kg_queries.fetch_subgraph(self.client, entity_id, max_depth=max_depth, limit=limit)
