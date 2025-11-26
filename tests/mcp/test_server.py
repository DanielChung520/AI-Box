# 代碼功能說明: MCP Server 測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 測試模組"""

import pytest
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
        enable_monitoring=True,
    )

    # 註冊測試工具
    task_analyzer = TaskAnalyzerTool()
    server.register_tool(
        name=task_analyzer.name,
        description=task_analyzer.description,
        input_schema=task_analyzer.input_schema,
        handler=task_analyzer.execute,
    )

    return server


@pytest.fixture
def client(mcp_server):
    """創建測試客戶端"""
    app = mcp_server.get_fastapi_app()
    return TestClient(app)


def test_health_check(client):
    """測試健康檢查端點"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["server"] == "test-server"


def test_readiness_check(client):
    """測試就緒檢查端點"""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_initialize(client):
    """測試初始化請求"""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    response = client.post("/mcp", json=request)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert data["result"]["protocolVersion"] == "2024-11-05"


def test_list_tools(client):
    """測試列出工具請求"""
    request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    response = client.post("/mcp", json=request)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) > 0


@pytest.mark.asyncio
async def test_tool_call(client, mcp_server):
    """測試工具調用"""
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "task_analyzer",
            "arguments": {"task": "Create a plan for project"},
        },
    }
    response = client.post("/mcp", json=request)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "content" in data["result"]


def test_unknown_method(client):
    """測試未知方法"""
    request = {"jsonrpc": "2.0", "id": 4, "method": "unknown/method"}
    response = client.post("/mcp", json=request)
    assert response.status_code == 500
