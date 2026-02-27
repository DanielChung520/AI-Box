# -*- coding: utf-8 -*-
"""
Embedding 管理器

職責：
- 提供語義匹配能力
- 優先使用本地 Ollama qwen3-embedding
- Fallback 到 Sentence-Transformers

使用方式：
    from embedding_manager import EmbeddingManager

    manager = EmbeddingManager()
    results = await manager.find_similar(
        query="工站 WC77 生產什麼料號",
        candidates={"WORKSTATION": "工作站、工作中心、工站、機台"},
        top_k=3
    )
"""

import httpx
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


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
    """Ollama Embedding 實作"""

    def __init__(
        self,
        model: str = "qwen3-embedding:latest",
        endpoint: str = "http://localhost:11434",
        timeout: int = 60,
    ):
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        try:
            response = await self.client.post(
                f"{self.endpoint}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise

    async def similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class SentenceTransformerEmbedder(Embedder):
    """Sentence-Transformers Fallback"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)
            logger.info(f"Sentence-Transformers loaded: {model_name}")
        except ImportError as e:
            logger.error(f"Sentence-Transformers not installed: {e}")
            raise ImportError("Please install: pip install sentence-transformers")

    async def embed(self, text: str) -> List[float]:
        """同步生成嵌入"""
        embedding = self.model.encode([text])[0]
        return embedding.tolist()

    async def similarity(self, a: List[float], b: List[float]) -> float:
        """計算餘弦相似度"""
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


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
    """Embedding 管理器（智能選擇）"""

    def __init__(
        self, config: Optional[Dict[str, Any]] = None, cache_dir: str = ".embedding_cache"
    ):
        self.config = config or {}
        self.primary: Optional[Embedder] = None
        self.fallback: Optional[Embedder] = None
        self.cache = EmbeddingCache(cache_dir)
        self._initialized = False

    async def initialize(self):
        """初始化（智能選擇最優 embedder）"""
        if self._initialized:
            return

        # 嘗試 Ollama
        ollama_config = self.config.get("primary", {})
        try:
            self.primary = OllamaEmbedder(
                model=ollama_config.get("model", "qwen3-embedding:latest"),
                endpoint=ollama_config.get("endpoint", "http://localhost:11434"),
                timeout=ollama_config.get("timeout", 60),
            )
            await self.primary.embed("test")
            logger.info("Embedding: 使用 Ollama qwen3-embedding:latest")
        except Exception as e:
            logger.warning(f"Ollama 不可用: {e}")
            self.primary = None

        # Fallback 準備
        fallback_config = self.config.get("fallback", {})
        try:
            model_name = fallback_config.get("model", "all-MiniLM-L6-v2")
            self.fallback = SentenceTransformerEmbedder(model_name)
            logger.info(f"Embedding: Sentence-Transformers {model_name} 已就緒")
        except Exception as e:
            logger.warning(f"Sentence-Transformers 不可用: {e}")
            self.fallback = None

        if not self.primary and not self.fallback:
            raise RuntimeError("沒有可用的 Embedding 方案!")

        self._initialized = True

    async def embed(self, text: str) -> List[float]:
        """生成嵌入（智能選擇）"""
        await self.initialize()

        # 檢查快取
        cached = self.cache.get(text)
        if cached is not None:
            return cached.tolist()

        # 優先使用 Ollama
        if self.primary:
            try:
                embedding = await self.primary.embed(text)
                self.cache.set(text, np.array(embedding))
                return embedding
            except Exception as e:
                logger.warning(f"Ollama embedding failed: {e}")

        # Fallback 到 Sentence-Transformers
        if self.fallback:
            embedding = await self.fallback.embed(text)
            self.cache.set(text, np.array(embedding))
            return embedding

        raise RuntimeError("無法生成 embedding")

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
                if self.primary:
                    sim = await self.primary.similarity(query_emb, doc_emb)
                else:
                    sim = await self.fallback.similarity(query_emb, doc_emb)

                if sim >= threshold:
                    results.append((item_id, float(sim)))
            except Exception as e:
                logger.warning(f"計算相似度失敗 {item_id}: {e}")
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
