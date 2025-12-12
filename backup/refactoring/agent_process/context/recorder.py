# 代碼功能說明: 上下文記錄器
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""上下文記錄器，提供消息記錄和檢索功能。"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import redis  # type: ignore[import-untyped]

from agent_process.context.models import ContextConfig, ContextMessage

logger = logging.getLogger(__name__)


class ContextRecorder:
    """上下文記錄器，負責記錄和檢索對話消息。"""

    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        redis_url: Optional[str] = None,
        namespace: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        初始化上下文記錄器。

        Args:
            config: 配置對象（優先使用）
            redis_url: Redis 連接 URL（如果 config 為 None 時使用）
            namespace: 命名空間（如果 config 為 None 時使用）
            ttl_seconds: TTL 秒數（如果 config 為 None 時使用）
        """
        if config is not None:
            self._config = config
        else:
            self._config = ContextConfig(
                redis_url=redis_url,
                namespace=namespace or "agent_process:context",
                ttl_seconds=ttl_seconds or 3600,
            )

        self._namespace = self._config.namespace
        self._ttl = self._config.ttl_seconds
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {}
        self._redis: Optional[redis.Redis] = None

        if self._config.redis_url:
            try:
                self._redis = redis.Redis.from_url(
                    self._config.redis_url, decode_responses=True
                )
                # 測試連接
                self._redis.ping()
                logger.info("Context Recorder 已連接到 Redis")
            except Exception as exc:
                logger.warning(
                    "Context Recorder 初始化 Redis 失敗，使用記憶體儲存: %s", exc
                )
                self._redis = None

    def _key(self, session_id: str, suffix: Optional[str] = None) -> str:
        """
        生成 Redis 鍵。

        Args:
            session_id: 會話 ID
            suffix: 可選後綴

        Returns:
            Redis 鍵
        """
        if suffix:
            return f"{self._namespace}:{session_id}:{suffix}"
        return f"{self._namespace}:{session_id}"

    def record(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        記錄消息。

        Args:
            session_id: 會話 ID
            role: 消息角色（user, assistant, system）
            content: 消息內容
            metadata: 元數據

        Returns:
            是否成功記錄
        """
        try:
            message = ContextMessage(
                role=role, content=content, metadata=metadata or {}
            )
            message_dict = message.model_dump()

            if self._redis is not None:
                # 使用 Redis List 存儲消息
                key = self._key(session_id, "messages")
                message_json = json.dumps(message_dict, default=str)
                self._redis.rpush(key, message_json)
                self._redis.expire(key, self._ttl)
            else:
                # 使用內存存儲
                if session_id not in self._memory_store:
                    self._memory_store[session_id] = []
                self._memory_store[session_id].append(message_dict)

            logger.debug("Recorded message in session %s (role: %s)", session_id, role)
            return True
        except Exception as exc:
            logger.error("Failed to record message: %s", exc)
            return False

    def get_conversation_context(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        獲取對話上下文，格式為 LLM 可用的消息列表。

        Args:
            session_id: 會話 ID
            limit: 限制返回的消息數量（None 表示返回所有）

        Returns:
            消息列表，格式為 [{"role": "...", "content": "..."}]
        """
        try:
            messages: List[Dict[str, Any]] = []

            if self._redis is not None:
                key = self._key(session_id, "messages")
                message_jsons = self._redis.lrange(key, 0, -1)
                if isinstance(message_jsons, list):
                    for msg_json in message_jsons:
                        if isinstance(msg_json, str):
                            messages.append(json.loads(msg_json))
            else:
                messages = self._memory_store.get(session_id, [])

            # 轉換為 LLM 格式
            llm_messages: List[Dict[str, str]] = []
            for msg in messages:
                llm_messages.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                )

            # 應用限制
            if limit is not None and limit > 0:
                llm_messages = llm_messages[-limit:]

            return llm_messages
        except Exception as exc:
            logger.error("Failed to get conversation context: %s", exc)
            return []

    def clear_session(self, session_id: str) -> bool:
        """
        清空會話的所有消息。

        Args:
            session_id: 會話 ID

        Returns:
            是否成功清空
        """
        try:
            if self._redis is not None:
                key = self._key(session_id, "messages")
                self._redis.delete(key)
            else:
                if session_id in self._memory_store:
                    del self._memory_store[session_id]

            logger.info("Cleared session %s", session_id)
            return True
        except Exception as exc:
            logger.error("Failed to clear session: %s", exc)
            return False

    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[ContextMessage]:
        """
        獲取完整的消息對象列表。

        Args:
            session_id: 會話 ID
            limit: 限制返回的消息數量

        Returns:
            消息對象列表
        """
        try:
            messages: List[Dict[str, Any]] = []

            if self._redis is not None:
                key = self._key(session_id, "messages")
                message_jsons = self._redis.lrange(key, 0, -1)
                if isinstance(message_jsons, list):
                    for msg_json in message_jsons:
                        if isinstance(msg_json, str):
                            messages.append(json.loads(msg_json))
            else:
                messages = self._memory_store.get(session_id, [])

            # 轉換為 ContextMessage 對象
            context_messages: List[ContextMessage] = []
            for msg_dict in messages:
                try:
                    # 處理時間戳字符串
                    if "timestamp" in msg_dict and isinstance(
                        msg_dict["timestamp"], str
                    ):
                        from datetime import datetime

                        msg_dict["timestamp"] = datetime.fromisoformat(
                            msg_dict["timestamp"]
                        )
                    context_messages.append(ContextMessage(**msg_dict))
                except Exception as exc:
                    logger.warning("Failed to parse message: %s", exc)

            # 應用限制
            if limit is not None and limit > 0:
                context_messages = context_messages[-limit:]

            return context_messages
        except Exception as exc:
            logger.error("Failed to get messages: %s", exc)
            return []
