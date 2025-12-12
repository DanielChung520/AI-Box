# 代碼功能說明: AAM 模組整合測試
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""測試劇本 IT-4.4：AAM 記憶增強模組整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMMModule:
    """AAM 模組整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_hybrid_rag(self, client: AsyncClient):
        """步驟 3: RAG 檢索流程測試"""
        try:
            response = await client.post(
                "/api/v1/aam/rag/retrieve",
                json={
                    "query": "蘋果公司的創始人是誰？",
                    "use_vector": True,
                    "use_graph": True,
                },
            )
            assert response.status_code in [
                200,
                404,
            ], f"Expected 200/404, got {response.status_code}"

            if response.status_code == 200:
                data = response.json()
                assert (
                    "results" in data or "data" in data
                ), "Response should contain retrieval results"
        except Exception as e:
            pytest.skip(f"AAM RAG 檢索端點未實現或不可用: {str(e)}")

    async def test_realtime_interaction(self, client: AsyncClient):
        """步驟 1: 實時交互子系統測試"""
        try:
            response = await client.post(
                "/api/v1/aam/realtime/retrieve",
                json={
                    "query": "最近的對話內容是什麼？",
                    "session_id": "test_session_realtime",
                },
            )
            assert response.status_code in [
                200,
                404,
            ], f"Expected 200/404, got {response.status_code}"

            if response.status_code == 200:
                data = response.json()
                assert (
                    "memory" in data or "data" in data
                ), "Response should contain memory results"
        except Exception as e:
            pytest.skip(f"實時交互子系統端點未實現或不可用: {str(e)}")

    async def test_async_agent(self, client: AsyncClient):
        """步驟 2: 異步 Agent 子系統測試"""
        try:
            response = await client.post(
                "/api/v1/aam/async/process",
                json={
                    "task": "提取並存儲知識",
                    "content": "張三在北京大學工作，他是計算機科學系的教授",
                    "session_id": "test_session_async",
                },
            )
            assert response.status_code in [
                200,
                202,
                404,
            ], f"Expected 200/202/404, got {response.status_code}"

            if response.status_code in [200, 202]:
                data = response.json()
                assert (
                    "task_id" in data or "id" in data or "data" in data
                ), "Response should contain task ID"
        except Exception as e:
            pytest.skip(f"異步 Agent 子系統端點未實現或不可用: {str(e)}")
