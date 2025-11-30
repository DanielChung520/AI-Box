# 代碼功能說明: Agent Orchestrator 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-2.2：Agent Orchestrator 協調整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentOrchestrator:
    """Agent Orchestrator 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_agent_registration(self, client: AsyncClient):
        """步驟 1: Agent 註冊測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/orchestrator/agents/register",
            json={
                "agent_id": "test_planning_agent",
                "agent_type": "planning",
                "capabilities": ["plan_generation", "plan_validation"],
            },
        )
        elapsed = time.time() - start_time

        # 允許 200, 201 (創建成功) 或 409 (已存在)
        assert response.status_code in [
            200,
            201,
            409,
        ], f"Agent 註冊失敗: {response.status_code} - {response.text}"
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})
            assert "agent_id" in result_data or "agent_id" in data, "響應缺少 agent_id"

    async def test_agent_discovery(self, client: AsyncClient):
        """步驟 2: Agent 發現測試"""
        start_time = time.time()
        response = await client.get("/api/v1/orchestrator/agents/discover")
        elapsed = time.time() - start_time

        assert_response_success(response)
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應格式
        assert "agents" in result_data or isinstance(
            result_data, list
        ), "響應格式不正確，應包含 agents 列表"

    async def test_task_submission(self, client: AsyncClient):
        """步驟 3: 任務提交測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/orchestrator/tasks/submit",
            json={
                "task_type": "planning",
                "task_data": {"task": "測試任務"},
                "required_agents": ["planning"],
            },
        )
        elapsed = time.time() - start_time

        assert_response_success(response)
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        data = response.json()
        result_data = data.get("data", {})
        assert "task_id" in result_data, "響應缺少 task_id"

    async def test_task_result_query(self, client: AsyncClient):
        """步驟 3.5: 任務結果查詢測試"""
        # 先提交一個任務
        submit_response = await client.post(
            "/api/v1/orchestrator/tasks/submit",
            json={
                "task_type": "test",
                "task_data": {"task": "測試查詢"},
            },
        )

        if submit_response.status_code in [200, 201]:
            submit_data = submit_response.json()
            task_id = submit_data.get("data", {}).get("task_id")

            if task_id:
                # 查詢任務結果
                response = await client.get(
                    f"/api/v1/orchestrator/tasks/{task_id}/result"
                )
                # 允許 200 (成功) 或 404 (任務不存在/未完成)
                assert response.status_code in [
                    200,
                    404,
                ], f"任務結果查詢失敗: {response.status_code}"

    async def test_multi_agent_collaboration(self, client: AsyncClient):
        """步驟 4: 多 Agent 協作測試"""
        # 註冊多個 Agent
        agents = [
            {
                "agent_id": "test_planning_agent",
                "agent_type": "planning",
                "capabilities": ["plan_generation"],
            },
            {
                "agent_id": "test_execution_agent",
                "agent_type": "execution",
                "capabilities": ["tool_execution"],
            },
            {
                "agent_id": "test_review_agent",
                "agent_type": "review",
                "capabilities": ["result_validation"],
            },
        ]

        registered_agents = []
        for agent in agents:
            response = await client.post(
                "/api/v1/orchestrator/agents/register",
                json=agent,
            )
            if response.status_code in [200, 201, 409]:  # 409 表示已存在
                registered_agents.append(agent["agent_id"])

        # 提交需要多個 Agent 協作的任務
        response = await client.post(
            "/api/v1/orchestrator/tasks/submit",
            json={
                "task_type": "complex",
                "task_data": {"task": "需要 Planning → Execution → Review 的任務"},
                "required_agents": registered_agents,
            },
        )

        # 驗證任務提交成功
        assert response.status_code in [
            200,
            201,
        ], f"多 Agent 協作任務提交失敗: {response.status_code}"

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})
            assert "task_id" in result_data, "響應缺少 task_id"

    async def test_result_aggregation(self, client: AsyncClient):
        """步驟 5: 結果聚合測試"""
        # 提交多個任務
        task_ids = []
        for i in range(3):
            response = await client.post(
                "/api/v1/orchestrator/tasks/submit",
                json={
                    "task_type": "test",
                    "task_data": {"task": f"測試任務 {i+1}"},
                },
            )
            if response.status_code in [200, 201]:
                data = response.json()
                task_id = data.get("data", {}).get("task_id")
                if task_id:
                    task_ids.append(task_id)

        # 如果有任務 ID，測試結果聚合
        if task_ids:
            response = await client.post(
                "/api/v1/orchestrator/tasks/aggregate",
                json={"task_ids": task_ids},
            )

            # 驗證聚合結果
            assert response.status_code in [
                200,
                201,
                404,
            ], f"結果聚合失敗: {response.status_code}"

            if response.status_code in [200, 201]:
                data = response.json()
                result_data = data.get("data", {})
                # 驗證聚合結果格式
                assert (
                    "success_count" in result_data or "results" in result_data
                ), "聚合結果格式不正確"
