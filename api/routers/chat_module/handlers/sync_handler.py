# 代碼功能說明: Chat 模塊 SyncHandler（經 ChatPipeline 委派）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""SyncHandler(BaseHandler)：handle 調用 get_chat_pipeline().process(request)，主聊天走 pipeline。"""

import logging

from api.routers.chat_module.dependencies import get_chat_pipeline
from api.routers.chat_module.handlers.base import BaseHandler, ChatHandlerRequest
from services.api.models.chat import ChatResponse

logger = logging.getLogger(__name__)

STEP_NAME = "SyncHandler.handle"


class SyncHandler(BaseHandler):
    """同步 Chat 處理器：經 ChatPipeline.process 委派，行為與委派一致。"""

    async def handle(self, request: ChatHandlerRequest) -> ChatResponse:
        """
        調用 get_chat_pipeline().process(request)，主聊天走 pipeline。

        Args:
            request: 請求上下文

        Returns:
            ChatResponse
        """
        try:
            return await get_chat_pipeline().process(request)
        except Exception as exc:
            logger.error(
                f"Chat error at step={STEP_NAME}: request_id={request.request_id}, "
                f"error_type={type(exc).__name__}, error={str(exc)}",
                exc_info=True,
            )
            raise
