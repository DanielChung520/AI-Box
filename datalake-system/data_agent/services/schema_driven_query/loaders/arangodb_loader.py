# 代碼功能說明: ArangoDB 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""ArangoDB Schema 載入器

從 ArangoDB 載入 Bindings 和 Entities
"""

import logging
from typing import Dict, Any, Optional
from arango.database import StandardDatabase

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database.arangodb.client import ArangoDBClient

from ..models import BindingsContainer, ConceptsContainer, IntentsContainer

logger = logging.getLogger(__name__)


class ArangoDBSchemaLoader:
    """
    ArangoDB Schema 載入器

    職責：
    - 從 ArangoDB 載入 Bindings
    - 從 ArangoDB 載入 Entities
    """

    def __init__(self, client: Optional[ArangoDBClient] = None, collection_prefix: str = "jp_"):
        self._client = client
        self._collection_prefix = collection_prefix

        self._entities_collection = f"{collection_prefix}entities"
        self._bindings_collection = f"{collection_prefix}bindings"
        self._relationships_collection = f"{collection_prefix}relationships"

    @property
    def client(self) -> ArangoDBClient:
        """獲取 ArangoDB 客戶端"""
        if self._client is None:
            self._client = ArangoDBClient()
        return self._client

    @property
    def db(self) -> StandardDatabase:
        """獲取 ArangoDB 資料庫"""
        return self.client.db

    def load_bindings(self, system_id: str = "jp_tiptop_erp") -> Optional[BindingsContainer]:
        """
        從 ArangoDB 載入 Bindings

        Args:
            system_id: 系統 ID

        Returns:
            BindingsContainer 或 None（如果載入失敗）
        """
        try:
            logger.info(f"Loading bindings from ArangoDB: {self._bindings_collection}")

            # 查詢所有 Bindings
            query = """
            FOR doc IN @@collection
                FILTER doc.system_id == @system_id
                RETURN doc
            """

            cursor = self.db.aql.execute(
                query, bind_vars={"@collection": self._bindings_collection, "system_id": system_id}
            )

            bindings_data = {}
            datasource = {"type": "ORACLE", "dialect": "ORACLE"}

            for doc in cursor:
                concept_name = doc.get("concept_name")
                bindings_data[concept_name] = {
                    "ORACLE": {
                        "table": doc.get("table", ""),
                        "column": doc.get("column", ""),
                        "aggregation": doc.get("aggregation"),
                        "operator": doc.get("operator", "="),
                    }
                }

            logger.info(f"Loaded {len(bindings_data)} bindings from ArangoDB")

            return BindingsContainer(version="1.0", datasource=datasource, bindings=bindings_data)

        except Exception as e:
            logger.error(f"Failed to load bindings from ArangoDB: {e}")
            return None

    def load_entities(self, system_id: str = "jp_tiptop_erp") -> Optional[Dict]:
        """
        從 ArangoDB 載入 Entities

        Args:
            system_id: 系統 ID

        Returns:
            Entities 字典或 None
        """
        try:
            logger.info(f"Loading entities from ArangoDB: {self._entities_collection}")

            # 查詢所有 Entities
            query = """
            FOR doc IN @@collection
                FILTER doc.system_id == @system_id
                RETURN doc
            """

            cursor = self.db.aql.execute(
                query, bind_vars={"@collection": self._entities_collection, "system_id": system_id}
            )

            entities = {}
            for doc in cursor:
                name = doc.get("name")
                entities[name] = doc

            logger.info(f"Loaded {len(entities)} entities from ArangoDB")

            return entities

        except Exception as e:
            logger.error(f"Failed to load entities from ArangoDB: {e}")
            return None

    def load_relationships(self, system_id: str = "jp_tiptop_erp") -> Optional[list]:
        """
        從 ArangoDB 載入 Relationships

        Args:
            system_id: 系統 ID

        Returns:
            Relationships 列表或 None
        """
        try:
            logger.info(f"Loading relationships from ArangoDB: {self._relationships_collection}")

            # 查詢所有 Relationships
            query = """
            FOR doc IN @@collection
                FILTER doc.system_id == @system_id
                RETURN doc
            """

            cursor = self.db.aql.execute(
                query,
                bind_vars={"@collection": self._relationships_collection, "system_id": system_id},
            )

            relationships = list(cursor)

            logger.info(f"Loaded {len(relationships)} relationships from ArangoDB")

            return relationships

        except Exception as e:
            logger.error(f"Failed to load relationships from ArangoDB: {e}")
            return None

    def check_collections(self) -> Dict[str, bool]:
        """檢查 Collection 是否存在"""
        result = {}

        for collection in [
            self._entities_collection,
            self._bindings_collection,
            self._relationships_collection,
        ]:
            try:
                result[collection] = self.db.has_collection(collection)
            except Exception:
                result[collection] = False

        return result


def load_bindings_from_arangodb(
    client: Optional[ArangoDBClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> Optional[BindingsContainer]:
    """便捷函數：從 ArangoDB 載入 Bindings"""
    loader = ArangoDBSchemaLoader(client, collection_prefix)
    return loader.load_bindings(system_id)


def load_entities_from_arangodb(
    client: Optional[ArangoDBClient] = None,
    collection_prefix: str = "jp_",
    system_id: str = "jp_tiptop_erp",
) -> Optional[Dict]:
    """便捷函數：從 ArangoDB 載入 Entities"""
    loader = ArangoDBSchemaLoader(client, collection_prefix)
    return loader.load_entities(system_id)
