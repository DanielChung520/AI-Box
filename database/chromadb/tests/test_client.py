# 代碼功能說明: ChromaDB 客戶端測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""ChromaDB 客戶端單元測試"""

import pytest
import os
import shutil
from typing import List
from database.chromadb import ChromaDBClient, ChromaCollection
from database.chromadb.exceptions import (
    ChromaDBConnectionError,
    ChromaDBOperationError,
)
from database.chromadb.utils import (
    validate_embedding_dimension,
    normalize_embeddings,
    validate_metadata,
    batch_items,
    validate_collection_name,
)


@pytest.fixture
def chroma_client():
    """創建測試用的 ChromaDB 客戶端（持久化模式）"""
    test_dir = "./test_chroma_data"
    # 清理舊的測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    client = ChromaDBClient(mode="persistent", persist_directory=test_dir)
    yield client
    client.close()
    # 清理測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def test_collection(chroma_client):
    """創建測試用的集合"""
    collection = chroma_client.get_or_create_collection(
        "test_collection", metadata={"test": "true"}
    )
    yield ChromaCollection(collection, expected_embedding_dim=384)
    try:
        chroma_client.delete_collection("test_collection")
    except Exception:
        pass


@pytest.fixture
def test_embeddings() -> List[List[float]]:
    """生成測試用的嵌入向量（384維）"""
    import random

    return [[random.random() for _ in range(384)] for _ in range(10)]


# ========== 客戶端測試 ==========


def test_client_connection(chroma_client):
    """測試客戶端連接"""
    assert chroma_client.client is not None
    status = chroma_client.heartbeat()
    assert status["status"] == "healthy"


def test_client_connection_pool(chroma_client):
    """測試連線池功能"""
    # 測試連線池大小
    assert chroma_client.pool_size >= 1
    # 測試獲取和釋放連線
    client = chroma_client._acquire_client()
    assert client is not None
    chroma_client._release_client(client)


def test_client_connection_timeout(chroma_client):
    """測試連線超時"""
    # 填充連線池
    clients = []
    for _ in range(chroma_client.pool_size):
        clients.append(chroma_client._acquire_client())

    # 嘗試獲取額外的連線（應該超時）
    with pytest.raises(ChromaDBConnectionError):
        chroma_client._acquire_client()

    # 釋放連線
    for client in clients:
        chroma_client._release_client(client)


def test_create_collection(chroma_client):
    """測試創建集合"""
    collection = chroma_client.get_or_create_collection(
        "test_create", metadata={"test": "true"}
    )
    assert collection is not None
    chroma_client.delete_collection("test_create")


def test_list_collections(chroma_client):
    """測試列出集合"""
    chroma_client.get_or_create_collection("test_list1", metadata={"test": "true"})
    chroma_client.get_or_create_collection("test_list2", metadata={"test": "true"})
    collections = chroma_client.list_collections()
    assert "test_list1" in collections
    assert "test_list2" in collections
    chroma_client.delete_collection("test_list1")
    chroma_client.delete_collection("test_list2")


def test_delete_collection(chroma_client):
    """測試刪除集合"""
    chroma_client.get_or_create_collection("test_delete", metadata={"test": "true"})
    chroma_client.delete_collection("test_delete")
    collections = chroma_client.list_collections()
    assert "test_delete" not in collections


def test_reset_database(chroma_client):
    """測試重置資料庫"""
    chroma_client.get_or_create_collection("test_reset1", metadata={"test": "true"})
    chroma_client.get_or_create_collection("test_reset2", metadata={"test": "true"})
    chroma_client.reset()
    collections = chroma_client.list_collections()
    assert len(collections) == 0


def test_client_close(chroma_client):
    """測試關閉客戶端"""
    chroma_client.close()
    assert chroma_client.client is None
    assert chroma_client._current_clients == 0


# ========== 集合操作測試 ==========


def test_add_documents(test_collection):
    """測試添加文檔"""
    test_collection.add(
        ids="doc1", documents="This is a test document", metadatas={"source": "test"}
    )
    count = test_collection.count()
    assert count == 1


def test_add_documents_with_embeddings(test_collection, test_embeddings):
    """測試添加帶嵌入向量的文檔"""
    test_collection.add(
        ids="doc1",
        embeddings=test_embeddings[0],
        documents="Test document",
        metadatas={"source": "test"},
    )
    count = test_collection.count()
    assert count == 1


def test_add_multiple_documents(test_collection, test_embeddings):
    """測試批量添加文檔"""
    test_collection.add(
        ids=["doc1", "doc2", "doc3"],
        embeddings=test_embeddings[:3],
        documents=["Doc 1", "Doc 2", "Doc 3"],
        metadatas=[{"id": 1}, {"id": 2}, {"id": 3}],
    )
    count = test_collection.count()
    assert count == 3


def test_add_documents_embedding_validation(test_collection):
    """測試嵌入向量維度驗證"""
    # 錯誤的維度
    with pytest.raises(ChromaDBOperationError):
        test_collection.add(
            ids="doc1", embeddings=[[0.1, 0.2, 0.3]], documents="Test"  # 3維，期望384維
        )


def test_batch_add_documents(test_collection, test_embeddings):
    """測試批量添加文檔"""
    items = [
        {
            "id": f"doc{i}",
            "embedding": test_embeddings[i],
            "metadata": {"index": i},
            "document": f"Document {i}",
        }
        for i in range(5)
    ]
    result = test_collection.batch_add(items, batch_size=2)
    assert result["success"] == 5
    assert result["failed"] == 0
    assert test_collection.count() == 5


