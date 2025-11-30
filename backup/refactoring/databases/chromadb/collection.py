# 代碼功能說明: ChromaDB 集合操作封裝
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 21:35 (UTC+8)

"""ChromaDB 集合操作封裝，提供 CRUD 和檢索功能"""

from typing import List, Dict, Any, Optional, Union
from chromadb.api.types import (
    Where,
    WhereDocument,
)
import logging
import os

from .utils import (
    validate_embedding_dimension,
    normalize_embeddings,
    batch_items,
)
from .exceptions import ChromaDBOperationError

logger = logging.getLogger(__name__)


class ChromaCollection:
    """ChromaDB 集合操作封裝類"""

    def __init__(
        self,
        collection,
        namespace: Optional[str] = None,
        expected_embedding_dim: Optional[int] = None,
        batch_size: int = 100,
    ):
        """
        初始化集合封裝

        Args:
            collection: ChromaDB Collection 對象
            namespace: 命名空間（用於隔離數據）
            expected_embedding_dim: 預期的嵌入向量維度
            batch_size: 批量操作時的批次大小
        """
        self.collection = collection
        self.name = collection.name
        self.namespace = namespace or os.getenv("CHROMADB_NAMESPACE")
        self.expected_embedding_dim = expected_embedding_dim
        self.batch_size = batch_size

    def _add_namespace_to_metadata(
        self, metadatas: Optional[List[Dict[str, Any]]], count: int
    ) -> Optional[List[Dict[str, Any]]]:
        """為 metadata 添加命名空間"""
        if not self.namespace:
            return metadatas

        if metadatas is None:
            metadatas = [{} for _ in range(count)]

        result = []
        for metadata in metadatas:
            if metadata is None:
                metadata = {}
            metadata = dict(metadata)  # 創建副本避免修改原始數據
            metadata["_namespace"] = self.namespace
            result.append(metadata)

        return result

    def add(
        self,
        ids: Union[str, List[str]],
        embeddings: Optional[Union[List[List[float]], List[float]]] = None,
        metadatas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        documents: Optional[Union[str, List[str]]] = None,
    ) -> None:
        """
        添加文檔到集合

        Args:
            ids: 文檔 ID 或 ID 列表
            embeddings: 嵌入向量或向量列表
            metadatas: 元數據字典或字典列表
            documents: 文檔文本或文本列表
        """
        try:
            # 標準化輸入格式
            if isinstance(ids, str):
                ids = [ids]
            if documents is not None and isinstance(documents, str):
                documents = [documents]
            if metadatas is not None and isinstance(metadatas, dict):
                metadatas = [metadatas]

            # 驗證嵌入維度
            if embeddings is not None:
                embeddings_list = normalize_embeddings(embeddings)
                validate_embedding_dimension(
                    embeddings_list, expected_dim=self.expected_embedding_dim
                )

            # 驗證並添加命名空間到 metadata
            if self.namespace:
                metadatas = self._add_namespace_to_metadata(metadatas, len(ids))

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            logger.info(f"Added {len(ids)} document(s) to collection '{self.name}'")
        except ValueError as e:
            logger.error(f"Validation error in collection '{self.name}': {e}")
            raise ChromaDBOperationError(str(e)) from e
        except Exception as e:
            logger.error(f"Failed to add documents to collection '{self.name}': {e}")
            raise ChromaDBOperationError(str(e)) from e

    def batch_add(
        self,
        items: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        批量添加文檔到集合（優化性能）

        Args:
            items: 文檔項目列表，每個項目包含 id, embedding, metadata, document
            batch_size: 批次大小（如果不提供，使用實例的 batch_size）

        Returns:
            包含成功和失敗統計的字典

        Example:
            items = [
                {
                    "id": "doc1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"source": "test"},
                    "document": "Sample text"
                },
                ...
            ]
        """
        batch_size = batch_size or self.batch_size
        total = len(items)
        success_count = 0
        failed_count = 0
        errors = []

        # 分批處理
        batches = batch_items(items, batch_size)

        for batch_idx, batch in enumerate(batches):
            try:
                # 提取各字段，確保長度一致
                ids = [item.get("id") for item in batch]
                embeddings_list: list[list[float] | None] = [
                    item.get("embedding") for item in batch
                ]
                metadatas_list: list[dict[str, Any] | None] = [
                    item.get("metadata") for item in batch
                ]
                documents_list: list[str | None] = [
                    item.get("document") for item in batch
                ]

                # 過濾 None 值，但保持列表長度一致
                # 如果所有 embeddings 都是 None，則傳遞 None
                embeddings: Optional[list[list[float]]] = None
                if not all(emb is None for emb in embeddings_list):
                    embeddings = [emb for emb in embeddings_list if emb is not None]

                # 如果所有 metadatas 都是 None，則傳遞 None
                metadatas: Optional[list[dict[str, Any]]] = None
                if not all(meta is None for meta in metadatas_list):
                    metadatas = [meta for meta in metadatas_list if meta is not None]

                # 如果所有 documents 都是 None，則傳遞 None
                documents: Optional[list[str]] = None
                if not all(doc is None for doc in documents_list):
                    documents = [doc for doc in documents_list if doc is not None]

                # 使用標準 add 方法
                self.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )
                success_count += len(batch)
                logger.debug(
                    f"Batch {batch_idx + 1}/{len(batches)} completed: "
                    f"{len(batch)} documents added"
                )
            except Exception as e:
                failed_count += len(batch)
                errors.append({"batch": batch_idx + 1, "error": str(e)})
                logger.error(f"Batch {batch_idx + 1} failed: {e}")

        result = {
            "total": total,
            "success": success_count,
            "failed": failed_count,
            "errors": errors,
        }
        logger.info(
            f"Batch add completed: {success_count}/{total} documents added successfully"
        )
        return result

    def get(
        self,
        ids: Optional[Union[str, List[str]]] = None,
        where: Optional[Where] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        where_document: Optional[WhereDocument] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        獲取文檔

        Args:
            ids: 文檔 ID 或 ID 列表
            where: 元數據過濾條件
            limit: 返回數量限制
            offset: 偏移量
            where_document: 文檔內容過濾條件
            include: 包含的字段列表 ['documents', 'metadatas', 'embeddings']

        Returns:
            包含 ids, embeddings, metadatas, documents 的字典
        """
        try:
            if isinstance(ids, str):
                ids = [ids]

            result = self.collection.get(
                ids=ids,
                where=where,
                limit=limit,
                offset=offset,
                where_document=where_document,
                include=include or ["documents", "metadatas"],
            )
            logger.debug(
                f"Retrieved {len(result['ids'])} document(s) from collection '{self.name}'"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get documents from collection '{self.name}': {e}")
            raise

    def update(
        self,
        ids: Union[str, List[str]],
        embeddings: Optional[Union[List[List[float]], List[float]]] = None,
        metadatas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        documents: Optional[Union[str, List[str]]] = None,
    ) -> None:
        """
        更新文檔

        Args:
            ids: 文檔 ID 或 ID 列表
            embeddings: 嵌入向量或向量列表
            metadatas: 元數據字典或字典列表
            documents: 文檔文本或文本列表
        """
        try:
            if isinstance(ids, str):
                ids = [ids]
            if documents is not None and isinstance(documents, str):
                documents = [documents]
            if metadatas is not None and isinstance(metadatas, dict):
                metadatas = [metadatas]

            self.collection.update(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            logger.info(f"Updated {len(ids)} document(s) in collection '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to update documents in collection '{self.name}': {e}")
            raise

    def delete(
        self,
        ids: Optional[Union[str, List[str]]] = None,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
    ) -> None:
        """
        刪除文檔

        Args:
            ids: 文檔 ID 或 ID 列表
            where: 元數據過濾條件
            where_document: 文檔內容過濾條件
        """
        try:
            if isinstance(ids, str):
                ids = [ids]

            self.collection.delete(ids=ids, where=where, where_document=where_document)
            logger.info(f"Deleted document(s) from collection '{self.name}'")
        except Exception as e:
            logger.error(
                f"Failed to delete documents from collection '{self.name}': {e}"
            )
            raise

    def query(
        self,
        query_embeddings: Optional[Union[List[List[float]], List[float]]] = None,
        query_texts: Optional[Union[str, List[str]]] = None,
        n_results: int = 10,
        where: Optional[Where] = None,
        where_document: Optional[WhereDocument] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        查詢相似文檔（向量檢索）

        Args:
            query_embeddings: 查詢嵌入向量或向量列表
            query_texts: 查詢文本或文本列表（將使用集合的嵌入函數）
            n_results: 返回結果數量
            where: 元數據過濾條件
            where_document: 文檔內容過濾條件
            include: 包含的字段列表

        Returns:
            包含 ids, embeddings, metadatas, documents, distances 的字典
        """
        try:
            if query_texts is not None and isinstance(query_texts, str):
                query_texts = [query_texts]

            result = self.collection.query(
                query_embeddings=query_embeddings,
                query_texts=query_texts,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include or ["documents", "metadatas", "distances"],
            )
            logger.debug(
                f"Query returned {len(result['ids'][0]) if result['ids'] else 0} result(s) from collection '{self.name}'"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to query collection '{self.name}': {e}")
            raise

    def peek(self, limit: int = 10) -> Dict[str, Any]:
        """
        查看集合中的前 N 個文檔

        Args:
            limit: 查看數量

        Returns:
            包含 ids, embeddings, metadatas, documents 的字典
        """
        try:
            result = self.collection.peek(limit=limit)
            logger.debug(
                f"Peeked {len(result['ids'])} document(s) from collection '{self.name}'"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to peek collection '{self.name}': {e}")
            raise

    def count(self) -> int:
        """
        獲取集合中文檔數量

        Returns:
            文檔數量
        """
        try:
            count = self.collection.count()
            logger.debug(f"Collection '{self.name}' contains {count} document(s)")
            return count
        except Exception as e:
            logger.error(f"Failed to count documents in collection '{self.name}': {e}")
            raise

    def modify(
        self,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        修改集合屬性

        Args:
            name: 新名稱
            metadata: 新元數據
        """
        try:
            self.collection.modify(name=name, metadata=metadata)
            if name:
                self.name = name
            logger.info(f"Modified collection '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to modify collection '{self.name}': {e}")
            raise
