# -*- coding: utf-8 -*-
# 代碼功能說明: Embedding 管理器 — 提供語義匹配能力，使用 Ollama qwen3-embedding (4096 dim)，失敗時重試
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""
Embedding 管理器

職責：
- 提供語義匹配能力
- 使用本地 Ollama qwen3-embedding (4096 dim)
- 失敗時自動重試（最多 3 次，帶指數退避）

使用方式：
    from dt_agent.src.core.embedding_manager import EmbeddingManager

    manager = EmbeddingManager()
    results = await manager.find_similar(
        query="工站 WC77 生產什麼料號",
        candidates={"WORKSTATION": "工作站、工作中心、工站、機台"},
        top_k=3
    )
"""

import asyncio

import httpx
import numpy as np
import structlog
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from abc import ABC, abstractmethod

logger = structlog.get_logger(__name__)


class Embedder(ABC):
    """Embedding 抽象介面"""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        pass

    @abstractmethod
    async def similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        pass


class OllamaEmbedder(Embedder):
    """Ollama Embedding 實作（帶重試機制）"""

    def __init__(
        self,
        model: str = "qwen3-embedding:latest",
        endpoint: str = "http://localhost:11434",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries

    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量（失敗時重試，指數退避）"""
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.endpoint}/api/embeddings",
                        json={
                            "model": self.model,
                            "prompt": text,
                        },
                    )
                    response.raise_for_status()
                    return response.json()["embedding"]
            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "Ollama embedding 失敗，準備重試",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    wait_seconds=wait_time,
                    error=str(e),
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
        raise RuntimeError(
            f"Ollama embedding 失敗（已重試 {self.max_retries} 次）: {last_error}"
        )

    async def similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))

class EmbeddingCache:
    """嵌入向量快取"""

    def __init__(self, cache_dir: str = ".embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._memory_cache: Dict[str, np.ndarray] = {}

    def _get_cache_path(self, text: str) -> Path:
        """生成快取檔案路徑"""
        text_hash = hash(text) % 1000000
        return self.cache_dir / f"{text_hash}.npy"

    def get(self, text: str) -> Optional[np.ndarray]:
        """從快取獲取"""
        # 記憶體快取
        text_hash = hash(text) % 1000000
        if text_hash in self._memory_cache:
            return self._memory_cache[text_hash]

        # 磁碟快取
        cache_path = self._get_cache_path(text)
        if cache_path.exists():
            embedding = np.load(cache_path)
            self._memory_cache[text_hash] = embedding
            return embedding

        return None

    def set(self, text: str, embedding: np.ndarray):
        """存入快取"""
        text_hash = hash(text) % 1000000
        self._memory_cache[text_hash] = embedding

        cache_path = self._get_cache_path(text)
        np.save(cache_path, embedding)


class EmbeddingManager:
    """Embedding 管理器（使用 Ollama qwen3-embedding，失敗重試）"""

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, cache_dir: str = ".embedding_cache"
    ):
        self.config = config or {}
        self.embedder: Optional[Embedder] = None
        self.cache = EmbeddingCache(cache_dir)
        self._initialized = False
        self._embedding_dim: Optional[int] = None  # 追蹤 embedding 維度

    async def initialize(self):
        """初始化 Ollama embedder"""
        if self._initialized:
            return

        ollama_config = self.config.get("primary", {})
        self.embedder = OllamaEmbedder(
            model=ollama_config.get("model", "qwen3-embedding:latest"),
            endpoint=ollama_config.get("endpoint", "http://localhost:11434"),
            timeout=ollama_config.get("timeout", 60),
            max_retries=ollama_config.get("max_retries", 3),
        )

        # 驗證連接
        try:
            await self.embedder.embed("test")
            logger.info("Embedding: Ollama qwen3-embedding 已就緒")
        except Exception as e:
            self.embedder = None
            raise RuntimeError(f"Ollama embedding 不可用: {e}") from e

        self._initialized = True

    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量（委派給 OllamaEmbedder，內建重試）"""
        await self.initialize()

        if self.embedder is None:
            raise RuntimeError("沒有可用的 Embedder")

        embedding = await self.embedder.embed(text)

        # 驗證維度一致性
        if self._embedding_dim is None:
            self._embedding_dim = len(embedding)
            logger.info("Embedding 維度已設定", dim=self._embedding_dim)
        elif len(embedding) != self._embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self._embedding_dim}, got {len(embedding)}"
            )

        return embedding

    async def find_similar(
        self, query: str, candidates: Dict[str, str], top_k: int = 3, threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        找到最相似的候選項目

        Args:
            query: 查詢文本
            candidates: {id: 描述文本}
            top_k: 返回前 k 個結果
            threshold: 相似度閾值

        Returns:
            [(id, similarity_score), ...]
        """
        await self.initialize()

        # 生成查詢嵌入
        query_emb = await self.embed(query)

        # 計算所有候選項目的相似度
        results = []
        for item_id, description in candidates.items():
            try:
                doc_emb = await self.embed(description)
                sim = await self.embedder.similarity(query_emb, doc_emb)
                if sim >= threshold:
                    results.append((item_id, float(sim)))
            except Exception as e:
                logger.warning("計算相似度失敗", item_id=item_id, error=str(e))
                continue

        # 排序並返回 top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入"""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings

    async def batch_similar(
        self, query: str, candidates_list: List[Dict[str, str]], threshold: float = 0.7
    ) -> List[List[Tuple[str, float]]]:
        """批量相似度查詢"""
        results = []
        for candidates in candidates_list:
            similar = await self.find_similar(query, candidates, top_k=3, threshold=threshold)
            results.append(similar)
        return results
