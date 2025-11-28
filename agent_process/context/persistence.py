# 代碼功能說明: 上下文記錄持久化
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""上下文記錄持久化管理器，提供持久化存儲到 ArangoDB 的功能。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from databases.arangodb import ArangoDBClient

from agent_process.context.models import ContextConfig, ContextMessage

logger = logging.getLogger(__name__)


class ContextPersistence:
    """上下文持久化管理器。"""

    def __init__(
        self,
        config: ContextConfig,
        arangodb_client: Optional[ArangoDBClient] = None,
    ) -> None:
        """
        初始化上下文持久化管理器。

        Args:
            config: 配置對象
            arangodb_client: ArangoDB 客戶端（如果為 None，則不啟用持久化）
        """
        self._config = config
        self._client = arangodb_client
        self._collection_name = config.arangodb_collection or "context_records"

        if self._client is not None and config.enable_persistence:
            self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保 ArangoDB 集合存在。"""
        if self._client is None:
            return

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return

            self._client.get_or_create_collection(
                self._collection_name, collection_type="document"
            )
            logger.info(
                "Context persistence collection ready: %s", self._collection_name
            )
        except Exception as exc:
            logger.error("Failed to ensure collection: %s", exc)

    def save_context(
        self,
        session_id: str,
        messages: List[ContextMessage],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        保存上下文記錄到 ArangoDB。

        Args:
            session_id: 會話 ID
            messages: 消息列表
            metadata: 元數據

        Returns:
            是否成功保存
        """
        if self._client is None or not self._config.enable_persistence:
            return False

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return False

            collection = self._client.db.collection(self._collection_name)

            # 構建文檔
            document: Dict[str, Any] = {
                "_key": session_id,
                "session_id": session_id,
                "messages": [msg.model_dump() for msg in messages],
                "message_count": len(messages),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            # 保存或更新
            if collection.has(session_id):
                collection.update(document)
            else:
                collection.insert(document)

            logger.info("Saved context to ArangoDB for session %s", session_id)
            return True
        except Exception as exc:
            logger.error("Failed to save context: %s", exc)
            return False

    def load_context(self, session_id: str) -> Optional[List[ContextMessage]]:
        """
        從 ArangoDB 加載上下文記錄。

        Args:
            session_id: 會話 ID

        Returns:
            消息列表，如果不存在則返回 None
        """
        if self._client is None or not self._config.enable_persistence:
            return None

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return None

            collection = self._client.db.collection(self._collection_name)

            if not collection.has(session_id):
                return None

            document = collection.get(session_id)

            if (
                document is None
                or not isinstance(document, dict)
                or "messages" not in document
            ):
                return None

            # 轉換為 ContextMessage 對象
            messages: List[ContextMessage] = []
            for msg_dict in document["messages"]:
                try:
                    # 處理時間戳字符串
                    if "timestamp" in msg_dict and isinstance(
                        msg_dict["timestamp"], str
                    ):
                        msg_dict["timestamp"] = datetime.fromisoformat(
                            msg_dict["timestamp"]
                        )
                    messages.append(ContextMessage(**msg_dict))
                except Exception as exc:
                    logger.warning("Failed to parse message: %s", exc)

            return messages
        except Exception as exc:
            logger.error("Failed to load context: %s", exc)
            return None

    def query_contexts(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢上下文記錄。

        Args:
            user_id: 用戶 ID 過濾器
            start_time: 開始時間過濾器
            end_time: 結束時間過濾器
            limit: 限制返回數量

        Returns:
            上下文記錄列表
        """
        if self._client is None or not self._config.enable_persistence:
            return []

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return []

            if self._client.db.aql is None:
                logger.warning("AQL is not available")
                return []

            # 構建 AQL 查詢
            filters: List[str] = []
            bind_vars: Dict[str, Any] = {}

            if user_id:
                filters.append("doc.metadata.user_id == @user_id")
                bind_vars["user_id"] = user_id

            if start_time:
                filters.append("doc.created_at >= @start_time")
                bind_vars["start_time"] = start_time.isoformat()

            if end_time:
                filters.append("doc.created_at <= @end_time")
                bind_vars["end_time"] = end_time.isoformat()

            filter_clause = " AND ".join(filters) if filters else "true"

            aql = f"""
                FOR doc IN {self._collection_name}
                    FILTER {filter_clause}
                    SORT doc.updated_at DESC
                    LIMIT @limit
                    RETURN doc
            """

            bind_vars["limit"] = limit

            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            if cursor is not None:
                results = list(cursor)  # type: ignore[arg-type]
                return results
            return []
        except Exception as exc:
            logger.error("Failed to query contexts: %s", exc)
            return []

    def archive_context(
        self, session_id: str, archive_key: Optional[str] = None
    ) -> bool:
        """
        歸檔上下文記錄。

        Args:
            session_id: 會話 ID
            archive_key: 歸檔鍵（如果為 None，則使用默認格式）

        Returns:
            是否成功歸檔
        """
        if self._client is None or not self._config.enable_persistence:
            return False

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return False

            collection = self._client.db.collection(self._collection_name)

            if not collection.has(session_id):
                return False

            document = collection.get(session_id)
            if document is None or not isinstance(document, dict):
                return False

            # 更新文檔標記為已歸檔
            archive_key_final = (
                archive_key or f"archive_{session_id}_{datetime.now().isoformat()}"
            )
            document["archived"] = True
            document["archive_key"] = archive_key_final
            document["archived_at"] = datetime.now().isoformat()

            collection.update(document)  # type: ignore[arg-type]

            logger.info("Archived context for session %s", session_id)
            return True
        except Exception as exc:
            logger.error("Failed to archive context: %s", exc)
            return False

    def cleanup_old_contexts(self, days: int = 30, dry_run: bool = False) -> int:
        """
        清理舊的上下文記錄。

        Args:
            days: 保留天數
            dry_run: 是否為試運行（不實際刪除）

        Returns:
            清理的記錄數量
        """
        if self._client is None or not self._config.enable_persistence:
            return 0

        try:
            self._client.ensure_connection()
            if self._client.db is None:
                logger.warning("ArangoDB database is not connected")
                return 0

            if self._client.db.aql is None:
                logger.warning("AQL is not available")
                return 0

            from datetime import timedelta

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            aql = f"""
                FOR doc IN {self._collection_name}
                    FILTER doc.updated_at < @cutoff_date
                    FILTER doc.archived != true
                    RETURN doc._key
            """

            cursor = self._client.db.aql.execute(
                aql, bind_vars={"cutoff_date": cutoff_date}
            )
            if cursor is not None:
                keys_to_delete = list(cursor)  # type: ignore[arg-type]
            else:
                keys_to_delete = []

            if not dry_run:
                collection = self._client.db.collection(self._collection_name)
                for key in keys_to_delete:
                    try:
                        collection.delete(key)
                    except Exception as exc:
                        logger.warning("Failed to delete key %s: %s", key, exc)

            logger.info(
                "Cleaned up %d old contexts (dry_run=%s)", len(keys_to_delete), dry_run
            )
            return len(keys_to_delete)
        except Exception as exc:
            logger.error("Failed to cleanup old contexts: %s", exc)
            return 0
