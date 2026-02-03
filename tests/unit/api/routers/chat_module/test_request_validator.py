# 代碼功能說明: request_validator 單元測試
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""validate_chat_request：合法通過、非法拋 422。"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.routers.chat_module.validators.request_validator import validate_chat_request
from services.api.models.chat import ChatMessage, ChatRequest, ModelSelector


def _make_request(
    messages: list | None = None,
    model_selector: ModelSelector | None = None,
) -> ChatRequest:
    """組裝 ChatRequest。"""
    if messages is None:
        messages = [ChatMessage(role="user", content="hello")]
    if model_selector is None:
        model_selector = ModelSelector(mode="auto")
    return ChatRequest(
        messages=messages,
        model_selector=model_selector,
    )


class TestValidateChatRequest:
    """validate_chat_request 測試。"""

    def test_valid_request_passes(self) -> None:
        """合法請求（messages 非空、有 content、model_selector 合法）應不拋異常。"""
        req = _make_request()
        validate_chat_request(req)  # 不應拋出

    def test_empty_content_raises_422(self) -> None:
        """最後一條消息 content 為空應拋 422。"""
        req = _make_request(
            messages=[
                ChatMessage(role="user", content="  "),
            ]
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_chat_request(req)
        assert exc_info.value.status_code == 422
        assert "內容不能為空" in str(exc_info.value.detail)

    def test_whitespace_only_content_raises_422(self) -> None:
        """最後一條消息僅空白應拋 422。"""
        req = _make_request(
            messages=[ChatMessage(role="user", content="   \t  ")]
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_chat_request(req)
        assert exc_info.value.status_code == 422
        assert "內容不能為空" in str(exc_info.value.detail)
