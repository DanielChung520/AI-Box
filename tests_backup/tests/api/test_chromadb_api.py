# 代碼功能說明: ChromaDB API 端點測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""ChromaDB API 端點測試"""

import pytest
import os
import shutil
from fastapi.testclient import TestClient
from typing import List

# 設置測試環境變數
os.environ["CHROMADB_MODE"] = "persistent"
os.environ["CHROMADB_PERSIST_DIR"] = "./test_chroma_api_data"

from services.api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    test_dir = "./test_chroma_api_data"
    # 清理舊的測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    with TestClient(app) as test_client:
        yield test_client

    # 清理測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def test_collection_name():
    """測試集合名稱"""
    return "test_api_collection"


@pytest.fixture
def test_embeddings() -> List[List[float]]:
    """生成測試用的嵌入向量（384維）"""
    import random

    return [[random.random() for _ in range(384)] for _ in range(10)]


@pytest.fixture(autouse=True)
def cleanup_collection(client, test_collection_name):
    """每個測試後清理集合"""
    yield
    try:
        client.delete(f"/api/v1/chromadb/collections/{test_collection_name}")
    except Exception:
        pass


# ========== 集合管理 API 測試 ==========


def test_create_collection(client, test_collection_name):
    """測試創建集合"""
    response = client.post(
        "/api/v1/chromadb/collections",
        json={
            "name": test_collection_name,
            "metadata": {"test": True},
            "embedding_dimension": 384,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == test_collection_name


def test_create_collection_duplicate(client, test_collection_name):
    """測試創建重複集合（應該成功，返回現有集合）"""
    # 第一次創建
    response1 = client.post(
        "/api/v1/chromadb/collections", json={"name": test_collection_name}
    )
    assert response1.status_code == 201

    # 第二次創建（應該返回現有集合）
    response2 = client.post(
        "/api/v1/chromadb/collections", json={"name": test_collection_name}
    )
    assert response2.status_code == 201


def test_list_collections(client, test_collection_name):
    """測試列出集合"""
    # 創建幾個集合
    client.post(
        "/api/v1/chromadb/collections", json={"name": f"{test_collection_name}_1"}
    )
    client.post(
        "/api/v1/chromadb/collections", json={"name": f"{test_collection_name}_2"}
    )

    response = client.get("/api/v1/chromadb/collections")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["collections"]) >= 2


def test_delete_collection(client, test_collection_name):
    """測試刪除集合"""
    # 先創建
    client.post("/api/v1/chromadb/collections", json={"name": test_collection_name})

    # 刪除
    response = client.delete(f"/api/v1/chromadb/collections/{test_collection_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_delete_nonexistent_collection(client):
    """測試刪除不存在的集合"""
    response = client.delete("/api/v1/chromadb/collections/nonexistent")
    # 可能返回 200 或 400，取決於 ChromaDB 的行為
    assert response.status_code in [200, 400]


# ========== 文檔操作 API 測試 ==========


def test_add_documents(client, test_collection_name, test_embeddings):
    """測試添加文檔"""
    # 先創建集合
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": "doc1",
            "embeddings": test_embeddings[0],
            "documents": "Test document",
            "metadatas": {"source": "test"},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["added_count"] == 1


def test_add_multiple_documents(client, test_collection_name, test_embeddings):
    """測試批量添加文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": ["doc1", "doc2", "doc3"],
            "embeddings": test_embeddings[:3],
            "documents": ["Doc 1", "Doc 2", "Doc 3"],
            "metadatas": [{"id": 1}, {"id": 2}, {"id": 3}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["added_count"] == 3


def test_add_documents_invalid_embedding(client, test_collection_name):
    """測試添加無效嵌入向量的文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": "doc1",
            "embeddings": [0.1, 0.2, 0.3],  # 錯誤維度
            "documents": "Test",
        },
    )
    assert response.status_code == 400


