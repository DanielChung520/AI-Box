# Schema Loader 主模組
# 代碼功能說明: Schema Loader 主模組
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

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

    支援多來源載入
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
        """載入 Concepts"""
        from ..config import get_config

        config = self.config or get_config()

        # 使用本地文件（暫時禁用 Qdrant）
        logger.info("Loading concepts from file...")
        data = self.file_loader.load_concepts()
        return ConceptsContainer(**data)

    def load_intents(self) -> IntentsContainer:
        """載入 Intents"""
        from ..config import get_config

        config = self.config or get_config()

        # 使用本地文件（暫時禁用 Qdrant）
        logger.info("Loading intents from file...")
        data = self.file_loader.load_intents()
        return IntentsContainer(**data)

    def load_bindings(self) -> BindingsContainer:
        """載入 Bindings"""
        from ..config import get_config

        config = self.config or get_config()

        # 使用本地文件（暫時禁用 ArangoDB）
        logger.info("Loading bindings from file...")
        data = self.file_loader.load_bindings()
        return BindingsContainer(**data)


def get_schema_loader(config: Optional[SchemaDrivenQueryConfig] = None) -> SchemaLoader:
    """獲取 Schema Loader"""
    return SchemaLoader(config)
