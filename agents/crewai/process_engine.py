# 代碼功能說明: Process Engine 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Sequential、Hierarchical、Consensual 三種流程模板與切換邏輯。"""

import logging
from typing import List, Optional

from crewai import Crew, Process
from crewai.agent import Agent
from crewai.task import Task

from agents.crewai.models import CollaborationMode, CrewConfig
from agents.crewai.process_templates import (
    get_process_template,
)
from agents.crewai.token_budget import TokenBudgetGuard

logger = logging.getLogger(__name__)


class ProcessEngine:
    """Process Engine 核心類。"""

    def __init__(self, llm_adapter):
        """
        初始化 Process Engine。

        Args:
            llm_adapter: LLM 適配器實例
        """
        self.llm_adapter = llm_adapter

    def create_sequential_process(
        self,
        agents: List[Agent],
        tasks: List[Task],
        config: CrewConfig,
    ) -> Crew:
        """
        創建順序流程（Agent 按順序執行）。

        Args:
            agents: Agent 列表
            tasks: 任務列表
            config: 隊伍配置

        Returns:
            Crew 實例
        """
        template = get_process_template(CollaborationMode.SEQUENTIAL)
        process_config = template.get_config()
        process_config["llm"] = self.llm_adapter

        logger.info(f"Creating sequential process with {len(agents)} agents")
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=process_config.get("verbose", True),
            max_iter=process_config.get(
                "max_iter", config.resource_quota.max_iterations
            ),
            memory=process_config.get("memory", config.enable_memory),
            llm=process_config["llm"],
        )

    def create_hierarchical_process(
        self,
        agents: List[Agent],
        tasks: List[Task],
        config: CrewConfig,
        manager_agent: Optional[Agent] = None,
    ) -> Crew:
        """
        創建層級流程（Manager Agent 協調其他 Agent）。

        Args:
            agents: Agent 列表
            tasks: 任務列表
            config: 隊伍配置
            manager_agent: Manager Agent（可選，如果未提供則使用第一個 Agent）

        Returns:
            Crew 實例
        """
        template = get_process_template(CollaborationMode.HIERARCHICAL)
        process_config = template.get_config()
        process_config["llm"] = self.llm_adapter

        # 如果未提供 Manager Agent，使用第一個 Agent
        if manager_agent is None and agents:
            manager_agent = agents[0]

        logger.info(
            f"Creating hierarchical process with {len(agents)} agents "
            f"(manager: {manager_agent.role if manager_agent else 'None'})"
        )
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.hierarchical,
            manager_llm=self.llm_adapter,
            verbose=process_config.get("verbose", True),
            max_iter=process_config.get(
                "max_iter", config.resource_quota.max_iterations
            ),
            memory=process_config.get("memory", config.enable_memory),
            llm=process_config["llm"],
        )

    def create_consensual_process(
        self,
        agents: List[Agent],
        tasks: List[Task],
        config: CrewConfig,
    ) -> Crew:
        """
        創建共識流程（多 Agent 協商達成共識）。

        Args:
            agents: Agent 列表
            tasks: 任務列表
            config: 隊伍配置

        Returns:
            Crew 實例
        """
        template = get_process_template(CollaborationMode.CONSENSUAL)
        process_config = template.get_config()
        process_config["llm"] = self.llm_adapter

        logger.info(f"Creating consensual process with {len(agents)} agents")
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.consensual,
            verbose=process_config.get("verbose", True),
            max_iter=process_config.get(
                "max_iter", config.resource_quota.max_iterations
            ),
            memory=process_config.get("memory", config.enable_memory),
            llm=process_config["llm"],
        )

    def switch_process(
        self,
        current_crew: Crew,
        new_mode: CollaborationMode,
        agents: List[Agent],
        tasks: List[Task],
        config: CrewConfig,
    ) -> Crew:
        """
        動態切換流程模式。

        Args:
            current_crew: 當前的 Crew 實例
            new_mode: 新的協作模式
            agents: Agent 列表
            tasks: 任務列表
            config: 隊伍配置

        Returns:
            新的 Crew 實例
        """
        logger.info(
            f"Switching process mode from {config.collaboration_mode} to {new_mode}"
        )

        if new_mode == CollaborationMode.SEQUENTIAL:
            return self.create_sequential_process(agents, tasks, config)
        elif new_mode == CollaborationMode.HIERARCHICAL:
            return self.create_hierarchical_process(agents, tasks, config)
        elif new_mode == CollaborationMode.CONSENSUAL:
            return self.create_consensual_process(agents, tasks, config)
        else:
            logger.warning(f"Unknown process mode: {new_mode}, using sequential")
            return self.create_sequential_process(agents, tasks, config)

    def create_crew_from_config(
        self,
        config: CrewConfig,
        agents: List[Agent],
        tasks: List[Task],
        token_guard: Optional[TokenBudgetGuard] = None,
    ) -> Crew:
        """
        根據配置創建 Crew 實例。

        Args:
            config: 隊伍配置
            agents: Agent 列表
            tasks: 任務列表
            token_guard: Token 預算守門員（可選）

        Returns:
            Crew 實例
        """
        # 檢查 Token 預算
        if token_guard and not token_guard.check_budget():
            logger.warning("Token budget exceeded, cannot create crew")
            raise ValueError("Token budget exceeded")

        # 根據協作模式創建 Crew
        if config.collaboration_mode == CollaborationMode.SEQUENTIAL:
            return self.create_sequential_process(agents, tasks, config)
        elif config.collaboration_mode == CollaborationMode.HIERARCHICAL:
            return self.create_hierarchical_process(agents, tasks, config)
        elif config.collaboration_mode == CollaborationMode.CONSENSUAL:
            return self.create_consensual_process(agents, tasks, config)
        else:
            logger.warning(
                f"Unknown collaboration mode: {config.collaboration_mode}, using sequential"
            )
            return self.create_sequential_process(agents, tasks, config)
