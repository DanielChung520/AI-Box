# 代碼功能說明: 對話歷史管理
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""對話歷史管理器，提供歷史記錄存儲、檢索、過濾和分頁功能。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent_process.context.models import ContextMessage
from agent_process.context.storage import MemoryStorageBackend, StorageBackend

logger = logging.getLogger(__name__)


class ConversationHistory:
    """對話歷史管理器。"""

    def __init__(
        self,
        storage_backend: Optional[StorageBackend] = None,
        namespace: str = "agent_process:history",
    ) -> None:
        """
        初始化對話歷史管理器。

        Args:
            storage_backend: 存儲後端（如果為 None，則使用內存存儲）
            namespace: 命名空間
        """
        self._storage = storage_backend or MemoryStorageBackend()
        self._namespace = namespace

    def _key(self, session_id: str, suffix: Optional[str] = None) -> str:
        """
        生成存儲鍵。

        Args:
            session_id: 會話 ID
            suffix: 可選後綴

        Returns:
            存儲鍵
        """
        if suffix:
            return f"{self._namespace}:{session_id}:{suffix}"
        return f"{self._namespace}:{session_id}"

    def save_message(
        self,
        session_id: str,
        message: ContextMessage,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        保存消息到歷史記錄。

        Args:
            session_id: 會話 ID
            message: 消息對象
            ttl: TTL 秒數（可選）

        Returns:
            是否成功保存
        """
        try:
            # 獲取現有消息列表
            key = self._key(session_id, "messages")
            messages_data = self._storage.load(key) or {"messages": []}

            # 添加新消息
            message_dict = message.model_dump()
            messages_data["messages"].append(message_dict)
            messages_data["updated_at"] = datetime.now().isoformat()

            # 保存
            return self._storage.save(key, messages_data, ttl=ttl)
        except Exception as exc:
            logger.error("Failed to save message: %s", exc)
            return False

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        agent_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[ContextMessage]:
        """
        獲取消息列表，支持過濾和分頁。

        Args:
            session_id: 會話 ID
            limit: 限制返回數量
            offset: 偏移量
            agent_filter: Agent 名稱過濾器
            role_filter: 角色過濾器
            start_time: 開始時間過濾器
            end_time: 結束時間過濾器

        Returns:
            消息對象列表
        """
        try:
            key = self._key(session_id, "messages")
            messages_data = self._storage.load(key)

            if not messages_data or "messages" not in messages_data:
                return []

            messages: List[ContextMessage] = []
            for msg_dict in messages_data["messages"]:
                try:
                    # 處理時間戳字符串
                    if "timestamp" in msg_dict and isinstance(
                        msg_dict["timestamp"], str
                    ):
                        msg_dict["timestamp"] = datetime.fromisoformat(
                            msg_dict["timestamp"]
                        )

                    message = ContextMessage(**msg_dict)

                    # 應用過濾器
                    if agent_filter and message.agent_name != agent_filter:
                        continue
                    if role_filter and message.role != role_filter:
                        continue
                    if start_time and message.timestamp < start_time:
                        continue
                    if end_time and message.timestamp > end_time:
                        continue

                    messages.append(message)
                except Exception as exc:
                    logger.warning("Failed to parse message: %s", exc)

            # 應用分頁
            if offset > 0:
                messages = messages[offset:]
            if limit is not None and limit > 0:
                messages = messages[:limit]

            return messages
        except Exception as exc:
            logger.error("Failed to get messages: %s", exc)
            return []

    def get_message_count(
        self,
        session_id: str,
        agent_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
    ) -> int:
        """
        獲取消息數量。

        Args:
            session_id: 會話 ID
            agent_filter: Agent 名稱過濾器
            role_filter: 角色過濾器

        Returns:
            消息數量
        """
        messages = self.get_messages(
            session_id=session_id,
            agent_filter=agent_filter,
            role_filter=role_filter,
        )
        return len(messages)

    def delete_messages(
        self,
        session_id: str,
        agent_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        刪除匹配過濾條件的消息。

        Args:
            session_id: 會話 ID
            agent_filter: Agent 名稱過濾器
            role_filter: 角色過濾器
            start_time: 開始時間過濾器
            end_time: 結束時間過濾器

        Returns:
            刪除的消息數量
        """
        try:
            key = self._key(session_id, "messages")
            messages_data = self._storage.load(key)

            if not messages_data or "messages" not in messages_data:
                return 0

            original_count = len(messages_data["messages"])
            filtered_messages: List[Dict[str, Any]] = []

            for msg_dict in messages_data["messages"]:
                # 檢查是否應該保留
                should_keep = True

                if agent_filter and msg_dict.get("agent_name") != agent_filter:
                    should_keep = False
                if role_filter and msg_dict.get("role") != role_filter:
                    should_keep = False
                if start_time:
                    msg_time = msg_dict.get("timestamp")
                    if isinstance(msg_time, str):
                        msg_time = datetime.fromisoformat(msg_time)
                    if msg_time and msg_time < start_time:
                        should_keep = False
                if end_time:
                    msg_time = msg_dict.get("timestamp")
                    if isinstance(msg_time, str):
                        msg_time = datetime.fromisoformat(msg_time)
                    if msg_time and msg_time > end_time:
                        should_keep = False

                if should_keep:
                    filtered_messages.append(msg_dict)

            messages_data["messages"] = filtered_messages
            messages_data["updated_at"] = datetime.now().isoformat()

            self._storage.save(key, messages_data)

            deleted_count = original_count - len(filtered_messages)
            logger.info(
                "Deleted %d messages from session %s", deleted_count, session_id
            )
            return deleted_count
        except Exception as exc:
            logger.error("Failed to delete messages: %s", exc)
            return 0

    def clear_history(self, session_id: str) -> bool:
        """
        清空會話的所有歷史記錄。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功清空
        """
        try:
            key = self._key(session_id, "messages")
            return self._storage.delete(key)
        except Exception as exc:
            logger.error("Failed to clear history: %s", exc)
            return False

    def archive_session(
        self, session_id: str, archive_key: Optional[str] = None
    ) -> bool:
        """
        歸檔會話歷史記錄。

        Args:
            session_id: 會話 ID
            archive_key: 歸檔鍵（如果為 None，則使用默認格式）

        Returns:
            是否成功歸檔
        """
        try:
            key = self._key(session_id, "messages")
            archive_key_final = archive_key or self._key(
                session_id, f"archive:{datetime.now().isoformat()}"
            )

            messages_data = self._storage.load(key)
            if messages_data:
                self._storage.save(archive_key_final, messages_data)
                self._storage.delete(key)
                logger.info("Archived session %s to %s", session_id, archive_key_final)
                return True
            return False
        except Exception as exc:
            logger.error("Failed to archive session: %s", exc)
            return False
