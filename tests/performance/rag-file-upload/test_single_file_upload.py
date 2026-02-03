# 代碼功能說明: 單文件上傳性能測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""單文件上傳性能測試 - 測試上傳時間、響應時間"""

import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


def test_small_file_upload_performance(client):
    """測試小文件上傳性能（< 1MB）"""
    content = b"x" * (100 * 1024)  # 100KB
    files = {"files": ("small_file.txt", BytesIO(content), "text/plain")}

    start_time = time.time()
    response = client.post("/api/v1/files/upload", files=files)
    end_time = time.time()

    assert response.status_code == 200
    upload_time = end_time - start_time

    # 小文件應該在1秒內完成上傳
    assert upload_time < 1.0
    print(f"小文件上傳時間: {upload_time:.2f}秒")


def test_medium_file_upload_performance(client):
    """測試中等文件上傳性能（1-10MB）"""
    content = b"x" * (5 * 1024 * 1024)  # 5MB
    files = {"files": ("medium_file.txt", BytesIO(content), "text/plain")}

    start_time = time.time()
    response = client.post("/api/v1/files/upload", files=files)
    end_time = time.time()

    assert response.status_code == 200
    upload_time = end_time - start_time

    # 中等文件應該在5秒內完成上傳
    assert upload_time < 5.0
    print(f"中等文件上傳時間: {upload_time:.2f}秒")


def test_large_file_upload_performance(client):
    """測試大文件上傳性能（10-50MB）"""
    content = b"x" * (20 * 1024 * 1024)  # 20MB
    files = {"files": ("large_file.txt", BytesIO(content), "text/plain")}

    start_time = time.time()
    response = client.post("/api/v1/files/upload", files=files)
    end_time = time.time()

    assert response.status_code == 200
    upload_time = end_time - start_time

    # 大文件應該在30秒內完成上傳
    assert upload_time < 30.0
    print(f"大文件上傳時間: {upload_time:.2f}秒")


def test_upload_response_time(client):
    """測試上傳響應時間"""
    content = "測試響應時間的文件內容".encode("utf-8")
    files = {"files": ("response_test.txt", BytesIO(content), "text/plain")}

    start_time = time.time()
    response = client.post("/api/v1/files/upload", files=files)
    end_time = time.time()

    response_time = end_time - start_time

    assert response.status_code == 200
    # 響應時間應該小於500ms
    assert response_time < 0.5
    print(f"上傳響應時間: {response_time*1000:.2f}毫秒")
