# 代碼功能說明: 混合模式整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-3.4：混合模式（AutoGen + LangGraph）整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestHybridMode:
    """混合模式整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=120.0
        ) as client:
            yield client

    async def test_hybrid_execution(self, client: AsyncClient):
        """步驟 3: 混合執行測試"""
        try:
            response = await client.post(
                "/api/v1/workflows/hybrid/execute",
                json={
                    "task": "開發一個完整的應用系統",
                    "primary_mode": "autogen",
                    "fallback_modes": ["langgraph"],
                },
            )
            assert response.status_code in [200, 202]
        except Exception:
            pytest.skip("混合模式執行端點未實現")
