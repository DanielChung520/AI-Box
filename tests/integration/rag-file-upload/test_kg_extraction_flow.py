# 代碼功能說明: 知識圖譜提取流程集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""知識圖譜提取流程集成測試 - 測試上傳 → 分塊 → KG提取 → 存儲到ArangoDB"""

import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


@pytest.fixture
def sample_kg_text_file():
    """創建包含實體和關係的測試文本"""
    content = """蘋果是一種水果。
蘋果富含維生素C。
維生素C對人體有益。
""".encode(
        "utf-8"
    )
    return ("test_kg.txt", content, "text/plain")


@pytest.mark.asyncio
async def test_kg_extraction_complete_flow(client, sample_kg_text_file):
    """測試完整知識圖譜提取流程"""
    filename, content, content_type = sample_kg_text_file

    # 1. 上傳文件
    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["success"] is True
    file_id = upload_data["data"]["uploaded"][0]["file_id"]

    # 2. 等待KG提取處理
    time.sleep(10)  # KG提取需要更長時間

    # 3. 查詢處理狀態
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200
    status_data = status_response.json()

    if status_data["success"]:
        processing_data = status_data["data"]

        # 驗證KG提取狀態
        if "kg_extraction" in processing_data:
            kg_status = processing_data["kg_extraction"]
            assert "status" in kg_status
            assert "progress" in kg_status

            # 如果處理完成，驗證統計信息
            if kg_status.get("status") == "completed":
                assert "triples_count" in kg_status
                assert "entities_count" in kg_status
                assert "relations_count" in kg_status


def test_kg_stats_endpoint(client, sample_kg_text_file):
    """測試KG統計信息端點"""
    filename, content, content_type = sample_kg_text_file

    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 等待處理
    time.sleep(10)

    # 查詢KG統計
    stats_response = client.get(f"/api/v1/files/{file_id}/kg/stats")
    assert stats_response.status_code == 200

    stats_data = stats_response.json()
    if stats_data["success"]:
        assert "data" in stats_data
        assert "file_id" in stats_data["data"]


def test_kg_triples_endpoint(client, sample_kg_text_file):
    """測試KG三元組查詢端點"""
    filename, content, content_type = sample_kg_text_file

    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 等待處理
    time.sleep(10)

    # 查詢三元組
    triples_response = client.get(f"/api/v1/files/{file_id}/kg/triples")
    assert triples_response.status_code == 200

    triples_data = triples_response.json()
    if triples_data["success"]:
        assert "data" in triples_data
        assert isinstance(triples_data["data"], list)
