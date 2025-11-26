# 代碼功能說明: Context Recorder 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Context Recorder - 實現上下文記錄和對話歷史管理"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """上下文條目"""

    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ContextRecorder:
    """上下文記錄器"""

    def __init__(
        self,
        max_history: int = 100,
        session_ttl: int = 3600,  # 1小時
    ):
        """
        初始化上下文記錄器

        Args:
            max_history: 最大歷史記錄數量
            session_ttl: 會話過期時間（秒）
        """
        self.max_history = max_history
        self.session_ttl = session_ttl
        self._sessions: Dict[str, deque] = {}
        self._session_timestamps: Dict[str, datetime] = {}

    def record(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        記錄上下文條目

        Args:
            session_id: 會話ID
            role: 角色（user, assistant, system）
            content: 內容
            metadata: 元數據

        Returns:
            是否成功記錄
        """
        try:
            # 獲取或創建會話
            if session_id not in self._sessions:
                self._sessions[session_id] = deque(maxlen=self.max_history)
                self._session_timestamps[session_id] = datetime.now()

            # 創建上下文條目
            entry = ContextEntry(
                role=role,
                content=content,
                metadata=metadata or {},
            )

            # 添加到會話歷史
            self._sessions[session_id].append(entry)
            self._session_timestamps[session_id] = datetime.now()

            logger.debug(f"Recorded context entry for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to record context entry: {e}")
            return False

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        role_filter: Optional[str] = None,
    ) -> List[ContextEntry]:
        """
        獲取會話歷史

        Args:
            session_id: 會話ID
            limit: 限制返回數量
            role_filter: 角色過濾器

        Returns:
            上下文條目列表
        """
        if session_id not in self._sessions:
            logger.warning(f"Session '{session_id}' not found")
            return []

        history = list(self._sessions[session_id])

        # 角色過濾
        if role_filter:
            history = [entry for entry in history if entry.role == role_filter]

        # 限制數量
        if limit:
            history = history[-limit:]

        return history

    def get_conversation_context(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        獲取對話上下文（用於 LLM 調用）

        Args:
            session_id: 會話ID
            limit: 限制返回數量

        Returns:
            對話上下文列表（格式：{"role": "...", "content": "..."}）
        """
        history = self.get_history(session_id, limit=limit)

        context = []
        for entry in history:
            context.append(
                {
                    "role": entry.role,
                    "content": entry.content,
                }
            )

        return context

    def clear_session(self, session_id: str) -> bool:
        """
        清空會話歷史

        Args:
            session_id: 會話ID

        Returns:
            是否成功清空
        """
        try:
            if session_id in self._sessions:
                self._sessions[session_id].clear()
                logger.info(f"Cleared session history: {session_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clear session '{session_id}': {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        刪除會話

        Args:
            session_id: 會話ID

        Returns:
            是否成功刪除
        """
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
            if session_id in self._session_timestamps:
                del self._session_timestamps[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session '{session_id}': {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        清理過期會話

        Returns:
            清理的會話數量
        """
        expired_sessions = []
        now = datetime.now()

        for session_id, timestamp in self._session_timestamps.items():
            elapsed = (now - timestamp).total_seconds()
            if elapsed > self.session_ttl:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.delete_session(session_id)

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

    def get_session_count(self) -> int:
        """
        獲取會話數量

        Returns:
            會話數量
        """
        return len(self._sessions)
