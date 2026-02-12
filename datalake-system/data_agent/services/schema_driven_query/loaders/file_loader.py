# 代碼功能說明: 文件載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""文件載入器

從本地文件載入 Schema 定義
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .concepts_loader import load_concepts_from_file
from .intents_loader import load_intents_from_file
from .bindings_loader import load_bindings_from_file
from .schema_loader import load_schema_from_file

logger = logging.getLogger(__name__)


class SchemaFileLoader:
    """
    Schema 文件載入器

    從本地 JSON/YAML 文件載入 Schema 定義
    """

    def __init__(self, metadata_path: str, system_id: str = "jp_tiptop_erp"):
        self.metadata_path = Path(metadata_path)
        self.system_id = system_id

    @property
    def concepts_path(self) -> Path:
        """Concepts 文件路徑"""
        return self.metadata_path / "systems" / self.system_id / "concepts.json"

    @property
    def intents_path(self) -> Path:
        """Intents 文件路徑"""
        return self.metadata_path / "systems" / self.system_id / "intents.json"

    @property
    def bindings_path(self) -> Path:
        """Bindings 文件路徑"""
        return self.metadata_path / "systems" / self.system_id / "bindings.json"

    @property
    def schema_path(self) -> Path:
        """Schema YAML 文件路徑"""
        return self.metadata_path / "systems" / self.system_id / f"{self.system_id}.yml"

    def load_concepts(self) -> Dict[str, Any]:
        """載入 Concepts"""
        if not self.concepts_path.exists():
            logger.warning(f"Concepts file not found: {self.concepts_path}")
            return {}

        with open(self.concepts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return load_concepts_from_file(data)

    def load_intents(self) -> Dict[str, Any]:
        """載入 Intents"""
        if not self.intents_path.exists():
            logger.warning(f"Intents file not found: {self.intents_path}")
            return {}

        with open(self.intents_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return load_intents_from_file(data)

    def load_bindings(self) -> Dict[str, Any]:
        """載入 Bindings"""
        if not self.bindings_path.exists():
            logger.warning(f"Bindings file not found: {self.bindings_path}")
            return {}

        with open(self.bindings_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return load_bindings_from_file(data)

    def load_schema(self) -> Dict[str, Any]:
        """載入 Schema"""
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found: {self.schema_path}")
            return {}

        return load_schema_from_file(self.schema_path)

    def load_all(self) -> Dict[str, Any]:
        """載入所有 Schema"""
        return {
            "concepts": self.load_concepts(),
            "intents": self.load_intents(),
            "bindings": self.load_bindings(),
            "schema": self.load_schema(),
        }
