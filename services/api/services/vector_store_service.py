# 代碼功能說明: 向量存儲服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""向量存儲服務 - 封裝 ChromaDB 操作，實現向量存儲和查詢"""

from __future__ import annotations

import os
from typing import List, Dict, Any, Optional
import structlog

from database.chromadb import ChromaDBClient, ChromaCollection
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 全局服務實例（單例模式）
_vector_store_service: Optional["VectorStoreService"] = None


class VectorStoreService:
    """向量存儲服務類"""

    def __init__(self, client: Optional[ChromaDBClient] = None):
        """
        初始化向量存儲服務

        Args:
            client: ChromaDB 客戶端，如果不提供則創建新實例
        """
        config = get_config_section("chromadb", default={}) or {}

        mode_value = config.get("mode") or os.getenv("CHROMADB_MODE", "http")
        if not isinstance(mode_value, str):
            mode_value = "http"
        self.client = client or ChromaDBClient(
            host=config.get("host") or os.getenv("CHROMADB_HOST"),
            port=config.get("port") or int(os.getenv("CHROMADB_PORT", "8001")),
            mode=mode_value,
            persist_directory=config.get("persist_directory")
            or os.getenv("CHROMADB_PERSIST_DIR"),
        )

        # Collection 命名策略
        self.collection_naming = config.get(
            "collection_naming", "file_based"
        )  # file_based 或 user_based

        logger.info(
            "VectorStoreService initialized",
            collection_naming=self.collection_naming,
        )

    def _get_collection_name(self, file_id: str, user_id: Optional[str] = None) -> str:
        """
        獲取 Collection 名稱

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            Collection 名稱
        """
        if self.collection_naming == "user_based" and user_id:
            return f"user_{user_id}"
        else:
            # 默認按文件分組
            return f"file_{file_id}"

    def get_or_create_collection(
        self, file_id: str, user_id: Optional[str] = None
    ) -> ChromaCollection:
        """
        獲取或創建 Collection

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            ChromaCollection 實例
        """
        collection_name = self._get_collection_name(file_id, user_id)

        # 使用 get_or_create_collection，如果不存在會自動創建
        metadata = {}
        if file_id:
            metadata["file_id"] = file_id
        if user_id:
            metadata["user_id"] = user_id

        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata=metadata if metadata else None,
        )
        logger.debug(
            "Retrieved or created collection",
            collection_name=collection_name,
        )
        return ChromaCollection(collection)

    def store_vectors(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        存儲向量到 ChromaDB

        Args:
            file_id: 文件 ID
            chunks: 分塊列表，每個分塊包含 text 和 metadata
            embeddings: 嵌入向量列表
            user_id: 用戶 ID（可選）

        Returns:
            如果存儲成功返回 True，否則返回 False

        Raises:
            ValueError: 如果 chunks 和 embeddings 數量不匹配
            RuntimeError: 如果存儲失敗
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks count ({len(chunks)}) and embeddings count ({len(embeddings)}) must match"
            )

        try:
            collection = self.get_or_create_collection(file_id, user_id)

            # 準備數據
            ids = [f"{file_id}_{i}" for i in range(len(chunks))]
            documents = [chunk.get("text", "") for chunk in chunks]
            metadatas = []

            for i, chunk in enumerate(chunks):
                # 從 chunk 中提取元數據（chunk 本身可能包含元數據字段）
                chunk_metadata = chunk.get("metadata", {})

                # 合併 chunk 的直接字段和 metadata 字段
                # 圖片文件的元數據（如 image_path, image_format 等）可能在 chunk 的直接字段中
                direct_metadata = {
                    k: v
                    for k, v in chunk.items()
                    if k not in ["text", "metadata"] and v is not None
                }

                # 添加標準元數據
                metadata = {
                    **chunk_metadata,
                    **direct_metadata,  # 優先使用直接字段（如 image_path）
                    "file_id": file_id,
                    "chunk_index": chunk.get("chunk_index", i),
                    "chunk_text": chunk.get("text", "")[:200],  # 前200字符用於索引
                }

                # 如果 chunk 有 content_type，保留它
                if "content_type" in chunk:
                    metadata["content_type"] = chunk["content_type"]

                if user_id:
                    metadata["user_id"] = user_id
                metadatas.append(metadata)

            # 批量存儲
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(
                "Stored vectors successfully",
                file_id=file_id,
                vector_count=len(embeddings),
                collection_name=collection.name,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to store vectors",
                file_id=file_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to store vectors: {e}") from e

    def query_vectors(
        self,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        n_results: int = 10,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查詢相似向量

        Args:
            query_text: 查詢文本（如果提供，將用於生成 embedding）
            query_embedding: 查詢向量（如果提供，直接使用）
            file_id: 文件 ID（用於過濾）
            user_id: 用戶 ID（用於過濾）
            n_results: 返回結果數量
            collection_name: Collection 名稱（如果不提供，根據 file_id/user_id 推斷）

        Returns:
            查詢結果列表，每個結果包含 document, metadata, distance 等

        Raises:
            ValueError: 如果既沒有提供 query_text 也沒有提供 query_embedding
        """
        if not query_text and not query_embedding:
            raise ValueError("Either query_text or query_embedding must be provided")

        try:
            # 確定 collection
            if collection_name:
                collection = ChromaCollection(
                    self.client.get_or_create_collection(name=collection_name)
                )
            elif file_id or user_id:
                collection = self.get_or_create_collection(file_id or "", user_id)
            else:
                raise ValueError("Must provide collection_name or file_id/user_id")

            # 構建過濾條件
            where: Dict[str, Any] = {}
            if file_id:
                where["file_id"] = file_id
            if user_id:
                where["user_id"] = user_id

            # 執行查詢
            if query_embedding:
                result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where if where else None,
                    include=["documents", "metadatas", "distances"],
                )
            else:
                # 使用文本查詢（需要 collection 有嵌入函數）
                if query_text is None:
                    raise ValueError(
                        "query_text is required when query_embedding is not provided"
                    )
                result = collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where=where if where else None,
                    include=["documents", "metadatas", "distances"],
                )

            # 格式化結果
            results: List[Dict[str, Any]] = []
            if result.get("ids") and len(result["ids"]) > 0:
                ids = result["ids"][0]
                documents = result.get("documents", [[]])[0]
                metadatas = result.get("metadatas", [[]])[0]
                distances = result.get("distances", [[]])[0]

                for i in range(len(ids)):
                    results.append(
                        {
                            "id": ids[i],
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                            "distance": distances[i] if i < len(distances) else None,
                        }
                    )

            logger.debug(
                "Query vectors completed",
                query_text_length=len(query_text) if query_text else 0,
                results_count=len(results),
            )
            return results

        except Exception as e:
            logger.error(
                "Failed to query vectors",
                error=str(e),
            )
            raise RuntimeError(f"Failed to query vectors: {e}") from e

    def get_vectors_by_file_id(
        self, file_id: str, user_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        根據文件 ID 獲取所有向量

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）
            limit: 返回數量限制

        Returns:
            向量列表
        """
        try:
            collection = self.get_or_create_collection(file_id, user_id)

            result = collection.get(
                where={"file_id": file_id},
                limit=limit,
                include=["documents", "metadatas"],
            )

            vectors: List[Dict[str, Any]] = []
            if result.get("ids"):
                ids = result["ids"]
                documents = result.get("documents", [])
                metadatas = result.get("metadatas", [])

                for i in range(len(ids)):
                    vectors.append(
                        {
                            "id": ids[i],
                            "document": documents[i] if i < len(documents) else "",
                            "metadata": metadatas[i] if i < len(metadatas) else {},
                        }
                    )

            logger.debug(
                "Retrieved vectors by file_id",
                file_id=file_id,
                count=len(vectors),
            )
            return vectors

        except Exception as e:
            logger.error(
                "Failed to get vectors by file_id",
                file_id=file_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get vectors by file_id: {e}") from e

    def delete_vectors_by_file_id(
        self, file_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        刪除文件的所有向量

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            如果刪除成功返回 True，否則返回 False
        """
        try:
            collection = self.get_or_create_collection(file_id, user_id)

            collection.delete(where={"file_id": file_id})

            logger.info(
                "Deleted vectors by file_id",
                file_id=file_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to delete vectors by file_id",
                file_id=file_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to delete vectors by file_id: {e}") from e

    def get_collection_stats(
        self, file_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取 Collection 統計信息

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            統計信息字典
        """
        try:
            collection = self.get_or_create_collection(file_id, user_id)

            count = collection.count()

            return {
                "collection_name": collection.name,
                "file_id": file_id,
                "user_id": user_id,
                "vector_count": count,
            }

        except Exception as e:
            logger.error(
                "Failed to get collection stats",
                file_id=file_id,
                error=str(e),
            )
            raise RuntimeError(f"Failed to get collection stats: {e}") from e


def get_vector_store_service() -> VectorStoreService:
    """獲取向量存儲服務實例（單例模式）

    Returns:
        VectorStoreService 實例
    """
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service


def reset_vector_store_service() -> None:
    """重置向量存儲服務實例（主要用於測試）"""
    global _vector_store_service
    _vector_store_service = None
