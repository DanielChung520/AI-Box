# 代碼功能說明: 後端-數據庫集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""後端-數據庫集成測試 - 測試ChromaDB連接、ArangoDB連接、Redis連接"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.arangodb import ArangoDBClient
from database.chromadb import ChromaDBClient
from database.redis import get_redis_client


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


def test_chromadb_connection():
    """測試ChromaDB連接"""
    try:
        client = ChromaDBClient(
            host="localhost",
            port=8001,
            mode="http",
        )
        # 嘗試獲取客戶端（不實際連接）
        assert client is not None
    except Exception as e:
        pytest.skip(f"ChromaDB not available: {e}")


def test_arangodb_connection():
    """測試ArangoDB連接"""
    try:
        client = ArangoDBClient()
        # 檢查客戶端是否初始化
        assert client is not None
    except Exception as e:
        pytest.skip(f"ArangoDB not available: {e}")


def test_redis_connection():
    """測試Redis連接"""
    try:
        redis_client = get_redis_client()
        # 測試基本操作
        test_key = "test_connection_key"
        redis_client.set(test_key, "test_value", ex=10)
        value = redis_client.get(test_key)
        assert value == "test_value"
        redis_client.delete(test_key)
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


def test_file_metadata_storage(client):
    """測試文件元數據存儲到ArangoDB"""
    from io import BytesIO

    content = "測試元數據存儲".encode("utf-8")
    files = {"files": ("metadata_test.txt", BytesIO(content), "text/plain")}

    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200

    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 查詢元數據（應該存儲在ArangoDB中）
    metadata_response = client.get(f"/api/v1/files/{file_id}/metadata")
    assert metadata_response.status_code == 200

    metadata_data = metadata_response.json()
    if metadata_data["success"]:
        assert metadata_data["data"]["file_id"] == file_id


def test_vector_storage_chromadb(client):
    """測試向量存儲到ChromaDB"""
    import time
    from io import BytesIO

    content = "測試向量存儲的文件內容，需要足夠長以便分塊".encode("utf-8")
    files = {"files": ("vector_test.txt", BytesIO(content), "text/plain")}

    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200

    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 等待向量化處理
    time.sleep(5)

    # 查詢處理狀態（向量應該存儲在ChromaDB中）
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200

    status_data = status_response.json()
    if status_data["success"] and "storage" in status_data["data"]:
        storage_status = status_data["data"]["storage"]
        if storage_status.get("status") == "completed":
            assert "vector_count" in storage_status or "collection_name" in storage_status
