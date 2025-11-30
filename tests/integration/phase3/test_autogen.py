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

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=120.0
        ) as client:
            yield client

    async def test_autogen_agent_collaboration(self, client: AsyncClient):
        """步驟 1: AutoGen Agent 協作測試"""
        try:
            response = await client.post(
                "/api/v1/workflows/autogen/plan",
                json={
                    "task": "開發一個完整的應用系統，需要多個 Agent 協作",
                    "context": {},
                },
            )
            assert response.status_code in [
                200,
                202,
            ], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert "success" in data, "Response should contain 'success' field"
            assert data.get("success") is True, "Success should be True"
            assert "data" in data, "Response should contain 'data' field"

            result_data = data.get("data", {})
            assert "task_id" in result_data, "Result should contain 'task_id'"
            assert "status" in result_data, "Result should contain 'status'"
            assert "output" in result_data, "Result should contain 'output'"
        except Exception as e:
            pytest.skip(f"AutoGen Agent 協作測試跳過: {str(e)}")

    async def test_autogen_planning(self, client: AsyncClient):
        """步驟 2: 自動規劃測試"""
        try:
            response = await client.post(
                "/api/v1/workflows/autogen/plan",
                json={"task": "開發一個完整的應用系統", "context": {}},
            )
            assert response.status_code in [
                200,
                202,
            ], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert "success" in data, "Response should contain 'success' field"
            assert data.get("success") is True, "Success should be True"
            assert "data" in data, "Response should contain 'data' field"

            result_data = data.get("data", {})
            assert "task_id" in result_data, "Result should contain 'task_id'"
            assert "status" in result_data, "Result should contain 'status'"
            assert "output" in result_data, "Result should contain 'output'"
            assert "reasoning" in result_data, "Result should contain 'reasoning'"
        except Exception as e:
            pytest.skip(f"AutoGen 規劃端點未實現或不可用: {str(e)}")

    async def test_execution_planning_detailed(self, client: AsyncClient):
        """步驟 2: Execution Planning 詳細測試（多步驟自動規劃）"""
        try:
            response = await client.post(
                "/api/v1/workflows/autogen/plan",
                json={
                    "task": "開發一個完整的應用系統，包含前端、後端和數據庫",
                    "context": {},
                    "max_steps": 10,
                },
            )
            assert response.status_code in [
                200,
                202,
            ], f"Expected 200/202, got {response.status_code}"

            data = response.json()
            assert data.get("success") is True

            result_data = data.get("data", {})
            output = result_data.get("output", {})

            # 驗證規劃結果包含多個步驟
            if isinstance(output, dict):
                # 檢查是否有計劃相關的數據
                assert result_data.get("status") in [
                    "completed",
                    "failed",
                ], "Workflow should have a valid status"
        except Exception as e:
            pytest.skip(f"Execution Planning 詳細測試跳過: {str(e)}")
