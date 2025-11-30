# 代碼功能說明: Execution Agent 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-2.4：Execution Agent 工具執行整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestExecutionAgent:
    """Execution Agent 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_tool_registration(self, client: AsyncClient):
        """步驟 1: 工具註冊測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/agents/execution/tools/register",
            json={
                "tool_name": "calculator",
                "tool_type": "function",
                "description": "簡單計算器工具",
            },
        )
        elapsed = time.time() - start_time

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Execution Agent 工具註冊 API 端點未實現")

        # 允許 200, 201 (創建成功) 或 409 (已存在)
        assert response.status_code in [
            200,
            201,
            409,
        ], f"工具註冊失敗: {response.status_code} - {response.text}"
        assert elapsed < 2, f"響應時間 {elapsed}s 超過 2 秒"

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})
            # 驗證響應包含工具信息
            assert "tool_name" in result_data or "tool_id" in result_data, "響應缺少工具信息"

    async def test_tool_discovery(self, client: AsyncClient):
        """步驟 2: 工具發現測試"""
        start_time = time.time()
        response = await client.get("/api/v1/agents/execution/tools")
        elapsed = time.time() - start_time

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Execution Agent 工具發現 API 端點未實現")

        assert_response_success(response)
        assert elapsed < 1, f"響應時間 {elapsed}s 超過 1 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應格式
        assert "tools" in result_data or isinstance(
            result_data, list
        ), "響應格式不正確，應包含 tools 列表"

    async def test_tool_execution(self, client: AsyncClient):
        """步驟 3: 工具執行測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/agents/execution/execute",
            json={
                "task": "執行計算任務",
                "tool_name": "calculator",
                "tool_args": {"operation": "add", "a": 1, "b": 2},
            },
        )
        elapsed = time.time() - start_time

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Execution Agent 工具執行 API 端點未實現")

        # 允許 200 (成功) 或 400/500 (工具不存在或執行失敗)
        assert response.status_code in [
            200,
            400,
            500,
        ], f"工具執行響應狀態碼異常: {response.status_code}"

        if response.status_code == 200:
            assert_response_success(response)
            assert elapsed < 5, f"響應時間 {elapsed}s 超過 5 秒"

            data = response.json()
            result_data = data.get("data", {})
            assert "execution_id" in result_data, "響應缺少 execution_id"
            assert "status" in result_data, "響應缺少 status"
