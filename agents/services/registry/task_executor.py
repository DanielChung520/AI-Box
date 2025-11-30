# 代碼功能說明: Agent Task Executor Agent 任務執行器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Task Executor - 通過 MCP Protocol 調用 Agent 執行任務"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from mcp.client.client import MCPClient
from agents.services.registry.registry import AgentRegistry
from agents.services.registry.models import AgentRegistryInfo

logger = logging.getLogger(__name__)


class AgentTaskExecutor:
    """Agent 任務執行器 - 通過 MCP Protocol 調用 Agent"""

    def __init__(self, registry: AgentRegistry):
        """
        初始化任務執行器

        Args:
            registry: Agent Registry 實例
        """
        self._registry = registry
        self._logger = logger
        self._mcp_clients: Dict[str, MCPClient] = {}  # Agent ID -> MCP Client 緩存

    async def execute_agent_task(
        self,
        agent_id: str,
        task_data: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        通過 MCP Protocol 調用 Agent 執行任務

        Args:
            agent_id: Agent ID
            task_data: 任務數據
            timeout: 超時時間（秒）

        Returns:
            執行結果字典
        """
        try:
            # 獲取 Agent 信息
            agent_info = self._registry.get_agent(agent_id)
            if not agent_info:
                raise ValueError(f"Agent not found: {agent_id}")

            if agent_info.status.value != "active":
                raise ValueError(
                    f"Agent is not active: {agent_id}, status: {agent_info.status.value}"
                )

            # 獲取或創建 MCP Client
            mcp_client = await self._get_mcp_client(agent_info)

            # 構建 MCP 工具調用請求
            # 使用 "execute_task" 作為工具名稱（Agent 需要實現此工具）
            tool_name = "execute_task"
            tool_arguments = {
                "task": task_data,
                "timestamp": datetime.now().isoformat(),
            }

            # 調用 Agent 的 MCP 工具
            self._logger.info(f"Calling agent {agent_id} via MCP to execute task")

            result = await mcp_client.call_tool(tool_name, tool_arguments)

            return {
                "agent_id": agent_id,
                "status": "completed",
                "result": result,
                "error": None,
            }

        except Exception as e:
            self._logger.error(f"Failed to execute task on agent {agent_id}: {e}")
            return {
                "agent_id": agent_id,
                "status": "failed",
                "result": None,
                "error": str(e),
            }

    async def _get_mcp_client(self, agent_info: AgentRegistryInfo) -> MCPClient:
        """
        獲取或創建 MCP Client

        Args:
            agent_info: Agent 信息

        Returns:
            MCP Client 實例
        """
        agent_id = agent_info.agent_id

        # 檢查緩存
        if agent_id in self._mcp_clients:
            return self._mcp_clients[agent_id]

        # 創建新的 MCP Client
        mcp_endpoint = agent_info.endpoints.mcp_endpoint
        client = MCPClient(
            endpoint=mcp_endpoint,
            client_name="ai-box-orchestrator",
            client_version="1.0.0",
            timeout=30.0,
        )

        # 初始化連接
        await client.initialize()

        # 緩存客戶端
        self._mcp_clients[agent_id] = client

        self._logger.info(f"Created MCP client for agent {agent_id}")
        return client

    async def close_all_clients(self):
        """關閉所有 MCP Client 連接"""
        for agent_id, client in self._mcp_clients.items():
            try:
                await client.close()
            except Exception as e:
                self._logger.warning(f"Failed to close MCP client for {agent_id}: {e}")

        self._mcp_clients.clear()
