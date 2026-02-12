# 代碼功能說明: Qdrant 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Qdrant Schema 載入器

從 Qdrant 載入 Concepts 和 Intents
"""

import logging
from typing import Dict, Any, Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database.qdrant.client import get_qdrant_client

from ..models import ConceptsContainer, IntentsContainer

logger = logging.getLogger(__name__)


class QdrantSchemaLoader:
    """
    Qdrant Schema 載入器

    職責：
    - 從 Qdrant 載入 Concepts
    - 從 Qdrant 載入 Intents
    """

    COLLECTION_CONCEPTS = "jp_concepts"
    COLLECTION_INTENTS = "jp_intents"

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

    def load_concepts(self, system_id: str = "jp_tiptop_erp") -> Optional[ConceptsContainer]:
        """
        從 Qdrant 載入 Concepts

        Args:
            system_id: 系統 ID

        Returns:
            ConceptsContainer 或 None（如果載入失敗）
        """
        try:
            logger.info(f"Loading concepts from Qdrant: {self._concepts_collection}")

            # 查詢所有 Concepts
            points = self.client.scroll(
                collection_name=self._concepts_collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="system_id", match=MatchValue(value=system_id))]
                ),
                limit=1000,
            )

            if not points or not points[0]:
                logger.warning(f"No concepts found in Qdrant: {self._concepts_collection}")
                return None

            # 構建 Concepts 結構
            concepts = {}
            for point in points[0]:
                payload = point.payload or {}
                name = payload.get("name")
                if name:
                    concepts[name] = {
                        "description": payload.get("description", ""),
                        "type": payload.get("type", "DIMENSION"),
                        "values": payload.get("values", {}),
                    }

            logger.info(f"Loaded {len(concepts)} concepts from Qdrant")

            return ConceptsContainer(version="1.0", concepts=concepts)

        except Exception as e:
            logger.error(f"Failed to load concepts from Qdrant: {e}")
            return None

    def load_intents(self, system_id: str = "jp_tiptop_erp") -> Optional[IntentsContainer]:
        """
        從 Qdrant 載入 Intents

        Args:
            system_id: 系統 ID

        Returns:
            IntentsContainer 或 None（如果載入失敗）
        """
        try:
            logger.info(f"Loading intents from Qdrant: {self._intents_collection}")

            # 查詢所有 Intents
            points = self.client.scroll(
                collection_name=self._intents_collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="system_id", match=MatchValue(value=system_id))]
                ),
                limit=1000,
            )

            if not points or not points[0]:
                logger.warning(f"No intents found in Qdrant: {self._intents_collection}")
                return None

            # 構建 Intents 結構
            intents = {}
            for point in points[0]:
                payload = point.payload or {}
                name = payload.get("name")
                if name:
                    intents[name] = {
                        "description": payload.get("description", ""),
                        "input": payload.get("input", {}),
                        "output": payload.get("output", {}),
                        "constraints": payload.get("constraints", {}),
                    }

            logger.info(f"Loaded {len(intents)} intents from Qdrant")

            return IntentsContainer(version="1.0", intents=intents)

        except Exception as e:
            logger.error(f"Failed to load intents from Qdrant: {e}")
            return None

    def check_collections(self) -> Dict[str, bool]:
        """檢查 Collection 是否存在"""
        result = {}

        for collection in [self._concepts_collection, self._intents_collection]:
            try:
                self.client.get_collection(collection_name=collection)
                result[collection] = True
            except Exception:
                result[collection] = False

        return result


def load_concepts_from_qdrant(
    client: Optional[QdrantClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> Optional[ConceptsContainer]:
    """便捷函數：從 Qdrant 載入 Concepts"""
    loader = QdrantSchemaLoader(client, collection_prefix)
    return loader.load_concepts(system_id)


def load_intents_from_qdrant(
    client: Optional[QdrantClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> Optional[IntentsContainer]:
    """便捷函數：從 Qdrant 載入 Intents"""
    loader = QdrantSchemaLoader(client, collection_prefix)
    return loader.load_intents(system_id)
