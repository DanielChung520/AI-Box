# 代碼功能說明: 上下文管理器核心
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""上下文管理器核心，提供統一的上下文管理接口。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from genai.workflows.context.history import ConversationHistory
from genai.workflows.context.models import ContextConfig, ContextMessage, ContextSession
from genai.workflows.context.persistence import ContextPersistence
from genai.workflows.context.recorder import ContextRecorder
from genai.workflows.context.window import ContextWindow

logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器，提供會話管理、消息記錄和上下文檢索功能。"""

    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        recorder: Optional[ContextRecorder] = None,
        history: Optional[ConversationHistory] = None,
        window: Optional[ContextWindow] = None,
        persistence: Optional[ContextPersistence] = None,
    ) -> None:
        """
        初始化上下文管理器。

        Args:
            config: 配置對象
            recorder: 上下文記錄器實例（如果為 None，則根據 config 創建）
            history: 對話歷史管理器（如果為 None，則根據 config 創建）
            window: 上下文窗口管理器（如果為 None，則使用默認配置）
            persistence: 持久化管理器（如果為 None，則根據 config 創建）
        """
        self._config = config or ContextConfig()
        self._recorder = recorder or ContextRecorder(config=self._config)
        self._history = history or ConversationHistory(namespace=self._config.namespace)
        self._window = window or ContextWindow(
            max_tokens=self._config.max_tokens,
            encoding_name=self._config.encoding_name,
        )
        self._persistence = persistence
        if self._persistence is None and self._config.enable_persistence:
            # 注意：需要外部提供 ArangoDB 客戶端
            logger.warning(
                "Persistence is enabled but no client provided. "
                "Context will not be persisted to ArangoDB."
            )
        self._sessions: Dict[str, ContextSession] = {}

    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextSession:
        """
        創建新會話。

        Args:
            session_id: 會話 ID
            user_id: 用戶 ID
            metadata: 元數據

        Returns:
            會話對象
        """
        session = ContextSession(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        logger.info("Created session %s", session_id)
        return session

    def get_session(self, session_id: str) -> Optional[ContextSession]:
        """
        獲取會話。

        Args:
            session_id: 會話 ID

        Returns:
            會話對象，如果不存在則返回 None
        """
        return self._sessions.get(session_id)

    def record_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        記錄消息。

        Args:
            session_id: 會話 ID
            role: 消息角色（user, assistant, system）
            content: 消息內容
            agent_name: Agent 名稱
            metadata: 元數據

        Returns:
            是否成功記錄
        """
        # 確保會話存在
        if session_id not in self._sessions:
            self.create_session(session_id)

        # 更新會話
        session = self._sessions.get(session_id)
        if session is not None:
            session.update()

        # 構建完整元數據
        full_metadata: Dict[str, Any] = metadata or {}
        if agent_name:
            full_metadata["agent_name"] = agent_name
        full_metadata["session_id"] = session_id

        # 記錄消息
        return self._recorder.record(
            session_id=session_id,
            role=role,
            content=content,
            metadata=full_metadata,
        )

    def get_context(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        獲取對話上下文（LLM 格式）。

        Args:
            session_id: 會話 ID
            limit: 限制返回的消息數量

        Returns:
            消息列表，格式為 [{"role": "...", "content": "..."}]
        """
        return self._recorder.get_conversation_context(session_id=session_id, limit=limit)

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ContextMessage]:
        """
        獲取完整的消息對象列表。

        Args:
            session_id: 會話 ID
            limit: 限制返回的消息數量

        Returns:
            消息對象列表
        """
        return self._recorder.get_messages(session_id=session_id, limit=limit)

    def clear_session(self, session_id: str) -> bool:
        """
        清空會話的所有消息。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功清空
        """
        # 清空記錄器中的消息
        result = self._recorder.clear_session(session_id)

        # 移除會話（可選，根據需求決定是否保留會話元數據）
        # self._sessions.pop(session_id, None)

        return result

    def delete_session(self, session_id: str) -> bool:
        """
        刪除會話（包括所有消息和會話元數據）。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功刪除
        """
        # 清空消息
        self._recorder.clear_session(session_id)

        # 移除會話
        if session_id in self._sessions:
            del self._sessions[session_id]

        logger.info("Deleted session %s", session_id)
        return True

    def list_sessions(self, user_id: Optional[str] = None) -> List[str]:
        """
        列出所有會話 ID。

        Args:
            user_id: 可選的用戶 ID 過濾器

        Returns:
            會話 ID 列表
        """
        if user_id is None:
            return list(self._sessions.keys())

        return [
            session_id
            for session_id, session in self._sessions.items()
            if session.user_id == user_id
        ]

    def get_context_with_window(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        獲取對話上下文（應用窗口管理）。

        Args:
            session_id: 會話 ID
            limit: 限制返回的消息數量（可選，窗口管理器會自動處理）

        Returns:
            消息列表，格式為 [{"role": "...", "content": "..."}]
        """
        messages = self.get_messages(session_id)
        if not messages:
            return []

        # 應用窗口截斷
        truncated_messages = self._window.truncate(messages)

        # 轉換為 LLM 格式
        return [{"role": msg.role, "content": msg.content} for msg in truncated_messages]

    def get_context_with_dynamic_window(
        self,
        session_id: str,
        reserved_tokens: int = 0,
    ) -> List[Dict[str, str]]:
        """
        獲取對話上下文（動態截斷，預留空間給 system 和 memory）。

        Args:
            session_id: 會話 ID
            reserved_tokens: 預留給 system 和 memory injection 的 token 數

        Returns:
            消息列表，格式為 [{"role": "...", "content": "..."}]
        """
        messages = self.get_messages(session_id)
        if not messages:
            return []

        # 計算可用空間
        available_tokens = self._window.max_tokens - reserved_tokens
        if available_tokens <= 0:
            return []

        # 根據剩餘空間截斷
        truncated_messages = self._window.truncate_for_space(messages, available_tokens)

        # 轉換為 LLM 格式
        return [{"role": msg.role, "content": msg.content} for msg in truncated_messages]

    @property
    def max_tokens(self) -> int:
        """返回窗口的最大 token 數。"""
        return self._window.max_tokens

    def save_to_history(self, session_id: str, message: ContextMessage) -> bool:
        """
        保存消息到歷史記錄。

        Args:
            session_id: 會話 ID
            message: 消息對象

        Returns:
            是否成功保存
        """
        return self._history.save_message(session_id, message)

    def persist_context(self, session_id: str) -> bool:
        """
        持久化上下文記錄。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功持久化
        """
        if self._persistence is None:
            return False

        messages = self.get_messages(session_id)
        session = self.get_session(session_id)
        metadata = session.metadata if session else {}

        return self._persistence.save_context(session_id, messages, metadata)
