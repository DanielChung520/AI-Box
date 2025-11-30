# 代碼功能說明: Agent Registry 核心服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry 核心服務實現"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.agent_registry.models import (
    AgentRegistryInfo,
    AgentRegistrationRequest,
    AgentStatus,
    AgentPermissionConfig,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent Registry 核心服務"""

    def __init__(self, storage: Optional[Any] = None):
        """
        初始化 Agent Registry

        Args:
            storage: 持久化存儲接口（可選，暫時使用內存存儲）
        """
        self._agents: Dict[str, AgentRegistryInfo] = {}
        self._storage = storage
        self._logger = logger

    def register_agent(self, request: AgentRegistrationRequest) -> bool:
        """
        註冊 Agent

        Args:
            request: Agent 註冊請求

        Returns:
            是否成功註冊
        """
        try:
            # 檢查 Agent ID 是否已存在
            if request.agent_id in self._agents:
                self._logger.warning(
                    f"Agent '{request.agent_id}' already exists, updating..."
                )
                # 更新現有 Agent
                existing = self._agents[request.agent_id]
                existing.status = AgentStatus.ACTIVE
                existing.capabilities = request.capabilities
                existing.metadata = request.metadata
                existing.endpoints = request.endpoints
                if request.permissions:
                    existing.permissions = request.permissions
                if request.extra:
                    existing.extra.update(request.extra)
                existing.last_updated = datetime.now()
                return True

            # 創建新的 Agent 註冊信息
            agent_info = AgentRegistryInfo(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                status=AgentStatus.PENDING,  # 默認為待審核狀態
                capabilities=request.capabilities,
                metadata=request.metadata,
                endpoints=request.endpoints,
                permissions=request.permissions or AgentPermissionConfig(),
                extra=request.extra or {},
                registered_at=datetime.now(),
                last_updated=datetime.now(),
            )

            self._agents[request.agent_id] = agent_info

            # 持久化存儲（如果有）
            if self._storage:
                try:
                    self._storage.save_agent(agent_info)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent: {e}")

            self._logger.info(
                f"Registered agent: {request.agent_id} "
                f"(type: {request.agent_type}, category: {request.metadata.category})"
            )
            return True

        except Exception as e:
            self._logger.error(f"Failed to register agent '{request.agent_id}': {e}")
            return False

    def unregister_agent(self, agent_id: str) -> bool:
        """
        取消註冊 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否成功取消註冊
        """
        try:
            if agent_id in self._agents:
                # 標記為離線狀態而非刪除
                self._agents[agent_id].status = AgentStatus.OFFLINE
                self._agents[agent_id].last_updated = datetime.now()

                if self._storage:
                    try:
                        self._storage.update_agent(self._agents[agent_id])
                    except Exception as e:
                        self._logger.error(f"Failed to persist agent update: {e}")

                self._logger.info(f"Unregistered agent: {agent_id}")
                return True
            else:
                self._logger.warning(f"Agent '{agent_id}' not found")
                return False

        except Exception as e:
            self._logger.error(f"Failed to unregister agent '{agent_id}': {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[AgentRegistryInfo]:
        """
        獲取 Agent 信息

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，如果不存在則返回 None
        """
        return self._agents.get(agent_id)

    def list_agents(
        self,
        agent_type: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        category: Optional[str] = None,
    ) -> List[AgentRegistryInfo]:
        """
        列出 Agent

        Args:
            agent_type: Agent 類型過濾器
            status: Agent 狀態過濾器
            category: Agent 分類過濾器

        Returns:
            Agent 列表
        """
        agents = list(self._agents.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if status:
            agents = [a for a in agents if a.status == status]
        if category:
            agents = [a for a in agents if a.metadata.category == category]

        return agents

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        更新 Agent 狀態

        Args:
            agent_id: Agent ID
            status: 新狀態

        Returns:
            是否成功更新
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status
            agent.last_updated = datetime.now()

            if self._storage:
                try:
                    self._storage.update_agent(agent)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent update: {e}")

            self._logger.debug(f"Updated agent {agent_id} status to {status.value}")
            return True
        return False

    def update_heartbeat(self, agent_id: str) -> bool:
        """
        更新 Agent 心跳

        Args:
            agent_id: Agent ID

        Returns:
            是否成功更新
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = datetime.now()
            # 如果之前是離線狀態，自動恢復為活躍狀態
            if agent.status == AgentStatus.OFFLINE:
                agent.status = AgentStatus.ACTIVE
                agent.last_updated = datetime.now()

            if self._storage:
                try:
                    self._storage.update_agent(agent)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent update: {e}")

            return True
        return False

    def get_all_agents(self) -> List[AgentRegistryInfo]:
        """
        獲取所有 Agent（包括離線的）

        Returns:
            所有 Agent 列表
        """
        return list(self._agents.values())


# 全局 Agent Registry 實例
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    獲取全局 Agent Registry 實例

    Returns:
        Agent Registry 實例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
