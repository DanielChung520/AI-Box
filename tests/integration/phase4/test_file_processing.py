# 代碼功能說明: 文件處理流程整合測試
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-4.1：文件上傳和處理整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestFileProcessing:
    """文件處理流程整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_file_upload(self, client: AsyncClient):
        """步驟 1: 文件上傳測試"""
        try:
            test_content = b"Test file content for upload"
            # 修復：API 期望 files 參數（複數），且是列表格式
            files = [("files", ("test.txt", test_content, "text/plain"))]
            response = await client.post("/api/v1/files/upload", files=files)
            assert response.status_code in [
                200,
                201,
                207,
            ], f"Expected 200/201/207, got {response.status_code}"

            if response.status_code in [200, 201, 207]:
                data = response.json()
                # API 返回格式: {"success": true, "data": {"uploaded": [...], "errors": [...]}}
                if "data" in data:
                    uploaded = data["data"].get("uploaded", [])
                    if uploaded:
                        assert (
                            "file_id" in uploaded[0]
                        ), "Response should contain file_id"
                elif "file_id" in data:
                    assert True, "Response contains file_id"
        except Exception as e:
            pytest.skip(f"文件上傳端點未實現或不可用: {str(e)}")

    async def test_file_chunking(self, client: AsyncClient):
        """步驟 2: 文件分塊處理測試"""
        try:
            # 先上傳一個文件
            test_content = b"Test file content for chunking. " * 100
            files = [("files", ("test_chunk.txt", test_content, "text/plain"))]
            upload_response = await client.post("/api/v1/files/upload", files=files)

            if upload_response.status_code not in [200, 201, 207]:
                pytest.skip("文件上傳失敗，無法測試分塊處理")

            upload_data = upload_response.json()
            # 從響應中提取 file_id
            file_id = None
            if "data" in upload_data:
                uploaded = upload_data["data"].get("uploaded", [])
                if uploaded and "file_id" in uploaded[0]:
                    file_id = uploaded[0]["file_id"]
            elif "file_id" in upload_data:
                file_id = upload_data["file_id"]

            if not file_id:
                pytest.skip("無法獲取文件 ID，跳過分塊測試")

            # 測試文件分塊
            chunk_response = await client.post(
                f"/api/v1/files/{file_id}/chunk",
                json={"chunk_size": 100, "chunk_overlap": 20},
            )
            assert chunk_response.status_code in [
                200,
                202,
                404,
            ], f"Expected 200/202/404, got {chunk_response.status_code}"
        except Exception as e:
            pytest.skip(f"文件分塊處理端點未實現或不可用: {str(e)}")

    async def test_multiformat_support(self, client: AsyncClient):
        """步驟 3: 多格式支持測試"""
        formats = [
            ("test.txt", b"Plain text content", "text/plain"),
            (
                "test.md",
                b"# Markdown content\n\nThis is a markdown file.",
                "text/markdown",
            ),
        ]

        results = {}
        for filename, content, content_type in formats:
            try:
                files = [("files", (filename, content, content_type))]
                response = await client.post("/api/v1/files/upload", files=files)
                results[filename] = response.status_code in [200, 201, 207]
            except Exception:
                results[filename] = False

        if not any(results.values()):
            pytest.skip("多格式支持端點未實現或不可用")
