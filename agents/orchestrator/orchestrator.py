# 代碼功能說明: Agent Orchestrator 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Agent Orchestrator - 實現 Agent 協調、調度、任務分發和結果聚合"""

import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.services.orchestrator.models import AgentInfo, TaskRequest, TaskResult, TaskStatus

# AgentStatus 從 registry.models 導入（因為 orchestrator.models 中沒有 AgentStatus）
from agents.services.registry.models import (
    AgentStatus,  # type: ignore[attr-defined]  # orchestrator.models 中沒有 AgentStatus
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 協調器"""

    def __init__(self):
        """初始化 Agent 協調器"""
        self._agents: Dict[str, AgentInfo] = {}
        self._tasks: Dict[str, TaskRequest] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._task_queue: deque = deque()
        self._agent_loads: Dict[str, int] = {}  # Agent 負載計數

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        註冊 Agent

        Args:
            agent_id: Agent ID
            agent_type: Agent 類型
            capabilities: 能力列表
            metadata: 元數據

        Returns:
            是否成功註冊
        """
        try:
            # AgentInfo 是 AgentRegistryInfo 的別名，需要提供所有必需參數
            from agents.services.registry.models import AgentEndpoints, AgentMetadata

            agent_info = AgentInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                name=agent_id,  # 使用 agent_id 作為默認名稱
                status=AgentStatus.IDLE,
                endpoints=AgentEndpoints(),  # type: ignore[call-arg]  # 所有參數都有默認值
                last_heartbeat=None,
                capabilities=capabilities or [],
                metadata=AgentMetadata() if not metadata else (AgentMetadata(**metadata) if isinstance(metadata, dict) else metadata),  # type: ignore[call-arg]  # 所有參數都有默認值
                load=0,  # 初始負載為 0
            )

            self._agents[agent_id] = agent_info
            self._agent_loads[agent_id] = 0

            logger.info(f"Registered agent: {agent_id} (type: {agent_type})")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent '{agent_id}': {e}")
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
                del self._agents[agent_id]
            if agent_id in self._agent_loads:
                del self._agent_loads[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister agent '{agent_id}': {e}")
            return False

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
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
    ) -> List[AgentInfo]:
        """
        列出 Agent

        Args:
            agent_type: Agent 類型過濾器
            status: Agent 狀態過濾器

        Returns:
            Agent 列表
        """
        agents = list(self._agents.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if status:
            agents = [a for a in agents if a.status == status]

        return agents

    def discover_agents(
        self,
        required_capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
    ) -> List[AgentInfo]:
        """
        發現可用的 Agent

        Args:
            required_capabilities: 需要的能力列表
            agent_type: Agent 類型過濾器

        Returns:
            匹配的 Agent 列表
        """
        agents = self.list_agents(agent_type=agent_type, status=AgentStatus.IDLE)

        if required_capabilities:
            matched_agents = []
            for agent in agents:
                if all(cap in agent.capabilities for cap in required_capabilities):
                    matched_agents.append(agent)
            return matched_agents

        return agents

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
        self._task_queue = deque(sorted(self._task_queue, key=lambda x: x[0], reverse=True))

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

    def _select_agent(self, task_request: TaskRequest) -> Optional[AgentInfo]:
        """
        選擇合適的 Agent

        Args:
            task_request: 任務請求

        Returns:
            選中的 Agent，如果沒有合適的則返回 None
        """
        # 如果指定了需要的 Agent
        if task_request.required_agents:
            for agent_id in task_request.required_agents:
                agent = self._agents.get(agent_id)
                if agent and agent.status == AgentStatus.IDLE:
                    return agent
            return None

        # 根據任務類型選擇 Agent
        agent_type_mapping = {
            "planning": "planning_agent",
            "execution": "execution_agent",
            "review": "review_agent",
        }

        preferred_type = agent_type_mapping.get(task_request.task_type)

        # 優先選擇空閒且負載最低的 Agent
        idle_agents = [agent for agent in self._agents.values() if agent.status == AgentStatus.IDLE]

        if preferred_type:
            preferred_agents = [
                agent for agent in idle_agents if agent.agent_type == preferred_type
            ]
            if preferred_agents:
                idle_agents = preferred_agents

        if not idle_agents:
            return None

        # 選擇負載最低的 Agent
        selected_agent = min(idle_agents, key=lambda a: self._agent_loads.get(a.agent_id, 0))

        return selected_agent

    def _assign_task(self, task_id: str, agent_id: str) -> bool:
        """
        分配任務給 Agent

        Args:
            task_id: 任務ID
            agent_id: Agent ID

        Returns:
            是否成功分配
        """
        try:
            task_request = self._tasks.get(task_id)
            agent = self._agents.get(agent_id)

            if not task_request or not agent:
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

            # 更新 Agent 狀態
            agent.status = AgentStatus.BUSY
            self._agent_loads[agent_id] = self._agent_loads.get(agent_id, 0) + 1

            logger.info(f"Assigned task {task_id} to agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to assign task '{task_id}' to agent '{agent_id}': {e}")
            return False

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

            # 更新 Agent 狀態
            if task_result.agent_id:
                agent = self._agents.get(task_result.agent_id)
                if agent:
                    agent.status = AgentStatus.IDLE
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
            agent.last_heartbeat = datetime.now()
            logger.debug(f"Updated agent {agent_id} status to {status.value}")
            return True
        return False
