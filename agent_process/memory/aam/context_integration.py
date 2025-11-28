# 代碼功能說明: AAM 上下文整合
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 上下文整合 - 實現上下文到記憶的映射和記憶到上下文的注入"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

from agent_process.context.manager import ContextManager
from agent_process.memory.aam.models import Memory, MemoryType, MemoryPriority
from agent_process.memory.aam.aam_core import AAMManager
from agent_process.memory.aam.realtime_retrieval import RealtimeRetrievalService

logger = structlog.get_logger(__name__)


class ContextIntegration:
    """上下文整合 - 整合 Context Manager 和 AAM"""

    def __init__(
        self,
        context_manager: ContextManager,
        aam_manager: AAMManager,
        retrieval_service: Optional[RealtimeRetrievalService] = None,
    ):
        """
        初始化上下文整合

        Args:
            context_manager: 上下文管理器
            aam_manager: AAM 管理器
            retrieval_service: 實時檢索服務（如果為 None 則自動創建）
        """
        self.context_manager = context_manager
        self.aam_manager = aam_manager
        self.retrieval_service = retrieval_service or RealtimeRetrievalService(
            aam_manager
        )
        self.logger = logger.bind(component="context_integration")

    def context_to_memory(
        self,
        session_id: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
    ) -> Optional[str]:
        """
        將上下文轉換為記憶並存儲

        Args:
            session_id: 會話 ID
            memory_type: 記憶類型
            priority: 記憶優先級

        Returns:
            記憶 ID，如果失敗則返回 None
        """
        try:
            # 獲取上下文消息
            messages = self.context_manager.get_messages(session_id)
            if not messages:
                self.logger.warning(
                    "No messages found in context", session_id=session_id
                )
                return None

            # 構建記憶內容（合併最近的幾條消息）
            content_parts: List[str] = []
            for msg in messages[-5:]:  # 只取最近5條消息
                content_parts.append(f"{msg.role}: {msg.content}")

            content = "\n".join(content_parts)

            # 構建元數據
            metadata: Dict[str, Any] = {
                "session_id": session_id,
                "message_count": len(messages),
                "source": "context_manager",
            }

            # 存儲記憶
            memory_id = self.aam_manager.store_memory(
                content=content,
                memory_type=memory_type,
                priority=priority,
                metadata=metadata,
            )

            if memory_id:
                self.logger.info(
                    "Stored context as memory",
                    session_id=session_id,
                    memory_id=memory_id,
                    memory_type=memory_type.value,
                )

            return memory_id
        except Exception as e:
            self.logger.error(
                "Failed to convert context to memory",
                error=str(e),
                session_id=session_id,
            )
            return None

    def inject_memory_to_context(
        self,
        session_id: str,
        query: Optional[str] = None,
        limit: int = 5,
        min_relevance: float = 0.5,
    ) -> List[Memory]:
        """
        將相關記憶注入到上下文

        Args:
            session_id: 會話 ID
            query: 查詢文本（如果為 None 則使用最近的上下文）
            limit: 注入的記憶數量限制
            min_relevance: 最小相關度閾值

        Returns:
            注入的記憶列表
        """
        try:
            # 如果沒有提供查詢，從上下文構建查詢
            if query is None:
                messages = self.context_manager.get_messages(session_id, limit=3)
                if messages:
                    query = " ".join([msg.content for msg in messages])
                else:
                    self.logger.warning(
                        "No messages found for query construction",
                        session_id=session_id,
                    )
                    return []

            # 構建上下文信息
            context: Dict[str, Any] = {
                "session_id": session_id,
            }

            # 檢索相關記憶
            memories = self.retrieval_service.retrieve(
                query=query,
                context=context,
                limit=limit,
                min_relevance=min_relevance,
            )

            # 將記憶注入到上下文（作為系統消息）
            for memory in memories:
                system_message = f"[Memory: {memory.memory_id}] {memory.content}"
                self.context_manager.record_message(
                    session_id=session_id,
                    role="system",
                    content=system_message,
                    agent_name="AAM",
                    metadata={
                        "memory_id": memory.memory_id,
                        "relevance": memory.relevance_score,
                    },
                )

            self.logger.info(
                "Injected memories to context",
                session_id=session_id,
                count=len(memories),
            )

            return memories
        except Exception as e:
            self.logger.error(
                "Failed to inject memory to context",
                error=str(e),
                session_id=session_id,
            )
            return []

    def sync_context_to_memory(
        self,
        session_id: str,
        auto_sync: bool = True,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
    ) -> Optional[str]:
        """
        同步上下文到記憶（實時更新）

        Args:
            session_id: 會話 ID
            auto_sync: 是否自動同步（如果為 True，則在每次消息記錄時自動同步）
            memory_type: 記憶類型

        Returns:
            記憶 ID，如果失敗則返回 None
        """
        try:
            # 獲取最新的上下文
            messages = self.context_manager.get_messages(session_id)
            if not messages:
                return None

            # 只同步最新的消息（增量更新）
            latest_message = messages[-1]
            content = f"{latest_message.role}: {latest_message.content}"

            metadata: Dict[str, Any] = {
                "session_id": session_id,
                "message_id": latest_message.message_id
                if hasattr(latest_message, "message_id")
                else None,
                "timestamp": latest_message.timestamp.isoformat()
                if hasattr(latest_message, "timestamp")
                else None,
                "source": "context_sync",
            }

            # 存儲記憶
            memory_id = self.aam_manager.store_memory(
                content=content,
                memory_type=memory_type,
                priority=MemoryPriority.MEDIUM,
                metadata=metadata,
            )

            if memory_id:
                self.logger.debug(
                    "Synced context to memory",
                    session_id=session_id,
                    memory_id=memory_id,
                )

            return memory_id
        except Exception as e:
            self.logger.error(
                "Failed to sync context to memory",
                error=str(e),
                session_id=session_id,
            )
            return None
