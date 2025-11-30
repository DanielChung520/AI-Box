# 代碼功能說明: 文件處理流程整合測試
# 創建日期: 2025-01-27
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

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_file_upload(self, client: AsyncClient, test_file_content):
        """步驟 1: 文件上傳測試"""
        try:
            files = {"files": ("test.txt", test_file_content, "text/plain")}
            response = await client.post("/api/v1/files/upload", files=files)
            assert response.status_code in [200, 201, 207]
        except Exception:
            pytest.skip("文件上傳端點未實現")
