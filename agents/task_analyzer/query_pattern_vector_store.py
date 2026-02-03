# 代碼功能說明: 查詢模式向量庫服務 - 使用向量比對檢測知識庫查詢
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""查詢模式向量庫服務 - 使用向量相似度比對檢測知識庫查詢"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 知識庫查詢範例向量庫 Collection 名稱
KNOWLEDGE_QUERY_PATTERNS_COLLECTION = "knowledge_query_patterns"


class QueryPatternVectorStore:
    """查詢模式向量庫服務 - 使用向量相似度比對檢測查詢類型"""

    def __init__(self):
        """初始化查詢模式向量庫服務"""
        self._vector_store_service = None
        self._embedding_service = None
        self._initialized = False

    def _get_vector_store_service(self):
        """獲取向量存儲服務（懶加載）"""
        if self._vector_store_service is not None:
            return self._vector_store_service

        try:
            from services.api.services.qdrant_vector_store_service import (
                get_qdrant_vector_store_service,
            )

            self._vector_store_service = get_qdrant_vector_store_service()
            return self._vector_store_service
        except Exception as e:
            logger.warning(f"Failed to get vector store service: {e}")
            return None

    def _get_embedding_service(self):
        """獲取 Embedding 服務（懶加載）"""
        if self._embedding_service is not None:
            return self._embedding_service

        try:
            from services.api.services.embedding_service import get_embedding_service

            self._embedding_service = get_embedding_service()
            return self._embedding_service
        except Exception as e:
            logger.warning(f"Failed to get embedding service: {e}")
            return None

    async def initialize_patterns(self) -> bool:
        """
        初始化知識庫查詢範例數據（種子數據）

        修改時間：2026-01-28 - 建立知識庫查詢範例向量庫

        Returns:
            是否初始化成功
        """
        if self._initialized:
            return True

        vector_service = self._get_vector_store_service()
        embedding_service = self._get_embedding_service()

        if vector_service is None or embedding_service is None:
            logger.warning("Vector store or embedding service not available")
            return False

        try:
            # 知識庫查詢範例（種子數據）
            knowledge_query_patterns = [
                # 文件列表/統計查詢
                "告訴我你的知識庫有多少文件",
                "知識庫裡有哪些文件",
                "告訴我你的知識庫裡有那些文件",
                "知識庫有多少文件",
                "文件區有多少文件",
                "文件區有哪些文件",
                "列出知識庫中的文件",
                "顯示知識庫文件列表",
                "查看知識庫文件",
                "知識庫文件統計",
                "知識庫文件數量",
                # 知識檢索查詢
                "查詢知識庫中的相關內容",
                "檢索知識庫",
                "搜索知識庫",
                "查找知識庫",
                "從知識庫中查找",
                "在知識庫中搜索",
                "知識庫檢索",
                # 知識資產查詢
                "查詢知識資產",
                "列出知識資產",
                "知識資產有哪些",
                "知識資產統計",
                # 英文範例
                "how many files in knowledge base",
                "list files in knowledge base",
                "query knowledge base",
                "search knowledge base",
                "retrieve from knowledge base",
                "knowledge assets list",
                "knowledge assets query",
            ]

            # 生成向量並存儲
            embeddings = await embedding_service.generate_embedding(
                texts=knowledge_query_patterns
            )

            if not embeddings or len(embeddings) != len(knowledge_query_patterns):
                logger.error("Failed to generate embeddings for query patterns")
                return False

            # 構建文檔 chunks（用於存儲）
            chunks = []
            for i, pattern in enumerate(knowledge_query_patterns):
                chunks.append(
                    {
                        "chunk_id": f"pattern_{i}",
                        "content": pattern,
                        "metadata": {
                            "query_type": "knowledge_base",
                            "pattern_id": i,
                            "pattern": pattern,
                        },
                    }
                )

            # 存儲到 Qdrant（使用特殊的 file_id 標識）
            # 注意：這裡使用一個固定的 file_id 來標識查詢模式向量庫
            PATTERN_FILE_ID = "query_patterns_knowledge_base"

            success = vector_service.store_vectors(
                file_id=PATTERN_FILE_ID,
                chunks=chunks,
                embeddings=embeddings,
                user_id=None,  # 系統級數據
            )

            if success:
                self._initialized = True
                logger.info(
                    f"Query pattern vector store initialized: {len(knowledge_query_patterns)} patterns stored"
                )
            else:
                logger.error("Failed to store query patterns")

            return success

        except Exception as e:
            logger.error(f"Failed to initialize query patterns: {e}", exc_info=True)
            return False

    async def is_knowledge_base_query(
        self, query: str, similarity_threshold: float = 0.75
    ) -> bool:
        """
        使用向量相似度比對檢測是否為知識庫查詢

        修改時間：2026-01-28 - 使用向量比對替代關鍵字匹配

        Args:
            query: 用戶查詢文本
            similarity_threshold: 相似度閾值（0.0-1.0），默認 0.75

        Returns:
            是否為知識庫查詢
        """
        if not query:
            return False

        # 確保已初始化
        if not self._initialized:
            await self.initialize_patterns()

        vector_service = self._get_vector_store_service()
        embedding_service = self._get_embedding_service()

        if vector_service is None or embedding_service is None:
            logger.debug("Vector store or embedding service not available, falling back to keyword matching")
            # Fallback 到關鍵字匹配
            return self._fallback_keyword_match(query)

        try:
            # 生成查詢向量
            query_embeddings = await embedding_service.generate_embedding(texts=[query])
            if not query_embeddings or len(query_embeddings) == 0:
                logger.warning("Failed to generate query embedding")
                return self._fallback_keyword_match(query)

            query_embedding = query_embeddings[0]

            # 查詢相似模式
            PATTERN_FILE_ID = "query_patterns_knowledge_base"
            results = vector_service.query_vectors(
                query_embedding=query_embedding,
                file_id=PATTERN_FILE_ID,
                user_id=None,
                n_results=3,  # 只取前 3 個最相似的
            )

            if not results:
                logger.debug("No similar patterns found, falling back to keyword matching")
                return self._fallback_keyword_match(query)

            # 檢查最高相似度是否超過閾值
            max_similarity = 0.0
            for result in results:
                score = result.get("score", 0.0)
                if score > max_similarity:
                    max_similarity = score

            is_match = max_similarity >= similarity_threshold

            logger.debug(
                f"Query pattern vector match: query='{query[:50]}...', "
                f"max_similarity={max_similarity:.3f}, threshold={similarity_threshold}, "
                f"is_match={is_match}"
            )

            return is_match

        except Exception as e:
            logger.warning(
                f"Vector similarity matching failed: {e}, falling back to keyword matching"
            )
            return self._fallback_keyword_match(query)

    def _fallback_keyword_match(self, query: str) -> bool:
        """
        Fallback 關鍵字匹配（當向量比對失敗時使用）

        Args:
            query: 用戶查詢文本

        Returns:
            是否為知識庫查詢
        """
        if not query:
            return False

        query_lower = query.lower()

        # 知識庫查詢關鍵詞（簡化版）
        knowledge_keywords = [
            "知識庫",
            "知識資產",
            "文件.*有多少",
            "文件.*有哪些",
            "文件區",
            "查詢.*知識",
            "檢索.*知識",
            "knowledge.*base",
            "knowledge.*asset",
        ]

        import re

        for pattern in knowledge_keywords:
            if re.search(pattern, query_lower):
                return True

        return False


# 全局單例
_query_pattern_vector_store: Optional[QueryPatternVectorStore] = None


def get_query_pattern_vector_store() -> QueryPatternVectorStore:
    """獲取查詢模式向量庫服務實例（單例模式）"""
    global _query_pattern_vector_store
    if _query_pattern_vector_store is None:
        _query_pattern_vector_store = QueryPatternVectorStore()
    return _query_pattern_vector_store


def reset_query_pattern_vector_store() -> None:
    """重置查詢模式向量庫服務實例（用於測試）"""
    global _query_pattern_vector_store
    _query_pattern_vector_store = None
