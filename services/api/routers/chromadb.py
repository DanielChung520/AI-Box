# 代碼功能說明: ChromaDB API 路由
# 創建日期: 2025-11-25 21:45 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 21:45 (UTC+8)

"""ChromaDB API 路由 - 提供向量資料庫操作接口"""

import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from services.api.clients.ollama_client import (
    get_ollama_client,
    OllamaClientError,
    OllamaHTTPError,
    OllamaTimeoutError,
)
from services.api.core.response import APIResponse
from services.api.core.settings import get_ollama_settings
from services.api.models.chromadb import (
    CollectionCreateRequest,
    DocumentAddRequest,
    DocumentUpdateRequest,
    QueryRequest,
    BatchAddRequest,
)
from databases.chromadb.utils import ensure_list

# 嘗試導入 ChromaDB 客戶端
try:
    from databases.chromadb import ChromaDBClient, ChromaCollection
    from databases.chromadb.exceptions import (
        ChromaDBError,
        ChromaDBConnectionError,  # noqa: F401
        ChromaDBOperationError,
    )

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

router = APIRouter(prefix="/chromadb", tags=["ChromaDB"])

# 全局 ChromaDB 客戶端（單例模式）
_chroma_client: Optional[ChromaDBClient] = None


async def _generate_embeddings_from_texts(
    texts: List[str],
    model_override: Optional[str],
) -> List[List[float]]:
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auto_embed 需要至少一筆 documents",
        )

    client = get_ollama_client()
    settings = get_ollama_settings()
    model = model_override or settings.embedding_model
    embeddings: List[List[float]] = []
    try:
        for text in texts:
            result = await client.embeddings(model=model, prompt=text)
            embedding = result.get("embedding")
            if not embedding:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="嵌入服務未回傳有效向量",
                )
            embeddings.append(embedding)
    except (OllamaClientError, OllamaHTTPError, OllamaTimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Embedding provider error: {exc}",
        ) from exc
    return embeddings


async def _resolve_embeddings_for_add(request: DocumentAddRequest):
    if request.embeddings is not None:
        return request.embeddings
    if not request.auto_embed:
        return None
    documents = ensure_list(request.documents)
    embeddings = await _generate_embeddings_from_texts(
        documents, request.embedding_model
    )
    return embeddings


async def _prepare_batch_items(request: BatchAddRequest) -> List[dict]:
    processed = []
    for item in request.items:
        embedding = item.embedding
        if embedding is None and request.auto_embed:
            if not item.document:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document '{item.id}' 缺少 document，無法自動產生 embedding",
                )
            embedding = (
                await _generate_embeddings_from_texts(
                    [item.document],
                    request.embedding_model,
                )
            )[0]
        processed.append(
            {
                "id": item.id,
                "embedding": embedding,
                "metadata": item.metadata,
                "document": item.document,
            }
        )
    return processed


def get_chroma_client() -> ChromaDBClient:
    """
    獲取 ChromaDB 客戶端實例

    Returns:
        ChromaDBClient: ChromaDB 客戶端實例

    Raises:
        HTTPException: 如果 ChromaDB 不可用或連接失敗
    """
    global _chroma_client

    if not CHROMADB_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ChromaDB client is not available. Please check dependencies.",
        )

    if _chroma_client is None:
        try:
            _chroma_client = ChromaDBClient(
                host=os.getenv("CHROMADB_HOST", "localhost"),
                port=int(os.getenv("CHROMADB_PORT", "8001")),
                mode=os.getenv("CHROMADB_MODE", "http"),
                pool_size=int(os.getenv("CHROMADB_CONNECTION_POOL_SIZE", "4")),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to ChromaDB: {str(e)}",
            ) from e

    return _chroma_client


# ========== 集合管理 ==========


@router.post("/collections", status_code=status.HTTP_201_CREATED)
async def create_collection(request: CollectionCreateRequest):
    """
    創建集合

    Args:
        request: 集合創建請求

    Returns:
        創建的集合信息
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name=request.name,
            metadata=request.metadata or {},
        )
        chroma_collection = ChromaCollection(
            collection,
            expected_embedding_dim=request.embedding_dimension,
        )
        return APIResponse.success(
            data={
                "name": collection.name,
                "metadata": collection.metadata,
                "count": chroma_collection.count(),
            },
            message=f"Collection '{request.name}' created successfully",
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}",
        ) from e


@router.get("/collections", status_code=status.HTTP_200_OK)
async def list_collections():
    """
    列出所有集合

    Returns:
        集合列表
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        return APIResponse.success(
            data={"collections": collections},
            message=f"Found {len(collections)} collection(s)",
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        ) from e