def test_get_documents(client, test_collection_name, test_embeddings):
    """測試獲取文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": "doc1",
            "embeddings": test_embeddings[0],
            "documents": "Test document",
        },
    )

    # 獲取文檔
    response = client.get(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        params={"ids": "doc1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["ids"]) == 1


def test_get_documents_with_limit(client, test_collection_name, test_embeddings):
    """測試帶限制的獲取文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加多個文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": [f"doc{i}" for i in range(10)],
            "embeddings": test_embeddings[:10],
            "documents": [f"Doc {i}" for i in range(10)],
        },
    )

    # 獲取文檔（限制5個）
    response = client.get(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        params={"limit": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["ids"]) <= 5


def test_update_document(client, test_collection_name, test_embeddings):
    """測試更新文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={"ids": "doc1", "embeddings": test_embeddings[0], "documents": "Original"},
    )

    # 更新文檔
    response = client.put(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents/doc1",
        json={"documents": "Updated", "metadatas": {"updated": True}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_delete_document(client, test_collection_name, test_embeddings):
    """測試刪除文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={"ids": "doc1", "embeddings": test_embeddings[0], "documents": "Test"},
    )

    # 刪除文檔
    response = client.delete(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents/doc1"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


# ========== 向量檢索 API 測試 ==========


def test_query_documents(client, test_collection_name, test_embeddings):
    """測試向量檢索"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": ["doc1", "doc2"],
            "embeddings": test_embeddings[:2],
            "documents": ["Doc 1", "Doc 2"],
        },
    )

    # 查詢
    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/query",
        json={"query_embeddings": test_embeddings[0], "n_results": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["ids"][0]) > 0


def test_query_with_where_filter(client, test_collection_name, test_embeddings):
    """測試帶過濾條件的查詢"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    # 添加文檔
    client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/documents",
        json={
            "ids": ["doc1", "doc2"],
            "embeddings": test_embeddings[:2],
            "documents": ["Doc 1", "Doc 2"],
            "metadatas": [{"category": "A"}, {"category": "B"}],
        },
    )

    # 查詢（過濾 category=A）
    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/query",
        json={
            "query_embeddings": test_embeddings[0],
            "n_results": 10,
            "where": {"category": "A"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_query_validation_error(client, test_collection_name):
    """測試查詢參數驗證錯誤"""
    client.post("/api/v1/chromadb/collections", json={"name": test_collection_name})

    # 缺少查詢參數
    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/query",
        json={"n_results": 10},
    )
    assert response.status_code == 422  # Validation error


# ========== 批量操作 API 測試 ==========


def test_batch_add_documents(client, test_collection_name, test_embeddings):
    """測試批量添加文檔"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    items = [
        {
            "id": f"doc{i}",
            "embedding": test_embeddings[i],
            "metadata": {"index": i},
            "document": f"Document {i}",
        }
        for i in range(5)
    ]

    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/batch-add",
        json={"items": items, "batch_size": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["success"] == 5


def test_batch_add_with_custom_batch_size(
    client, test_collection_name, test_embeddings
):
    """測試自定義批次大小的批量添加"""
    client.post(
        "/api/v1/chromadb/collections",
        json={"name": test_collection_name, "embedding_dimension": 384},
    )

    items = [
        {"id": f"doc{i}", "embedding": test_embeddings[i], "document": f"Doc {i}"}
        for i in range(10)
    ]

    response = client.post(
        f"/api/v1/chromadb/collections/{test_collection_name}/batch-add",
        json={"items": items, "batch_size": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["success"] == 10


# ========== 錯誤處理測試 ==========


def test_invalid_collection_name(client):
    """測試無效的集合名稱"""
    response = client.post("/api/v1/chromadb/collections", json={"name": ""})  # 空名稱
    # 可能返回 400 或 422
    assert response.status_code in [400, 422]


def test_nonexistent_collection_operation(client):
    """測試對不存在集合的操作"""
    response = client.get("/api/v1/chromadb/collections/nonexistent/documents")
    # ChromaDB 可能會自動創建集合，所以可能返回 200
    assert response.status_code in [200, 400, 404]
