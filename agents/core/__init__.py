# 代碼功能說明: 核心 Agent 模組
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""核心 Agent 模組

提供 AI-Box 核心業務邏輯 Agent：
- Planning Agent: 計劃生成和驗證
- Execution Agent: 工具執行和任務執行
- Review Agent: 結果驗證和反饋生成

這些 Agent 是內部 Agent，需要註冊到 Registry，但標記為 is_internal=True。
"""

import logging
from typing import Dict, Optional

from agents.services.protocol.base import AgentServiceProtocol
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
)
from agents.services.protocol.base import AgentServiceProtocolType

from .planning.agent import PlanningAgent
from .execution.agent import ExecutionAgent
from .review.agent import ReviewAgent

__all__ = [
    "PlanningAgent",
    "ExecutionAgent",
    "ReviewAgent",
    "register_core_agents",
    "get_core_agent",
]

logger = logging.getLogger(__name__)

# 全局核心 Agent 实例字典
_core_agents: Dict[str, AgentServiceProtocol] = {}


def register_core_agents() -> Dict[str, AgentServiceProtocol]:
    """
    註冊所有核心 Agent 到 Registry

    Returns:
        核心 Agent 實例字典
    """
    global _core_agents

    if _core_agents:
        # 已經註冊，直接返回
        return _core_agents

    registry = get_agent_registry()

    # 創建核心 Agent 實例
    planning_agent = PlanningAgent()
    execution_agent = ExecutionAgent()
    review_agent = ReviewAgent()

    # 註冊 Planning Agent
    planning_request = AgentRegistrationRequest(
        agent_id="planning-agent",
        agent_type="planning",
        name="Planning Agent",
        endpoints=AgentEndpoints(
            http=None,
            mcp=None,
            protocol=AgentServiceProtocolType.HTTP,
            is_internal=True,  # 標記為內部 Agent
        ),
        capabilities=["plan_generation", "plan_validation", "task_analysis"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="任務計劃生成和驗證服務",
            author="AI-Box Team",
            tags=["planning", "core"],
        ),
        permissions=AgentPermissionConfig(),  # 內部 Agent 使用默認權限（完整權限）
    )

    success = registry.register_agent(planning_request, instance=planning_agent)
    if success:
        _core_agents["planning-agent"] = planning_agent
        logger.info("Planning Agent registered successfully")
    else:
        logger.error("Failed to register Planning Agent")

    # 註冊 Execution Agent
    execution_request = AgentRegistrationRequest(
        agent_id="execution-agent",
        agent_type="execution",
        name="Execution Agent",
        endpoints=AgentEndpoints(
            http=None,
            mcp=None,
            protocol=AgentServiceProtocolType.HTTP,
            is_internal=True,  # 標記為內部 Agent
        ),
        capabilities=["tool_execution", "auto_tool_selection", "task_execution"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="工具執行和任務執行服務",
            author="AI-Box Team",
            tags=["execution", "core"],
        ),
        permissions=AgentPermissionConfig(),  # 內部 Agent 使用默認權限（完整權限）
    )

    success = registry.register_agent(execution_request, instance=execution_agent)
    if success:
        _core_agents["execution-agent"] = execution_agent
        logger.info("Execution Agent registered successfully")
    else:
        logger.error("Failed to register Execution Agent")

    # 註冊 Review Agent
    review_request = AgentRegistrationRequest(
        agent_id="review-agent",
        agent_type="review",
        name="Review Agent",
        endpoints=AgentEndpoints(
            http=None,
            mcp=None,
            protocol=AgentServiceProtocolType.HTTP,
            is_internal=True,  # 標記為內部 Agent
        ),
        capabilities=["result_validation", "quality_scoring", "feedback_generation"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="結果驗證和反饋生成服務",
            author="AI-Box Team",
            tags=["review", "core"],
        ),
        permissions=AgentPermissionConfig(),  # 內部 Agent 使用默認權限（完整權限）
    )

    success = registry.register_agent(review_request, instance=review_agent)
    if success:
        _core_agents["review-agent"] = review_agent
        logger.info("Review Agent registered successfully")
    else:
        logger.error("Failed to register Review Agent")

    logger.info(f"Registered {len(_core_agents)} core agents")
    return _core_agents


def get_core_agent(agent_id: str) -> Optional[AgentServiceProtocol]:
    """
    獲取核心 Agent 實例

    Args:
        agent_id: Agent ID（planning-agent, execution-agent, review-agent）

    Returns:
        核心 Agent 實例，如果不存在返回 None
    """
    if not _core_agents:
        # 如果未註冊，先註冊
        register_core_agents()

    return _core_agents.get(agent_id)
