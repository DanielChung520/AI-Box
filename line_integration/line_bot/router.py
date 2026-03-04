# 代碼功能說明: Agent 路由器
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""Agent 路由器

根據會話類型路由到不同的 Agent。
"""

import logging
import os
from typing import Any, Dict, Optional

from line_integration.agents import get_agent_adapter
from line_integration.agents.base import AgentAdapter, AgentType

logger = logging.getLogger(__name__)


class AgentRouter:
    """Agent 路由器

    負責根據 Agent 類型選擇合適的 Agent 適配器。
    """

    def __init__(self):
        """初始化 Agent 路由器"""
        self._adapters: Dict[str, AgentAdapter] = {}
        self._default_agent = AgentType.MM_AGENT

    def get_adapter(self, agent_type: str) -> AgentAdapter:
        """獲取 Agent 適配器

        Args:
            agent_type: Agent 類型

        Returns:
            AgentAdapter 實例

        Raises:
            ValueError: 不支持的 Agent 類型
        """
        if agent_type not in self._adapters:
            # 根據 Agent 類型獲取對應的 URL
            agent_url = self._get_agent_url(agent_type)

            # 創建適配器
            self._adapters[agent_type] = get_agent_adapter(
                agent_type,
                agent_url=agent_url,
            )

            logger.info(f"Created adapter for {agent_type} at {agent_url}")

        return self._adapters[agent_type]

    def _get_agent_url(self, agent_type: str) -> str:
        """獲取 Agent 服務 URL

        Args:
            agent_type: Agent 類型

        Returns:
            Agent 服務 URL
        """
        url_env_map = {
            AgentType.MM_AGENT: "LINE_MM_AGENT_URL",
            AgentType.FI_AGENT: "LINE_FI_AGENT_URL",
            AgentType.QA_AGENT: "LINE_QA_AGENT_URL",
        }

        env_var = url_env_map.get(agent_type)
        if env_var:
            url = os.getenv(env_var)
            if url:
                return url

        # 預設 URL
        default_urls = {
            AgentType.MM_AGENT: "http://localhost:8003",
            AgentType.FI_AGENT: "http://localhost:8005",  # 預留
            AgentType.QA_AGENT: "http://localhost:8006",  # 預留
        }

        return default_urls.get(agent_type, "http://localhost:8003")

    async def route(
        self,
        agent_type: str,
        instruction: str,
        session_id: str,
        user_id: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """路由到指定的 Agent

        Args:
            agent_type: Agent 類型
            instruction: 用戶指令
            session_id: 會話 ID
            user_id: 用戶 ID
            conversation_history: 對話歷史
            context: 額外上下文

        Returns:
            Agent 執行結果
        """
        adapter = self.get_adapter(agent_type)

        logger.info(f"[AgentRouter] Routing to {agent_type} for session {session_id}")

        return await adapter.execute(
            instruction=instruction,
            session_id=session_id,
            user_id=user_id,
            conversation_history=conversation_history,
            context=context,
        )

    def set_default_agent(self, agent_type: str) -> None:
        """設定預設 Agent 類型

        Args:
            agent_type: Agent 類型
        """
        self._default_agent = agent_type
        logger.info(f"Default agent set to {agent_type}")

    def get_default_agent(self) -> str:
        """獲取預設 Agent 類型

        Returns:
            預設 Agent 類型
        """
        return self._default_agent


# 單例實例
_agent_router: Optional[AgentRouter] = None


def get_agent_router() -> AgentRouter:
    """獲取 Agent 路由器單例

    Returns:
        AgentRouter 實例
    """
    global _agent_router

    if _agent_router is None:
        _agent_router = AgentRouter()

    return _agent_router
