# -*- coding: utf-8 -*-
"""
Data-Agent-JP mmMasterRAG Qdrant Client

mmMasterRAG Collection 的語意檢索操作

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-10
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    SearchResponse,
)

from database.qdrant.client import get_qdrant_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "mmMasterRAG"
VECTOR_SIZE = 1024
DISTANCE = Distance.COSINE


@dataclass
class ItemEmbedding:
    """料號向量化資料"""

    item_no: str
    item_name: Optional[str] = None
    spec: Optional[str] = None
    vector: Optional[List[float]] = None
    searchable_text: Optional[str] = None

    def to_point(self, idx: int) -> PointStruct:
        """轉換為 Qdrant Point"""
        return PointStruct(
            id=idx,
            vector=self.vector or [],
            payload={
                "type": "item",
                "item_no": self.item_no,
                "item_name": self.item_name,
                "spec": self.spec,
                "searchable_text": self.searchable_text
                or f"{self.item_name or ''} {self.spec or ''} {self.item_no}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
        )


@dataclass
class WarehouseEmbedding:
    """倉庫向量化資料"""

    warehouse_no: str
    warehouse_name: Optional[str] = None
    location: Optional[str] = None
    vector: Optional[List[float]] = None
    searchable_text: Optional[str] = None

    def to_point(self, idx: int) -> PointStruct:
        """轉換為 Qdrant Point"""
        return PointStruct(
            id=idx,
            vector=self.vector or [],
            payload={
                "type": "warehouse",
                "warehouse_no": self.warehouse_no,
                "warehouse_name": self.warehouse_name,
                "location": self.location,
                "searchable_text": self.searchable_text
                or f"{self.warehouse_name or ''} {self.location or ''} {self.warehouse_no}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
        )


@dataclass
class WorkstationEmbedding:
    """工作站向量化資料"""

    workstation_id: str
    workstation_name: Optional[str] = None
    line: Optional[str] = None
    vector: Optional[List[float]] = None
    searchable_text: Optional[str] = None

    def to_point(self, idx: int) -> PointStruct:
        """轉換為 Qdrant Point"""
        return PointStruct(
            id=idx,
            vector=self.vector or [],
            payload={
                "type": "workstation",
                "workstation_id": self.workstation_id,
                "workstation_name": self.workstation_name,
                "line": self.line,
                "searchable_text": self.searchable_text
                or f"{self.workstation_name or ''} {self.line or ''} {self.workstation_id}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
        )


class MMMasterRAGClient:
    """
    mmMasterRAG Collection Client

    提供語意搜尋和混合檢索功能
    """

    def __init__(self, client: Optional[QdrantClient] = None):
        """
        初始化 Client

        Args:
            client: Qdrant Client（可選，若未提供則自動建立）
        """
        self._client = client
        self._collection_ready = False

    @property
    def client(self) -> QdrantClient:
        """取得 Qdrant Client"""
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    def ensure_collection(self, recreate: bool = False):
        """
        確保 Collection 存在

        Args:
            recreate: 是否重新建立（刪除現有）
        """
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if COLLECTION_NAME in collection_names:
                if recreate:
                    self.client.delete_collection(COLLECTION_NAME)
                    logger.info(f"Deleted existing collection: {COLLECTION_NAME}")
                else:
                    logger.info(f"Collection already exists: {COLLECTION_NAME}")
                    self._collection_ready = True
                    return

            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
            )
            logger.info(f"Created collection: {COLLECTION_NAME}")
            self._collection_ready = True

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def upsert_items(self, items: List[ItemEmbedding], vectors: List[List[float]]) -> int:
        """
        新增或更新料號向量化資料

        Args:
            items: 料號資料清單
            vectors: 對應的向量化清單

        Returns:
            int: 新增/更新的點數量
        """
        if not items:
            return 0

        points = []
        for idx, (item, vector) in enumerate(zip(items, vectors)):
            item.vector = vector
            points.append(item.to_point(idx))

        try:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Upserted {len(points)} item embeddings")
            return len(points)
        except Exception as e:
            logger.error(f"Failed to upsert items: {e}")
            return 0

    def upsert_warehouses(
        self, warehouses: List[WarehouseEmbedding], vectors: List[List[float]]
    ) -> int:
        """新增或更新倉庫向量化資料"""
        if not warehouses:
            return 0

        points = []
        for idx, (wh, vector) in enumerate(zip(warehouses, vectors)):
            wh.vector = vector
            points.append(wh.to_point(idx))

        try:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Upserted {len(points)} warehouse embeddings")
            return len(points)
        except Exception as e:
            logger.error(f"Failed to upsert warehouses: {e}")
            return 0

    def upsert_workstations(
        self, workstations: List[WorkstationEmbedding], vectors: List[List[float]]
    ) -> int:
        """新增或更新工作站向量化資料"""
        if not workstations:
            return 0

        points = []
        for idx, (ws, vector) in enumerate(zip(workstations, vectors)):
            ws.vector = vector
            points.append(ws.to_point(idx))

        try:
            self.client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(f"Upserted {len(points)} workstation embeddings")
            return len(points)
        except Exception as e:
            logger.error(f"Failed to upsert workstations: {e}")
            return 0

    def search(
        self,
        query_vector: List[float],
        query_type: str = "item",
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        語意搜尋

        Args:
            query_vector: 查詢向量
            query_type: 查詢類型 ("item", "warehouse", "workstation", None=全部)
            limit: 返回結果數量
            score_threshold: 相似度閾值

        Returns:
            List[Dict]: 搜尋結果
        """
        filter_condition = None
        if query_type and query_type != "all":
            filter_condition = Filter(
                must=[FieldCondition(key="type", match=MatchValue(value=query_type))]
            )

        try:
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=filter_condition,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "payload": r.payload,
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_items(
        self,
        query_vector: List[float],
        text: str = "",
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """搜尋料號"""
        results = self.search(
            query_vector, query_type="item", limit=limit, score_threshold=score_threshold
        )
        if text and not results:
            fallback = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=limit,
                filter=Filter(must=[FieldCondition(key="type", match=MatchValue(value="item"))]),
            )
            results = [{"id": p.id, "score": 1.0, "payload": p.payload} for p in fallback[0]]
        return results

    def search_warehouses(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """搜尋倉庫"""
        return self.search(
            query_vector, query_type="warehouse", limit=limit, score_threshold=score_threshold
        )

    def search_workstations(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """搜尋工作站"""
        return self.search(
            query_vector, query_type="workstation", limit=limit, score_threshold=score_threshold
        )

    def hybrid_search(
        self,
        text: str,
        embedding_model,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        混合搜尋（關鍵詞 + 語意）

        Args:
            text: 查詢文字
            embedding_model: 向量化模型（需有 encode 方法）
            limit: 返回數量

        Returns:
            List[Dict]: 混合搜尋結果
        """
        try:
            vector = embedding_model.encode(text).tolist()
            return self.search(vector, query_type="all", limit=limit, score_threshold=0.3)
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def count_by_type(self) -> Dict[str, int]:
        """取得各類型文件數量"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            counts = {}
            for doc_type in ["item", "warehouse", "workstation"]:
                result = self.client.count(
                    collection_name=COLLECTION_NAME,
                    count_filter=Filter(
                        must=[FieldCondition(key="type", match=MatchValue(value=doc_type))]
                    ),
                )
                counts[doc_type] = result.count
            return counts
        except Exception as e:
            logger.error(f"Count by type failed: {e}")
            return {}

    def delete_all(self) -> int:
        """刪除所有文件（危險操作）"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            result = self.client.delete(
                collection_name=COLLECTION_NAME,
                points_filter=Filter(
                    must=[FieldCondition(key="type", match=MatchValue(value="*"))]
                ),
            )
            return result
        except Exception as e:
            logger.error(f"Delete all failed: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            counts = self.count_by_type()
            return {
                "status": "healthy",
                "collection": COLLECTION_NAME,
                "counts": counts,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Singleton instance
_mm_master_rag_client: Optional[MMMasterRAGClient] = None


def get_mm_master_rag_client() -> MMMasterRAGClient:
    """取得 mmMasterRAG Client Singleton"""
    global _mm_master_rag_client
    if _mm_master_rag_client is None:
        _mm_master_rag_client = MMMasterRAGClient()
    return _mm_master_rag_client
