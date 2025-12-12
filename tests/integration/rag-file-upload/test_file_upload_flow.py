# 代碼功能說明: 文件上傳流程集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""文件上傳流程集成測試 - 測試文件上傳 → 存儲 → 返回file_id"""

import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient
from io import BytesIO

from api.main import app


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


@pytest.fixture
def temp_storage():
    """創建臨時存儲目錄"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_txt_file():
    """創建示例文本文件"""
    content = b"This is a test file content for upload flow testing."
    return ("test_upload.txt", content, "text/plain")


@pytest.fixture
def sample_pdf_file():
    """創建示例PDF文件（模擬）"""
    # 簡化的PDF文件頭
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    return ("test_upload.pdf", content, "application/pdf")


def test_upload_file_complete_flow(client, sample_txt_file):
    """測試完整文件上傳流程"""
    filename, content, content_type = sample_txt_file

    files = {"files": (filename, BytesIO(content), content_type)}
    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "uploaded" in data["data"]
    assert len(data["data"]["uploaded"]) == 1

    uploaded_file = data["data"]["uploaded"][0]
    assert "file_id" in uploaded_file
    assert uploaded_file["filename"] == filename
    assert uploaded_file["file_size"] == len(content)

    file_id = uploaded_file["file_id"]

    # 驗證文件信息可以查詢
    info_response = client.get(f"/api/v1/files/{file_id}")
    assert info_response.status_code == 200
    info_data = info_response.json()
    assert info_data["success"] is True


def test_upload_multiple_files_flow(client, sample_txt_file, sample_pdf_file):
    """測試多文件上傳流程"""
    files = [
        (
            "files",
            (sample_txt_file[0], BytesIO(sample_txt_file[1]), sample_txt_file[2]),
        ),
        (
            "files",
            (sample_pdf_file[0], BytesIO(sample_pdf_file[1]), sample_pdf_file[2]),
        ),
    ]

    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["uploaded"]) == 2

    # 驗證每個文件都有file_id
    for uploaded_file in data["data"]["uploaded"]:
        assert "file_id" in uploaded_file
        file_id = uploaded_file["file_id"]

        # 驗證文件可以查詢
        info_response = client.get(f"/api/v1/files/{file_id}")
        assert info_response.status_code == 200


def test_upload_file_with_metadata(client, sample_txt_file):
    """測試文件上傳並創建元數據"""
    filename, content, content_type = sample_txt_file

    files = {"files": (filename, BytesIO(content), content_type)}
    response = client.post("/api/v1/files/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    file_id = data["data"]["uploaded"][0]["file_id"]

    # 驗證元數據已創建
    metadata_response = client.get(f"/api/v1/files/{file_id}/metadata")
    assert metadata_response.status_code == 200
    metadata_data = metadata_response.json()
    assert metadata_data["success"] is True
    assert metadata_data["data"]["file_id"] == file_id
    assert metadata_data["data"]["filename"] == filename


def test_upload_file_validation(client):
    """測試文件上傳驗證"""
    # 測試不支持的文件類型
    content = b"test content"
    files = {"files": ("test.exe", BytesIO(content), "application/x-msdownload")}

    response = client.post("/api/v1/files/upload", files=files)

    # 應該返回錯誤或部分成功
    assert response.status_code in [200, 400]
    data = response.json()

    if response.status_code == 200:
        # 部分成功的情況
        assert len(data["data"].get("errors", [])) > 0
    else:
        # 完全失敗的情況
        assert data["success"] is False
