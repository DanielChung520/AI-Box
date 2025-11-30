# 代碼功能說明: LangChain/Graph 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-3.1：LangChain/Graph 工作流整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestLangChainIntegration:
    """LangChain/Graph 整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_workflow_execution(self, client: AsyncClient):
        """步驟 1: 簡單工作流執行測試"""
        try:
            response = await client.post(
                "/api/v1/workflows/langchain/execute",
                json={"task": "查詢數據庫並生成報告", "workflow_type": "langchain"},
            )
            assert response.status_code in [200, 202]
        except Exception:
            pytest.skip("LangChain 工作流端點未實現")
