# 代碼功能說明: Chat 模塊 StreamHandler（SSE 流式響應，與前端對齊）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""StreamHandler(BaseHandler)：handle 返回 SSE 流；格式與前端對齊（start/content/file_created/error/done）。"""

import json
import logging
from typing import Any, AsyncGenerator, Dict

from api.routers.chat_module.dependencies import get_chat_pipeline
from api.routers.chat_module.handlers.base import BaseHandler, ChatHandlerRequest
from api.routers.chat_module.utils.error_helper import ErrorHandler

logger = logging.getLogger(__name__)


def _sse_line(event: Dict[str, Any]) -> str:
    """將事件轉為 SSE 行：data: {...}\\n\\n"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class StreamHandler(BaseHandler):
    """
    流式 Chat 處理器：返回 SSE 流，格式與前端對齊（階段六 T6.1–T6.5）。
    - start: 流開始
    - content: 內容塊（data.chunk）
    - file_created: 檔案建立（來自 response.actions）
    - error: 錯誤時送出後結束流
    - done: 流結束
    """

    async def handle(self, request: ChatHandlerRequest) -> AsyncGenerator[str, None]:
        """
        調用 pipeline.process，再以與前端對齊的 SSE 格式 yield。

        Yields:
            SSE 行（data: {...}\\n\\n）
        """
        session_id = request.request_body.session_id or ""
        # T6.2：流開始時送出 start 事件
        yield _sse_line({
            "type": "start",
            "data": {"request_id": request.request_id, "session_id": session_id},
        })
        try:
            pipeline = get_chat_pipeline()
            response = await pipeline.process(request)
        except Exception as exc:
            # T6.5：錯誤時送出 error 事件後結束流
            logger.exception(f"Stream pipeline failed: request_id={request.request_id}")
            msg, code = ErrorHandler.handle_llm_error(exc)
            yield _sse_line({
                "type": "error",
                "data": {"error": msg, "error_code": code.value},
            })
            return
        content = response.content or ""
        # T6.1：內容塊改為 type: content, data: { chunk }
        chunk_size = 1
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            yield _sse_line({
                "type": "content",
                "data": {"chunk": chunk},
            })
        # T6.4：若有 file_created 動作，在 done 前送出
        if response.actions:
            for action in response.actions:
                if isinstance(action, dict) and action.get("type") == "file_created":
                    yield _sse_line({"type": "file_created", "data": action})
        # T6.3：done 事件，含 data 包裝以與前端一致，並保留頂層 routing/observability
        done_event: Dict[str, Any] = {
            "type": "done",
            "data": {"request_id": request.request_id},
            "request_id": request.request_id,
            "routing": response.routing.model_dump(mode="json") if response.routing else {},
            "observability": (
                response.observability.model_dump(mode="json")
                if response.observability
                else None
            ),
        }
        yield _sse_line(done_event)
