# 代碼功能說明: LINE Chat 持久化存儲服務
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""LINE Chat 持久化存儲服務

使用 ArangoDB 存儲 LINE 用戶的對話歷史和會話資訊。
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.arangodb import ArangoDBClient, ArangoCollection

logger = logging.getLogger(__name__)

# Collection 名稱
LINE_CHAT_SESSIONS = "line_chat_sessions"
LINE_CHAT_MESSAGES = "line_chat_messages"


class ChatStore:
    """LINE Chat 存儲服務

    負責管理 LINE 用戶的會話和對話歷史。
    """

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """初始化 Chat Store

        Args:
            client: ArangoDB 客戶端，如果為 None則創建新實例
        """
        self._client = client
        self._sessions_collection: Optional[ArangoCollection] = None
        self._messages_collection: Optional[ArangoCollection] = None
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """確保所需的 collection 存在"""
        if self._client is None:
            try:
                self._client = ArangoDBClient()
            except Exception as e:
                logger.error(f"Failed to connect to ArangoDB: {e}")
                return

        if self._client.db is None:
            logger.warning("ArangoDB client not connected")
            return

        # 創建或獲取 sessions collection
        sessions = self._client.get_or_create_collection(LINE_CHAT_SESSIONS)
        self._sessions_collection = ArangoCollection(sessions)

        # 創建或獲取 messages collection
        messages = self._client.get_or_create_collection(LINE_CHAT_MESSAGES)
        self._messages_collection = ArangoCollection(messages)

        # 確保索引
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if not self._sessions_collection or not self._messages_collection:
            return

        try:
            # Sessions: user_id 索引
            self._sessions_collection.collection.ensure_index(
                {
                    "type": "hash",
                    "fields": ["user_id"],
                    "unique": False,
                    "sparse": False,
                }
            )

            # Sessions: channel 索引
            self._sessions_collection.collection.ensure_index(
                {
                    "type": "hash",
                    "fields": ["channel"],
                    "unique": False,
                    "sparse": False,
                }
            )

            # Messages: session_id 索引
            self._messages_collection.collection.ensure_index(
                {
                    "type": "hash",
                    "fields": ["session_id"],
                    "unique": False,
                    "sparse": False,
                }
            )

            # Messages: timestamp 索引
            self._messages_collection.collection.ensure_index(
                {
                    "type": "skiplist",
                    "fields": ["timestamp"],
                    "unique": False,
                    "sparse": False,
                }
            )

            logger.info("Chat Store indexes ensured")
        except Exception as e:
            logger.warning(f"Failed to ensure indexes: {e}")

    def create_session(
        self,
        user_id: str,
        agent_type: str = "mm_agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """創建新的會話

        Args:
            user_id: LINE 用戶 ID
            agent_type: Agent 類型
            metadata: 額外元數據

        Returns:
            會話資訊
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        session_doc = {
            "_key": session_id,
            "session_id": session_id,
            "user_id": user_id,
            "agent_type": agent_type,
            "channel": "line",
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "metadata": metadata or {},
        }

        if self._sessions_collection:
            self._sessions_collection.insert(session_doc)
            logger.info(f"Created session {session_id} for user {user_id}")

        return session_doc

    def get_session_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根據用戶 ID 獲取會話

        Args:
            user_id: LINE 用戶 ID

        Returns:
            會話資訊，如果不存在返回 None
        """
        if not self._sessions_collection:
            return None

        try:
            results = self._sessions_collection.find(
                filters={"user_id": user_id, "status": "active"},
                limit=1,
            )
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to get session for user {user_id}: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """根據會話 ID 獲取會話

        Args:
            session_id: 會話 ID

        Returns:
            會話資訊，如果不存在返回 None
        """
        if not self._sessions_collection:
            return None

        try:
            return self._sessions_collection.get(session_id)
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加訊息到會話

        Args:
            session_id: 會話 ID
            role: 角色 (user/assistant/system)
            content: 訊息內容
            metadata: 額外元數據

        Returns:
            訊息文檔
        """
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        message_doc = {
            "_key": message_id,
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "metadata": metadata or {},
        }

        if self._messages_collection:
            self._messages_collection.insert(message_doc)

            # 更新會話的 message_count
            if self._sessions_collection:
                session = self._sessions_collection.get(session_id)
                if session:
                    self._sessions_collection.update(
                        {
                            "_key": session_id,
                            "message_count": session.get("message_count", 0) + 1,
                            "updated_at": now,
                        }
                    )

        return message_doc

    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """獲取對話歷史

        Args:
            session_id: 會話 ID
            limit: 返回訊息數量限制

        Returns:
            訊息列表
        """
        if not self._messages_collection:
            return []

        try:
            results = self._messages_collection.find(
                filters={"session_id": session_id},
                limit=limit,
                order_by="timestamp",
                order_desc=True,
            )
            # 反轉順序，最舊的在前面
            return list(reversed(results))
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def update_session_agent(
        self,
        session_id: str,
        agent_type: str,
    ) -> None:
        """更新會話的 Agent 類型

        Args:
            session_id: 會話 ID
            agent_type: 新的 Agent 類型
        """
        if not self._sessions_collection:
            return

        try:
            self._sessions_collection.update(
                {
                    "_key": session_id,
                    "agent_type": agent_type,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"Updated session {session_id} agent to {agent_type}")
        except Exception as e:
            logger.error(f"Failed to update session agent: {e}")

    def close_session(self, session_id: str) -> None:
        """關閉會話

        Args:
            session_id: 會話 ID
        """
        if not self._sessions_collection:
            return

        try:
            self._sessions_collection.update(
                {
                    "_key": session_id,
                    "status": "closed",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"Closed session {session_id}")
        except Exception as e:
            logger.error(f"Failed to close session: {e}")


# 單例實例
_chat_store: Optional[ChatStore] = None


def get_chat_store() -> ChatStore:
    """獲取 Chat Store 單例

    Returns:
        ChatStore 實例
    """
    global _chat_store

    if _chat_store is None:
        _chat_store = ChatStore()

    return _chat_store
