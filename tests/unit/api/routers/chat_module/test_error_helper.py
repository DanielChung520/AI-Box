# 代碼功能說明: ErrorHandler 單元測試
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""ErrorHandler.handle_llm_error、create_http_exception 單元測試。"""

from __future__ import annotations

from api.routers.chat_module.models.internal import ErrorCode
from api.routers.chat_module.utils.error_helper import ErrorHandler


class TestErrorHandlerHandleLlmError:
    """handle_llm_error 測試。"""

    def test_timeout_error_returns_llm_timeout(self) -> None:
        """TimeoutError 應返回 LLM_TIMEOUT 與友好消息。"""
        exc = TimeoutError("Request timed out")
        message, code = ErrorHandler.handle_llm_error(exc)
        assert code == ErrorCode.LLM_TIMEOUT
        assert "時間" in message or "超時" in message or "TIMEOUT" in message.upper()

    def test_connection_error_returns_llm_service_error(self) -> None:
        """ConnectionError 應返回 LLM_SERVICE_ERROR。"""
        exc = ConnectionError("Connection refused")
        message, code = ErrorHandler.handle_llm_error(exc)
        assert code == ErrorCode.LLM_SERVICE_ERROR
        assert "網路" in message or "NETWORK" in message.upper()

    def test_unauthorized_string_returns_auth_error(self) -> None:
        """含 'unauthorized' 的錯誤應返回 AUTHENTICATION_ERROR。"""
        exc = ValueError("Invalid API key unauthorized")
        message, code = ErrorHandler.handle_llm_error(exc)
        assert code == ErrorCode.AUTHENTICATION_ERROR

    def test_rate_limit_string_returns_llm_rate_limit(self) -> None:
        """含 'rate limit' 的錯誤應返回 LLM_RATE_LIMIT。"""
        exc = RuntimeError("Rate limit exceeded 429")
        message, code = ErrorHandler.handle_llm_error(exc)
        assert code == ErrorCode.LLM_RATE_LIMIT

    def test_generic_error_returns_internal_server_error(self) -> None:
        """未識別錯誤應返回 INTERNAL_SERVER_ERROR。"""
        exc = ValueError("Something else")
        message, code = ErrorHandler.handle_llm_error(exc)
        assert code == ErrorCode.INTERNAL_SERVER_ERROR
        assert "小狀況" in message or "INTERNAL" in message.upper()


class TestErrorHandlerCreateHttpException:
    """create_http_exception 測試。"""

    def test_returns_http_exception_with_detail(self) -> None:
        """應返回 HTTPException，detail 為 ChatErrorResponse 結構。"""
        exc = TimeoutError("timed out")
        http_exc = ErrorHandler.create_http_exception(
            exc, request_id="req_123", status_code=500
        )
        assert http_exc.status_code == 500
        assert isinstance(http_exc.detail, dict)
        assert http_exc.detail.get("error_code") == ErrorCode.LLM_TIMEOUT.value
        assert "message" in http_exc.detail
        assert "request_id" in http_exc.detail
        assert http_exc.detail["request_id"] == "req_123"
