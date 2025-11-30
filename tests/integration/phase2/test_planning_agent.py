# 代碼功能說明: Planning Agent 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-2.3：Planning Agent 計劃生成整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestPlanningAgent:
    """Planning Agent 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=60.0
        ) as client:
            yield client

    async def test_plan_generation(self, client: AsyncClient):
        """步驟 1: 計劃生成測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/agents/planning/generate",
            json={"task": "開發一個簡單的待辦事項應用", "context": {}},
        )
        elapsed = time.time() - start_time

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Planning Agent API 端點未實現")

        assert_response_success(response)
        assert elapsed < 5, f"響應時間 {elapsed}s 超過 5 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應內容
        assert "plan_id" in result_data, "響應缺少 plan_id"
        assert "steps" in result_data, "響應缺少 steps"
        assert isinstance(result_data.get("steps"), list), "steps 應該是列表"

        # 驗證計劃步驟
        steps = result_data.get("steps", [])
        if steps:
            step = steps[0]
            assert "step_id" in step, "步驟缺少 step_id"
            assert "description" in step, "步驟缺少 description"

    async def test_plan_validation(self, client: AsyncClient):
        """步驟 2: 計劃驗證測試"""
        # 先生成一個計劃
        response = await client.post(
            "/api/v1/agents/planning/generate",
            json={"task": "測試計劃驗證", "context": {}},
        )

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Planning Agent API 端點未實現")

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})

            # 驗證計劃格式
            assert "plan_id" in result_data, "計劃缺少 plan_id"
            assert "steps" in result_data, "計劃缺少 steps"
            assert isinstance(result_data.get("steps"), list), "steps 應該是列表"

            # 驗證計劃步驟完整性
            steps = result_data.get("steps", [])
            for step in steps:
                assert "step_id" in step, "步驟缺少 step_id"
                assert "step_number" in step, "步驟缺少 step_number"
                assert "description" in step, "步驟缺少 description"
                assert "action" in step, "步驟缺少 action"

            # 驗證計劃可行性評分
            if "feasibility_score" in result_data:
                feasibility_score = result_data.get("feasibility_score")
                assert isinstance(
                    feasibility_score, (int, float)
                ), "feasibility_score 應該是數字"
                assert (
                    0.0 <= feasibility_score <= 1.0
                ), f"feasibility_score 應在 0.0-1.0 範圍內，實際為: {feasibility_score}"
