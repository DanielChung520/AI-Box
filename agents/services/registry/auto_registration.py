# 代碼功能說明: Agent Auto Registration Agent 自動註冊服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Auto Registration - Agent 啟動時自動註冊到 Registry"""

import logging
import asyncio
from typing import Optional, Dict, Any

from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentMetadata,
    AgentEndpoints,
)

logger = logging.getLogger(__name__)


class AgentAutoRegistration:
    """Agent 自動註冊服務"""

    def __init__(self, registry_url: str):
        """
        初始化自動註冊服務

        Args:
            registry_url: Agent Registry API URL
        """
        self._registry_url = registry_url.rstrip("/")
        self._logger = logger
        self._registry = get_agent_registry()

    async def register_on_startup(
        self,
        agent_id: str,
        agent_type: str,
        metadata: Dict[str, Any],
        endpoints: Dict[str, str],
        capabilities: Optional[list] = None,
    ) -> bool:
        """
        Agent 啟動時自動註冊

        Args:
            agent_id: Agent ID
            agent_type: Agent 類型
            metadata: Agent 元數據字典
            endpoints: Agent 端點字典（必須包含 mcp_endpoint 和 health_endpoint）
            capabilities: 能力列表（可選）

        Returns:
            是否成功註冊
        """
        try:
            # 構建註冊請求
            request = AgentRegistrationRequest(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=capabilities or [],
                metadata=AgentMetadata(**metadata),
                endpoints=AgentEndpoints(**endpoints),
            )

            # 註冊到 Registry
            success = self._registry.register_agent(request)

            if success:
                self._logger.info(f"Agent '{agent_id}' auto-registered successfully")
            else:
                self._logger.error(f"Failed to auto-register agent '{agent_id}'")

            return success

        except Exception as e:
            self._logger.error(f"Auto-registration failed for '{agent_id}': {e}")
            return False

    async def start_heartbeat(self, agent_id: str, interval: int = 60):
        """
        啟動心跳發送任務

        Args:
            agent_id: Agent ID
            interval: 心跳間隔（秒）
        """
        while True:
            try:
                self._registry.update_heartbeat(agent_id)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Heartbeat failed for '{agent_id}': {e}")
                await asyncio.sleep(interval)
