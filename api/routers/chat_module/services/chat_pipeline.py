# 代碼功能說明: Chat 管道（最小可行：委派 _process_chat_request）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""ChatPipeline：process(request) -> ChatResponse，內部先調用現有 _process_chat_request（最小可行）。"""

import logging
from typing import TYPE_CHECKING

from api.routers.chat import _process_chat_request
from services.api.models.chat import ChatResponse

if TYPE_CHECKING:
    from api.routers.chat_module.handlers.base import ChatHandlerRequest

logger = logging.getLogger(__name__)

STEP_NAME = "chat_pipeline.process"


class ChatPipeline:
    """
    Chat 處理管道（階段二 b 最小可行）。
    process(request) 內部調用 _process_chat_request，與委派行為一致。
    後續可逐步替換為 L0→L1→…→L5、RAG、記憶、上下文、LLM、任務治理等。
    """

    async def process(self, request: "ChatHandlerRequest") -> ChatResponse:
        """
        處理 Chat 請求：委派給現有 _process_chat_request，返回 ChatResponse。

        Args:
            request: Handler 請求上下文（request_body、request_id、tenant_id、current_user）

        Returns:
            ChatResponse
        """
        try:
            response = await _process_chat_request(
                request_body=request.request_body,
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                current_user=request.current_user,
            )
            return response
        except Exception as exc:
            logger.error(
                f"Chat error at step={STEP_NAME}: request_id={request.request_id}, "
                f"error_type={type(exc).__name__}, error={str(exc)}",
                exc_info=True,
            )
            raise
