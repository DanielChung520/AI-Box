# 代碼功能說明: 增量重新索引服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-22 22:33 UTC+8

"""增量重新索引服務 - 檢測修改的 chunks 並重新索引"""

from typing import Any, Dict, List, Optional, Set

import structlog

from services.api.processors.chunk_processor import ChunkProcessor, ChunkStrategy
from services.api.services.embedding_service import get_embedding_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

logger = structlog.get_logger(__name__)

# 單例實例
_incremental_reindex_service: Optional["IncrementalReindexService"] = None


def get_incremental_reindex_service() -> "IncrementalReindexService":
    """獲取增量重新索引服務實例（單例模式）"""
    global _incremental_reindex_service
    if _incremental_reindex_service is None:
        _incremental_reindex_service = IncrementalReindexService()
    return _incremental_reindex_service


class IncrementalReindexService:
    """增量重新索引服務"""

    def __init__(self) -> None:
        """初始化服務"""
        # 修改時間：2026-01-22 - 遷移到 Qdrant 向量存儲服務
        self.vector_store_service = get_qdrant_vector_store_service()
        self.embedding_service = get_embedding_service()
        self.chunk_processor = ChunkProcessor(
            strategy=ChunkStrategy.AST_DRIVEN, min_tokens=500, max_tokens=1000
        )

    async def reindex_modified_chunks(
        self,
        file_id: str,
        original_content: str,
        modified_content: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        增量重新索引修改的 chunks

        Args:
            file_id: 文件 ID
            original_content: 原始文件內容
            modified_content: 修改後的文件內容
            user_id: 用戶 ID（可選）

        Returns:
            包含重新索引統計信息的字典
        """
        try:
            # 1. 獲取現有的 chunks 和向量
            existing_vectors = self._get_existing_vectors(file_id, user_id)
            if not existing_vectors:
                logger.info(f"文件 {file_id} 沒有現有向量，跳過增量重新索引")
                return {
                    "reindexed_chunks": 0,
                    "total_chunks": 0,
                    "message": "沒有現有向量，跳過重新索引",
                }

            # 2. 檢測受影響的 chunks
            affected_chunk_indices = self._detect_affected_chunks(
                original_content, modified_content, existing_vectors
            )

            if not affected_chunk_indices:
                logger.info(f"文件 {file_id} 沒有受影響的 chunks，跳過重新索引")
                return {
                    "reindexed_chunks": 0,
                    "total_chunks": len(existing_vectors),
                    "message": "沒有受影響的 chunks",
                }

            # 3. 重新處理修改的內容，獲取新的 chunks
            new_chunks = self.chunk_processor.process(
                text=modified_content,
                file_id=file_id,
                metadata=None,
            )

            # 4. 過濾出需要重新索引的 chunks
            chunks_to_reindex = [
                chunk
                for chunk in new_chunks
                if chunk.get("chunk_index", -1) in affected_chunk_indices
            ]

            if not chunks_to_reindex:
                logger.warning(f"文件 {file_id} 檢測到受影響的 chunks，但新 chunks 中找不到對應的索引")
                return {
                    "reindexed_chunks": 0,
                    "total_chunks": len(existing_vectors),
                    "message": "無法找到對應的新 chunks",
                }

            # 5. 重新計算 embeddings
            chunk_texts = [chunk.get("text", "") for chunk in chunks_to_reindex]
            new_embeddings = await self.embedding_service.generate_embeddings_batch(chunk_texts)

            # 6. 更新 Qdrant 向量（已从 ChromaDB 迁移）
            # 使用 Qdrant 向量存储服务更新向量
            from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service
            
            qdrant_service = get_qdrant_vector_store_service()
            collection = qdrant_service.get_or_create_collection(file_id, user_id)
            
            # 准备数据
            ids = [f"{file_id}_{chunk.get('chunk_index', i)}" for i, chunk in enumerate(chunks_to_reindex)]
            documents = [chunk.get("text", "") for chunk in chunks_to_reindex]
            metadatas = []
            for i, chunk in enumerate(chunks_to_reindex):
                chunk_metadata = chunk.get("metadata", {})
                metadata = {
                    **chunk_metadata,
                    "file_id": file_id,
                    "chunk_index": chunk.get("chunk_index", i),
                    "chunk_text": chunk.get("text", "")[:200],
                }
                if user_id:
                    metadata["user_id"] = user_id
                metadatas.append(metadata)
            
            # 更新向量
            collection.upsert(
                ids=ids,
                vectors=new_embeddings,
                payloads=[{"text": doc, **meta} for doc, meta in zip(documents, metadatas)],
            )
            
            logger.info(
                f"成功更新 {len(chunks_to_reindex)} 個向量到 Qdrant",
                file_id=file_id,
                chunk_count=len(chunks_to_reindex),
            )

            logger.info(
                "增量重新索引完成",
                file_id=file_id,
                reindexed_chunks=len(chunks_to_reindex),
                total_chunks=len(existing_vectors),
            )

            return {
                "reindexed_chunks": len(chunks_to_reindex),
                "total_chunks": len(existing_vectors),
                "affected_indices": list(affected_chunk_indices),
                "message": f"成功重新索引 {len(chunks_to_reindex)} 個 chunks",
            }

        except Exception as e:
            logger.error(f"增量重新索引失敗: {e}", exc_info=True)
            raise

    def _get_existing_vectors(
        self, file_id: str, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取現有的向量數據

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            向量數據列表
        """
        try:
            # 使用 vector_store_service 的方法獲取向量
            vectors = self.vector_store_service.get_vectors_by_file_id(
                file_id=file_id,
                user_id=user_id,
                limit=None,  # 獲取所有向量
            )

            if not vectors:
                return []

            # 轉換格式
            result_vectors = []
            for vector in vectors:
                result_vectors.append(
                    {
                        "id": vector.get("id", ""),
                        "text": vector.get("document", ""),
                        "metadata": vector.get("metadata", {}),
                        "embedding": vector.get("embedding"),
                    }
                )

            return result_vectors

        except Exception as e:
            logger.error(f"獲取現有向量失敗: {e}", exc_info=True)
            return []

    def _detect_affected_chunks(
        self,
        original_content: str,
        modified_content: str,
        existing_vectors: List[Dict[str, Any]],
    ) -> Set[int]:
        """
        檢測受影響的 chunks

        Args:
            original_content: 原始文件內容
            modified_content: 修改後的文件內容
            existing_vectors: 現有向量列表

        Returns:
            受影響的 chunk 索引集合
        """
        affected_indices: Set[int] = set()

        # 簡單的檢測策略：比較原始內容和修改後內容
        # 如果內容完全相同，沒有受影響的 chunks
        if original_content == modified_content:
            return affected_indices

        # 構建 chunk 索引到文本位置的映射
        # 這裡使用簡化的方法：基於 chunk_index 和文本位置
        # 實際實現可以更複雜，比如使用 AST 解析來精確定位

        # 方法 1: 如果所有 chunks 都有 start_position 和 end_position
        for vector in existing_vectors:
            metadata = vector.get("metadata", {})
            chunk_index = metadata.get("chunk_index")

            if chunk_index is None:
                continue

            # 獲取 chunk 的原始文本
            chunk_text = vector.get("text", "")

            if not chunk_text:
                continue

            # 檢查原始內容中是否包含這個 chunk 的文本
            # 如果不在原始內容中，或者在修改後內容中已經改變，則標記為受影響
            if chunk_text not in original_content:
                # chunk 文本不在原始內容中，可能已經被刪除或修改
                affected_indices.add(chunk_index)
            elif chunk_text not in modified_content:
                # chunk 文本在原始內容中，但不在修改後內容中，被刪除
                affected_indices.add(chunk_index)
            else:
                # 檢查文本是否發生變化（簡單的字符串比較）
                # 注意：這種方法可能不夠精確，但對於大多數情況足夠
                original_pos = original_content.find(chunk_text)
                modified_pos = modified_content.find(chunk_text)

                if original_pos == -1 or modified_pos == -1:
                    affected_indices.add(chunk_index)
                else:
                    # 檢查前後的上下文是否變化
                    # 如果上下文變化，也可能影響這個 chunk
                    context_size = 50
                    original_start = max(0, original_pos - context_size)
                    original_end = min(
                        len(original_content), original_pos + len(chunk_text) + context_size
                    )
                    modified_start = max(0, modified_pos - context_size)
                    modified_end = min(
                        len(modified_content), modified_pos + len(chunk_text) + context_size
                    )

                    original_context = original_content[original_start:original_end]
                    modified_context = modified_content[modified_start:modified_end]

                    if original_context != modified_context:
                        affected_indices.add(chunk_index)

        # 如果檢測到任何變更，但沒有找到具體的受影響 chunks，
        # 則標記所有 chunks 為受影響（保守策略）
        if not affected_indices and original_content != modified_content:
            logger.warning("無法精確檢測受影響的 chunks，標記所有 chunks 為受影響")
            for vector in existing_vectors:
                metadata = vector.get("metadata", {})
                chunk_index = metadata.get("chunk_index")
                if chunk_index is not None:
                    affected_indices.add(chunk_index)

        return affected_indices

    # _update_vectors_in_chromadb 方法已移除（已迁移到 Qdrant）
    # 请使用 Qdrant 向量存储服务进行向量更新
