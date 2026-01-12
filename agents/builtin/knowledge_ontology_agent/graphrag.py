# 代碼功能說明: GraphRAG 增強功能
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""GraphRAG 增強功能 - 實體檢索、關係路徑查詢、子圖提取等"""

import logging
from typing import Any, Dict, List, Optional

from database.arangodb import ArangoDBClient
from genai.api.services.kg_builder_service import KGBuilderService

logger = logging.getLogger(__name__)


class GraphRAGService:
    """GraphRAG 服務 - 提供增強的圖譜查詢功能"""

    def __init__(
        self, kg_service: Optional[KGBuilderService] = None, client: Optional[ArangoDBClient] = None
    ):
        """
        初始化 GraphRAG 服務

        Args:
            kg_service: 知識圖譜構建服務（可選，如果不提供則自動創建）
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self._kg_service = kg_service or KGBuilderService(client=client)
        self._logger = logger

    async def entity_retrieval(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        實體檢索（Entity Retrieval）

        Args:
            entity_name: 實體名稱
            entity_type: 實體類型（可選）
            limit: 返回數量限制

        Returns:
            檢索結果，包含實體列表和相關信息
        """
        try:
            entities = self._kg_service.list_entities(
                entity_type=entity_type, limit=limit, offset=0
            )

            # 過濾匹配的實體
            matched_entities = [
                e
                for e in entities
                if entity_name.lower() in e.get("name", "").lower()
                or entity_name.lower() in e.get("text", "").lower()
            ]

            return {
                "query": entity_name,
                "entity_type": entity_type,
                "entities": matched_entities[:limit],
                "total": len(matched_entities),
            }

        except Exception as e:
            self._logger.error(f"Entity retrieval failed: {e}")
            raise

    async def relation_path_query(
        self,
        from_entity: str,
        to_entity: str,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        關係路徑查詢（Relation Path Query）

        Args:
            from_entity: 起始實體名稱或 ID
            to_entity: 目標實體名稱或 ID
            relation_types: 關係類型列表（可選）
            max_depth: 最大深度

        Returns:
            路徑查詢結果，包含路徑列表和相關信息
        """
        try:
            # 首先查找實體
            from_entities = self._kg_service.list_entities(limit=100, offset=0)
            from_entity_obj = next(
                (
                    e
                    for e in from_entities
                    if from_entity in e.get("name", "") or from_entity == e.get("_key", "")
                ),
                None,
            )
            to_entity_obj = next(
                (
                    e
                    for e in from_entities
                    if to_entity in e.get("name", "") or to_entity == e.get("_key", "")
                ),
                None,
            )

            if not from_entity_obj or not to_entity_obj:
                return {
                    "from_entity": from_entity,
                    "to_entity": to_entity,
                    "paths": [],
                    "error": "Entity not found",
                }

            from_entity_id = from_entity_obj.get("_id")
            to_entity_id = to_entity_obj.get("_id")

            # 使用 AQL 查詢路徑
            if self._kg_service.client is None or self._kg_service.client.db is None:
                raise RuntimeError("ArangoDB client is not connected")
            if self._kg_service.client.db.aql is None:
                raise RuntimeError("ArangoDB AQL is not available")

            # 構建 AQL 查詢
            filter_clause = ""
            bind_vars: Dict[str, Any] = {
                "@relations": "relations",
                "from_id": from_entity_id,
                "to_id": to_entity_id,
                "max_depth": max_depth,
            }

            if relation_types:
                filter_clause = "FILTER r.type IN @relation_types"
                bind_vars["relation_types"] = relation_types

            aql = f"""
            FOR v, e, p IN 1..@max_depth ANY @from_id @@relations
                {filter_clause}
                FILTER v._id == @to_id
                LIMIT 10
                RETURN {{
                    path: p.vertices[*].name,
                    edges: p.edges[*].type,
                    length: LENGTH(p.edges)
                }}
            """

            cursor = self._kg_service.client.db.aql.execute(aql, bind_vars=bind_vars)
            paths = list(cursor)

            return {
                "from_entity": from_entity,
                "to_entity": to_entity,
                "paths": paths,
                "total": len(paths),
            }

        except Exception as e:
            self._logger.error(f"Relation path query failed: {e}")
            raise

    async def subgraph_extraction(
        self,
        center_entity: str,
        max_depth: int = 2,
        limit: int = 50,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        子圖提取（Subgraph Extraction）

        Args:
            center_entity: 中心實體名稱或 ID
            max_depth: 最大深度
            limit: 返回數量限制
            relation_types: 關係類型列表（可選）

        Returns:
            子圖數據，包含實體和關係
        """
        try:
            # 查找中心實體
            entities = self._kg_service.list_entities(limit=100, offset=0)
            center_entity_obj = next(
                (
                    e
                    for e in entities
                    if center_entity in e.get("name", "") or center_entity == e.get("_key", "")
                ),
                None,
            )

            if not center_entity_obj:
                return {
                    "center_entity": center_entity,
                    "entities": [],
                    "relations": [],
                    "error": "Center entity not found",
                }

            center_entity_id = center_entity_obj.get("_id")

            # 使用 KGBuilderService 的 get_entity_subgraph 方法
            subgraph = self._kg_service.get_entity_subgraph(
                entity_id=center_entity_id,
                max_depth=max_depth,
                limit=limit,
            )

            return {
                "center_entity": center_entity,
                "subgraph": subgraph,
                "max_depth": max_depth,
                "limit": limit,
            }

        except Exception as e:
            self._logger.error(f"Subgraph extraction failed: {e}")
            raise

    def calculate_entity_similarity(
        self, entity1: Dict[str, Any], entity2: Dict[str, Any]
    ) -> float:
        """
        實體相似度計算

        Args:
            entity1: 第一個實體
            entity2: 第二個實體

        Returns:
            相似度分數（0-1）
        """
        # 簡單的相似度計算（可以後續增強）
        name1 = entity1.get("name", "").lower()
        name2 = entity2.get("name", "").lower()

        if name1 == name2:
            return 1.0

        # 計算字符串相似度（簡單實現）
        if name1 in name2 or name2 in name1:
            return 0.7

        # 計算共同字符比例
        common_chars = set(name1) & set(name2)
        total_chars = set(name1) | set(name2)
        if total_chars:
            return len(common_chars) / len(total_chars)

        return 0.0

    def evaluate_relation_strength(self, relation: Dict[str, Any]) -> float:
        """
        關係強度評估

        Args:
            relation: 關係數據

        Returns:
            關係強度分數（0-1）
        """
        # 使用置信度作為關係強度
        confidence = relation.get("confidence", 0.0)
        weight = relation.get("weight", 0.0)

        # 綜合評估
        strength = (confidence + weight) / 2.0
        return min(1.0, max(0.0, strength))

    def analyze_graph_paths(self, paths: List[List[str]], center_entity: str) -> Dict[str, Any]:
        """
        圖譜路徑分析

        Args:
            paths: 路徑列表
            center_entity: 中心實體

        Returns:
            路徑分析結果
        """
        if not paths:
            return {
                "center_entity": center_entity,
                "total_paths": 0,
                "avg_path_length": 0.0,
                "max_path_length": 0,
                "min_path_length": 0,
            }

        path_lengths = [len(path) for path in paths]

        return {
            "center_entity": center_entity,
            "total_paths": len(paths),
            "avg_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0.0,
            "max_path_length": max(path_lengths) if path_lengths else 0,
            "min_path_length": min(path_lengths) if path_lengths else 0,
        }
