# 代碼功能說明: Retrieval Manager 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Retrieval Manager - 實現 Hybrid RAG 檢索管理"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

from database.chromadb.client import ChromaDBClient

logger = logging.getLogger(__name__)

# AAM 整合（可選）
try:
    from genai.workflows.rag.hybrid_rag import HybridRAGService
    from agent_process.memory.aam.aam_core import AAMManager

    AAM_AVAILABLE = True
except ImportError:
    AAM_AVAILABLE = False
    HybridRAGService = None  # type: ignore[assignment, misc]
    AAMManager = None  # type: ignore[assignment, misc]


class RetrievalStrategy(str, Enum):
    """檢索策略枚舉"""

    VECTOR_ONLY = "vector_only"  # 僅向量檢索
    KEYWORD_ONLY = "keyword_only"  # 僅關鍵詞檢索
    HYBRID = "hybrid"  # 混合檢索


class RetrievalManager:
    """檢索管理器 - 實現 Hybrid RAG"""

    def __init__(
        self,
        chromadb_client: Optional[ChromaDBClient] = None,
        default_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        aam_hybrid_rag: Optional[Any] = None,  # HybridRAGService
    ):
        """
        初始化檢索管理器

        Args:
            chromadb_client: ChromaDB 客戶端
            default_strategy: 默認檢索策略
            aam_hybrid_rag: AAM 混合 RAG 服務（可選）
        """
        self.chromadb_client = chromadb_client
        self.default_strategy = default_strategy
        self.aam_hybrid_rag = aam_hybrid_rag

    def retrieve(
        self,
        query: str,
        collection_name: str = "documents",
        n_results: int = 5,
        strategy: Optional[RetrievalStrategy] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        檢索相關文檔

        Args:
            query: 查詢文本
            collection_name: 集合名稱
            n_results: 返回結果數量
            strategy: 檢索策略
            filters: 過濾條件

        Returns:
            檢索結果列表
        """
        strategy = strategy or self.default_strategy

        logger.info(f"Retrieving documents with strategy: {strategy.value}")

        # 如果啟用了 AAM 混合 RAG，優先使用它
        if self.aam_hybrid_rag is not None and AAM_AVAILABLE:
            try:
                aam_results = self.aam_hybrid_rag.retrieve(query, top_k=n_results)
                if aam_results:
                    logger.debug(f"AAM Hybrid RAG returned {len(aam_results)} results")
                    return aam_results
            except Exception as e:
                logger.warning(
                    f"AAM Hybrid RAG failed, falling back to standard retrieval: {e}"
                )

        # 標準檢索邏輯
        if strategy == RetrievalStrategy.VECTOR_ONLY:
            return self._vector_retrieval(query, collection_name, n_results, filters)
        elif strategy == RetrievalStrategy.KEYWORD_ONLY:
            return self._keyword_retrieval(query, collection_name, n_results, filters)
        elif strategy == RetrievalStrategy.HYBRID:
            return self._hybrid_retrieval(query, collection_name, n_results, filters)
        else:
            logger.warning(f"Unknown strategy: {strategy}, using vector retrieval")
            return self._vector_retrieval(query, collection_name, n_results, filters)

    def _vector_retrieval(
        self,
        query: str,
        collection_name: str,
        n_results: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量檢索

        Args:
            query: 查詢文本
            collection_name: 集合名稱
            n_results: 返回結果數量
            filters: 過濾條件

        Returns:
            檢索結果列表
        """
        if not self.chromadb_client:
            logger.warning("ChromaDB client not available")
            return []

        try:
            results = self.chromadb_client.query(  # type: ignore[attr-defined]
                collection_name=collection_name,
                query_text=query,
                n_results=n_results,
                where=filters,
            )
            logger.debug(f"Vector retrieval returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return []

    def _keyword_retrieval(
        self,
        query: str,
        collection_name: str,
        n_results: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        關鍵詞檢索

        Args:
            query: 查詢文本
            collection_name: 集合名稱
            n_results: 返回結果數量
            filters: 過濾條件

        Returns:
            檢索結果列表
        """
        if not self.chromadb_client:
            logger.warning("ChromaDB client not available")
            return []

        try:
            # 簡單的關鍵詞匹配（實際實現應該更複雜）
            # 這裡使用向量檢索作為基礎，然後進行關鍵詞過濾
            results = self.chromadb_client.query(  # type: ignore[attr-defined]
                collection_name=collection_name,
                query_text=query,
                n_results=n_results * 2,  # 獲取更多結果以便過濾
                where=filters,
            )

            # 關鍵詞過濾
            query_keywords = set(query.lower().split())
            filtered_results = []
            for result in results:
                content = result.get("content", "").lower()
                if any(keyword in content for keyword in query_keywords):
                    filtered_results.append(result)
                    if len(filtered_results) >= n_results:
                        break

            logger.debug(f"Keyword retrieval returned {len(filtered_results)} results")
            return filtered_results
        except Exception as e:
            logger.error(f"Keyword retrieval failed: {e}")
            return []

    def _hybrid_retrieval(
        self,
        query: str,
        collection_name: str,
        n_results: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        混合檢索（向量 + 關鍵詞）

        Args:
            query: 查詢文本
            collection_name: 集合名稱
            n_results: 返回結果數量
            filters: 過濾條件

        Returns:
            檢索結果列表
        """
        # 獲取向量檢索結果
        vector_results = self._vector_retrieval(
            query, collection_name, n_results, filters
        )

        # 獲取關鍵詞檢索結果
        keyword_results = self._keyword_retrieval(
            query, collection_name, n_results, filters
        )

        # 合併結果並去重
        seen_ids = set()
        merged_results = []

        # 優先添加向量檢索結果（通常更相關）
        for result in vector_results:
            result_id = result.get("id")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                merged_results.append(result)

        # 添加關鍵詞檢索結果
        for result in keyword_results:
            result_id = result.get("id")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                merged_results.append(result)

        # 限制結果數量
        merged_results = merged_results[:n_results]

        logger.debug(f"Hybrid retrieval returned {len(merged_results)} results")
        return merged_results

    def add_document(
        self,
        content: str,
        collection_name: str = "documents",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        添加文檔到檢索集合

        Args:
            content: 文檔內容
            collection_name: 集合名稱
            metadata: 元數據

        Returns:
            文檔ID，如果失敗則返回 None
        """
        if not self.chromadb_client:
            logger.warning("ChromaDB client not available")
            return None

        try:
            doc_id = self.chromadb_client.add_document(  # type: ignore[attr-defined]
                collection_name=collection_name,
                content=content,
                metadata=metadata or {},
            )
            logger.debug(f"Added document to collection '{collection_name}': {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return None
