# 代碼功能說明: Agent Health Monitor Agent 健康檢查監控
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Health Monitor - 監控 Agent 健康狀態，自動下線不健康的 Agent"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import httpx

from agents.services.registry.registry import AgentRegistry
from agents.services.registry.models import AgentRegistryInfo, AgentStatus

logger = logging.getLogger(__name__)


class AgentHealthMonitor:
    """Agent 健康檢查監控"""

    def __init__(
        self,
        registry: AgentRegistry,
        check_interval: int = 60,
        heartbeat_timeout: int = 300,
        health_check_timeout: float = 5.0,
    ):
        """
        初始化健康監控

        Args:
            registry: Agent Registry 實例
            check_interval: 檢查間隔（秒）
            heartbeat_timeout: 心跳超時時間（秒）
            health_check_timeout: 健康檢查請求超時時間（秒）
        """
        self._registry = registry
        self._check_interval = check_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._health_check_timeout = health_check_timeout
        self._logger = logger
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self):
        """啟動健康監控"""
        if self._running:
            self._logger.warning("Health monitor is already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._logger.info("Agent health monitor started")

    async def stop(self):
        """停止健康監控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._logger.info("Agent health monitor stopped")

    async def _monitor_loop(self):
        """監控循環"""
        while self._running:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(self._check_interval)

    async def _check_all_agents(self):
        """檢查所有 Agent 的健康狀態"""
        agents = self._registry.get_all_agents()

        for agent in agents:
            # 跳過非活躍的 Agent
            if agent.status not in [AgentStatus.ACTIVE, AgentStatus.PENDING]:
                continue

            # 檢查心跳
            if not self._check_heartbeat(agent):
                self._logger.warning(
                    f"Agent {agent.agent_id} heartbeat timeout, marking as offline"
                )
                self._registry.update_agent_status(agent.agent_id, AgentStatus.OFFLINE)
                continue

            # 檢查健康端點
            if agent.endpoints.health_endpoint:
                is_healthy = await self._check_health_endpoint(agent)
                if not is_healthy:
                    self._logger.warning(
                        f"Agent {agent.agent_id} health check failed, marking as offline"
                    )
                    self._registry.update_agent_status(
                        agent.agent_id, AgentStatus.OFFLINE
                    )

    def _check_heartbeat(self, agent: AgentRegistryInfo) -> bool:
        """
        檢查 Agent 心跳

        Args:
            agent: Agent 信息

        Returns:
            是否健康
        """
        if agent.last_heartbeat is None:
            # 如果沒有心跳記錄，檢查註冊時間
            timeout_threshold = datetime.now() - timedelta(
                seconds=self._heartbeat_timeout
            )
            return agent.registered_at > timeout_threshold

        timeout_threshold = datetime.now() - timedelta(seconds=self._heartbeat_timeout)
        return agent.last_heartbeat > timeout_threshold

    async def _check_health_endpoint(self, agent: AgentRegistryInfo) -> bool:
        """
        檢查 Agent 健康端點

        Args:
            agent: Agent 信息

        Returns:
            是否健康
        """
        try:
            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(agent.endpoints.health_endpoint)
                return response.status_code == 200
        except Exception as e:
            self._logger.debug(f"Health check failed for {agent.agent_id}: {e}")
            return False
