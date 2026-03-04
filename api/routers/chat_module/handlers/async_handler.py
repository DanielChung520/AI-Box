# 代碼功能說明: AsyncHandler - 異步處理器
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""AsyncHandler - 異步 Chat 處理器"""

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from api.routers.chat_module.config import ChatConfig
from api.routers.chat_module.services.async_request_store import (
    AsyncRequestRecord,
    create_async_request,
    set_async_request_status,
)
from api.routers.chat_module.services.orchestrator_service import (
    get_orchestrator_service,
)
from services.api.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class AsyncHandler:
    """異步 Chat 處理器

    處理流程：
    1. 創建異步請求記錄
    2. 在後台執行 OrchestratorService
    3. 返回 request_id (202)
    """

    async def process(
        self,
        messages: list[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> str:
        """處理異步請求

        Args:
            messages: 訊息列表
            config: Chat 配置
            context: 上下文

        Returns:
            request_id: 異步請求 ID
        """
        request_id = str(uuid.uuid4())
        tenant_id = context.get("tenant_id")
        user_id = context.get("user_id")

        # 創建異步請求記錄
        await create_async_request(
            priority="normal",
            task_id=context.get("task_id"),
            request_body={
                "messages": [m.model_dump() for m in messages],
                "config": config.model_dump(),
                "context": context,
            },
            tenant_id=tenant_id,
        )

        logger.info(
            f"[AsyncHandler] created: request_id={request_id}, "
            f"tenant_id={tenant_id}, user_id={user_id}"
        )

        # 在後台執行
        asyncio.create_task(self._execute_in_background(request_id, messages, config, context))

        return request_id

    async def _execute_in_background(
        self,
        request_id: str,
        messages: list[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> None:
        """在後台執行 OrchestratorService"""
        try:
            # 更新狀態為 running
            await set_async_request_status(request_id, "running")

            # 獲取 OrchestratorService
            orchestrator = get_orchestrator_service()

            # 執行處理
            result = await orchestrator.process(
                messages=messages,
                config=config,
                context=context,
            )

            # 設置結果
            await set_async_request_status(request_id, "completed", result=result)

            logger.info(f"[AsyncHandler] completed: request_id={request_id}")

        except Exception as e:
            logger.error(
                f"[AsyncHandler] failed: request_id={request_id}, error={str(e)}",
                exc_info=True,
            )
            await set_async_request_status(request_id, "failed", error=str(e))

    async def get_status(self, request_id: str) -> Optional[AsyncRequestRecord]:
        """獲取異步請求狀態"""
        from api.routers.chat_module.services.async_request_store import (
            get_async_request,
        )

        return await get_async_request(request_id)

    async def retry(self, request_id: str) -> str:
        """重試異步請求"""
        from api.routers.chat_module.services.async_request_store import (
            get_async_request,
        )

        # 獲取原請求
        record = await get_async_request(request_id)
        if not record:
            raise ValueError(f"Request not found: {request_id}")

        if record.status != "failed":
            raise ValueError(f"Only failed requests can be retried: {request_id}")

        # 重新創建請求
        request_body = record.request_body
        messages = request_body.get("messages", [])
        config = request_body.get("config", {})
        context = request_body.get("context", {})

        # 轉換為 ChatMessage
        chat_messages = [ChatMessage(**msg) for msg in messages]

        # 轉換為 ChatConfig
        chat_config = ChatConfig(**config)

        # 處理
        new_request_id = await self.process(
            messages=chat_messages,
            config=chat_config,
            context=context,
        )

        return new_request_id


# 全局實例
_async_handler: Optional[AsyncHandler] = None


def get_async_handler() -> AsyncHandler:
    """獲取全局 AsyncHandler 實例"""
    global _async_handler
    if _async_handler is None:
        _async_handler = AsyncHandler()
    return _async_handler
