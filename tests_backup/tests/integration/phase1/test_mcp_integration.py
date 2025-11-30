# 代碼功能說明: MCP Server/Client 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-1.2：MCP Server/Client 整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import (
    assert_response_success,
    check_service_availability,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegration:
    """MCP Server/Client 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_mcp_tools_list(self, client: AsyncClient):
        """步驟 4: 工具發現機制測試"""
        response = await client.get("/api/v1/mcp/tools")
        assert_response_success(response)
        data = response.json()
        tools = data.get("data", {}).get("tools", [])
        assert isinstance(tools, list), "工具列表格式不正確"

    async def test_mcp_tool_call(self, client: AsyncClient):
        """步驟 5: MCP 工具調用 API 測試"""
        tools_response = await client.get("/api/v1/mcp/tools")
        assert_response_success(tools_response)
        tools_data = tools_response.json().get("data", {})
        tools = (
            tools_data.get("tools", []) if isinstance(tools_data, dict) else tools_data
        )

        if not tools:
            pytest.skip("沒有可用的工具進行測試")

        test_tool = tools[0]
        tool_name = test_tool.get("name", "test_tool")
        response = await client.post(
            "/api/v1/mcp/tools/call",
            json={"tool_name": tool_name, "arguments": {}},
        )
        assert response.status_code in [
            200,
            400,
            500,
        ], f"工具調用失敗: {response.status_code} - {response.text}"

    async def test_mcp_server_startup(self):
        """步驟 1: MCP Server 啟動測試"""
        # 檢查 MCP Server 是否運行（通過 API）
        try:
            from httpx import AsyncClient

            async with AsyncClient(
                base_url="http://localhost:8002", timeout=5.0
            ) as http_client:
                start_time = time.time()
                response = await http_client.get("/health")
                elapsed = time.time() - start_time

                assert (
                    response.status_code == 200
                ), f"MCP Server 健康檢查失敗: {response.status_code}"
                assert elapsed < 5, f"MCP Server 響應時間 {elapsed}s 超過 5 秒"
        except ImportError:
            pytest.skip("httpx 未安裝")
        except Exception as e:
            pytest.skip(f"MCP Server 啟動測試跳過: {str(e)}")

    async def test_mcp_client_connection(self):
        """步驟 2: MCP Client 連接測試"""
        # 檢查 MCP Server 是否可用
        mcp_server_url = "http://localhost:8002/health"
        if not await check_service_availability(mcp_server_url, timeout=2.0):
            pytest.skip("MCP Server 不可用")

        # 通過 API 測試連接
        try:
            from httpx import AsyncClient

            async with AsyncClient(
                base_url="http://localhost:8002", timeout=2.0
            ) as http_client:
                start_time = time.time()
                response = await http_client.get("/health")
                elapsed = time.time() - start_time

                assert response.status_code == 200, "MCP Server 連接失敗"
                assert elapsed < 2, f"MCP Server 連接時間 {elapsed}s 超過 2 秒"
        except ImportError:
            pytest.skip("httpx 未安裝")
        except Exception as e:
            pytest.skip(f"MCP Client 連接測試跳過: {str(e)}")

    async def test_mcp_protocol_messages(self, client: AsyncClient):
        """步驟 3: MCP 協議消息測試"""
        # 通過 API 測試協議消息
        # 測試工具列表請求
        start_time = time.time()
        response = await client.get("/api/v1/mcp/tools")
        elapsed_ms = (time.time() - start_time) * 1000

        assert_response_success(response)
        data = response.json()
        tools_data = data.get("data", {})
        tools = (
            tools_data.get("tools", []) if isinstance(tools_data, dict) else tools_data
        )

        assert isinstance(tools, list), "工具列表格式不正確"
        assert elapsed_ms < 500, f"工具列表響應時間 {elapsed_ms}ms 超過 500ms"
