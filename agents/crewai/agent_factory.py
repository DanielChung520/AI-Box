# 代碼功能說明: Agent 工廠實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Agent 工廠，從模板創建 Agent 實例。"""

import logging
from typing import List, Optional

from crewai import Agent

from agents.crewai.agent_templates import get_agent_template
from agents.crewai.llm_adapter import OllamaLLMAdapter
from agents.crewai.models import AgentRole
from agents.crewai.tool_adapter import ToolAdapter

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent 工廠。"""

    def __init__(
        self,
        llm_adapter: OllamaLLMAdapter,
        tool_adapter: Optional[ToolAdapter] = None,
    ):
        """
        初始化 Agent 工廠。

        Args:
            llm_adapter: LLM 適配器
            tool_adapter: 工具適配器（可選）
        """
        self._llm_adapter = llm_adapter
        self._tool_adapter = tool_adapter

    def create_agent_from_template(
        self,
        template_name: str,
        custom_tools: Optional[List[str]] = None,
    ) -> Optional[Agent]:
        """
        從模板創建 Agent。

        Args:
            template_name: 模板名稱
            custom_tools: 自定義工具列表（可選）

        Returns:
            Agent 實例，如果創建失敗則返回 None
        """
        template = get_agent_template(template_name)
        if not template:
            logger.error(f"Agent template '{template_name}' not found")
            return None

        # 獲取工具
        tools = []
        if self._tool_adapter:
            tool_names = custom_tools or template.tools
            tools = self._tool_adapter.get_tools_for_agent(tool_names)

        try:
            agent = Agent(
                role=template.role,
                goal=template.goal,
                backstory=template.backstory,
                tools=tools,
                verbose=template.verbose,
                allow_delegation=template.allow_delegation,
                llm=self._llm_adapter,
            )
            logger.info(f"Created agent from template '{template_name}': {template.role}")
            return agent
        except Exception as exc:
            logger.error(f"Failed to create agent from template '{template_name}': {exc}")
            return None

    def create_custom_agent(
        self,
        role: str,
        goal: str,
        backstory: str,
        tools: Optional[List[str]] = None,
        verbose: bool = True,
        allow_delegation: bool = False,
    ) -> Optional[Agent]:
        """
        創建自定義 Agent。

        Args:
            role: 角色名稱
            goal: 目標
            backstory: 背景故事
            tools: 工具列表（可選）
            verbose: 是否輸出詳細日誌
            allow_delegation: 是否允許委派任務

        Returns:
            Agent 實例，如果創建失敗則返回 None
        """
        # 獲取工具
        crewai_tools = []
        if self._tool_adapter and tools:
            crewai_tools = self._tool_adapter.get_tools_for_agent(tools)

        try:
            agent = Agent(
                role=role,
                goal=goal,
                backstory=backstory,
                tools=crewai_tools,
                verbose=verbose,
                allow_delegation=allow_delegation,
                llm=self._llm_adapter,
            )
            logger.info(f"Created custom agent: {role}")
            return agent
        except Exception as exc:
            logger.error(f"Failed to create custom agent '{role}': {exc}")
            return None

    def create_agent_from_role(
        self,
        agent_role: AgentRole,
        custom_tools: Optional[List[str]] = None,
    ) -> Optional[Agent]:
        """
        從 AgentRole 創建 Agent。

        Args:
            agent_role: Agent 角色定義
            custom_tools: 自定義工具列表（可選，會覆蓋 agent_role.tools）

        Returns:
            Agent 實例，如果創建失敗則返回 None
        """
        # 獲取工具
        tool_names = custom_tools or agent_role.tools
        crewai_tools = []
        if self._tool_adapter and tool_names:
            crewai_tools = self._tool_adapter.get_tools_for_agent(tool_names)

        try:
            agent = Agent(
                role=agent_role.role,
                goal=agent_role.goal,
                backstory=agent_role.backstory,
                tools=crewai_tools,
                verbose=agent_role.verbose,
                allow_delegation=agent_role.allow_delegation,
                llm=self._llm_adapter,
            )
            logger.info(f"Created agent from role: {agent_role.role}")
            return agent
        except Exception as exc:
            logger.error(f"Failed to create agent from role '{agent_role.role}': {exc}")
            return None

    def configure_agent_tools(
        self,
        agent: Agent,
        tool_names: List[str],
    ) -> bool:
        """
        配置 Agent 工具。

        Args:
            agent: Agent 實例
            tool_names: 工具名稱列表

        Returns:
            是否成功配置
        """
        if not self._tool_adapter:
            logger.warning("Tool adapter not available, cannot configure tools")
            return False

        try:
            tools = self._tool_adapter.get_tools_for_agent(tool_names)
            agent.tools = tools
            logger.info(f"Configured {len(tools)} tools for agent '{agent.role}'")
            return True
        except Exception as exc:
            logger.error(f"Failed to configure tools for agent: {exc}")
            return False
