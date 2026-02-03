# 代碼功能說明: Chat 請求驗證（messages 非空、model_selector 合法）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""validate_chat_request：校驗 messages 非空、model_selector 合法，不通過則 raise HTTPException(422)。"""

import logging
from fastapi import HTTPException, status

from services.api.models.chat import ChatRequest, ModelSelector

logger = logging.getLogger(__name__)


def validate_chat_request(body: ChatRequest) -> None:
    """
    校驗 Chat 請求：messages 非空、最後一條有 content、model_selector 合法。

    Args:
        body: 已解析的 ChatRequest（Pydantic 已做基本校驗）

    Raises:
        HTTPException: 422 當 messages 為空、content 為空、或 model_selector 不合法
    """
    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "消息列表不能為空",
            },
        )
    last_msg = body.messages[-1]
    if not (last_msg.content and last_msg.content.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "消息內容不能為空",
            },
        )
    # model_selector 在 Pydantic 已校驗 mode/model_id；可再補 business 校驗
    _validate_model_selector(body.model_selector)


def _validate_model_selector(selector: ModelSelector) -> None:
    """校驗 model_selector：manual/favorite 時 model_id 必填（Pydantic 已做，此處可擴展）。"""
    if selector.mode in ("manual", "favorite") and not selector.model_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "manual 或 favorite 模式下 model_id 必填",
            },
        )
