# 代碼功能說明: DA_IntentRAG 意圖匹配（Qdrant + fallback）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

import asyncio
import concurrent.futures
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
    intent: str
    confidence: float
    description: str
    input_filters: List[str]
    mart_table: Optional[str]
    complexity: str = "simple"


COMPLEX_QUERY_KEYWORDS = [
    "最大", "最多", "最少", "最低", "最高",
    "排序", "名", "佔比", "比例", "百分比",
    "比較", "對比",
    "總計", "合計", "小計",
    "統計", "趨勢", "分析",
    "月度", "年度", "季度",
    "彙總", "匯總", "平均", "排名",
]


def detect_query_complexity(query: str) -> str:
    """根據查詢內容判斷複雜度（context-aware 「前」處理）"""
    # Context-aware check for 「前」: ranking/Top-N usage → complex
    # e.g. 前10名, 前5大, 前三個（排名意圖）
    if re.search(r'前\s*\d+\s*[名大個位]', query):
        return "complex"
    # Temporal / positional / pagination uses of 「前」→ NOT complex
    # (前天, 前月, 前年, 以前, 之前, 前幾, 最前, 前10筆 — these fall through)

    # Standard keyword check (「前」excluded from list)
    for keyword in COMPLEX_QUERY_KEYWORDS:
        if keyword in query:
            return "complex"
    return "simple"


class DA_IntentRAG:
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
        if self._intents:
            return

        try:
            intents_path = Path(self.intents_file)
            if not intents_path.exists():
                logger.warning("Intent file not found", path=self.intents_file)
                return

            with open(intents_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            intents = data.get("intents", {})
            for intent_id, intent_def in intents.items():
                self._intents[intent_id] = {
                    "description": intent_def.get("description", ""),
                    "full_description": self._build_intent_description(intent_id, intent_def),
                    "input_filters": intent_def.get("input", {}).get("filters", []),
                    "mart_table": intent_def.get("mart_table"),
                }

            logger.info(
                "DA_IntentRAG intents loaded", count=len(self._intents), path=self.intents_file
            )
        except Exception as exc:
            logger.error("Failed to load intents", error=str(exc), exc_info=True)

    def _build_intent_description(self, intent_id: str, intent_def: Dict[str, Any]) -> str:
        parts: List[str] = [intent_def.get("description", ""), f"intent:{intent_id}"]

        filters = intent_def.get("input", {}).get("filters", [])
        if filters:
            parts.append(f"支持筛选: {', '.join(filters)}")

        metrics = intent_def.get("output", {}).get("metrics", [])
        if metrics:
            parts.append(f"输出指标: {', '.join(metrics)}")

        dimensions = intent_def.get("output", {}).get("dimensions", [])
        if dimensions:
            parts.append(f"维度: {', '.join(dimensions)}")

        mart_table = intent_def.get("mart_table")
        if mart_table:
            parts.append(f"mart_table: {mart_table}")

        return " | ".join(parts)

    async def _get_embedding_manager(self) -> Any:
        if self._embedding_manager is None:
            from .embedding_manager import EmbeddingManager

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

    async def match_intent(self, nlq: str) -> Optional[IntentMatchResult]:
        self.load_intents()
        if not self._intents:
            logger.warning("No intents loaded")
            return None

        try:
            embed_manager = await self._get_embedding_manager()
            vector = await embed_manager.embed(nlq)

            if self._qdrant_available:
                try:
                    query_response = self.qdrant_client.query_points(
                        collection_name="jp_intents",
                        query=vector,
                        limit=3,
                    )
                    points = query_response.points
                    if points:
                        top = points[0]
                        score = float(top.score or 0.0)
                        payload = top.payload or {}
                        if score >= self.confidence_threshold:
                            intent_name = str(payload.get("intent_name", ""))
                            intent_data = self._intents.get(intent_name)
                            if intent_data is not None:
                                return IntentMatchResult(
                                    intent=intent_name,
                                    confidence=score,
                                    description=str(intent_data.get("description", "")),
                                    input_filters=list(intent_data.get("input_filters", [])),
                                    mart_table=intent_data.get("mart_table"),
                                    complexity=detect_query_complexity(nlq),
                                )
                            logger.warning(
                                "Top Qdrant intent not found in intents.json", intent=intent_name
                            )
                except Exception as exc:
                    self._qdrant_available = False
                    logger.warning("Qdrant query failed, switch to fallback", error=str(exc))

            return await self._fallback_match(nlq=nlq, query_vector=vector)
        except Exception as exc:
            logger.error("Intent matching failed", error=str(exc), exc_info=True)
            return None

    async def _fallback_match(
        self, nlq: str, query_vector: List[float]
    ) -> Optional[IntentMatchResult]:
        logger.warning("Qdrant unavailable, falling back to in-memory")

        try:
            await self._ensure_fallback_embeddings()
            if not self._fallback_intent_vectors:
                return None

            query_arr = np.array(query_vector, dtype=float)
            best_intent: Optional[str] = None
            best_score = 0.0

            for intent_name, intent_vec in self._fallback_intent_vectors.items():
                score = self._cosine_similarity_array(query_arr, intent_vec)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name

            if best_intent is None or best_score < self.confidence_threshold:
                return None

            intent_data = self._intents.get(best_intent)
            if intent_data is None:
                return None

            return IntentMatchResult(
                intent=best_intent,
                confidence=best_score,
                description=str(intent_data.get("description", "")),
                input_filters=list(intent_data.get("input_filters", [])),
                mart_table=intent_data.get("mart_table"),
                complexity=detect_query_complexity(nlq),
            )
        except Exception as exc:
            logger.error("Fallback intent matching failed", error=str(exc), exc_info=True)
            return None

    async def _ensure_fallback_embeddings(self) -> None:
        if self._fallback_intent_vectors:
            return

        embed_manager = await self._get_embedding_manager()
        vectors: Dict[str, np.ndarray] = {}

        for intent_name, intent_data in self._intents.items():
            description = str(intent_data.get("full_description", ""))
            vector = await embed_manager.embed(description)
            vectors[intent_name] = np.array(vector, dtype=float)

        self._fallback_intent_vectors = vectors
        logger.info("Fallback intent embeddings cached", count=len(self._fallback_intent_vectors))

    def _cosine_similarity_array(self, a: np.ndarray, b: np.ndarray) -> float:
        dot_product = float(np.dot(a, b))
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    @classmethod
    async def get_instance(cls) -> "DA_IntentRAG":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "DA_IntentRAG":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def match_intent_sync(self, query: str) -> Optional[IntentMatchResult]:
        def _run_in_new_loop() -> Optional[IntentMatchResult]:
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(self.match_intent(query))
            finally:
                new_loop.close()

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_run_in_new_loop)
                return future.result(timeout=30)
        except Exception as exc:
            logger.error("Sync intent matching failed", error=str(exc), exc_info=True)
            return None
