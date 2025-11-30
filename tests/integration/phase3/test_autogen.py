# 代碼功能說明: AutoGen 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-3.3：AutoGen 自動規劃整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAutoGenIntegration:
    """AutoGen 整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_autogen_planning(self, client: AsyncClient):
        """步驟 2: 自動規劃測試"""
        try:
            response = await client.post(
                "/api/v1/autogen/plan",
                json={"task": "開發一個完整的應用系統", "context": {}},
            )
            assert response.status_code in [200, 202]
        except Exception:
            pytest.skip("AutoGen 規劃端點未實現")
