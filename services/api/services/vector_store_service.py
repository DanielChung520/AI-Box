# 代碼功能說明: 向量存儲服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""向量存儲服務 - 封裝 ChromaDB 操作，實現向量存儲和查詢"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import structlog

from database.chromadb import ChromaCollection, ChromaDBClient
from services.api.services.file_metadata_service import get_metadata_service
from services.api.services.file_permission_service import get_file_permission_service
from system.infra.config.config import get_config_section
from system.security.models import Permission, User

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
        # 優先從 datastores.chromadb 讀取配置，然後從 chromadb 讀取（向後兼容）
        datastores_config = get_config_section("datastores", default={}) or {}
        chromadb_config = datastores_config.get("chromadb", {}) if datastores_config else {}

        # 如果 datastores.chromadb 沒有配置，嘗試直接讀取 chromadb 配置（向後兼容）
        if not chromadb_config:
            chromadb_config = get_config_section("chromadb", default={}) or {}

        # 合併配置：優先使用 datastores.chromadb，然後使用環境變量
        mode_value = chromadb_config.get("mode") or os.getenv("CHROMADB_MODE", "http")
        if not isinstance(mode_value, str):
            mode_value = "http"

        # persist_directory 優先使用 mount_path（datastores 配置），然後使用 persist_directory，最後使用環境變量
        persist_dir = (
            chromadb_config.get("mount_path")  # datastores.chromadb.mount_path
            or chromadb_config.get("persist_directory")  # chromadb.persist_directory（向後兼容）
            or os.getenv("CHROMADB_PERSIST_DIR")  # 環境變量
            or "./data/datasets/chromadb"  # 默認值：統一使用 data/datasets 目錄
        )

        self.client = client or ChromaDBClient(
            host=chromadb_config.get("host") or os.getenv("CHROMADB_HOST"),
            port=chromadb_config.get("port") or int(os.getenv("CHROMADB_PORT", "8001")),
            mode=mode_value,
            persist_directory=persist_dir,
        )

        # Collection 命名策略
        self.collection_naming = chromadb_config.get(
            "collection_naming", "file_based"
        )  # file_based 或 user_based

        # 向量维度缓存（避免重复查询）
        self._dimension_cache: Dict[str, Optional[int]] = {}

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

    def get_collection_embedding_dimension(self, collection_name: str) -> Optional[int]:
        """
        獲取集合的向量維度

        Args:
            collection_name: 集合名稱

        Returns:
            向量維度，如果集合為空或無法檢測則返回 None
        """
        # 檢查緩存
        cache_key = f"dimension_{collection_name}"
        if hasattr(self, "_dimension_cache"):
            if cache_key in self._dimension_cache:
                return self._dimension_cache[cache_key]
        else:
            self._dimension_cache: Dict[str, Optional[int]] = {}

        try:
            # 獲取集合
            collection = self.client.get_or_create_collection(name=collection_name)

            # 查詢第一個向量（limit=1, include=['embeddings']）
            data = collection.get(limit=1, include=["embeddings"])

            # 檢查是否有向量數據
            embeddings = data.get("embeddings") if data else None
            # 處理 numpy 數組或列表
            if embeddings is not None:
                try:
                    # 檢查是否為 numpy 數組
                    import numpy as np

                    if isinstance(embeddings, np.ndarray):
                        # numpy 數組：shape[0] 是向量數量，shape[1] 是維度
                        if len(embeddings.shape) >= 2 and embeddings.shape[0] > 0:
                            embedding_dim = embeddings.shape[1]
                        elif len(embeddings.shape) == 1:
                            # 單個向量
                            embedding_dim = embeddings.shape[0]
                        else:
                            embedding_dim = None
                    elif isinstance(embeddings, list) and len(embeddings) > 0:
                        # 列表：獲取第一個元素的長度
                        first_embedding = embeddings[0]
                        if isinstance(first_embedding, np.ndarray):
                            embedding_dim = (
                                first_embedding.shape[0]
                                if len(first_embedding.shape) == 1
                                else first_embedding.shape[1]
                            )
                        elif hasattr(first_embedding, "__len__") and not isinstance(
                            first_embedding, str
                        ):
                            embedding_dim = len(first_embedding)
                        else:
                            embedding_dim = None
                    else:
                        embedding_dim = None
                except (TypeError, ValueError, AttributeError, ImportError):
                    # 如果無法獲取長度，返回 None
                    embedding_dim = None
                # 緩存結果
                self._dimension_cache[cache_key] = embedding_dim
                logger.debug(
                    "Collection embedding dimension detected",
                    collection_name=collection_name,
                    dimension=embedding_dim,
                )
                return embedding_dim
            else:
                # 集合為空，緩存 None
                self._dimension_cache[cache_key] = None
                logger.warning(
                    "Collection is empty, cannot detect dimension",
                    collection_name=collection_name,
                )
                return None

        except Exception as e:
            logger.error(
                "Failed to detect collection embedding dimension",
                collection_name=collection_name,
                error=str(e),
            )
            # 緩存 None 以避免重複失敗的查詢
            self._dimension_cache[cache_key] = None
            return None

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
        # 產品級容錯：過濾掉失敗的 embeddings（空列表）和對應的 chunks
        # 這樣可以允許部分失敗，而不會導致整個文件處理失敗
        valid_pairs: List[tuple[Dict[str, Any], List[float]]] = []
        failed_count = 0

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # 檢查 embedding 是否有效（非空且長度 > 0）
            if embedding and len(embedding) > 0:
                valid_pairs.append((chunk, embedding))
            else:
                failed_count += 1
                logger.warning(
                    "Skipping chunk with failed embedding",
                    file_id=file_id,
                    chunk_index=i,
                    chunk_preview=chunk.get("text", "")[:50] if chunk.get("text") else "N/A",
                )

        if failed_count > 0:
            logger.warning(
                "Some embeddings failed, filtering them out",
                file_id=file_id,
                failed_count=failed_count,
                total_count=len(chunks),
                valid_count=len(valid_pairs),
            )

        # 如果所有 embeddings 都失敗，拋出異常
        if len(valid_pairs) == 0:
            raise ValueError(f"All {len(chunks)} embeddings failed for file {file_id}")

        # 如果部分失敗，使用有效的 pairs
        if len(valid_pairs) < len(chunks):
            chunks = [pair[0] for pair in valid_pairs]
            embeddings = [pair[1] for pair in valid_pairs]
            logger.info(
                "Using filtered chunks and embeddings",
                file_id=file_id,
                original_count=len(chunks) + failed_count,
                filtered_count=len(chunks),
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
                # ChromaDB 只支持 str, int, float, bool, SparseVector, None 类型的 metadata
                # 需要过滤掉列表和字典类型
                direct_metadata = {}
                for k, v in chunk.items():
                    if k not in ["text", "metadata"] and v is not None:
                        # 过滤掉列表和字典类型（ChromaDB 不支持）
                        # ChromaDB 只支持 str, int, float, bool, SparseVector, None 类型
                        if isinstance(v, (list, dict)):
                            # 将列表或字典转换为 JSON 字符串
                            direct_metadata[k] = json.dumps(v, ensure_ascii=False)
                        else:
                            direct_metadata[k] = v

                # 处理 chunk_metadata 中的列表和字典
                cleaned_chunk_metadata = {}
                for k, v in chunk_metadata.items():
                    if isinstance(v, (list, dict)):
                        cleaned_chunk_metadata[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        cleaned_chunk_metadata[k] = v

                # 添加標準元數據
                metadata = {
                    **cleaned_chunk_metadata,
                    **direct_metadata,  # 優先使用直接字段（如 image_path）
                    "file_id": file_id,
                    "chunk_index": chunk.get("chunk_index", i),
                    "chunk_text": chunk.get("text", "")[:200],  # 前200字符用於索引
                }

                # 如果 chunk 有 content_type，保留它
                if "content_type" in chunk:
                    content_type = chunk["content_type"]
                    # 确保 content_type 不是列表或字典
                    if isinstance(content_type, (list, dict)):
                        metadata["content_type"] = json.dumps(content_type, ensure_ascii=False)
                    else:
                        metadata["content_type"] = content_type

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
                target_collection_name = collection_name
            elif file_id or user_id:
                collection = self.get_or_create_collection(file_id or "", user_id)
                target_collection_name = self._get_collection_name(file_id or "", user_id)
            else:
                raise ValueError("Must provide collection_name or file_id/user_id")

            # 檢測集合的向量維度，如果使用 query_text 則需要動態選擇模型
            if query_text and not query_embedding:
                collection_dimension = self.get_collection_embedding_dimension(
                    target_collection_name
                )
                if collection_dimension:
                    # 動態選擇對應的 embedding 模型
                    from services.api.services.embedding_service import get_embedding_service

                    embedding_service = get_embedding_service()
                    model_for_dimension = embedding_service.get_model_for_dimension(
                        collection_dimension
                    )

                    # 如果模型不匹配，使用對應的模型生成查詢向量
                    if model_for_dimension != embedding_service.model:
                        logger.info(
                            "Using different embedding model for query",
                            collection_dimension=collection_dimension,
                            selected_model=model_for_dimension,
                            default_model=embedding_service.model,
                        )
                        # 創建臨時的 EmbeddingService 實例使用對應的模型
                        import asyncio

                        temp_embedding_service = type(embedding_service)(
                            model=model_for_dimension,
                            ollama_url=embedding_service.ollama_url,
                        )
                        query_embedding = asyncio.run(
                            temp_embedding_service.generate_embedding(query_text)
                        )
                    else:
                        # 使用默認模型，但需要生成 embedding
                        query_embedding = asyncio.run(
                            embedding_service.generate_embedding(query_text)
                        )
                else:
                    # 無法檢測維度，使用默認方式（文本查詢）
                    query_embedding = None

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
                    raise ValueError("query_text is required when query_embedding is not provided")
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

    def query_vectors_with_acl(
        self,
        user: User,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        n_results: int = 10,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """帶訪問控制權限檢查的向量檢索

        AI治理要求：
        1. 只返回用戶有權限訪問的文件向量
        2. 根據文件訪問級別過濾結果

        Args:
            query_text: 查詢文本（如果提供，將用於生成 embedding）
            query_embedding: 查詢向量（如果提供，直接使用）
            user: 當前用戶（用於權限檢查）
            file_id: 文件 ID（用於過濾）
            user_id: 用戶 ID（用於過濾）
            n_results: 返回結果數量（會多檢索一些，用於過濾）
            collection_name: Collection 名稱（如果不提供，根據 file_id/user_id 推斷）

        Returns:
            過濾後的查詢結果列表，只包含用戶有權訪問的文件向量

        Raises:
            ValueError: 如果既沒有提供 query_text 也沒有提供 query_embedding
        """
        # 1. 執行向量檢索（多檢索一些，用於過濾）
        # 為了確保過濾後仍有足夠的結果，我們檢索更多
        expanded_n_results = n_results * 2 if n_results > 0 else 20

        try:
            results = self.query_vectors(
                query_text=query_text,
                query_embedding=query_embedding,
                file_id=file_id,
                user_id=user_id,
                n_results=expanded_n_results,
                collection_name=collection_name,
            )
        except Exception as e:
            logger.error(
                "Failed to query vectors for ACL filtering",
                error=str(e),
            )
            raise

        # 2. 獲取文件元數據並檢查權限
        permission_service = get_file_permission_service()
        metadata_service = get_metadata_service()
        filtered_results: List[Dict[str, Any]] = []

        # 批量獲取文件元數據（優化性能）
        file_ids_seen: set = set()
        file_metadata_cache: Dict[str, Any] = {}

        for result in results:
            result_file_id = result.get("metadata", {}).get("file_id")
            if not result_file_id:
                # 如果沒有 file_id，跳過（不應該發生，但為了安全）
                continue

            # 如果已經處理過這個文件，直接使用緩存結果
            if result_file_id in file_ids_seen:
                if result_file_id in file_metadata_cache:
                    if file_metadata_cache[result_file_id]:
                        filtered_results.append(result)
                        if len(filtered_results) >= n_results:
                            break
                continue

            file_ids_seen.add(result_file_id)

            # 獲取文件元數據
            try:
                file_metadata = metadata_service.get(result_file_id)
                if not file_metadata:
                    # 文件元數據不存在，跳過
                    file_metadata_cache[result_file_id] = None
                    continue

                # 檢查訪問權限
                has_access = permission_service.check_file_access_with_acl(
                    user=user,
                    file_metadata=file_metadata,
                    required_permission=Permission.FILE_READ.value,
                )

                file_metadata_cache[result_file_id] = file_metadata if has_access else None

                if has_access:
                    filtered_results.append(result)
                    if len(filtered_results) >= n_results:
                        break
            except Exception as e:
                logger.warning(
                    "Failed to check file access for vector result",
                    file_id=result_file_id,
                    error=str(e),
                )
                # 權限檢查失敗，跳過這個結果（安全優先）
                file_metadata_cache[result_file_id] = None
                continue

        logger.debug(
            "Query vectors with ACL completed",
            query_text_length=len(query_text) if query_text else 0,
            total_results=len(results),
            filtered_results=len(filtered_results),
            filtered_count=len(results) - len(filtered_results),
        )

        return filtered_results

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

    def delete_vectors_by_file_id(self, file_id: str, user_id: Optional[str] = None) -> bool:
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

    def get_collection_stats(self, file_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
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

            stats = {
                "collection_name": collection.name,
                "file_id": file_id,
                "user_id": user_id,
                "vector_count": count,
            }

            # 如果有向量，获取更多统计信息
            if count > 0:
                try:
                    # 获取一个向量来检查维度
                    results = collection.get(limit=1, include=["embeddings", "documents"])
                    embeddings = results.get("embeddings", [])

                    if embeddings is not None and len(embeddings) > 0:
                        # 确保 embeddings[0] 是列表或数组
                        first_embedding = embeddings[0]
                        if hasattr(first_embedding, "__len__"):
                            stats["dimension"] = len(first_embedding)

                    # 获取所有文档来计算统计
                    if count <= 1000:  # 只对小于1000的集合计算详细统计
                        all_results = collection.get(limit=count, include=["documents"])
                        all_documents = all_results.get("documents", [])

                        if all_documents and len(all_documents) > 0:
                            total_chars = sum(len(doc) for doc in all_documents)
                            total_words = sum(len(doc.split()) for doc in all_documents)

                            stats["total_chars"] = total_chars
                            stats["avg_chars_per_chunk"] = round(total_chars / count, 0)
                            stats["total_words"] = total_words
                            stats["avg_words_per_chunk"] = round(total_words / count, 0)
                except Exception as e:
                    logger.warning(
                        "Failed to get detailed stats",
                        file_id=file_id,
                        error=str(e),
                    )
                    # 继续返回基础统计

            return stats
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
