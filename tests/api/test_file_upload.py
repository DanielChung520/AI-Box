# 代碼功能說明: 文件上傳 API 測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件上傳 API 端點測試"""

import pytest
import os
import shutil
from fastapi.testclient import TestClient
from io import BytesIO

from services.api.main import app

# 設置測試環境變數
TEST_STORAGE_PATH = "./test_file_storage"


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    test_dir = TEST_STORAGE_PATH
    # 清理舊的測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    with TestClient(app) as test_client:
        yield test_client

    # 清理測試數據
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def sample_txt_file():
    """創建示例文本文件"""
    content = b"This is a test file content."
    return ("test.txt", content)


@pytest.fixture
def sample_md_file():
    """創建示例 Markdown 文件"""
    content = b"# Test Markdown\n\nThis is a test markdown file."
    return ("test.md", content)


@pytest.fixture
def large_file():
    """創建大文件（超過限制）"""
    content = b"x" * (105 * 1024 * 1024)  # 105MB
    return ("large.txt", content)


def test_upload_single_file(client, sample_txt_file):
    """測試單文件上傳"""
    filename, content = sample_txt_file

    files = {"files": (filename, BytesIO(content), "text/plain")}
    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["uploaded"]) == 1
    assert data["data"]["success_count"] == 1
    assert "file_id" in data["data"]["uploaded"][0]
    assert data["data"]["uploaded"][0]["filename"] == filename


def test_upload_multiple_files(client, sample_txt_file, sample_md_file):
    """測試多文件上傳"""
    files = [
        ("files", (sample_txt_file[0], BytesIO(sample_txt_file[1]), "text/plain")),
        ("files", (sample_md_file[0], BytesIO(sample_md_file[1]), "text/markdown")),
    ]

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["uploaded"]) == 2
    assert data["data"]["success_count"] == 2


def test_upload_invalid_extension(client):
    """測試上傳不支持的文件擴展名"""
    content = b"test content"
    files = {"files": ("test.exe", BytesIO(content), "application/x-msdownload")}

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert len(data["data"]["errors"]) == 1


def test_upload_file_too_large(client, large_file):
    """測試上傳過大的文件"""
    filename, content = large_file
    files = {"files": (filename, BytesIO(content), "text/plain")}

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert len(data["data"]["errors"]) == 1


def test_upload_empty_file(client):
    """測試上傳空文件"""
    files = {"files": ("empty.txt", BytesIO(b""), "text/plain")}

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False


def test_get_file_info(client, sample_txt_file):
    """測試獲取文件信息"""
    # 先上傳文件
    filename, content = sample_txt_file
    files = {"files": (filename, BytesIO(content), "text/plain")}
    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 獲取文件信息
    response = client.get(f"/api/v1/files/{file_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["file_id"] == file_id


def test_get_nonexistent_file(client):
    """測試獲取不存在的文件信息"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/files/{fake_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False


def test_delete_file(client, sample_txt_file):
    """測試刪除文件"""
    # 先上傳文件
    filename, content = sample_txt_file
    files = {"files": (filename, BytesIO(content), "text/plain")}
    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200
    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 刪除文件
    response = client.delete(f"/api/v1/files/{file_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # 驗證文件已刪除
    get_response = client.get(f"/api/v1/files/{file_id}")
    assert get_response.status_code == 404


def test_delete_nonexistent_file(client):
    """測試刪除不存在的文件"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/v1/files/{fake_id}")

    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False


def test_upload_partial_failure(client, sample_txt_file):
    """測試部分文件上傳失敗的情況"""
    files = [
        ("files", (sample_txt_file[0], BytesIO(sample_txt_file[1]), "text/plain")),
        ("files", ("invalid.exe", BytesIO(b"test"), "application/x-msdownload")),
    ]

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 207  # Multi-Status
    data = response.json()
    assert data["success"] is True
    assert data["data"]["success_count"] == 1
    assert data["data"]["error_count"] == 1
