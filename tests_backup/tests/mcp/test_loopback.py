# 代碼功能說明: MCP Loopback 測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Loopback 測試模組 - 測試 client-server 通信"""

import pytest
import time
from fastapi.testclient import TestClient

from mcp_server.server import MCPServer
from services.mcp_server.tools.task_analyzer import TaskAnalyzerTool


@pytest.fixture
def mcp_server():
    """創建 MCP Server 實例"""
    server = MCPServer(
        name="test-server",
        version="1.0.0",
        protocol_version="2024-11-05",
    )

    # 註冊工具
    task_analyzer = TaskAnalyzerTool()
    server.register_tool(
        name=task_analyzer.name,
        description=task_analyzer.description,
        input_schema=task_analyzer.input_schema,
        handler=task_analyzer.execute,
    )

    return server


@pytest.mark.asyncio
async def test_loopback_communication(mcp_server):
    """測試 client-server 通信"""
    # 創建測試客戶端（模擬 HTTP 客戶端）
    app = mcp_server.get_fastapi_app()
    client = TestClient(app)

    # 初始化請求
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    response = client.post("/mcp", json=init_request)
    assert response.status_code == 200
    init_data = response.json()
    assert "result" in init_data

    # 列出工具
    list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    response = client.post("/mcp", json=list_request)
    assert response.status_code == 200
    list_data = response.json()
    assert "result" in list_data
    assert "tools" in list_data["result"]
    assert len(list_data["result"]["tools"]) > 0

    # 調用工具
    tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "task_analyzer", "arguments": {"task": "Test task"}},
    }

    response = client.post("/mcp", json=tool_request)
    assert response.status_code == 200
    tool_data = response.json()
    assert "result" in tool_data
    assert "content" in tool_data["result"]


@pytest.mark.asyncio
async def test_latency_measurement(mcp_server):
    """測試延遲測量"""
    app = mcp_server.get_fastapi_app()
    client = TestClient(app)

    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

    latencies = []
    for _ in range(10):
        start_time = time.time()
        response = client.post("/mcp", json=request)
        end_time = time.time()

        assert response.status_code == 200
        latencies.append((end_time - start_time) * 1000)  # 轉換為毫秒

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    min_latency = min(latencies)

    print(f"Average latency: {avg_latency:.2f}ms")
    print(f"Max latency: {max_latency:.2f}ms")
    print(f"Min latency: {min_latency:.2f}ms")

    # 驗證延遲在合理範圍內（應該小於 100ms）
    assert avg_latency < 100, f"Average latency too high: {avg_latency}ms"


@pytest.mark.asyncio
async def test_stability(mcp_server):
    """測試穩定性（多次請求）"""
    app = mcp_server.get_fastapi_app()
    client = TestClient(app)

    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

    success_count = 0
    error_count = 0

    for i in range(100):
        try:
            response = client.post("/mcp", json=request)
            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            print(f"Request {i} failed: {e}")

    success_rate = success_count / 100
    print(f"Success rate: {success_rate * 100:.2f}%")
    print(f"Success: {success_count}, Errors: {error_count}")

    # 驗證成功率應該大於 95%
    assert success_rate >= 0.95, f"Success rate too low: {success_rate * 100}%"
