# 代碼功能說明: 知識圖譜構建服務
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-05

"""知識圖譜構建服務 - 實現三元組到圖譜的轉換、實體和關係的創建/更新/清理"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient
from genai.api.models.triple_models import Triple
from services.api.services.file_metadata_service import get_metadata_service
from services.api.services.file_permission_service import get_file_permission_service
from system.security.models import Permission, User

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
    ) -> tuple[str, bool]:
        """
        查找或創建實體（實體去重）

        Returns:
            (entity_id, is_created): 實體ID和是否為新創建的標記
        """
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
                return (f"{ENTITIES_COLLECTION}/{entity_key}", False)
        except Exception:
            pass

        # 創建新實體
        entity_doc = {
            "_key": entity_key,
            "type": entity_type,
            "label": entity_type,  # 添加 label 字段（與 type 相同，用於查詢）
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
        return (f"{ENTITIES_COLLECTION}/{entity_key}", True)

    def _find_or_create_relation(
        self,
        from_vertex: str,
        to_vertex: str,
        relation_type: str,
        confidence: float,
        context: str,
        file_id: Optional[str] = None,
    ) -> tuple[Optional[str], bool]:
        """
        查找或創建關係（關係去重）

        Returns:
            (relation_id, is_created): 關係ID和是否為新創建的標記
        """
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
                return (f"{RELATIONS_COLLECTION}/{relation_key}", False)
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
        return (f"{RELATIONS_COLLECTION}/{relation_key}", True)

    def _judge_triples(
        self,
        triples: List[Triple],
        min_confidence: float = 0.5,
        core_node_threshold: float = 0.9,
    ) -> Dict[str, Any]:
        """
        GraphRAG 裁決層：過濾和評估三元組

        Args:
            triples: 候選三元組列表
            min_confidence: 最小置信度閾值（低於此值不入圖）
            core_node_threshold: 核心節點閾值（高於此值標記為核心節點）

        Returns:
            裁決結果字典，包含：
            - filtered_triples: 過濾後的三元組列表
            - filtered_count: 被過濾的三元組數量
            - core_node_count: 核心節點數量
            - statistics: 統計信息
        """
        filtered_triples: List[Triple] = []
        filtered_count = 0
        core_node_count = 0
        confidence_stats = {
            "high": 0,  # >= 0.9
            "medium": 0,  # 0.7-0.9
            "low": 0,  # 0.5-0.7
            "rejected": 0,  # < 0.5
        }

        for triple in triples:
            confidence = triple.confidence

            # 統計置信度分佈
            if confidence >= 0.9:
                confidence_stats["high"] += 1
            elif confidence >= 0.7:
                confidence_stats["medium"] += 1
            elif confidence >= 0.5:
                confidence_stats["low"] += 1
            else:
                confidence_stats["rejected"] += 1

            # 裁決：過濾低置信度三元組
            if confidence < min_confidence:
                filtered_count += 1
                logger.debug(
                    "Triple rejected by judgment layer",
                    confidence=confidence,
                    min_confidence=min_confidence,
                    subject=triple.subject.text,
                    relation=triple.relation.type,
                    object=triple.object.text,
                )
                continue

            # 標記核心節點（高置信度通常表示核心節點）
            if confidence >= core_node_threshold:
                core_node_count += 1

            filtered_triples.append(triple)

        statistics = {
            "total": len(triples),
            "filtered": filtered_count,
            "accepted": len(filtered_triples),
            "core_nodes": core_node_count,
            "confidence_distribution": confidence_stats,
            "filter_rate": filtered_count / len(triples) if triples else 0.0,
        }

        logger.info(
            "GraphRAG judgment layer completed",
            total_triples=len(triples),
            filtered_count=filtered_count,
            accepted_count=len(filtered_triples),
            core_node_count=core_node_count,
            min_confidence=min_confidence,
            core_node_threshold=core_node_threshold,
        )

        return {
            "filtered_triples": filtered_triples,
            "filtered_count": filtered_count,
            "core_node_count": core_node_count,
            "statistics": statistics,
        }

    async def build_from_triples(
        self,
        triples: List[Triple],
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_confidence: float = 0.5,
        core_node_threshold: float = 0.9,
        enable_judgment: bool = True,
    ) -> Dict:
        """
        從三元組構建知識圖譜

        Args:
            triples: 三元組列表
            file_id: 文件ID（可選）
            user_id: 用戶ID（可選）
            min_confidence: 最小置信度閾值（低於此值不入圖，默認 0.5）
            core_node_threshold: 核心節點閾值（高於此值標記為核心節點，默認 0.9）
            enable_judgment: 是否啟用裁決層（默認 True）

        Returns:
            構建結果字典，包含：
            - entities_created: 創建的實體數量
            - entities_updated: 更新的實體數量
            - relations_created: 創建的關係數量
            - relations_updated: 更新的關係數量
            - total_triples: 總三元組數量
            - judgment_stats: 裁決層統計信息（如果啟用）
        """
        # GraphRAG 裁決層：過濾低置信度三元組
        judgment_result = None
        if enable_judgment:
            judgment_result = self._judge_triples(
                triples=triples,
                min_confidence=min_confidence,
                core_node_threshold=core_node_threshold,
            )
            triples = judgment_result["filtered_triples"]

        entities_created = 0
        entities_updated = 0
        relations_created = 0
        relations_updated = 0

        for triple in triples:
            try:
                # 創建或更新主體實體
                subject_id, subject_created = self._find_or_create_entity(
                    triple.subject.text,
                    triple.subject.type,
                    triple.subject.start,
                    triple.subject.end,
                    file_id=file_id,
                )
                if subject_created:
                    entities_created += 1
                else:
                    entities_updated += 1

                # 創建或更新客體實體
                object_id, object_created = self._find_or_create_entity(
                    triple.object.text,
                    triple.object.type,
                    triple.object.start,
                    triple.object.end,
                    file_id=file_id,
                )
                if object_created:
                    entities_created += 1
                else:
                    entities_updated += 1

                # 創建或更新關係
                relation_id, relation_created = self._find_or_create_relation(
                    subject_id,
                    object_id,
                    triple.relation.type,
                    triple.confidence,
                    triple.context,
                    file_id=file_id,
                )
                if relation_id:
                    if relation_created:
                        relations_created += 1
                    else:
                        relations_updated += 1

            except Exception as e:
                logger.error("kg_build_triple_failed", error=str(e), triple=triple)

        result = {
            "entities_created": entities_created,
            "entities_updated": entities_updated,
            "relations_created": relations_created,
            "relations_updated": relations_updated,
            "total_triples": len(triples),
        }

        # 添加裁決層統計信息
        if judgment_result:
            result["judgment_stats"] = judgment_result["statistics"]

        return result

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

        # 1) 清理 relations（分離查詢以避免 ERR 1579 錯誤）
        # 修改時間：2026-01-05 - 將relations清理分成多個獨立查詢，避免ERR 1579錯誤

        # 1.1) 查詢需要處理的relations（不修改數據）
        check_rel_query = """
            FOR r IN @@relations
                LET ids = (
                    r.file_ids != null ? r.file_ids :
                    (r.file_id != null ? [r.file_id] : [])
                )
                FILTER @file_id IN ids
                LET new_ids = REMOVE_VALUE(ids, @file_id)
                RETURN {
                    key: r._key,
                    new_ids: new_ids
                }
        """
        check_rel_bind: Dict[str, Any] = {
            "@relations": RELATIONS_COLLECTION,
            "file_id": file_id,
        }
        check_rel_result = self.client.execute_aql(check_rel_query, bind_vars=check_rel_bind)
        rel_targets = check_rel_result.get("results", [])

        # 1.2) 分類relations：需要刪除的和需要更新的
        relations_to_delete: List[str] = []
        relations_to_update: List[Dict[str, Any]] = []

        for target in rel_targets:
            new_ids = target.get("new_ids", [])
            rel_key = target.get("key")

            if len(new_ids) == 0:
                relations_to_delete.append(rel_key)
            else:
                relations_to_update.append(
                    {
                        "key": rel_key,
                        "new_ids": new_ids,
                    }
                )

        # 1.3) 刪除relations（單獨的查詢）
        relations_deleted = 0
        if relations_to_delete:
            delete_rel_query = """
            FOR key IN @keys
                REMOVE key IN @@relations
                RETURN 1
            """
            delete_rel_bind: Dict[str, Any] = {
                "@relations": RELATIONS_COLLECTION,
                "keys": relations_to_delete,
            }
            delete_rel_result = self.client.execute_aql(delete_rel_query, bind_vars=delete_rel_bind)
            relations_deleted = len(delete_rel_result.get("results", []))

        # 1.4) 更新relations（單獨的查詢）
        relations_updated = 0
        if relations_to_update:
            update_rel_query = f"""
            FOR item IN @items
                UPDATE item.key WITH {{
                    file_ids: item.new_ids,
                    file_id: FIRST(item.new_ids),
                    updated_at: {now_expr}
                }} IN @@relations
                RETURN 1
            """
            update_rel_bind: Dict[str, Any] = {
                "@relations": RELATIONS_COLLECTION,
                "items": relations_to_update,
            }
            update_rel_result = self.client.execute_aql(update_rel_query, bind_vars=update_rel_bind)
            relations_updated = len(update_rel_result.get("results", []))

        # 2) 清理 entities（分離查詢以避免 ERR 1579 錯誤）
        # 修改時間：2026-01-03 - 將entities清理分成多個獨立查詢，避免ERR 1579錯誤

        # 2.1) 查詢需要處理的entities（不修改數據）
        check_query = """
            FOR e IN @@entities
                LET ids = (
                    e.file_ids != null ? e.file_ids :
                    (e.file_id != null ? [e.file_id] : [])
                )
                FILTER @file_id IN ids
                LET new_ids = REMOVE_VALUE(ids, @file_id)
            RETURN {
                key: e._key,
                id: e._id,
                new_ids: new_ids
            }
        """
        check_bind: Dict[str, Any] = {
            "@entities": ENTITIES_COLLECTION,
            "file_id": file_id,
        }
        check_result = self.client.execute_aql(check_query, bind_vars=check_bind)
        targets = check_result.get("results", [])

        if not targets:
            entities_deleted = 0
            entities_updated = 0
        else:
            # 2.2) 分類entities：需要刪除的和需要更新的
            entity_ids_to_check: List[str] = []  # 需要檢查是否有關聯relations的entity IDs
            entities_map: Dict[str, Dict[str, Any]] = {}  # entity_id -> {key, new_ids}
            entities_to_update: List[Dict[str, Any]] = []

            for target in targets:
                new_ids = target.get("new_ids", [])
                entity_key = target.get("key")
                entity_id = target.get("id")
                entities_map[entity_id] = {"key": entity_key, "new_ids": new_ids}

                if len(new_ids) == 0:
                    entity_ids_to_check.append(entity_id)
                else:
                    entities_to_update.append(
                        {
                            "key": entity_key,
                            "new_ids": new_ids,
                        }
                    )

            # 2.3) 批量查詢哪些entities有關聯的relations（在relations已經清理後，這個查詢不會觸發ERR 1579）
            entities_to_delete: List[str] = []
            if entity_ids_to_check:
                # 查詢所有沒有關聯relations的entity IDs
                has_edge_query = """
                FOR entity_id IN @entity_ids
                LET has_edge = LENGTH(
                    FOR r IN @@relations
                            FILTER r._from == entity_id OR r._to == entity_id
                        LIMIT 1
                        RETURN 1
                ) > 0
                FILTER has_edge == false
                    RETURN entity_id
                """
                has_edge_bind: Dict[str, Any] = {
                    "@relations": RELATIONS_COLLECTION,
                    "entity_ids": entity_ids_to_check,
                }
                has_edge_result = self.client.execute_aql(has_edge_query, bind_vars=has_edge_bind)
                entities_without_edges = has_edge_result.get("results", [])

                # 找出對應的entity keys
                for entity_id in entities_without_edges:
                    if entity_id in entities_map:
                        entities_to_delete.append(entities_map[entity_id]["key"])

            # 2.4) 刪除entities（單獨的查詢）
            entities_deleted = 0
            if entities_to_delete:
                delete_query = """
                FOR key IN @keys
                    REMOVE key IN @@entities
                RETURN 1
                """
                delete_bind: Dict[str, Any] = {
                    "@entities": ENTITIES_COLLECTION,
                    "keys": entities_to_delete,
                }
                delete_result = self.client.execute_aql(delete_query, bind_vars=delete_bind)
                entities_deleted = len(delete_result.get("results", []))

            # 2.5) 更新entities（單獨的查詢）
            entities_updated = 0
            if entities_to_update:
                update_query = f"""
                FOR item IN @items
                    UPDATE item.key WITH {{
                        file_ids: item.new_ids,
                        file_id: FIRST(item.new_ids),
                    updated_at: {now_expr}
                }} IN @@entities
                RETURN 1
                """
                update_bind: Dict[str, Any] = {
                    "@entities": ENTITIES_COLLECTION,
                    "items": entities_to_update,
                }
                update_result = self.client.execute_aql(update_query, bind_vars=update_bind)
                entities_updated = len(update_result.get("results", []))

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

    def list_triples_by_file_id_with_acl(
        self,
        file_id: str,
        user: User,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """帶訪問控制權限檢查的依 file_id 查詢三元組

        AI治理要求：
        1. 只返回用戶有權限訪問的文件三元組
        2. 根據文件訪問級別過濾結果

        Args:
            file_id: 文件 ID
            user: 當前用戶（用於權限檢查）
            limit: 回傳上限
            offset: 偏移量

        Returns:
            dict: { total: int, triples: List[Dict[str, Any]] }，只包含用戶有權訪問的三元組
        """
        # 1. 檢查文件訪問權限
        permission_service = get_file_permission_service()
        metadata_service = get_metadata_service()

        file_metadata = metadata_service.get(file_id)
        if not file_metadata:
            # 文件不存在，返回空結果
            return {"total": 0, "triples": [], "limit": limit, "offset": offset}

        # 檢查訪問權限
        if not permission_service.check_file_access_with_acl(
            user=user,
            file_metadata=file_metadata,
            required_permission=Permission.FILE_READ.value,
        ):
            # 無權訪問，返回空結果
            logger.debug(
                "User denied access to file for KG query",
                user_id=user.user_id,
                file_id=file_id,
            )
            return {"total": 0, "triples": [], "limit": limit, "offset": offset}

        # 2. 有權訪問，執行正常查詢
        return self.list_triples_by_file_id(file_id=file_id, limit=limit, offset=offset)

    def list_entities_with_acl(
        self,
        user: User,
        entity_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        """帶訪問控制權限檢查的查詢實體列表

        AI治理要求：
        1. 只返回用戶有權限訪問的文件實體
        2. 根據文件訪問級別過濾結果

        Args:
            user: 當前用戶（用於權限檢查）
            entity_type: 實體類型（可選）
            limit: 回傳上限
            offset: 偏移量

        Returns:
            過濾後的實體列表，只包含用戶有權訪問的文件實體
        """
        # 1. 執行正常查詢（獲取更多結果，用於過濾）
        expanded_limit = limit * 2 if limit > 0 else 20
        entities = self.list_entities(entity_type=entity_type, limit=expanded_limit, offset=offset)

        # 2. 獲取文件元數據並檢查權限
        permission_service = get_file_permission_service()
        metadata_service = get_metadata_service()
        filtered_entities: List[Dict] = []

        # 批量獲取文件元數據（優化性能）
        file_ids_seen: set = set()
        file_access_cache: Dict[str, bool] = {}

        for entity in entities:
            # 從實體的 file_id 或 file_ids 獲取文件ID
            entity_file_ids: List[str] = []
            if entity.get("file_id"):
                entity_file_ids.append(entity["file_id"])
            if entity.get("file_ids"):
                entity_file_ids.extend(entity["file_ids"])

            # 如果實體沒有關聯文件，跳過（不應該發生，但為了安全）
            if not entity_file_ids:
                continue

            # 檢查實體關聯的所有文件，只要有一個文件有權訪問，就包含該實體
            has_access = False
            for file_id in entity_file_ids:
                if file_id in file_ids_seen:
                    # 使用緩存結果
                    if file_access_cache.get(file_id, False):
                        has_access = True
                        break
                    continue

                file_ids_seen.add(file_id)

                # 獲取文件元數據
                try:
                    file_metadata = metadata_service.get(file_id)
                    if not file_metadata:
                        file_access_cache[file_id] = False
                        continue

                    # 檢查訪問權限
                    access = permission_service.check_file_access_with_acl(
                        user=user,
                        file_metadata=file_metadata,
                        required_permission=Permission.FILE_READ.value,
                    )
                    file_access_cache[file_id] = access

                    if access:
                        has_access = True
                        break
                except Exception as e:
                    logger.warning(
                        "Failed to check file access for entity",
                        entity_id=entity.get("_key"),
                        file_id=file_id,
                        error=str(e),
                    )
                    # 權限檢查失敗，跳過（安全優先）
                    file_access_cache[file_id] = False
                    continue

            if has_access:
                filtered_entities.append(entity)
                if len(filtered_entities) >= limit:
                    break

        logger.debug(
            "List entities with ACL completed",
            entity_type=entity_type,
            total_entities=len(entities),
            filtered_entities=len(filtered_entities),
            filtered_count=len(entities) - len(filtered_entities),
        )

        return filtered_entities

    def get_entity_neighbors_with_acl(
        self,
        entity_id: str,
        user: User,
        relation_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """帶訪問控制權限檢查的獲取實體鄰居節點

        AI治理要求：
        1. 只返回用戶有權限訪問的文件實體和關係
        2. 根據文件訪問級別過濾結果

        Args:
            entity_id: 實體 ID
            user: 當前用戶（用於權限檢查）
            relation_types: 關係類型列表（可選）
            limit: 回傳上限

        Returns:
            過濾後的鄰居節點列表，只包含用戶有權訪問的文件實體
        """
        # 1. 執行正常查詢
        neighbors = self.get_entity_neighbors(
            entity_id=entity_id, relation_types=relation_types, limit=limit * 2
        )

        # 2. 過濾結果（類似 list_entities_with_acl 的邏輯）
        permission_service = get_file_permission_service()
        metadata_service = get_metadata_service()
        filtered_neighbors: List[Dict] = []

        file_ids_seen: set = set()
        file_access_cache: Dict[str, bool] = {}

        for neighbor in neighbors:
            # 從鄰居實體的 file_id 或 file_ids 獲取文件ID
            neighbor_file_ids: List[str] = []
            if neighbor.get("file_id"):
                neighbor_file_ids.append(neighbor["file_id"])
            if neighbor.get("file_ids"):
                neighbor_file_ids.extend(neighbor["file_ids"])

            if not neighbor_file_ids:
                continue

            has_access = False
            for file_id in neighbor_file_ids:
                if file_id in file_ids_seen:
                    if file_access_cache.get(file_id, False):
                        has_access = True
                        break
                    continue

                file_ids_seen.add(file_id)

                try:
                    file_metadata = metadata_service.get(file_id)
                    if not file_metadata:
                        file_access_cache[file_id] = False
                        continue

                    access = permission_service.check_file_access_with_acl(
                        user=user,
                        file_metadata=file_metadata,
                        required_permission=Permission.FILE_READ.value,
                    )
                    file_access_cache[file_id] = access

                    if access:
                        has_access = True
                        break
                except Exception as e:
                    logger.warning(
                        "Failed to check file access for neighbor",
                        neighbor_id=neighbor.get("_key"),
                        file_id=file_id,
                        error=str(e),
                    )
                    file_access_cache[file_id] = False
                    continue

            if has_access:
                filtered_neighbors.append(neighbor)
                if len(filtered_neighbors) >= limit:
                    break

        return filtered_neighbors
