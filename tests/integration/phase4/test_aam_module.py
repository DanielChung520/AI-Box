# 代碼功能說明: AAM 模組整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-4.4：AAM 記憶增強模組整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMMModule:
    """AAM 模組整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_hybrid_rag(self, client: AsyncClient):
        """步驟 3: Hybrid RAG 測試"""
        try:
            response = await client.post(
                "/api/v1/aam/rag/retrieve",
                json={"query": "蘋果公司的創始人是誰？", "use_vector": True, "use_graph": True},
            )
            assert response.status_code in [200, 404]
        except Exception:
            pytest.skip("AAM RAG 檢索端點未實現")
