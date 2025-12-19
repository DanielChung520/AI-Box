# 代碼功能說明: AutoGen Agent 協作機制
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現 Agent 之間的通信協議、任務分配邏輯和協作流程編排。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """消息類型。"""

    TASK_REQUEST = "task_request"
    TASK_ASSIGNMENT = "task_assignment"
    EXECUTION_RESULT = "execution_result"
    EVALUATION_RESULT = "evaluation_result"
    RETRY_REQUEST = "retry_request"
    TERMINATE = "terminate"


@dataclass
class AgentMessage:
    """Agent 消息。"""

    message_type: MessageType
    from_agent: str
    to_agent: Optional[str] = None  # None 表示廣播
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class AgentCoordinator:
    """Agent 協調器，管理 Agent 之間的通信和協作。"""

    def __init__(self):
        """初始化協調器。"""
        self._agents: Dict[str, Any] = {}
        self._message_queue: List[AgentMessage] = []
        self._task_assignments: Dict[str, str] = {}  # task_id -> agent_name

    def register_agent(self, agent_name: str, agent: Any) -> bool:
        """
        註冊 Agent。

        Args:
            agent_name: Agent 名稱
            agent: Agent 實例

        Returns:
            是否成功註冊
        """
        try:
            self._agents[agent_name] = agent
            logger.info(f"Registered agent: {agent_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to register agent '{agent_name}': {exc}")
            return False

    def send_message(
        self,
        message_type: MessageType,
        from_agent: str,
        to_agent: Optional[str] = None,
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        發送消息。

        Args:
            message_type: 消息類型
            from_agent: 發送者 Agent 名稱
            to_agent: 接收者 Agent 名稱（None 表示廣播）
            content: 消息內容
            metadata: 元數據

        Returns:
            是否成功發送
        """
        try:
            message = AgentMessage(
                message_type=message_type,
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                metadata=metadata or {},
            )
            self._message_queue.append(message)
            logger.debug(
                f"Message sent: {message_type.value} from {from_agent} to {to_agent or 'all'}"
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to send message: {exc}")
            return False

    def get_messages(
        self,
        agent_name: Optional[str] = None,
        message_type: Optional[MessageType] = None,
    ) -> List[AgentMessage]:
        """
        獲取消息。

        Args:
            agent_name: Agent 名稱（None 表示所有消息）
            message_type: 消息類型過濾器

        Returns:
            消息列表
        """
        messages = self._message_queue

        # Agent 過濾
        if agent_name:
            messages = [
                msg for msg in messages if msg.to_agent == agent_name or msg.to_agent is None
            ]

        # 類型過濾
        if message_type:
            messages = [msg for msg in messages if msg.message_type == message_type]

        return messages

    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """
        分配任務。

        Args:
            task_id: 任務 ID
            agent_name: Agent 名稱

        Returns:
            是否成功分配
        """
        try:
            if agent_name not in self._agents:
                logger.warning(f"Agent '{agent_name}' not registered")
                return False

            self._task_assignments[task_id] = agent_name
            logger.info(f"Assigned task {task_id} to agent {agent_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to assign task: {exc}")
            return False

    def get_task_agent(self, task_id: str) -> Optional[str]:
        """
        獲取任務分配的 Agent。

        Args:
            task_id: 任務 ID

        Returns:
            Agent 名稱，如果未分配則返回 None
        """
        return self._task_assignments.get(task_id)

    def get_agent(self, agent_name: str) -> Optional[Any]:
        """
        獲取 Agent 實例。

        Args:
            agent_name: Agent 名稱

        Returns:
            Agent 實例，如果不存在則返回 None
        """
        return self._agents.get(agent_name)

    def clear_messages(self) -> None:
        """清空消息隊列。"""
        self._message_queue.clear()
        logger.debug("Cleared message queue")

    def get_coordination_summary(self) -> Dict[str, Any]:
        """
        獲取協調摘要。

        Returns:
            協調摘要字典
        """
        return {
            "registered_agents": list(self._agents.keys()),
            "message_count": len(self._message_queue),
            "task_assignments": len(self._task_assignments),
            "recent_messages": [
                {
                    "type": msg.message_type.value,
                    "from": msg.from_agent,
                    "to": msg.to_agent,
                }
                for msg in self._message_queue[-10:]
            ],
        }
