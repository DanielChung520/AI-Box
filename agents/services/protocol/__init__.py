# 代碼功能說明: Agent Service Protocol 接口定義
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Service Protocol - 定義 Agent 服務的標準接口

用於協調層與執行層之間的通信協議，支持 HTTP 和 MCP 兩種方式。
"""

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceProtocolType,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.services.protocol.factory import AgentServiceClientFactory
from agents.services.protocol.http_client import HTTPAgentServiceClient
from agents.services.protocol.mcp_client import MCPAgentServiceClient

__all__ = [
    "AgentServiceProtocol",
    "AgentServiceProtocolType",
    "AgentServiceRequest",
    "AgentServiceResponse",
    "AgentServiceStatus",
    "HTTPAgentServiceClient",
    "MCPAgentServiceClient",
    "AgentServiceClientFactory",
]
