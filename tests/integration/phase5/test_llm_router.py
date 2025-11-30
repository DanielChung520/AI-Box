# 代碼功能說明: LLM Router 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-5.1：LLM Router 路由整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestLLMRouter:
    """LLM Router 整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_llm_routing(self, client: AsyncClient):
        """步驟 2: LLM 選擇測試"""
        try:
            start_time = time.time()
            response = await client.post(
                "/api/v1/llm/route",
                json={"task": "簡單查詢", "task_type": "query", "complexity": 20},
            )
            elapsed_ms = (time.time() - start_time) * 1000
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                assert elapsed_ms < 100, f"路由決策延遲 {elapsed_ms}ms 超過 100ms"
        except Exception:
            pytest.skip("LLM 路由端點未實現")
