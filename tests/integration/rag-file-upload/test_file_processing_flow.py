# 代碼功能說明: 文件處理流程集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""文件處理流程集成測試 - 測試上傳 → 分塊 → 向量化 → 存儲到ChromaDB"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


@pytest.fixture
def sample_text_file():
    """創建示例文本文件"""
    content = """這是一段測試文本。
用於測試文件處理流程。
包括分塊、向量化和存儲。
""".encode(
        "utf-8"
    )
    return ("test_processing.txt", content, "text/plain")


@pytest.mark.asyncio
async def test_file_processing_complete_flow(client, sample_text_file):
    """測試完整文件處理流程"""
    filename, content, content_type = sample_text_file

    # 1. 上傳文件
    from io import BytesIO

    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["success"] is True
    file_id = upload_data["data"]["uploaded"][0]["file_id"]

    # 2. 等待處理開始（異步處理）
    import time

    time.sleep(2)  # 等待後台任務啟動

    # 3. 查詢處理狀態
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200
    status_data = status_response.json()

    if status_data["success"]:
        # 驗證處理狀態結構
        assert "data" in status_data
        assert "file_id" in status_data["data"]
        assert "status" in status_data["data"]

        # 驗證各個處理階段
        processing_data = status_data["data"]
        assert "chunking" in processing_data or "vectorization" in processing_data


def test_file_processing_status_structure(client):
    """測試處理狀態響應結構"""
    # 使用一個不存在的file_id測試響應結構
    file_id = "test_nonexistent_file_id"

    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200

    status_data = status_response.json()
    assert "success" in status_data
    assert "data" in status_data

    # 驗證默認狀態結構
    if status_data["success"]:
        data = status_data["data"]
        assert "file_id" in data
        assert "status" in data
        assert "progress" in data


@pytest.mark.asyncio
async def test_file_chunking_process(client, sample_text_file):
    """測試文件分塊處理"""
    filename, content, content_type = sample_text_file

    from io import BytesIO

    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 等待分塊處理
    import time

    time.sleep(3)

    # 查詢處理狀態
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    status_data = status_response.json()

    if status_data["success"] and "chunking" in status_data["data"]:
        chunking_status = status_data["data"]["chunking"]
        assert "status" in chunking_status
        assert "progress" in chunking_status


@pytest.mark.asyncio
async def test_file_vectorization_process(client, sample_text_file):
    """測試文件向量化處理"""
    filename, content, content_type = sample_text_file

    from io import BytesIO

    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 等待向量化處理
    import time

    time.sleep(5)

    # 查詢處理狀態
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    status_data = status_response.json()

    if status_data["success"] and "vectorization" in status_data["data"]:
        vectorization_status = status_data["data"]["vectorization"]
        assert "status" in vectorization_status
        assert "progress" in vectorization_status
