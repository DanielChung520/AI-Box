# Schema Loader 主模組
# 代碼功能說明: Schema Loader 主模組
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 修改日期: 2026-02-13

"""Schema Loader 主模組

載入策略：
1. Qdrant (Concepts/Intents 首選)
2. ArangoDB (Bindings 首選)
3. 本地文件 (Fallback)
"""

import logging
from typing import Optional

from ..config import SchemaDrivenQueryConfig
from ..models import ConceptsContainer, IntentsContainer, BindingsContainer
from .file_loader import SchemaFileLoader

logger = logging.getLogger(__name__)


class SchemaLoader:
    """
    Schema 載入器

    支援多來源載入：
    - Qdrant: Concepts / Intents
    - ArangoDB: Bindings
    - 本地文件: Fallback
    """

    def __init__(self, config: Optional[SchemaDrivenQueryConfig] = None):
        self.config = config
        self._file_loader: Optional[SchemaFileLoader] = None
        self._qdrant_loader = None
        self._arangodb_loader = None

    @property
    def file_loader(self) -> SchemaFileLoader:
        """獲取文件載入器"""
        if self._file_loader is None:
            from ..config import get_config

            config = self.config or get_config()
            self._file_loader = SchemaFileLoader(
                metadata_path=str(config.metadata_path), system_id=config.system_id
            )
        return self._file_loader

    def _get_qdrant_loader(self):
        """獲取 Qdrant 載入器"""
        if self._qdrant_loader is None:
            from ..config import get_config

            config = self.config or get_config()
            from .qdrant_loader import QdrantSchemaLoader

            self._qdrant_loader = QdrantSchemaLoader(
                collection_prefix=config.qdrant.collection_prefix
            )
        return self._qdrant_loader

    def _get_arangodb_loader(self):
        """獲取 ArangoDB 載入器"""
        if self._arangodb_loader is None:
            from ..config import get_config

            config = self.config or get_config()
            from .arangodb_loader import ArangoDBSchemaLoader

            self._arangodb_loader = ArangoDBSchemaLoader(
                collection_prefix=config.arangodb.collection_prefix
            )
        return self._arangodb_loader

    def load_concepts(self) -> ConceptsContainer:
        """載入 Concepts

        策略：
        1. 優先從 Qdrant 載入
        2. Fallback 到本地文件
        """
        from ..config import get_config

        config = self.config or get_config()

        if config.qdrant.use_qdrant:
            logger.info("Loading concepts from Qdrant...")
            try:
                qdrant_data = self._get_qdrant_loader().load_concepts()
                if qdrant_data:
                    logger.info(f"Loaded {len(qdrant_data.concepts)} concepts from Qdrant")
                    return qdrant_data
            except Exception as e:
                logger.warning(f"Failed to load concepts from Qdrant: {e}")

        logger.info("Loading concepts from file (fallback)...")
        data = self.file_loader.load_concepts()
        return ConceptsContainer(**data)

    def load_intents(self) -> IntentsContainer:
        """載入 Intents

        策略：
        1. 優先從 Qdrant 載入
        2. Fallback 到本地文件
        """
        from ..config import get_config

        config = self.config or get_config()

        if config.qdrant.use_qdrant:
            logger.info("Loading intents from Qdrant...")
            try:
                qdrant_data = self._get_qdrant_loader().load_intents()
                if qdrant_data:
                    logger.info(f"Loaded {len(qdrant_data.intents)} intents from Qdrant")
                    return qdrant_data
            except Exception as e:
                logger.warning(f"Failed to load intents from Qdrant: {e}")

        logger.info("Loading intents from file (fallback)...")
        data = self.file_loader.load_intents()
        return IntentsContainer(**data)

    def load_bindings(self) -> BindingsContainer:
        """載入 Bindings

        策略：
        1. 優先從 ArangoDB 載入
        2. Fallback 到本地文件
        """
        from ..config import get_config

        config = self.config or get_config()

        if config.arangodb.use_arangodb:
            logger.info("Loading bindings from ArangoDB...")
            try:
                arango_data = self._get_arangodb_loader().load_bindings()
                if arango_data and arango_data.bindings:
                    logger.info(f"Loaded {len(arango_data.bindings)} bindings from ArangoDB")
                    return arango_data
                elif arango_data:
                    logger.warning(
                        f"ArangoDB returned empty bindings ({len(arango_data.bindings)}), falling back to file"
                    )
            except Exception as e:
                logger.warning(f"Failed to load bindings from ArangoDB: {e}")

        logger.info("Loading bindings from file (fallback)...")
        data = self.file_loader.load_bindings()
        return BindingsContainer(**data)


def get_schema_loader(config: Optional[SchemaDrivenQueryConfig] = None) -> SchemaLoader:
    """獲取 Schema Loader"""
    return SchemaLoader(config)
