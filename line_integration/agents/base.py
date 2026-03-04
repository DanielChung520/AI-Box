# 代碼功能說明: Agent 適配器基礎介面
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""Agent 適配器基礎介面

定義統一的 Agent 調用介面，支持多種 Agent 類型。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AgentAdapter(ABC):
    """Agent 適配器抽象類

    所有 Agent 適配器都應繼承此類並實現相應方法。
    """

    def __init__(self, agent_url: str, agent_type: str):
        """初始化 Agent 適配器

        Args:
            agent_url: Agent 服務 URL
            agent_type: Agent 類型標識
        """
        self.agent_url = agent_url
        self.agent_type = agent_type
        self.endpoint = f"{agent_url}/execute"

    @abstractmethod
    async def execute(
        self,
        instruction: str,
        session_id: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行 Agent 任務

        Args:
            instruction: 用戶指令
            session_id: 會話 ID
            user_id: 用戶 ID
            conversation_history: 對話歷史（可選）
            context: 額外上下文（可選）

        Returns:
            Agent 執行結果
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """獲取 Agent 支持的能力

        Returns:
            能力列表
        """
        pass


class AgentType:
    """Agent 類型常量"""

    MM_AGENT = "mm_agent"  # 物料管理 Agent
    FI_AGENT = "fi_agent"  # 財務 Agent (預留)
    QA_AGENT = "qa_agent"  # 問答 Agent (預留)


# Agent 適配器註冊表
_AGENT_ADAPTERS: Dict[str, type] = {}


def register_agent_adapter(agent_type: str, adapter_class: type) -> None:
    """註冊 Agent 適配器

    Args:
        agent_type: Agent 類型標識
        adapter_class: 適配器類
    """
    _AGENT_ADAPTERS[agent_type] = adapter_class


def get_agent_adapter(agent_type: str, **kwargs) -> AgentAdapter:
    """獲取 Agent 適配器實例

    Args:
        agent_type: Agent 類型標識
        **kwargs: 傳遞給適配器的參數

    Returns:
        AgentAdapter 實例

    Raises:
        ValueError: 不支持的 Agent 類型
    """
    if agent_type not in _AGENT_ADAPTERS:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return _AGENT_ADAPTERS[agent_type](**kwargs)
