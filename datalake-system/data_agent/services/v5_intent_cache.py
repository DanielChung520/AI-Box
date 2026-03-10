# -*- coding: utf-8 -*-
# 代碼功能說明: V5 意圖分類快取 — 預計算所有 intent embeddings 避免每次請求重複計算
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10
"""
CachedIntentMatcher — 快取所有 intent embedding 的意圖匹配器

DA_IntentRAG.match_intent() 每次呼叫會對 16 個 intent 各做一次 embedding（共 16+1 次 Ollama 呼叫）。
本模組預先計算並快取所有 intent 的 embedding，後續匹配只需 1 次 Ollama 呼叫（query embedding）
再以 numpy cosine similarity 在本地比對，大幅減少 Ollama 延遲。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# ──────────────────────────────────────────────────
# 從 da_intent_rag.py 匯入（該檔案目前有語法錯誤，故用 try/except 並附本地備份定義）
# ──────────────────────────────────────────────────
try:
    from data_agent.services.schema_driven_query.da_intent_rag import (
        IntentMatchResult,
        detect_query_complexity,
    )
except (SyntaxError, ImportError):
    from dataclasses import dataclass

    logger.warning(
        "無法從 da_intent_rag 匯入，使用本地相容定義",
        reason="da_intent_rag.py 存在語法錯誤",
    )

    @dataclass
    class IntentMatchResult:  # type: ignore[no-redef]
        """意圖匹配結果（相容備份）"""

        intent: str
        confidence: float
        description: str
        input_filters: List[str]
        mart_table: Optional[str]
        complexity: str = "simple"

    COMPLEX_QUERY_KEYWORDS = [
        "最大",
        "最多",
        "最少",
        "最低",
        "最高",
        "排序",
        "前",
        "名",
        "佔比",
        "比例",
        "百分比",
        "比較",
        "對比",
        "總計",
        "合計",
        "小計",
    ]

    def detect_query_complexity(query: str) -> str:  # type: ignore[no-redef]
        """根據查詢內容判斷複雜度"""
        for keyword in COMPLEX_QUERY_KEYWORDS:
            if keyword in query:
                return "complex"
        return "simple"


class CachedIntentMatcher:
    """
    快取版意圖匹配器

    首次呼叫 match_intent() 時：
      1. 從 intents.json 載入所有 16 個意圖定義
      2. 使用 EmbeddingManager 批次計算所有 intent 的 embedding 並快取
    後續呼叫：
      1. 僅計算 query 的 embedding（1 次 Ollama 呼叫）
      2. 使用 numpy cosine similarity 在本地比對

    效能提升：16+1 次 Ollama 呼叫 → 1 次 Ollama 呼叫
    """

    def __init__(
        self,
        intents_file: Optional[str] = None,
        confidence_threshold: float = 0.3,
    ) -> None:
        self.confidence_threshold = confidence_threshold

        if intents_file is None:
            base_path = Path(__file__).parent.parent.parent
            intents_file = str(base_path / "metadata" / "systems" / "tiptop_jp" / "intents.json")

        self.intents_file = intents_file

        # 意圖定義（由 _load_intents 填充）
        self._intents: Dict[str, Dict] = {}
        self._intent_names: List[str] = []
        self._intent_descriptions: List[str] = []
        self._intents_loaded: bool = False

        # embedding 快取（lazy init）
        self._intent_embeddings_cache: Optional[Dict[str, np.ndarray]] = None
        self._embedding_manager = None

    # ─── 意圖載入 ───────────────────────────────────

    def _load_intents(self) -> None:
        """從 intents.json 載入意圖定義（複用 DA_IntentRAG 相同邏輯）"""
        if self._intents_loaded:
            return

        try:
            intents_path = Path(self.intents_file)
            if not intents_path.exists():
                logger.warning("Intent 檔案不存在", path=self.intents_file)
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
                    "mart_table": intent_def.get("mart_table"),
                }

                self._intent_names.append(intent_id)
                self._intent_descriptions.append(full_description)

            self._intents_loaded = True
            logger.info(
                "已載入意圖定義",
                intent_count=len(self._intents),
                file=self.intents_file,
            )

        except Exception as e:
            logger.error("載入意圖定義失敗", error=str(e), exc_info=True)

    @staticmethod
    def _build_intent_description(intent_id: str, intent_def: Dict) -> str:
        """構建意圖的完整描述文本（與 DA_IntentRAG 相同邏輯）"""
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

    # ─── Embedding Manager ──────────────────────────

    async def _get_embedding_manager(self):
        """獲取 EmbeddingManager 實例（與 DA_IntentRAG 相同配置）"""
        if self._embedding_manager is None:
            from data_agent.services.schema_driven_query.embedding_manager import (
                EmbeddingManager,
            )

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

    # ─── 快取初始化 ─────────────────────────────────

    async def _ensure_cache(self) -> None:
        """確保 intent embeddings 已快取（lazy init）"""
        if self._intent_embeddings_cache is not None:
            return

        self._load_intents()

        if not self._intents:
            logger.warning("沒有可快取的意圖定義")
            return

        logger.info("開始預計算 intent embeddings", intent_count=len(self._intents))

        try:
            embed_manager = await self._get_embedding_manager()
            cache: Dict[str, np.ndarray] = {}

            for i, intent_name in enumerate(self._intent_names):
                desc = self._intent_descriptions[i]
                embedding = await embed_manager.embed(desc)
                cache[intent_name] = np.array(embedding, dtype=np.float32)

            self._intent_embeddings_cache = cache
            logger.info(
                "Intent embeddings 快取完成",
                cached_count=len(cache),
                vector_dim=next(iter(cache.values())).shape[0] if cache else 0,
            )

        except Exception as e:
            logger.error("預計算 intent embeddings 失敗", error=str(e), exc_info=True)
            # 不設置快取，下次呼叫會重試
            self._intent_embeddings_cache = None

    # ─── 核心匹配 ───────────────────────────────────

    async def match_intent(self, nlq: str) -> IntentMatchResult:
        """
        使用快取的 intent embeddings 進行語義匹配

        只需 1 次 Ollama 呼叫（embed query），其餘為本地 numpy 計算。

        Args:
            nlq: 自然語言查詢

        Returns:
            IntentMatchResult — 匹配結果（若無匹配則 confidence=0.0, intent="UNKNOWN"）
        """
        # 確保快取已建立
        try:
            await self._ensure_cache()
        except Exception as e:
            logger.error("快取初始化失敗", error=str(e))
            return self._unknown_result(nlq)

        if not self._intent_embeddings_cache:
            logger.warning("Intent embeddings 快取為空，無法匹配")
            return self._unknown_result(nlq)

        try:
            # 1 次 Ollama 呼叫：embed query
            embed_manager = await self._get_embedding_manager()
            query_embedding = np.array(await embed_manager.embed(nlq), dtype=np.float32)

            # 本地 cosine similarity 計算
            best_intent: Optional[str] = None
            best_score: float = 0.0

            for intent_name, intent_vec in self._intent_embeddings_cache.items():
                score = self._cosine_similarity(query_embedding, intent_vec)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name

            # 閾值檢查
            if best_intent is not None and best_score >= self.confidence_threshold:
                intent_data = self._intents[best_intent]
                return IntentMatchResult(
                    intent=best_intent,
                    confidence=float(best_score),
                    description=intent_data["description"],
                    input_filters=intent_data["input_filters"],
                    mart_table=intent_data.get("mart_table"),
                    complexity=detect_query_complexity(nlq),
                )

            logger.info(
                "未找到匹配意圖",
                nlq=nlq,
                best_intent=best_intent,
                best_score=f"{best_score:.3f}",
                threshold=self.confidence_threshold,
            )
            return self._unknown_result(nlq)

        except Exception as e:
            logger.error("Intent 匹配失敗", error=str(e), nlq=nlq, exc_info=True)
            return self._unknown_result(nlq)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """計算餘弦相似度"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    @staticmethod
    def _unknown_result(nlq: str) -> IntentMatchResult:
        """產生未知意圖結果（graceful degradation）"""
        return IntentMatchResult(
            intent="UNKNOWN",
            confidence=0.0,
            description="",
            input_filters=[],
            mart_table=None,
            complexity=detect_query_complexity(nlq),
        )


# ──────────────────────────────────────────────────
# Singleton Factory
# ──────────────────────────────────────────────────

_singleton: Optional[CachedIntentMatcher] = None


def get_cached_intent_matcher() -> CachedIntentMatcher:
    """取得 CachedIntentMatcher 單例"""
    global _singleton  # noqa: PLW0603
    if _singleton is None:
        _singleton = CachedIntentMatcher()
    return _singleton
