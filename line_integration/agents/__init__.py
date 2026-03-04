# 代碼功能說明: Agent 適配器模組
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""Agent 適配器模組

提供多種 Agent 的適配器，支持 LINE Bot 調用不同的 AI-Box Agent。
"""

from line_integration.agents.base import (
    AgentAdapter,
    AgentType,
    get_agent_adapter,
    register_agent_adapter,
)
from line_integration.agents.mm_agent import MMAgentAdapter

__all__ = [
    "AgentAdapter",
    "AgentType",
    "MMAgentAdapter",
    "get_agent_adapter",
    "register_agent_adapter",
]
