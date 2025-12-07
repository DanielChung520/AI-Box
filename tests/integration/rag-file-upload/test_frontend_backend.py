# 代碼功能說明: 前端-後端集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""前端-後端集成測試 - 測試前端上傳 → 後端處理 → 狀態查詢"""

import pytest
import time
from fastapi.testclient import TestClient
from io import BytesIO

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


def test_frontend_upload_backend_processing(client):
    """測試前端上傳後端處理流程"""
    # 模擬前端上傳請求
    content = "前端上傳的測試文件內容".encode("utf-8")
    files = {"files": ("frontend_test.txt", BytesIO(content), "text/plain")}

    # 1. 前端發送上傳請求
    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200

    upload_data = upload_response.json()
    assert upload_data["success"] is True
    file_id = upload_data["data"]["uploaded"][0]["file_id"]

    # 2. 前端查詢上傳進度
    progress_response = client.get(f"/api/v1/files/upload/{file_id}/progress")
    assert progress_response.status_code == 200

    progress_data = progress_response.json()
    assert progress_data["success"] is True
    assert "data" in progress_data

    # 3. 等待後端處理
    time.sleep(3)

    # 4. 前端查詢處理狀態
    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200

    status_data = status_response.json()
    assert status_data["success"] is True
    assert "data" in status_data
    assert "file_id" in status_data["data"]


def test_backend_status_polling(client):
    """測試後端狀態輪詢機制"""
    content = "測試輪詢的文件內容".encode("utf-8")
    files = {"files": ("polling_test.txt", BytesIO(content), "text/plain")}

    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 模擬前端輪詢狀態
    max_polls = 5
    for i in range(max_polls):
        status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        if status_data["success"]:
            processing_status = status_data["data"].get("status", "pending")
            progress = status_data["data"].get("progress", 0)

            # 如果處理完成，停止輪詢
            if processing_status == "completed":
                assert progress == 100
                break

        time.sleep(1)
