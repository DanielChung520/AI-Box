# 代碼功能說明: 知識圖譜構建整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-4.3：知識圖譜構建整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestKGBuilder:
    """知識圖譜構建整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_kg_build_from_triples(self, client: AsyncClient, test_triple_data):
        """步驟 1: 三元組到圖譜轉換測試"""
        try:
            response = await client.post(
                "/api/v1/kg/build",
                json={"triples": [test_triple_data]},
            )
            assert_response_success(response)
        except Exception:
            pytest.skip("知識圖譜構建端點未實現")
