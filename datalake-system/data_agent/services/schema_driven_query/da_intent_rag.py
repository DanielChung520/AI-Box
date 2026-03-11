# -*- coding: utf-8 -*-
"""
代碼功能說明: DA_IntentRAG 意圖匹配與複雜度檢測
創建日期: 2026-03-11
創建人: Daniel Chung
最後修改日期: 2026-03-11
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
from qdrant_client import QdrantClient

logger = structlog.get_logger(__name__)


@dataclass
class IntentMatchResult:
    """意圖匹配結果"""

    intent: str
    confidence: float
    description: str
    input_filters: List[str]
    mart_table: Optional[str]
    complexity: str = "simple"


# 複雜查詢關鍵詞
# 注意：不包含 "前"，因為需要上下文感知判斷
COMPLEX_QUERY_KEYWORDS = [
    "最大",
    "最多",
    "最少",
    "最低",
    "最高",  # Top-N
    "排序",
    "名",  # 排序
    "佔比",
    "比例",
    "百分比",  # 佔比
    "比較",
    "對比",
    "對比",  # 比較
    "總計",
    "合計",
    "小計",  # 聚合統計
]


def detect_query_complexity(query: str) -> str:
    """
    根據查詢內容判斷複雜度 (context-aware)

    處理「前」字的上下文感知邏輯：
    1. 「前」+ 排名詞（名、大、個、位）→ complex (ranking)
        例："前10名", "前5大", "前3個料號"
    2. 「前」+ 分頁詞（筆、條、項）→ simple (pagination)
        例："前10筆", "前5條", "前3項資料"
    3. 「前」+ 時間/位置詞 → simple (temporal/positional)
        例："前天", "前月", "以前", "之前", "最前面"
    4. 其他複雜關鍵詞 → complex
    """

    # ──────────────────────────────────────────────────
    # Step 1: Context-aware 「前」字檢測
    # ──────────────────────────────────────────────────

    # 檢測「前」作為 ranking indicator
    # 例："前10名", "前5大", "前3個料號"
    if re.search(r"前\s*\d+\s*[名大個位]", query):
        return "complex"

    # 檢測「前」作為 pagination indicator（不復雜）
    # 例："前10筆", "前5條", "前3項"
    if re.search(r"前\s*\d+\s*[筆條項]", query):
        return "simple"

    # 檢測「前」作為 temporal/positional indicator（不復雜）
    # 例："前天", "前月", "以前", "之前", "最前面", "前幾天"
    if re.search(r"前[天月年週]|以前|之前|前幾", query):
        return "simple"

    # ──────────────────────────────────────────────────
    # Step 2: 檢測其他複雜關鍵詞
    # ──────────────────────────────────────────────────

    for keyword in COMPLEX_QUERY_KEYWORDS:
        if keyword in query:
            return "complex"

    return "simple"


class DA_IntentRAG:
    """Data Agent Intent RAG - Schema-Driven Query 意圖匹配"""

    _instance: Optional["DA_IntentRAG"] = None

    def __init__(
        self,
        intents_file: Optional[str] = None,
        confidence_threshold: float = 0.3,
    ) -> None:
        self.confidence_threshold = confidence_threshold

        if intents_file is None:
            base_path = Path(__file__).parent.parent.parent.parent
            intents_file = str(base_path / "metadata" / "systems" / "tiptop_jp" / "intents.json")

        self.intents_file = intents_file
        self._intents: Dict[str, Dict[str, Any]] = {}
        self._embedding_manager: Optional[Any] = None
        self._fallback_intent_vectors: Dict[str, np.ndarray] = {}

        self.qdrant_client = QdrantClient(host="localhost", port=6333)
        self._qdrant_available = False
        try:
            self.qdrant_client.get_collection(collection_name="jp_intents")
            self._qdrant_available = True
            logger.info("DA_IntentRAG Qdrant ready", collection="jp_intents")
        except Exception as exc:
            self._qdrant_available = False
            logger.warning("DA_IntentRAG Qdrant unavailable at init", error=str(exc))

        self.load_intents()

    def load_intents(self) -> None:
        """從 intents.json 加載意圖定義"""
        if self._intents:
            return

        try:
            intents_path = Path(self.intents_file)
            if not intents_path.exists():
                logger.warning(f"Intent file not found: {self.intents_file}")
                return

            with open(intents_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            intents = data.get("intents", {})

            for intent_id, intent_def in intents.items():
                self._intents[intent_id] = {
                    "description": intent_def.get("description", ""),
                    "input_filters": intent_def.get("input_filters", []),
                    "mart_table": intent_def.get("mart_table"),
                    "complexity": intent_def.get("complexity", "simple"),
                }

            logger.info(f"Loaded {len(self._intents)} intents from {self.intents_file}")

        except Exception as e:
            logger.error(f"Failed to load intents: {e}", exc_info=True)

    async def match_intent(
        self, query: str, user_id: Optional[str] = None
    ) -> Optional[IntentMatchResult]:
        """匹配意圖"""
        self.load_intents()

        if not self._intents:
            logger.warning("No intents loaded")
            return None

        # 這是簡化版本，實際應使用 embedding 進行語義搜索
        return None