@router.delete("/collections/{name}", status_code=status.HTTP_200_OK)
async def delete_collection(name: str):
    """
    刪除集合

    Args:
        name: 集合名稱

    Returns:
        刪除結果
    """
    try:
        client = get_chroma_client()
        client.delete_collection(name=name)
        return APIResponse.success(
            data=None,
            message=f"Collection '{name}' deleted successfully",
        )
    except ChromaDBError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}",
        ) from e


# ========== 文檔操作 ==========


@router.post(
    "/collections/{collection_name}/documents", status_code=status.HTTP_201_CREATED
)
async def add_documents(collection_name: str, request: DocumentAddRequest):
    """
    添加文檔到集合

    Args:
        collection_name: 集合名稱
        request: 添加文檔請求

    Returns:
        添加結果
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(collection)

        embeddings = await _resolve_embeddings_for_add(request)

        chroma_collection.add(
            ids=request.ids,
            embeddings=embeddings,
            metadatas=request.metadatas,
            documents=request.documents,
        )

        ids_list = request.ids if isinstance(request.ids, list) else [request.ids]
        return APIResponse.success(
            data={"added_count": len(ids_list)},
            message=f"Added {len(ids_list)} document(s) to collection '{collection_name}'",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add documents: {str(e)}",
        ) from e


@router.get("/collections/{collection_name}/documents", status_code=status.HTTP_200_OK)
async def get_documents(
    collection_name: str,
    ids: Optional[str] = Query(None, description="文檔 ID，多個用逗號分隔"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="返回數量限制"),
):
    """
    獲取文檔

    Args:
        collection_name: 集合名稱
        ids: 文檔 ID（可選，多個用逗號分隔）
        limit: 返回數量限制

    Returns:
        文檔列表
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(collection)

        ids_list = ids.split(",") if ids else None
        result = chroma_collection.get(ids=ids_list, limit=limit)

        return APIResponse.success(
            data=result,
            message=f"Retrieved {len(result.get('ids', []))} document(s)",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get documents: {str(e)}",
        ) from e


@router.put(
    "/collections/{collection_name}/documents/{doc_id}", status_code=status.HTTP_200_OK
)
async def update_document(
    collection_name: str,
    doc_id: str,
    request: DocumentUpdateRequest,
):
    """
    更新文檔

    Args:
        collection_name: 集合名稱
        doc_id: 文檔 ID
        request: 更新請求

    Returns:
        更新結果
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(collection)

        chroma_collection.update(
            ids=doc_id,
            embeddings=request.embeddings,
            metadatas=request.metadatas,
            documents=request.documents,
        )

        return APIResponse.success(
            data=None,
            message=f"Document '{doc_id}' updated successfully",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}",
        ) from e


@router.delete(
    "/collections/{collection_name}/documents/{doc_id}", status_code=status.HTTP_200_OK
)
async def delete_document(collection_name: str, doc_id: str):
    """
    刪除文檔

    Args:
        collection_name: 集合名稱
        doc_id: 文檔 ID

    Returns:
        刪除結果
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(collection)

        chroma_collection.delete(ids=doc_id)

        return APIResponse.success(
            data=None,
            message=f"Document '{doc_id}' deleted successfully",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        ) from e


# ========== 向量檢索 ==========


@router.post("/collections/{collection_name}/query", status_code=status.HTTP_200_OK)
async def query_documents(collection_name: str, request: QueryRequest):
    """
    向量檢索

    Args:
        collection_name: 集合名稱
        request: 查詢請求

    Returns:
        檢索結果
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(collection)

        result = chroma_collection.query(
            query_embeddings=request.query_embeddings,
            query_texts=request.query_texts,
            n_results=request.n_results,
            where=request.where,
            where_document=request.where_document,  # type: ignore[arg-type]
            include=request.include,
        )

        return APIResponse.success(
            data=result,
            message="Query completed successfully",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query documents: {str(e)}",
        ) from e


@router.post("/collections/{collection_name}/batch-add", status_code=status.HTTP_200_OK)
async def batch_add_documents(collection_name: str, request: BatchAddRequest):
    """
    批量添加文檔（優化性能）

    Args:
        collection_name: 集合名稱
        request: 批量添加請求

    Returns:
        批量添加結果
    """
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)
        chroma_collection = ChromaCollection(
            collection, batch_size=request.batch_size or 100
        )

        items = await _prepare_batch_items(request)

        result = chroma_collection.batch_add(items, batch_size=request.batch_size)

        return APIResponse.success(
            data=result,
            message=f"Batch add completed: {result['success']}/{result['total']} documents added",
        )
    except ChromaDBOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch add documents: {str(e)}",
        ) from e
