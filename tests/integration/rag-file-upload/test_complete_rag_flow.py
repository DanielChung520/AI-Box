# 代碼功能說明: 完整RAG流程端到端測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""完整RAG流程端到端測試 - 測試上傳 → 處理 → 查詢 → 下載 → 刪除（使用階段4的文件管理功能）"""

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
def sample_rag_file():
    """創建RAG測試文件"""
    content = """這是一份測試文檔。
用於測試完整的RAG流程。
包括文件上傳、分塊、向量化、知識圖譜提取。
以及文件管理功能，如查詢、下載、刪除。
""".encode(
        "utf-8"
    )
    return ("rag_test.txt", content, "text/plain")


@pytest.mark.asyncio
async def test_complete_rag_flow_with_file_management(client, sample_rag_file):
    """測試完整RAG流程（包含文件管理）"""
    filename, content, content_type = sample_rag_file

    # ========== 步驟1: 文件上傳 ==========
    files = {"files": (filename, BytesIO(content), content_type)}
    upload_response = client.post("/api/v1/files/upload", files=files)

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["success"] is True
    file_id = upload_data["data"]["uploaded"][0]["file_id"]

    # ========== 步驟2: 查詢文件列表 ==========
    file_list_response = client.get("/api/v1/files?limit=10&offset=0")
    assert file_list_response.status_code == 200

    file_list_data = file_list_response.json()
    if file_list_data["success"]:
        # 驗證文件在列表中
        files_in_list = file_list_data["data"]["files"]
        file_ids = [f["file_id"] for f in files_in_list]
        assert file_id in file_ids

    # ========== 步驟3: 查詢文件元數據 ==========
    metadata_response = client.get(f"/api/v1/files/{file_id}/metadata")
    assert metadata_response.status_code == 200

    metadata_data = metadata_response.json()
    if metadata_data["success"]:
        assert metadata_data["data"]["file_id"] == file_id
        assert metadata_data["data"]["filename"] == filename

    # ========== 步驟4: 等待處理完成 ==========
    max_wait_time = 30  # 最多等待30秒
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        if status_data["success"]:
            processing_status = status_data["data"].get("status", "pending")
            if processing_status == "completed":
                break

        time.sleep(2)

    # ========== 步驟5: 查詢處理狀態 ==========
    final_status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert final_status_response.status_code == 200

    final_status_data = final_status_response.json()
    if final_status_data["success"]:
        # 驗證處理完成
        assert final_status_data["data"]["status"] == "completed"
        assert final_status_data["data"]["progress"] == 100

    # ========== 步驟6: 查詢KG統計（如果啟用） ==========
    kg_stats_response = client.get(f"/api/v1/files/{file_id}/kg/stats")
    assert kg_stats_response.status_code == 200

    kg_stats_data = kg_stats_response.json()
    if kg_stats_data["success"]:
        assert "data" in kg_stats_data
        assert "file_id" in kg_stats_data["data"]

    # ========== 步驟7: 文件搜索 ==========
    search_response = client.get(f"/api/v1/files/search?query={filename.split('.')[0]}&limit=10")
    assert search_response.status_code == 200

    search_data = search_response.json()
    if search_data["success"]:
        # 驗證搜索結果包含該文件
        search_files = search_data["data"]["files"]
        search_file_ids = [f["file_id"] for f in search_files]
        assert file_id in search_file_ids

    # ========== 步驟8: 文件預覽 ==========
    preview_response = client.get(f"/api/v1/files/{file_id}/preview")
    assert preview_response.status_code == 200

    preview_data = preview_response.json()
    if preview_data["success"]:
        assert "data" in preview_data
        assert "content" in preview_data["data"]

    # ========== 步驟9: 文件下載 ==========
    download_response = client.get(f"/api/v1/files/{file_id}/download")
    assert download_response.status_code == 200
    # 下載響應應該是文件流
    assert download_response.headers.get("content-type") is not None

    # ========== 步驟10: 文件刪除 ==========
    delete_response = client.delete(f"/api/v1/files/{file_id}")
    assert delete_response.status_code == 200

    delete_data = delete_response.json()
    assert delete_data["success"] is True

    # ========== 步驟11: 驗證文件已刪除 ==========
    # 查詢文件信息應該返回404
    info_response = client.get(f"/api/v1/files/{file_id}")
    assert info_response.status_code == 404


def test_file_management_search_functionality(client):
    """測試文件管理搜索功能"""
    # 上傳幾個測試文件
    files_to_upload = [
        ("search_test_1.txt", BytesIO("測試文件1".encode("utf-8")), "text/plain"),
        ("search_test_2.txt", BytesIO("測試文件2".encode("utf-8")), "text/plain"),
        ("other_file.txt", BytesIO("其他文件".encode("utf-8")), "text/plain"),
    ]

    uploaded_file_ids = []
    for filename, content, content_type in files_to_upload:
        files = {"files": (filename, content, content_type)}
        upload_response = client.post("/api/v1/files/upload", files=files)
        if upload_response.status_code == 200:
            file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]
            uploaded_file_ids.append(file_id)

    # 搜索包含"search_test"的文件
    search_response = client.get("/api/v1/files/search?query=search_test&limit=10")
    assert search_response.status_code == 200

    search_data = search_response.json()
    if search_data["success"]:
        search_files = search_data["data"]["files"]
        # 應該找到至少2個文件
        assert len(search_files) >= 2

        # 驗證文件名包含搜索關鍵字
        for file_metadata in search_files:
            assert "search_test" in file_metadata["filename"].lower()

    # 清理測試文件
    for file_id in uploaded_file_ids:
        try:
            client.delete(f"/api/v1/files/{file_id}")
        except:
            pass


def test_file_tree_structure(client):
    """測試文件樹結構功能"""
    # 上傳文件（可以指定task_id）
    content = "測試文件樹結構".encode("utf-8")
    files = {"files": ("tree_test.txt", BytesIO(content), "text/plain")}

    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200

    file_id = upload_response.json()["data"]["uploaded"][0]["file_id"]

    # 查詢文件樹
    tree_response = client.get("/api/v1/files/tree")
    assert tree_response.status_code == 200

    tree_data = tree_response.json()
    if tree_data["success"]:
        assert "data" in tree_data
        assert "tree" in tree_data["data"]
        assert "total_tasks" in tree_data["data"]
        assert "total_files" in tree_data["data"]

    # 清理
    try:
        client.delete(f"/api/v1/files/{file_id}")
    except:
        pass
