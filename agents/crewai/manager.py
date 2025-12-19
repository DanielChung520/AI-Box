# 代碼功能說明: Crew Manager 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Crew Manager，管理隊伍定義、角色權限、資源配額、觀測指標。"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from agents.crewai.crew_registry import CrewRegistry
from agents.crewai.models import (
    AgentRole,
    CollaborationMode,
    CrewConfig,
    CrewMetrics,
    CrewResourceQuota,
)

logger = logging.getLogger(__name__)


class CrewManager:
    """Crew Manager 核心類。"""

    def __init__(self):
        """初始化 Crew Manager。"""
        self._registry = CrewRegistry()

    def create_crew(
        self,
        name: str,
        description: Optional[str] = None,
        agents: Optional[List[AgentRole]] = None,
        collaboration_mode: CollaborationMode = CollaborationMode.SEQUENTIAL,
        resource_quota: Optional[CrewResourceQuota] = None,
        metadata: Optional[Dict] = None,
    ) -> CrewConfig:
        """
        創建隊伍。

        Args:
            name: 隊伍名稱
            description: 隊伍描述
            agents: Agent 列表
            collaboration_mode: 協作模式
            resource_quota: 資源配額
            metadata: 元數據

        Returns:
            隊伍配置
        """
        crew_id = str(uuid.uuid4())
        config = CrewConfig(
            crew_id=crew_id,
            name=name,
            description=description,
            agents=agents or [],
            collaboration_mode=collaboration_mode,
            resource_quota=resource_quota or CrewResourceQuota(),
            metadata=metadata or {},
        )

        metrics = CrewMetrics(crew_id=crew_id, agent_count=len(config.agents))
        self._registry.register(crew_id, config, metrics)

        logger.info(f"Created crew: {crew_id} ({name})")
        return config

    def add_agent(
        self,
        crew_id: str,
        agent: AgentRole,
    ) -> bool:
        """
        添加 Agent 到隊伍。

        Args:
            crew_id: 隊伍 ID
            agent: Agent 角色

        Returns:
            是否成功添加
        """
        entry = self._registry.get(crew_id)
        if not entry:
            logger.error(f"Crew '{crew_id}' not found")
            return False

        config = entry.config
        config.agents.append(agent)
        config.updated_at = datetime.now()

        # 更新指標
        metrics = entry.metrics
        metrics.agent_count = len(config.agents)
        metrics.last_updated = datetime.now()

        logger.info(f"Added agent '{agent.role}' to crew: {crew_id}")
        return True

    def remove_agent(
        self,
        crew_id: str,
        agent_role: str,
    ) -> bool:
        """
        從隊伍移除 Agent。

        Args:
            crew_id: 隊伍 ID
            agent_role: Agent 角色名稱

        Returns:
            是否成功移除
        """
        entry = self._registry.get(crew_id)
        if not entry:
            logger.error(f"Crew '{crew_id}' not found")
            return False

        config = entry.config
        original_count = len(config.agents)
        config.agents = [a for a in config.agents if a.role != agent_role]
        config.updated_at = datetime.now()

        if len(config.agents) == original_count:
            logger.warning(f"Agent '{agent_role}' not found in crew: {crew_id}")
            return False

        # 更新指標
        metrics = entry.metrics
        metrics.agent_count = len(config.agents)
        metrics.last_updated = datetime.now()

        logger.info(f"Removed agent '{agent_role}' from crew: {crew_id}")
        return True

    def get_crew(self, crew_id: str) -> Optional[CrewConfig]:
        """
        獲取隊伍信息。

        Args:
            crew_id: 隊伍 ID

        Returns:
            隊伍配置，如果不存在則返回 None
        """
        entry = self._registry.get(crew_id)
        return entry.config if entry else None

    def list_crews(self) -> List[CrewConfig]:
        """
        列出所有隊伍。

        Returns:
            隊伍配置列表
        """
        entries = self._registry.list_crews()
        return [entry.config for entry in entries]

    def update_resource_quota(
        self,
        crew_id: str,
        resource_quota: CrewResourceQuota,
    ) -> bool:
        """
        更新資源配額。

        Args:
            crew_id: 隊伍 ID
            resource_quota: 資源配額

        Returns:
            是否成功更新
        """
        entry = self._registry.get(crew_id)
        if not entry:
            logger.error(f"Crew '{crew_id}' not found")
            return False

        config = entry.config
        config.resource_quota = resource_quota
        config.updated_at = datetime.now()

        logger.info(f"Updated resource quota for crew: {crew_id}")
        return True

    def get_metrics(self, crew_id: str) -> Optional[CrewMetrics]:
        """
        獲取觀測指標。

        Args:
            crew_id: 隊伍 ID

        Returns:
            觀測指標，如果不存在則返回 None
        """
        entry = self._registry.get(crew_id)
        return entry.metrics if entry else None

    def update_metrics(
        self,
        crew_id: str,
        token_usage: Optional[int] = None,
        execution_time: Optional[float] = None,
        task_count: Optional[int] = None,
        success_rate: Optional[float] = None,
    ) -> bool:
        """
        更新觀測指標。

        Args:
            crew_id: 隊伍 ID
            token_usage: Token 使用量
            execution_time: 執行時間
            task_count: 任務數量
            success_rate: 成功率

        Returns:
            是否成功更新
        """
        entry = self._registry.get(crew_id)
        if not entry:
            logger.error(f"Crew '{crew_id}' not found")
            return False

        metrics = entry.metrics
        if token_usage is not None:
            metrics.token_usage = token_usage
        if execution_time is not None:
            metrics.execution_time = execution_time
        if task_count is not None:
            metrics.task_count = task_count
        if success_rate is not None:
            metrics.success_rate = success_rate
        metrics.last_updated = datetime.now()

        self._registry.update_metrics(crew_id, metrics)
        logger.info(f"Updated metrics for crew: {crew_id}")
        return True

    def delete_crew(self, crew_id: str) -> bool:
        """
        刪除隊伍。

        Args:
            crew_id: 隊伍 ID

        Returns:
            是否成功刪除
        """
        return self._registry.unregister(crew_id)
