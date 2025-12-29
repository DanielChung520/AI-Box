# 代碼功能說明: 惡意文件檢測測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""惡意文件檢測測試 - 測試病毒文件、惡意代碼、路徑遍歷攻擊"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


def test_path_traversal_attack(client):
    """測試路徑遍歷攻擊防護"""
    content = b"\xe6\x83\xa1\xe6\x84\x8f\xe5\x85\xa7\xe5\xae\xb9"
    # 嘗試使用路徑遍歷攻擊
    malicious_filename = "../../../etc/passwd"
    files = {"files": (malicious_filename, BytesIO(content), "text/plain")}

    response = client.post("/api/v1/files/upload", files=files)

    # 應該拒絕或清理文件名
    if response.status_code == 200:
        data = response.json()
        # 文件名應該被清理，不包含路徑遍歷字符
        if data["success"]:
            uploaded_file = data["data"]["uploaded"][0]
            assert ".." not in uploaded_file["filename"]
            assert "/" not in uploaded_file["filename"] or uploaded_file["filename"].count("/") <= 1


def test_executable_file_rejection(client):
    """測試可執行文件拒絕"""
    # 模擬可執行文件內容
    content = b"MZ\x90\x00"  # PE文件頭
    files = {"files": ("malicious.exe", BytesIO(content), "application/x-msdownload")}

    response = client.post("/api/v1/files/upload", files=files)

    # 應該拒絕可執行文件
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        # 應該在errors中
        assert len(data["data"].get("errors", [])) > 0 or data["data"]["success_count"] == 0


def test_script_file_rejection(client):
    """測試腳本文件拒絕"""
    # 模擬惡意腳本
    content = b"#!/bin/bash\nrm -rf /\n"
    files = {"files": ("malicious.sh", BytesIO(content), "application/x-sh")}

    response = client.post("/api/v1/files/upload", files=files)

    # 應該拒絕腳本文件
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        assert len(data["data"].get("errors", [])) > 0 or data["data"]["success_count"] == 0


def test_file_size_limit(client):
    """測試文件大小限制"""
    # 創建超大文件（超過100MB限制）
    content = b"x" * (101 * 1024 * 1024)  # 101MB
    files = {"files": ("oversized.txt", BytesIO(content), "text/plain")}

    response = client.post("/api/v1/files/upload", files=files)

    # 應該拒絕超大文件
    assert response.status_code in [200, 400, 413]
    if response.status_code == 200:
        data = response.json()
        assert len(data["data"].get("errors", [])) > 0 or data["data"]["success_count"] == 0
