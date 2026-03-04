# -*- coding: utf-8 -*-
"""
DA_IntentRAG - Data Agent Intent RAG 系統

產品化的意圖識別解決方案：
- 使用向量語義搜索而不是正則表達式
- 從 intents.json 動態加載意圖定義
- 支持置信度閾值配置
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IntentMatchResult:
    """意圖匹配結果"""

    intent: str
    confidence: float
    description: str
    input_filters: List[str]
    mart_table: Optional[str]
    complexity: str = "simple"  # simple / complex - 用於模型路由


# 複雜查詢關鍵詞
COMPLEX_QUERY_KEYWORDS = [
    "最大", "最多", "最少", "最低", "最高",  # Top-N
    "排序", "前", "名",  # 排序
    "佔比", "比例", "百分比",  # 佔比
    "比較", "對比", "對比",  # 比較
    "總計", "合計", "小計",  # 聚合統計
]


def detect_query_complexity(query: str) -> str:
    """根據查詢內容判斷複雜度"""
    for keyword in COMPLEX_QUERY_KEYWORDS:
        if keyword in query:
            return "complex"
    return "simple"


QV|


class DA_IntentRAG:
    """
    Data Agent Intent RAG - 產品化意圖識別
    """

    _instance: Optional["DA_IntentRAG"] = None
    _intents_loaded: bool = False

    def __init__(
        self,
        intents_file: Optional[str] = None,
        confidence_threshold: float = 0.3,
    ):
        self.confidence_threshold = confidence_threshold

        if intents_file is None:
            base_path = Path(__file__).parent.parent.parent.parent
            intents_file = str(base_path / "metadata" / "systems" / "tiptop_jp" / "intents.json")

        self.intents_file = intents_file
        self._intents: Dict[str, Dict] = {}
        self._intent_descriptions: List[str] = []
        self._intent_names: List[str] = []
        self._embedding_manager = None

    def load_intents(self) -> None:
        """從 intents.json 加載意圖定義"""
        if self._intents_loaded:
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
                description = intent_def.get("description", "")
                full_description = self._build_intent_description(intent_id, intent_def)

                self._intents[intent_id] = {
                    "description": description,
                    "full_description": full_description,
                    "input_filters": intent_def.get("input", {}).get("filters", []),
                    "output_metrics": intent_def.get("output", {}).get("metrics", []),
                    "output_dimensions": intent_def.get("output", {}).get("dimensions", []),
                    "mart_table": intent_def.get("mart_table"),
                    "constraints": intent_def.get("constraints", {}),
                }

                self._intent_names.append(intent_id)
                self._intent_descriptions.append(full_description)

            self._intents_loaded = True
            logger.info(f"Loaded {len(self._intents)} intents from {self.intents_file}")

        except Exception as e:
            logger.error(f"Failed to load intents: {e}")

    def _build_intent_description(self, intent_id: str, intent_def: Dict) -> str:
        """構建意圖的完整描述文本"""
        parts = [intent_def.get("description", "")]

        filters = intent_def.get("input", {}).get("filters", [])
        if filters:
            parts.append(f"支持筛选: {', '.join(filters)}")

        metrics = intent_def.get("output", {}).get("metrics", [])
        if metrics:
            parts.append(f"输出指标: {', '.join(metrics)}")

        dimensions = intent_def.get("output", {}).get("dimensions", [])
        if dimensions:
            parts.append(f"维度: {', '.join(dimensions)}")

        return " | ".join(parts)

    async def _get_embedding_manager(self):
        """獲取 EmbeddingManager 實例"""
        if self._embedding_manager is None:
            from .embedding_manager import EmbeddingManager

            # [FIX] 啟用 Ollama qwen3-embedding (4096維)
            config = {
                "primary": {
                    "model": "qwen3-embedding:latest",
                    "endpoint": "http://localhost:11434",
                    "timeout": 60,
                },
                "fallback": {
                    "model": "all-MiniLM-L6-v2",
                },
            }

            self._embedding_manager = EmbeddingManager(config)

        return self._embedding_manager

    async def match_intent(self, query: str) -> Optional[IntentMatchResult]:
        """使用語義搜索匹配意圖"""
        self.load_intents()

        if not self._intents:
            logger.warning("No intents loaded")
            return None

        try:
            embed_manager = await self._get_embedding_manager()

            # 生成查詢向量
            query_embedding = await embed_manager.embed(query)

            # 計算與所有意圖的相似度
            best_match = None
            best_score = 0.0

            for i, intent_name in enumerate(self._intent_names):
                intent_desc = self._intent_descriptions[i]
                intent_embedding = await embed_manager.embed(intent_desc)

                score = self._cosine_similarity(query_embedding, intent_embedding)

                if score > best_score:
                    best_score = score
                    best_match = {
                        "intent": intent_name,
                        "confidence": score,
                        "index": i,
                    }

            if best_match and best_match["confidence"] >= self.confidence_threshold:
                intent_data = self._intents[best_match["intent"]]

                return IntentMatchResult(
                    intent=best_match["intent"],
                    confidence=best_match["confidence"],
                    description=intent_data["description"],
                    input_filters=intent_data["input_filters"],
                    output_metrics=intent_data["output_metrics"],
                    output_dimensions=intent_data["output_dimensions"],
                    QT|                    complexity=detect_query_complexity(query),
                )

            return None

        except Exception as e:
            logger.error(f"Intent matching failed: {e}")
            return None

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        a = np.array(a)
        b = np.array(b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    @classmethod
    async def get_instance(cls) -> "DA_IntentRAG":
        """獲取單例實例（異步版本）"""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load_intents()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "DA_IntentRAG":
        """
        獲取單例實例（同步版本）

        技術債說明：短期方案，長期應使用異步版本
        參考: /docs/技術債/README.md
        """
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.load_intents()
        return cls._instance

    def match_intent_sync(self, query: str) -> Optional[IntentMatchResult]:
        """
        同步版本的意圖匹配（短期方案）

        技術債說明：
        - 長期方案應將調用鏈全部改為 async（參考 /docs/技術債/README.md）
        - 短期使用 ThreadPoolExecutor + 全新事件循環 避免 FastAPI 事件循環衝突
        """
        import concurrent.futures

        def _run_in_new_loop() -> Optional[IntentMatchResult]:
            """在全新的事件循環中執行異步匹配"""
            # 創建全新的事件循環，與 FastAPI 的事件循環完全隔離
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(self.match_intent(query))
            finally:
                new_loop.close()

        try:
            # 使用執行緒池 + 全新事件循環
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_in_new_loop)
                return future.result(timeout=30)

        except Exception as e:
            logger.error(f"Sync intent matching failed: {e}")
            return None
