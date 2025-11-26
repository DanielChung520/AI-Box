# 代碼功能說明: Agent 模板定義
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""定義標準 Agent 模板，覆蓋規劃/研究/執行/評審等角色。"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from agents.crewai.models import AgentRole


@dataclass
class AgentTemplate:
    """Agent 模板定義。"""

    name: str
    role: str
    goal: str
    backstory: str
    tools: List[str]
    verbose: bool = True
    allow_delegation: bool = False


class PlanningAgentTemplate(AgentTemplate):
    """規劃 Agent 模板。"""

    def __init__(self):
        super().__init__(
            name="planning_agent",
            role="Strategic Planner",
            goal="Analyze tasks and create detailed execution plans with clear steps and dependencies",
            backstory="You are an experienced strategic planner with expertise in breaking down complex tasks into manageable steps. You excel at identifying dependencies, risks, and optimal execution sequences.",
            tools=["task_analyzer", "planning_tool"],
            verbose=True,
            allow_delegation=False,
        )


class ResearchAgentTemplate(AgentTemplate):
    """研究 Agent 模板。"""

    def __init__(self):
        super().__init__(
            name="research_agent",
            role="Research Specialist",
            goal="Gather comprehensive information, analyze data, and provide insights on various topics",
            backstory="You are a meticulous researcher with strong analytical skills. You excel at finding relevant information, verifying facts, and synthesizing complex data into clear insights.",
            tools=["web_search", "database_query", "rag_retrieval"],
            verbose=True,
            allow_delegation=False,
        )


class ExecutionAgentTemplate(AgentTemplate):
    """執行 Agent 模板。"""

    def __init__(self):
        super().__init__(
            name="execution_agent",
            role="Task Executor",
            goal="Execute tasks efficiently using available tools and resources",
            backstory="You are a reliable executor with strong technical skills. You excel at using tools, following instructions precisely, and completing tasks on time.",
            tools=["code_executor", "api_client", "file_manager"],
            verbose=True,
            allow_delegation=True,
        )


class ReviewAgentTemplate(AgentTemplate):
    """評審 Agent 模板。"""

    def __init__(self):
        super().__init__(
            name="review_agent",
            role="Quality Reviewer",
            goal="Review and validate outputs for quality, accuracy, and completeness",
            backstory="You are a thorough reviewer with attention to detail. You excel at identifying errors, inconsistencies, and areas for improvement in outputs.",
            tools=["validator", "quality_checker"],
            verbose=True,
            allow_delegation=False,
        )


class WritingAgentTemplate(AgentTemplate):
    """寫作 Agent 模板。"""

    def __init__(self):
        super().__init__(
            name="writing_agent",
            role="Content Writer",
            goal="Create well-structured, clear, and engaging written content",
            backstory="You are a skilled writer with expertise in various writing styles. You excel at creating documents, reports, and other written materials that are clear, concise, and well-organized.",
            tools=["text_processor", "document_generator"],
            verbose=True,
            allow_delegation=False,
        )


# Agent 模板註冊表
AGENT_TEMPLATES: Dict[str, AgentTemplate] = {
    "planning": PlanningAgentTemplate(),
    "research": ResearchAgentTemplate(),
    "execution": ExecutionAgentTemplate(),
    "review": ReviewAgentTemplate(),
    "writing": WritingAgentTemplate(),
}


def get_agent_template(template_name: str) -> Optional[AgentTemplate]:
    """
    獲取 Agent 模板。

    Args:
        template_name: 模板名稱

    Returns:
        Agent 模板，如果不存在則返回 None
    """
    return AGENT_TEMPLATES.get(template_name.lower())


def list_agent_templates() -> List[str]:
    """
    列出所有可用的 Agent 模板名稱。

    Returns:
        模板名稱列表
    """
    return list(AGENT_TEMPLATES.keys())


def create_agent_role_from_template(template_name: str) -> Optional[AgentRole]:
    """
    從模板創建 Agent 角色。

    Args:
        template_name: 模板名稱

    Returns:
        Agent 角色，如果模板不存在則返回 None
    """
    template = get_agent_template(template_name)
    if not template:
        return None

    return AgentRole(
        role=template.role,
        goal=template.goal,
        backstory=template.backstory,
        tools=template.tools,
        verbose=template.verbose,
        allow_delegation=template.allow_delegation,
    )