def test_batch_add_with_failure(test_collection):
    """測試批量添加中的失敗處理"""
    items = [
        {"id": "doc1", "document": "Valid doc"},
        {"id": "doc2", "embedding": [0.1, 0.2]},  # 錯誤維度
        {"id": "doc3", "document": "Valid doc 2"},
    ]
    result = test_collection.batch_add(items, batch_size=1)
    assert result["failed"] > 0
    assert result["success"] > 0


def test_query_documents(test_collection, test_embeddings):
    """測試查詢文檔"""
    # 添加測試文檔
    test_collection.add(
        ids=["doc1", "doc2"],
        embeddings=test_embeddings[:2],
        documents=["Test document 1", "Test document 2"],
        metadatas=[{"source": "test"}, {"source": "test"}],
    )

    # 使用嵌入向量查詢
    results = test_collection.query(query_embeddings=test_embeddings[0], n_results=2)
    assert len(results["ids"][0]) > 0


def test_query_with_where_filter(test_collection, test_embeddings):
    """測試帶過濾條件的查詢"""
    test_collection.add(
        ids=["doc1", "doc2"],
        embeddings=test_embeddings[:2],
        documents=["Doc 1", "Doc 2"],
        metadatas=[{"category": "A"}, {"category": "B"}],
    )

    results = test_collection.query(
        query_embeddings=test_embeddings[0], n_results=10, where={"category": "A"}
    )
    assert len(results["ids"][0]) >= 1


def test_get_documents(test_collection):
    """測試獲取文檔"""
    test_collection.add(
        ids="doc1", documents="Test document", metadatas={"source": "test"}
    )

    result = test_collection.get(ids="doc1")
    assert len(result["ids"]) == 1
    assert result["ids"][0] == "doc1"


def test_get_documents_with_limit(test_collection, test_embeddings):
    """測試帶限制的獲取"""
    test_collection.add(
        ids=[f"doc{i}" for i in range(10)],
        embeddings=test_embeddings[:10],
        documents=[f"Doc {i}" for i in range(10)],
    )

    result = test_collection.get(limit=5)
    assert len(result["ids"]) <= 5


def test_update_documents(test_collection):
    """測試更新文檔"""
    test_collection.add(
        ids="doc1", documents="Original document", metadatas={"source": "test"}
    )

    test_collection.update(
        ids="doc1", documents="Updated document", metadatas={"source": "updated"}
    )

    result = test_collection.get(ids="doc1")
    assert result["documents"][0] == "Updated document"


def test_delete_documents(test_collection):
    """測試刪除文檔"""
    test_collection.add(
        ids="doc1", documents="Test document", metadatas={"source": "test"}
    )

    test_collection.delete(ids="doc1")
    count = test_collection.count()
    assert count == 0


def test_delete_with_where_filter(test_collection, test_embeddings):
    """測試帶過濾條件的刪除"""
    test_collection.add(
        ids=["doc1", "doc2"],
        embeddings=test_embeddings[:2],
        metadatas=[{"category": "A"}, {"category": "B"}],
    )

    test_collection.delete(where={"category": "A"})
    count = test_collection.count()
    assert count == 1


def test_peek_collection(test_collection, test_embeddings):
    """測試查看集合"""
    test_collection.add(
        ids=[f"doc{i}" for i in range(5)], embeddings=test_embeddings[:5]
    )

    result = test_collection.peek(limit=3)
    assert len(result["ids"]) <= 3


def test_count_collection(test_collection, test_embeddings):
    """測試計數"""
    test_collection.add(
        ids=[f"doc{i}" for i in range(5)], embeddings=test_embeddings[:5]
    )
    assert test_collection.count() == 5


def test_modify_collection(test_collection):
    """測試修改集合"""
    test_collection.modify(metadata={"updated": True})
    # 驗證修改成功（通過獲取集合元數據）
    assert test_collection.collection.metadata.get("updated") is True


def test_namespace_isolation(test_collection, test_embeddings):
    """測試命名空間隔離"""
    # 創建帶命名空間的集合
    collection_with_ns = ChromaCollection(
        test_collection.collection, namespace="test_ns"
    )

    collection_with_ns.add(ids="doc1", embeddings=test_embeddings[0], documents="Test")

    # 驗證 metadata 包含命名空間
    result = collection_with_ns.get(ids="doc1")
    assert result["metadatas"][0].get("_namespace") == "test_ns"


# ========== 工具函數測試 ==========


def test_validate_embedding_dimension():
    """測試嵌入向量維度驗證"""
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    dim = validate_embedding_dimension(embeddings, expected_dim=3)
    assert dim == 3

    with pytest.raises(ValueError):
        validate_embedding_dimension(embeddings, expected_dim=4)


def test_normalize_embeddings():
    """測試嵌入向量標準化"""
    # 單個向量
    single = [0.1, 0.2, 0.3]
    result = normalize_embeddings(single)
    assert len(result) == 1
    assert len(result[0]) == 3

    # 向量列表
    multiple = [[0.1, 0.2], [0.3, 0.4]]
    result = normalize_embeddings(multiple)
    assert len(result) == 2


def test_validate_metadata():
    """測試 metadata 驗證"""
    # 正常情況
    validate_metadata({"source": "test"})

    # 必需字段
    validate_metadata({"source": "test", "id": 1}, required_fields=["source"])

    # 缺少必需字段
    with pytest.raises(ValueError):
        validate_metadata({"id": 1}, required_fields=["source"])


def test_batch_items():
    """測試分批功能"""
    items = list(range(10))
    batches = batch_items(items, batch_size=3)
    assert len(batches) == 4
    assert len(batches[0]) == 3
    assert len(batches[-1]) == 1


def test_validate_collection_name():
    """測試集合名稱驗證"""
    validate_collection_name("valid_name")

    with pytest.raises(ValueError):
        validate_collection_name("")

    with pytest.raises(ValueError):
        validate_collection_name("invalid/name")
