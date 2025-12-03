# 代碼功能說明: Agent Discovery 服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Discovery 服務 - 實現按能力、權限、分類等條件發現 Agent"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from agents.services.registry.models import (
    AgentRegistryInfo,
    AgentStatus,
    AgentPermission,
)
from agents.services.registry.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentDiscovery:
    """Agent Discovery 服務"""

    def __init__(self, registry: AgentRegistry):
        """
        初始化 Agent Discovery

        Args:
            registry: Agent Registry 實例
        """
        self._registry = registry
        self._logger = logger

    def discover_agents(
        self,
        required_capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        user_id: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
    ) -> List[AgentRegistryInfo]:
        """
        發現可用的 Agent

        Args:
            required_capabilities: 需要的能力列表
            agent_type: Agent 類型過濾器
            category: Agent 分類過濾器
            status: Agent 狀態過濾器（默認為 ACTIVE）
            user_id: 用戶 ID（用於權限檢查）
            user_roles: 用戶角色列表（用於權限檢查）

        Returns:
            匹配的 Agent 列表
        """
        # 默認只返回在線的 Agent
        if status is None:
            status = AgentStatus.ONLINE

        # 獲取基礎 Agent 列表
        agents = self._registry.list_agents(agent_type=agent_type, status=status)

        # 過濾分類（如果提供）
        if category:
            agents = [a for a in agents if category in (a.metadata.tags or [])]

        # 過濾能力
        if required_capabilities:
            agents = self._filter_by_capabilities(agents, required_capabilities)

        # 過濾權限
        if user_id or user_roles:
            agents = self._filter_by_permissions(
                agents, user_id=user_id, user_roles=user_roles
            )

        # 過濾健康狀態（排除長時間無心跳的 Agent）
        agents = self._filter_by_health(agents)

        # 按評分排序（如果有）
        agents = self._sort_agents(agents)

        return agents

    def _filter_by_capabilities(
        self, agents: List[AgentRegistryInfo], required_capabilities: List[str]
    ) -> List[AgentRegistryInfo]:
        """
        按能力過濾 Agent

        Args:
            agents: Agent 列表
            required_capabilities: 需要的能力列表

        Returns:
            匹配的 Agent 列表
        """
        matched_agents = []
        required_set = set(required_capabilities)

        for agent in agents:
            agent_capabilities = set(agent.capabilities)
            # 檢查是否包含所有必需的能力
            if required_set.issubset(agent_capabilities):
                matched_agents.append(agent)

        return matched_agents

    def _filter_by_permissions(
        self,
        agents: List[AgentRegistryInfo],
        user_id: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
    ) -> List[AgentRegistryInfo]:
        """
        按權限過濾 Agent

        Args:
            agents: Agent 列表
            user_id: 用戶 ID
            user_roles: 用戶角色列表

        Returns:
            有權限訪問的 Agent 列表
        """
        accessible_agents = []
        user_roles_set = set(user_roles or [])

        for agent in agents:
            permissions = agent.permissions

            # 公開 Agent：沒有 secret_id 或 api_key 的視為公開
            # 已認證用戶可訪問：有 secret_id 或 api_key 且提供了 user_id
            # 基於角色的權限：檢查 allowed_roles（如果存在）
            # 特定用戶權限：檢查 allowed_users（如果存在）

            # 如果沒有認證要求（沒有 secret_id 和 api_key），視為公開
            if not permissions.secret_id and not permissions.api_key:
                accessible_agents.append(agent)
                continue

            # 如果有認證要求且提供了 user_id，允許訪問
            if user_id and (permissions.secret_id or permissions.api_key):
                accessible_agents.append(agent)
                continue

        return accessible_agents

    def _filter_by_health(
        self, agents: List[AgentRegistryInfo], heartbeat_timeout: int = 300
    ) -> List[AgentRegistryInfo]:
        """
        按健康狀態過濾 Agent（排除長時間無心跳的）

        Args:
            agents: Agent 列表
            heartbeat_timeout: 心跳超時時間（秒，默認 5 分鐘）

        Returns:
            健康的 Agent 列表
        """
        healthy_agents = []
        now = datetime.now()
        timeout_threshold = now - timedelta(seconds=heartbeat_timeout)

        for agent in agents:
            # 如果 Agent 狀態不是在線，跳過健康檢查
            if agent.status != AgentStatus.ONLINE:
                continue

            # 如果沒有心跳記錄，視為不健康（除非剛註冊）
            if agent.last_heartbeat is None:
                # 如果註冊時間在超時時間內，仍然認為是健康的
                if agent.registered_at > timeout_threshold:
                    healthy_agents.append(agent)
                continue

            # 檢查心跳是否超時
            if agent.last_heartbeat > timeout_threshold:
                healthy_agents.append(agent)

        return healthy_agents

    def _sort_agents(self, agents: List[AgentRegistryInfo]) -> List[AgentRegistryInfo]:
        """
        對 Agent 進行排序（按註冊時間、狀態等）

        Args:
            agents: Agent 列表

        Returns:
            排序後的 Agent 列表
        """
        # 簡單的排序邏輯：按註冊時間倒序（最新的在前）
        # 未來可以添加更複雜的評分機制
        return sorted(agents, key=lambda a: a.registered_at, reverse=True)

    def get_agent_by_category(self, category: str) -> List[AgentRegistryInfo]:
        """
        按分類獲取 Agent

        Args:
            category: Agent 分類

        Returns:
            該分類下的 Agent 列表
        """
        return self.discover_agents(category=category, status=AgentStatus.ONLINE)
