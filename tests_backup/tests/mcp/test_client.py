# 代碼功能說明: MCP Client 測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Client 測試模組"""

import pytest
from mcp_client.client import MCPClient
from mcp_client.connection.manager import MCPConnectionManager
from mcp_client.connection.pool import LoadBalanceStrategy


@pytest.mark.asyncio
async def test_client_initialization():
    """測試客戶端初始化"""
    client = MCPClient(
        endpoint="http://localhost:8002/mcp",
        client_name="test-client",
        client_version="1.0.0",
    )

    # 注意：這需要實際運行的 MCP Server
    # 在實際測試中，應該使用測試服務器
    assert client.endpoint == "http://localhost:8002/mcp"
    assert client.client_name == "test-client"
    assert not client.initialized


@pytest.mark.asyncio
async def test_connection_manager():
    """測試連線管理器"""
    manager = MCPConnectionManager(
        endpoints=["http://localhost:8002/mcp"],
        load_balance_strategy=LoadBalanceStrategy.ROUND_ROBIN,
        max_retries=3,
    )

    assert len(manager.pool.connections) == 1
    assert manager.pool.load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN


@pytest.mark.asyncio
async def test_request_id_generation():
    """測試請求 ID 生成"""
    manager = MCPConnectionManager(endpoints=["http://localhost:8002/mcp"])

    id1 = manager.generate_request_id()
    id2 = manager.generate_request_id()

    assert id1 == 1
    assert id2 == 2
    assert id2 > id1
