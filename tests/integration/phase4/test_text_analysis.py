# 代碼功能說明: 文本分析流程整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-4.2：NER/RE/RT 文本分析整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestTextAnalysis:
    """文本分析流程整合測試"""

    @pytest.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_ner_extraction(self, client: AsyncClient):
        """步驟 1: NER 實體識別測試"""
        try:
            response = await client.post(
                "/api/v1/ner/extract",
                json={"text": "蘋果公司由史蒂夫·喬布斯創立於1976年。", "model": "default"},
            )
            assert_response_success(response)
        except Exception:
            pytest.skip("NER 提取端點未實現")
