# 代碼功能說明: Qdrant 上傳器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Qdrant Schema 上傳器

將 Concepts 和 Intents 上傳到 Qdrant
"""

import json
import logging
from typing import Dict, Any, Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
)

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database.qdrant.client import get_qdrant_client

logger = logging.getLogger(__name__)


class QdrantSchemaUploader:
    """
    Qdrant Schema 上傳器

    職責：
    - 上傳 Concepts 到 Qdrant
    - 上傳 Intents 到 Qdrant
    - 管理 Collection 創建
    """

    COLLECTION_CONCEPTS = "jp_concepts"
    COLLECTION_INTENTS = "jp_intents"
    EMBEDDING_DIMENSION = 1024

    def __init__(self, client: Optional[QdrantClient] = None, collection_prefix: str = "jp_"):
        self._client = client
        self._collection_prefix = collection_prefix

        self._concepts_collection = f"{collection_prefix}concepts"
        self._intents_collection = f"{collection_prefix}intents"

    @property
    def client(self) -> QdrantClient:
        """獲取 Qdrant 客戶端"""
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    def ensure_collections(self) -> Dict[str, bool]:
        """確保 Collection 存在"""
        result = {}

        for collection in [self._concepts_collection, self._intents_collection]:
            try:
                self.client.get_collection(collection_name=collection)
                logger.info(f"Collection already exists: {collection}")
                result[collection] = True
            except Exception:
                logger.info(f"Creating collection: {collection}")
                try:
                    self.client.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(
                            size=self.EMBEDDING_DIMENSION, distance=Distance.COSINE
                        ),
                    )
                    result[collection] = True
                except Exception as e:
                    logger.error(f"Failed to create collection {collection}: {e}")
                    result[collection] = False

        return result

    def _generate_embedding(self, text: str) -> List[float]:
        """
        生成文字的向量嵌入

        預留：未來接入 Ollama nomic-embed-text
        目前使用簡化的 hash 向量
        """
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [(hash_val % 100) / 100.0 for _ in range(self.EMBEDDING_DIMENSION)]

        return vector

    def upload_concepts(
        self, concepts_data: Dict[str, Any], system_id: str = "jp_tiptop_erp"
    ) -> int:
        """
        上傳 Concepts 到 Qdrant

        Args:
            concepts_data: Concepts JSON 數據
            system_id: 系統 ID

        Returns:
            上傳的點數量
        """
        concepts = concepts_data.get("concepts", {})

        if not concepts:
            logger.warning("No concepts to upload")
            return 0

        points = []

        for idx, (name, concept) in enumerate(concepts.items()):
            description = concept.get("description", "")
            concept_type = concept.get("type", "DIMENSION")
            values = concept.get("values", {})

            # 生成文字表示
            labels = []
            for key, value in values.items():
                labels.extend(value.get("labels", []))

            text = f"{name}: {description}, 類型: {concept_type}, 標籤: {', '.join(labels)}"

            points.append(
                PointStruct(
                    id=idx,
                    vector=self._generate_embedding(text),
                    payload={
                        "type": "concept",
                        "system_id": system_id,
                        "name": name,
                        "description": description,
                        "concept_type": concept_type,
                        "values": values,
                        "labels": labels,
                        "text": text,
                    },
                )
            )

        # 上傳到 Qdrant
        self.client.upsert(collection_name=self._concepts_collection, points=points)

        logger.info(f"Uploaded {len(points)} concepts to {self._concepts_collection}")

        return len(points)

    def upload_intents(self, intents_data: Dict[str, Any], system_id: str = "jp_tiptop_erp") -> int:
        """
        上傳 Intents 到 Qdrant

        Args:
            intents_data: Intents JSON 數據
            system_id: 系統 ID

        Returns:
            上傳的點數量
        """
        intents = intents_data.get("intents", {})

        if not intents:
            logger.warning("No intents to upload")
            return 0

        points = []

        for idx, (name, intent) in enumerate(intents.items()):
            description = intent.get("description", "")
            input_filters = intent.get("input", {}).get("filters", [])
            output_metrics = intent.get("output", {}).get("metrics", [])
            output_dims = intent.get("output", {}).get("dimensions", [])

            # 生成文字表示
            text = f"{name}: {description}, 過濾器: {', '.join(input_filters)}, 指標: {', '.join(output_metrics)}, 維度: {', '.join(output_dims)}"

            points.append(
                PointStruct(
                    id=idx,
                    vector=self._generate_embedding(text),
                    payload={
                        "type": "intent",
                        "system_id": system_id,
                        "name": name,
                        "description": description,
                        "input_filters": input_filters,
                        "output_metrics": output_metrics,
                        "output_dimensions": output_dims,
                        "text": text,
                    },
                )
            )

        # 上傳到 Qdrant
        self.client.upsert(collection_name=self._intents_collection, points=points)

        logger.info(f"Uploaded {len(points)} intents to {self._intents_collection}")

        return len(points)

    def search_concepts(
        self, query: str, system_id: str = "jp_tiptop_erp", limit: int = 5
    ) -> List[Dict]:
        """
        搜尋 Concepts

        Args:
            query: 搜尋查詢
            system_id: 系統 ID
            limit: 返回數量限制

        Returns:
            搜尋結果列表
        """
        query_vector = self._generate_embedding(query)

        results = self.client.search(
            collection_name=self._concepts_collection,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="system_id", match=MatchValue(value=system_id))]
            ),
            limit=limit,
        )

        return [
            {
                "name": r.payload.get("name"),
                "description": r.payload.get("description"),
                "score": r.score,
            }
            for r in results
        ]

    def search_intents(
        self, query: str, system_id: str = "jp_tiptop_erp", limit: int = 5
    ) -> List[Dict]:
        """
        搜尋 Intents

        Args:
            query: 搜尋查詢
            system_id: 系統 ID
            limit: 返回數量限制

        Returns:
            搜尋結果列表
        """
        query_vector = self._generate_embedding(query)

        results = self.client.search(
            collection_name=self._intents_collection,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="system_id", match=MatchValue(value=system_id))]
            ),
            limit=limit,
        )

        return [
            {
                "name": r.payload.get("name"),
                "description": r.payload.get("description"),
                "score": r.score,
            }
            for r in results
        ]


def upload_concepts_to_qdrant(
    concepts_data: Dict[str, Any],
    client: Optional[QdrantClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> int:
    """便捷函數：上傳 Concepts 到 Qdrant"""
    uploader = QdrantSchemaUploader(client, collection_prefix)
    return uploader.upload_concepts(concepts_data, system_id)


def upload_intents_to_qdrant(
    intents_data: Dict[str, Any],
    client: Optional[QdrantClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> int:
    """便捷函數：上傳 Intents 到 Qdrant"""
    uploader = QdrantSchemaUploader(client, collection_prefix)
    return uploader.upload_intents(intents_data, system_id)
