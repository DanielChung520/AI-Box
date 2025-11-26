# 代碼功能說明: AutoGen 會話管理
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現多 Agent 會話管理和與 Context Recorder 的整合。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent_process.context.recorder import ContextRecorder

logger = logging.getLogger(__name__)


class ConversationManager:
    """管理 AutoGen 多 Agent 會話。"""

    def __init__(
        self,
        session_id: str,
        context_recorder: Optional[ContextRecorder] = None,
    ):
        """
        初始化會話管理器。

        Args:
            session_id: 會話 ID
            context_recorder: Context Recorder 實例（可選）
        """
        self.session_id = session_id
        self.context_recorder = context_recorder or ContextRecorder()
        self._conversation_history: List[Dict[str, Any]] = []

    def record_message(
        self,
        agent_name: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        記錄會話消息。

        Args:
            agent_name: Agent 名稱
            role: 角色（user, assistant, system）
            content: 消息內容
            metadata: 元數據

        Returns:
            是否成功記錄
        """
        try:
            # 構建完整的元數據
            full_metadata = {
                "agent_name": agent_name,
                "session_id": self.session_id,
                **(metadata or {}),
            }

            # 記錄到 Context Recorder
            self.context_recorder.record(
                session_id=self.session_id,
                role=role,
                content=content,
                metadata=full_metadata,
            )

            # 記錄到本地歷史
            self._conversation_history.append(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "content": content,
                    "metadata": full_metadata,
                }
            )

            logger.debug(
                f"Recorded message from {agent_name} in session {self.session_id}"
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to record message: {exc}")
            return False

    def get_conversation_history(
        self,
        limit: Optional[int] = None,
        agent_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        獲取會話歷史。

        Args:
            limit: 限制返回數量
            agent_filter: Agent 名稱過濾器

        Returns:
            會話歷史列表
        """
        history = self._conversation_history

        # Agent 過濾
        if agent_filter:
            history = [msg for msg in history if msg.get("agent_name") == agent_filter]

        # 限制數量
        if limit:
            history = history[-limit:]

        return history

    def get_context_for_llm(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        獲取用於 LLM 的上下文格式。

        Args:
            limit: 限制返回數量

        Returns:
            消息列表，格式為 [{"role": "...", "content": "..."}]
        """
        return self.context_recorder.get_conversation_context(
            session_id=self.session_id,
            limit=limit,
        )

    def clear_history(self) -> bool:
        """
        清空會話歷史。

        Returns:
            是否成功清空
        """
        try:
            self._conversation_history.clear()
            self.context_recorder.clear_session(self.session_id)
            logger.info(f"Cleared conversation history for session {self.session_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to clear history: {exc}")
            return False

    def export_summary(self) -> Dict[str, Any]:
        """
        導出會話摘要。

        Returns:
            會話摘要字典
        """
        return {
            "session_id": self.session_id,
            "message_count": len(self._conversation_history),
            "agents": list(
                set(msg.get("agent_name") for msg in self._conversation_history)
            ),
            "last_message": self._conversation_history[-1]
            if self._conversation_history
            else None,
        }
