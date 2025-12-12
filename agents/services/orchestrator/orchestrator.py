# 代碼功能說明: Agent Orchestrator 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Orchestrator - 實現 Agent 協調、調度、任務分發和結果聚合

使用 AgentRegistry 管理 Agent，支持內部/外部 Agent 統一調度。
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque

from .models import (
    AgentRegistryInfo,
    AgentStatus,
    TaskRequest,
    TaskResult,
    TaskStatus,
)
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.discovery import AgentDiscovery
from agents.services.protocol.base import (
    AgentServiceRequest,
    AgentServiceResponse,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 協調器

    使用 AgentRegistry 管理 Agent，支持內部/外部 Agent 統一調度。
    """

    def __init__(self, registry: Optional[Any] = None):
        """
        初始化 Agent 協調器

        Args:
            registry: AgentRegistry 實例（可選，默認使用全局實例）
        """
        self._registry = registry or get_agent_registry()
        self._discovery = AgentDiscovery(registry=self._registry)
        self._tasks: Dict[str, TaskRequest] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._task_queue: deque = deque()
        self._agent_loads: Dict[str, int] = {}  # Agent 負載計數（從 Registry 獲取）

    def get_agent(self, agent_id: str) -> Optional[AgentRegistryInfo]:
        """
        獲取 Agent 信息（從 Registry）

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，如果不存在則返回 None
        """
        return self._registry.get_agent_info(agent_id)

    def list_agents(
        self,
        agent_type: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[AgentRegistryInfo]:
        """
        列出 Agent（從 Registry）

        Args:
            agent_type: Agent 類型過濾器
            status: Agent 狀態過濾器

        Returns:
            Agent 列表
        """
        return self._discovery.discover_agents(agent_type=agent_type, status=status)

    def discover_agents(
        self,
        required_capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
    ) -> List[AgentRegistryInfo]:
        """
        發現可用的 Agent（從 Registry）

        Args:
            required_capabilities: 需要的能力列表
            agent_type: Agent 類型過濾器

        Returns:
            匹配的 Agent 列表
        """
        return self._discovery.discover_agents(
            required_capabilities=required_capabilities,
            agent_type=agent_type,
            status=AgentStatus.ONLINE,  # 使用 ONLINE 狀態（對應原來的 IDLE）
        )

    def submit_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        required_agents: Optional[List[str]] = None,
        priority: int = 0,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交任務

        Args:
            task_type: 任務類型
            task_data: 任務數據
            required_agents: 需要的Agent列表
            priority: 優先級
            timeout: 超時時間（秒）
            metadata: 元數據

        Returns:
            任務ID
        """
        task_id = str(uuid.uuid4())

        task_request = TaskRequest(
            task_id=task_id,
            task_type=task_type,
            task_data=task_data,
            required_agents=required_agents,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {},
        )

        self._tasks[task_id] = task_request
        self._task_queue.append((priority, task_id))

        logger.info(f"Submitted task: {task_id} (type: {task_type})")

        # 嘗試立即分配任務
        self._try_assign_tasks()

        return task_id

    def _try_assign_tasks(self):
        """嘗試分配任務"""
        # 按優先級排序任務隊列
        self._task_queue = deque(
            sorted(self._task_queue, key=lambda x: x[0], reverse=True)
        )

        for priority, task_id in list(self._task_queue):
            task_request = self._tasks.get(task_id)
            if not task_request:
                continue

            # 檢查任務是否已經分配
            if task_id in self._task_results:
                result = self._task_results[task_id]
                if result.status in [TaskStatus.ASSIGNED, TaskStatus.RUNNING]:
                    continue

            # 尋找合適的 Agent
            agent = self._select_agent(task_request)

            if agent:
                # 分配任務
                self._assign_task(task_id, agent.agent_id)
                self._task_queue.remove((priority, task_id))

    def _select_agent(self, task_request: TaskRequest) -> Optional[AgentRegistryInfo]:
        """
        選擇合適的 Agent（優先選擇內部 Agent）

        Args:
            task_request: 任務請求

        Returns:
            選中的 Agent，如果沒有合適的則返回 None
        """
        # 如果指定了需要的 Agent
        if task_request.required_agents:
            for agent_id in task_request.required_agents:
                agent_info = self._registry.get_agent_info(agent_id)
                if agent_info and agent_info.status == AgentStatus.ONLINE:
                    return agent_info
            return None

        # 根據任務類型選擇 Agent
        agent_type_mapping = {
            "planning": "planning",
            "execution": "execution",
            "review": "review",
        }

        preferred_type = agent_type_mapping.get(task_request.task_type)

        # 發現可用的 Agent
        available_agents = self.discover_agents(agent_type=preferred_type)

        if not available_agents:
            return None

        # 優先選擇內部 Agent（性能更好）
        internal_agents = [
            agent for agent in available_agents if agent.endpoints.is_internal
        ]
        if internal_agents:
            available_agents = internal_agents

        # 選擇負載最低的 Agent（從 Registry 獲取負載信息）
        selected_agent = min(
            available_agents,
            key=lambda a: self._agent_loads.get(a.agent_id, a.load),
        )

        return selected_agent

    def _assign_task(self, task_id: str, agent_id: str) -> bool:
        """
        分配任務給 Agent 並執行

        Args:
            task_id: 任務ID
            agent_id: Agent ID

        Returns:
            是否成功分配
        """
        try:
            task_request = self._tasks.get(task_id)
            agent_info = self._registry.get_agent_info(agent_id)

            if not task_request or not agent_info:
                return False

            # 更新任務狀態
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.ASSIGNED,
                agent_id=agent_id,
                started_at=datetime.now(),
                result=None,
                error=None,
                completed_at=None,
            )
            self._task_results[task_id] = task_result

            # 更新負載計數
            self._agent_loads[agent_id] = self._agent_loads.get(agent_id, 0) + 1

            logger.info(f"Assigned task {task_id} to agent {agent_id}")

            # 異步執行任務（這裡先標記為已分配，實際執行由調用方處理）
            # 或者可以在這裡直接執行任務
            return True
        except Exception as e:
            logger.error(
                f"Failed to assign task '{task_id}' to agent '{agent_id}': {e}"
            )
            return False

    async def execute_task(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
    ) -> Optional[TaskResult]:
        """
        執行任務（使用 AgentServiceProtocol 接口）

        Args:
            task_id: 任務ID
            agent_id: Agent ID（可選，如果不提供則自動選擇）

        Returns:
            任務結果，如果失敗則返回 None
        """
        try:
            task_request = self._tasks.get(task_id)
            if not task_request:
                logger.error(f"Task not found: {task_id}")
                return None

            # 如果未指定 Agent，自動選擇
            if not agent_id:
                agent_info = self._select_agent(task_request)
                if not agent_info:
                    logger.error(f"No available agent for task {task_id}")
                    return None
                agent_id = agent_info.agent_id
            else:
                agent_info = self._registry.get_agent_info(agent_id)
                if not agent_info:
                    logger.error(f"Agent not found: {agent_id}")
                    return None

            # 獲取 Agent 實例或客戶端
            agent = self._registry.get_agent(agent_id)
            if not agent:
                logger.error(f"Failed to get agent instance: {agent_id}")
                return None

            # 構建 AgentServiceRequest
            service_request = AgentServiceRequest(
                task_id=task_id,
                task_type=task_request.task_type,
                task_data=task_request.task_data,
                context=task_request.metadata.get("context"),
                metadata=task_request.metadata,
            )

            # 執行任務
            task_result = self._task_results.get(task_id)
            if task_result:
                task_result.status = TaskStatus.RUNNING

            logger.info(f"Executing task {task_id} on agent {agent_id}")
            service_response: AgentServiceResponse = await agent.execute(
                service_request
            )

            # 更新任務結果
            if task_result:
                if service_response.status == "completed":
                    task_result.status = TaskStatus.COMPLETED
                    task_result.result = service_response.result
                else:
                    task_result.status = TaskStatus.FAILED
                    task_result.error = service_response.error
                task_result.completed_at = datetime.now()
            else:
                # 創建新的任務結果
                task_result = TaskResult(
                    task_id=task_id,
                    status=(
                        TaskStatus.COMPLETED
                        if service_response.status == "completed"
                        else TaskStatus.FAILED
                    ),
                    agent_id=agent_id,
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    result=service_response.result,
                    error=service_response.error,
                )
                self._task_results[task_id] = task_result

            # 更新負載計數
            self._agent_loads[agent_id] = max(0, self._agent_loads.get(agent_id, 0) - 1)

            logger.info(
                f"Task {task_id} completed with status: {service_response.status}"
            )
            return task_result

        except Exception as e:
            logger.error(f"Failed to execute task '{task_id}': {e}")
            task_result = self._task_results.get(task_id)
            if task_result:
                task_result.status = TaskStatus.FAILED
                task_result.error = str(e)
                task_result.completed_at = datetime.now()
            return None

    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        完成任務

        Args:
            task_id: 任務ID
            result: 任務結果
            error: 錯誤信息

        Returns:
            是否成功完成
        """
        try:
            task_result = self._task_results.get(task_id)
            if not task_result:
                logger.warning(f"Task result not found: {task_id}")
                return False

            # 更新任務狀態
            if error:
                task_result.status = TaskStatus.FAILED
                task_result.error = error
            else:
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result

            task_result.completed_at = datetime.now()

            # 更新負載計數（Agent 狀態由 Registry 管理）
            if task_result.agent_id:
                self._agent_loads[task_result.agent_id] = max(
                    0, self._agent_loads.get(task_result.agent_id, 0) - 1
                )

            logger.info(f"Completed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete task '{task_id}': {e}")
            return False

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        獲取任務結果

        Args:
            task_id: 任務ID

        Returns:
            任務結果，如果不存在則返回 None
        """
        return self._task_results.get(task_id)

    def aggregate_results(
        self,
        task_ids: List[str],
    ) -> Dict[str, Any]:
        """
        聚合多個任務的結果

        Args:
            task_ids: 任務ID列表

        Returns:
            聚合結果
        """
        results = []
        errors = []

        for task_id in task_ids:
            task_result = self._task_results.get(task_id)
            if task_result:
                if task_result.status == TaskStatus.COMPLETED:
                    results.append(task_result.result)
                elif task_result.status == TaskStatus.FAILED:
                    errors.append(
                        {
                            "task_id": task_id,
                            "error": task_result.error,
                        }
                    )

        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> bool:
        """
        更新 Agent 狀態（通過 Registry）

        Args:
            agent_id: Agent ID
            status: 新狀態

        Returns:
            是否成功更新

        注意：Agent 狀態應由 Registry 管理，此方法僅為向後兼容保留。
        """
        agent_info = self._registry.get_agent_info(agent_id)
        if agent_info:
            # Agent 狀態由 Registry 管理，這裡僅記錄日誌
            logger.debug(f"Agent {agent_id} status update requested: {status.value}")
            # 實際狀態更新應通過 Registry 的心跳機制完成
            return True
        return False
