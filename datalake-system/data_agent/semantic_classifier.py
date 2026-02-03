# 代碼功能說明: 語義分類器 - 使用 Ollama Embedding 模型
# 創建日期: 2026-01-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""語義分類器 - 使用 Ollama Embedding 模型進行快速語義分類"""

import json
import logging
import math
from typing import Dict, List, Optional

import numpy as np
import requests

from .semantic_scenarios import SEMANTIC_SCENARIOS, HANDLING_TYPES, QUERY_TYPES

logger = logging.getLogger(__name__)


class SemanticClassifier:
    """語義分類器 - 使用 Ollama Embedding 模型"""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen3-embedding:latest",
        similarity_threshold: float = 0.7,
    ):
        """
        初始化語義分類器

        Args:
            ollama_url: Ollama 服務 URL
            model_name: Embedding 模型名稱
            similarity_threshold: 相似度閾值（低於此閾值視為不匹配）
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self._logger = logger
        self.scenarios = SEMANTIC_SCENARIOS
        self.scenario_embeddings = self._compute_embeddings()

        self._logger.info(
            f"語義分類器初始化：model={model_name}, scenarios={len(self.scenarios)}, "
            f"similarity_threshold={similarity_threshold}"
        )

    def _compute_embeddings(self) -> List[List[float]]:
        """預先計算場景 embeddings"""
        embeddings = []

        for scenario in self.scenarios:
            natural_language = scenario.get("natural_language", "")
            embedding = self._get_embedding(natural_language)

            if embedding:
                embeddings.append(embedding)
            else:
                # 如果 embedding 失敗，使用零向量
                embeddings.append([0.0] * 4096)

        self._logger.info(f"預先計算 {len(embeddings)} 個場景 embeddings")
        return embeddings

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        使用 Ollama API 獲取文本 embedding

        Args:
            text: 輸入文本

        Returns:
            Embedding 向量（4096 維度）
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding", [])
                return embedding
            else:
                self._logger.warning(f"Ollama API 請求失敗: status_code={response.status_code}")
                return None

        except Exception as e:
            self._logger.error(f"獲取 embedding 失敗: {e}", exc_info=True)
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        計算餘弦相似度

        Args:
            vec1: 向量 1
            vec2: 向量 2

        Returns:
            相似度（-1 到 1）
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def classify_query(self, natural_language: str) -> Dict[str, any]:
        """
        分類查詢並返回處置方式

        Args:
            natural_language: 自然語言查詢

        Returns:
            分類結果字典
        """
        # 獲取查詢 embedding
        query_embedding = self._get_embedding(natural_language)

        if not query_embedding:
            # 如果 embedding 失敗，返回默認分類
            self._logger.warning(f"無法獲取查詢 embedding，使用默認分類")
            return {
                "query_type": "語義不清楚",
                "handling": "回問",
                "reason": "無法進行語義分類，請重新輸入",
                "similarity": 0.0,
                "similar_scenario": None,
                "matched": False,
            }

        # 計算與所有場景的相似度
        similarities = []
        for i, scenario in enumerate(self.scenarios):
            scenario_embedding = self.scenario_embeddings[i]
            similarity = self._cosine_similarity(query_embedding, scenario_embedding)
            similarities.append((i, similarity))

        # 找到最相似的場景
        best_match_idx, best_similarity = max(similarities, key=lambda x: x[1])
        best_match = self.scenarios[best_match_idx]

        # 判斷是否匹配
        matched = best_similarity >= self.similarity_threshold

        # 如果不匹配，返回默認分類
        if not matched:
            self._logger.warning(
                f"查詢與場景相似度過低: similarity={best_similarity:.3f}, "
                f"threshold={self.similarity_threshold}"
            )
            return {
                "query_type": "語義不清楚",
                "handling": "回問",
                "reason": f"查詢語義不清楚，請重新輸入（相似度: {best_similarity:.3f}）",
                "similarity": best_similarity,
                "similar_scenario": best_match,
                "matched": False,
            }

        # 返回分類結果
        self._logger.info(
            f"查詢分類：type={best_match.get('query_type')}, "
            f"handling={best_match.get('handling')}, "
            f"similarity={best_similarity:.3f}"
        )

        return {
            "query_type": best_match.get("query_type", "語義不清楚"),
            "handling": best_match.get("handling", "執行"),
            "reason": best_match.get("reason", ""),
            "similarity": best_similarity,
            "similar_scenario": best_match,
            "matched": True,
        }

    def batch_classify(self, natural_languages: List[str]) -> List[Dict[str, any]]:
        """
        批量分類查詢

        Args:
            natural_languages: 自然語言查詢列表

        Returns:
            分類結果列表
        """
        results = []

        for nl in natural_languages:
            result = self.classify_query(nl)
            results.append(result)

        return results
