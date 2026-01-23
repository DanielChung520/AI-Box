# 代碼功能說明: Qdrant 向量存儲服務
# 創建日期: 2026-01-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 01:33 UTC+8
#
# 說明:
# 此服務用於替代 ChromaDB 向量存儲，使用 Qdrant 作為後端。
# Qdrant 是一個高性能的 Rust 向量數據庫，適合大規模部署。
#
# 遷移說明:
# 1. 配置文件: config/config.json → datastores.qdrant
# 2. Docker: docker-compose.qdrant.yml
# 3. 回滾: 切換回 ChromaDB，見 CHROMADB_TO_QDRANT_MIGRATION.md
#
"""Qdrant 向量存儲服務 - 封裝 Qdrant 操作，實現向量存儲和查詢"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.models import (
    Distance,
    PointStruct,
    SetPayload,
    SetPayloadOperation,
    VectorParams,
)

from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 全局服務實例（單例模式）
_vector_store_service: Optional["QdrantVectorStoreService"] = None


class QdrantVectorStoreService:
    """Qdrant 向量存儲服務類"""

    def __init__(self, client: Optional[QdrantClient] = None):
        """
        初始化 Qdrant 向量存儲服務

        Args:
            client: Qdrant 客戶端，如果不提供則創建新實例
        """
        datastores_config = get_config_section("datastores", default={}) or {}
        qdrant_config = datastores_config.get("qdrant", {}) if datastores_config else {}

        host = qdrant_config.get("host") or os.getenv("QDRANT_HOST", "localhost")
        port = qdrant_config.get("port") or int(os.getenv("QDRANT_PORT", "6333"))
        api_key = qdrant_config.get("api_key") or os.getenv("QDRANT_API_KEY")
        timeout = qdrant_config.get("timeout", 30)

        if client is not None:
            self.client = client
        else:
            if api_key:
                self.client = QdrantClient(
                    host=host,
                    port=port,
                    api_key=api_key,
                    timeout=timeout,
                )
            else:
                self.client = QdrantClient(
                    host=host,
                    port=port,
                    timeout=timeout,
                )

        hnsw_config = qdrant_config.get("hnsw", {})
        self.hnsw_m = hnsw_config.get("m", 16)
        self.hnsw_ef_construct = hnsw_config.get("ef_construct", 100)
        self.hnsw_full_scan_threshold = hnsw_config.get("full_scan_threshold", 10000)

        optimizers_config = qdrant_config.get("optimizers", {})
        self.default_segment_number = optimizers_config.get("default_segment_number", 2)
        self.max_optimization_threads = optimizers_config.get("max_optimization_threads", 1)

        self.collection_naming = qdrant_config.get("collection_naming", "file_based")
        self._dimension_cache: Dict[str, Optional[int]] = {}

        logger.info(
            "QdrantVectorStoreService initialized",
            host=host,
            port=port,
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
            return f"file_{file_id}"

    def _ensure_collection(self, collection_name: str, vector_size: int) -> None:
        """
        確保 Collection 存在，如果不存在則創建

        Args:
            collection_name: Collection 名稱
            vector_size: 向量維度
        """
        try:
            self.client.get_collection(collection_name)
            logger.debug("Collection exists", collection_name=collection_name)
        except Exception:
            logger.info(
                "Creating collection", collection_name=collection_name, vector_size=vector_size
            )

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                    on_disk=True,
                ),
            )

            # 創建索引
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="file_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

    def store_vectors(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        存儲向量到 Qdrant

        Args:
            file_id: 文件 ID
            chunks: 分塊列表，每個分塊包含 text 和 metadata
            embeddings: 嵌入向量列表
            user_id: 用戶 ID（可選）

        Returns:
            如果存儲成功返回 True，否則返回 False
        """
        if not embeddings or len(embeddings) == 0:
            logger.warning("No embeddings to store", file_id=file_id)
            return False

        collection_name = self._get_collection_name(file_id, user_id)
        vector_size = len(embeddings[0]) if embeddings else 768

        try:
            self._ensure_collection(collection_name, vector_size)

            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if not embedding or len(embedding) == 0:
                    continue

                chunk_metadata = chunk.get("metadata", {})

                payload = {
                    "file_id": file_id,
                    "chunk_index": chunk.get("chunk_index", i),
                    "chunk_text": chunk.get("text", "") if chunk.get("text") else "",
                }

                for k, v in chunk_metadata.items():
                    if isinstance(v, (list, dict)):
                        payload[k] = json.dumps(v, ensure_ascii=False)
                    elif v is not None:
                        payload[k] = v

                if user_id:
                    payload["user_id"] = user_id

                points.append(
                    PointStruct(
                        id=i,
                        vector=embedding,
                        payload=payload,
                    )
                )

            if points:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                )

                logger.info(
                    "Stored vectors successfully",
                    file_id=file_id,
                    vector_count=len(points),
                    collection_name=collection_name,
                )
                return True
            else:
                logger.warning("No valid points to store", file_id=file_id)
                return False

        except Exception as e:
            logger.error(
                "Failed to store vectors",
                file_id=file_id,
                error=str(e),
            )
            return False

    def update_vectors_payload(
        self,
        file_id: str,
        chunks: List[Dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> bool:
        """
        更新 Qdrant Payload（保留原有向量 ID）

        用於 Stage 2 完成後更新 Contextual Header、Global Summary 等

        Args:
            file_id: 文件 ID
            chunks: 更新後的分塊列表
            user_id: 用戶 ID（可選）

        Returns:
            是否成功更新
        """
        collection_name = self._get_collection_name(file_id, user_id)

        try:
            existing_points = self.get_vectors_by_file_id(
                file_id=file_id,
                user_id=user_id,
                limit=10000,
                with_vector=False,
            )

            if not existing_points:
                logger.warning(
                    "No existing points found to update",
                    file_id=file_id,
                )
                return False

            logger.info(
                "Found existing points for payload update",
                file_id=file_id,
                point_count=len(existing_points),
            )

            update_operations = []
            for i, chunk in enumerate(chunks):
                existing_point = next(
                    (p for p in existing_points if p.get("payload", {}).get("chunk_index") == i),
                    None,
                )

                if existing_point:
                    point_id = existing_point.get("id")
                    chunk_metadata = chunk.get("metadata", {})

                    updated_payload = {
                        **existing_point.get("payload", {}),
                        "global_summary": chunk_metadata.get("global_summary"),
                        "contextual_header": chunk_metadata.get("contextual_header"),
                        "image_description": chunk_metadata.get("image_description"),
                        "element_type": chunk_metadata.get("element_type"),
                        "updated_at": time.time(),
                    }

                    update_operations.append(
                        SetPayloadOperation(
                            set_payload=SetPayload(
                                payload=updated_payload,
                                points=[point_id],
                            )
                        )
                    )

            if update_operations:
                self.client.batch_update_points(
                    collection_name=collection_name,
                    update_operations=update_operations,
                )
                logger.info(
                    "Payload update completed",
                    file_id=file_id,
                    updated_count=len(update_operations),
                )
                return True
            else:
                logger.warning(
                    "No matching points to update",
                    file_id=file_id,
                )
                return False

        except Exception as e:
            logger.error(
                "Failed to update vectors payload",
                file_id=file_id,
                error=str(e),
                exc_info=True,
            )
            return False

    def query_vectors(
        self,
        query_embedding: List[float],
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        查詢相似向量

        Args:
            query_embedding: 查詢向量
            file_id: 過濾的 file_id（可選）
            user_id: 過濾的 user_id（可選）
            limit: 返回結果數量
            score_threshold: 相似度閾值（可選）

        Returns:
            查詢結果列表
        """
        try:
            if file_id:
                collections = [self._get_collection_name(file_id, user_id)]
            else:
                collections = self._list_collections()

            results = []

            for collection_name in collections:
                must_conditions = []

                if file_id:
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key="file_id",
                            match=qmodels.MatchValue(value=file_id),
                        )
                    )

                if user_id:
                    must_conditions.append(
                        qmodels.FieldCondition(
                            key="user_id",
                            match=qmodels.MatchValue(value=user_id),
                        )
                    )

                filter_model = None
                if must_conditions:
                    filter_model = qmodels.Filter(must=must_conditions)

                search_result = self.client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=filter_model,
                    with_payload=True,
                ).points

                for hit in search_result:
                    results.append(
                        {
                            "id": str(hit.id),
                            "score": hit.score,
                            "payload": hit.payload,
                        }
                    )

            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(
                "Failed to query vectors",
                error=str(e),
            )
            return []

    def query_vectors_with_acl(
        self,
        query_embedding: List[float],
        user_id: str,
        user_permissions: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        查詢向量（帶 ACL 權限過濾）

        Args:
            query_embedding: 查詢向量
            user_id: 用戶 ID
            user_permissions: 用戶權限列表
            limit: 返回結果數量

        Returns:
            查詢結果列表
        """
        must_conditions = [
            qmodels.FieldCondition(
                key="access_level",
                match=qmodels.MatchValue(value="public"),
            ),
            qmodels.FieldCondition(
                key="authorized_users",
                match=qmodels.MatchAny(any=[user_id, "all"]),
            ),
        ]

        try:
            results = []
            collections = self._list_collections()

            for collection_name in collections:
                filter_model = qmodels.Filter(must=must_conditions)

                search_result = self.client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    limit=limit,
                    query_filter=filter_model,
                    with_payload=True,
                ).points

                for hit in search_result:
                    results.append(
                        {
                            "id": str(hit.id),
                            "score": hit.score,
                            "payload": hit.payload,
                        }
                    )

            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:limit]

        except Exception as e:
            logger.error(
                "Failed to query vectors with ACL",
                user_id=user_id,
                error=str(e),
            )
            return []

    def delete_vectors_by_file_id(self, file_id: str, user_id: Optional[str] = None) -> bool:
        """
        刪除指定 file_id 的所有向量

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            是否成功
        """
        try:
            collection_name = self._get_collection_name(file_id, user_id)

            self.client.delete(
                collection_name=collection_name,
                points_selector=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="file_id",
                            match=qmodels.MatchValue(value=file_id),
                        )
                    ]
                ),
            )

            logger.info(
                "Deleted vectors by file_id",
                file_id=file_id,
                collection_name=collection_name,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to delete vectors",
                file_id=file_id,
                error=str(e),
            )
            return False

    def get_collection_stats(self, file_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取 Collection 統計信息

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）

        Returns:
            統計信息字典
        """
        collection_name = self._get_collection_name(file_id, user_id)

        try:
            collection_info = self.client.get_collection(collection_name)
            vector_count = self.client.count(collection_name).count

            return {
                "collection_name": collection_name,
                "vector_count": vector_count,
                "status": str(collection_info.status),
            }
        except Exception as e:
            logger.error(
                "Failed to get collection stats",
                file_id=file_id,
                error=str(e),
            )
            return {
                "collection_name": collection_name,
                "vector_count": 0,
                "status": "error",
            }

    def _list_collections(self) -> List[str]:
        """列出所有 collections"""
        try:
            collections = self.client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error("Failed to list collections", error=str(e))
            return []

    def get_vectors_by_file_id(
        self,
        file_id: str,
        user_id: Optional[str] = None,
        limit: int = 1000,
        with_vector: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        根據 file_id 獲取向量

        修改時間：2026-01-21 12:20 UTC+8 - 添加 with_vector 參數，支持返回向量數據

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選）
            limit: 返回結果數量限制
            with_vector: 是否包含向量數據（默認 False，因為向量數據很大）

        Returns:
            向量列表（包含 id, payload, 可選的 vector）
        """
        collection_name = self._get_collection_name(file_id, user_id)

        try:
            # 使用 scroll_points 獲取所有匹配的 points（支持分頁）
            # 修改時間：2026-01-21 12:20 UTC+8 - 使用 scroll 獲取所有匹配的 points（支持分頁）
            # 先檢查 collection 是否存在
            try:
                self.client.get_collection(collection_name)
            except Exception:
                # Collection 不存在，返回空列表
                return []

            # 修改時間：2026-01-21 12:25 UTC+8 - 支持 offset 分頁，使用 scroll 獲取 points
            # 如果 limit 是 None，獲取所有（使用大數）
            scroll_limit = limit if limit is not None else 10000

            # 使用 scroll 獲取 points（支持分頁）
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=(
                    qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="file_id",
                                match=qmodels.MatchValue(value=file_id),
                            )
                        ]
                    )
                    if file_id
                    else None
                ),
                limit=scroll_limit,
                offset=None,  # Qdrant scroll 不支持 offset，我們在結果中手動切片
                with_payload=True,
                with_vectors=with_vector,
            )

            result_points = scroll_result[0]  # points 列表

            # 返回結果（注意：Qdrant scroll 不支持 offset，如果需要 offset 需要在應用層處理）
            return [
                {
                    "id": str(point.id),
                    "payload": point.payload,
                    **({"vector": point.vector} if with_vector and point.vector else {}),
                }
                for point in result_points
            ]

        except Exception as e:
            logger.error(
                "Failed to get vectors by file_id",
                file_id=file_id,
                error=str(e),
            )
            return []


def get_qdrant_vector_store_service() -> QdrantVectorStoreService:
    """獲取向 量存儲服務實例（單例模式）

    Returns:
        QdrantVectorStoreService 實例
    """
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = QdrantVectorStoreService()
    return _vector_store_service


def reset_qdrant_vector_store_service() -> None:
    """重置向量存儲服務實例（主要用於測試）"""
    global _vector_store_service
    _vector_store_service = None
