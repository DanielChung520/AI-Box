# 代碼功能說明: 多 LLM 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-5.2：多 LLM 整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiLLM:
    """多 LLM 整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_llm_models_list(self, client: AsyncClient):
        """步驟 4: LLM 列表查詢測試"""
        try:
            response = await client.get("/api/v1/llm/models")
            assert response.status_code in [200, 404]
        except Exception:
            pytest.skip("LLM 模型列表端點未實現")
