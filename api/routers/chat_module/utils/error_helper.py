# 代碼功能說明: Chat 統一錯誤處理（ErrorHandler）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31 14:30 UTC+8

"""ErrorHandler：handle_llm_error、create_http_exception，用於統一錯誤響應。"""

import logging
from typing import Optional, Tuple

from fastapi import HTTPException, status

from api.routers.chat_module.models.internal import ChatErrorResponse, ErrorCode

logger = logging.getLogger(__name__)


class ErrorHandler:
    """統一錯誤處理器。"""

    @staticmethod
    def handle_llm_error(error: Exception) -> Tuple[str, ErrorCode]:
        """
        處理 LLM 相關錯誤，返回友好錯誤消息和錯誤碼。

        與 v1 chat.py translate_error_to_user_message 對齊：
        - Ollama 本地服務 401/403 視為連線異常，非 API 授權
        - 僅當明確提及 api key/credentials 時才歸類為 API 授權問題

        Args:
            error: 原始異常

        Returns:
            (user_friendly_message, error_code)
        """
        # 合併異常鏈（__cause__）以捕獲被包裝的錯誤訊息
        error_str = str(error).lower()
        if hasattr(error, "__cause__") and error.__cause__ is not None:
            error_str += " " + str(error.__cause__).lower()

        # 0. Ollama 特殊處理：本地 Ollama 不需要 API key，401/403/auth 通常是連線或模型問題
        # 辨識：含 ollama 或 localhost:11434（Ollama 預設埠），且含 401/403/auth 關鍵字
        is_ollama_context = (
            "ollama" in error_str or "localhost:11434" in error_str or ":11434" in error_str
        )
        ollama_auth_keywords = [
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "authentication",
            "auth failed",
        ]
        if is_ollama_context and any(kw in error_str for kw in ollama_auth_keywords):
            return (
                "哎呀，發生了一些小狀況！🦙 Ollama 服務連線異常，請確認 Ollama 是否運行、模型是否已拉取（錯誤代碼：OLLAMA_ERROR）😅",
                ErrorCode.LLM_SERVICE_ERROR,
            )

        # 0.1 HTTP 401/403 但非 API key 情境：LLM 服務連線/模型問題（避免誤判為 API 授權）
        has_explicit_api_key = any(
            kw in error_str for kw in ["api key", "apikey", "invalid credentials"]
        )
        has_401_403 = any(kw in error_str for kw in ["401", "403", "unauthorized", "forbidden"])
        if has_401_403 and not has_explicit_api_key:
            return (
                "哎呀，發生了一些小狀況！🤖 LLM 服務連線異常，請確認模型服務是否運行、模型是否已拉取（錯誤代碼：LLM_SERVICE_ERROR）😅",
                ErrorCode.LLM_SERVICE_ERROR,
            )

        # 1. API Key 無效或授權錯誤（明確提及 api key、credentials 等）
        if any(
            k in error_str
            for k in ["api key", "apikey", "unauthorized", "401", "invalid credentials"]
        ):
            return (
                "哎呀，發生了一些小狀況！🔐 API 授權出現問題，請通知管理員（錯誤代碼：API_INVALID）😅",
                ErrorCode.AUTHENTICATION_ERROR,
            )
        if any(k in error_str for k in ["connection", "timeout", "network"]):
            return (
                "哎呀，發生了一些小狀況！🌐 網路連線出現問題，請檢查網路連線後再試（錯誤代碼：NETWORK_ERROR）😅",
                ErrorCode.LLM_SERVICE_ERROR,
            )
        if any(k in error_str for k in ["timeout", "timed out"]):
            return (
                "哎呀，發生了一些小狀況！⏱️ 請求處理時間過長，請稍後再試或通知管理員（錯誤代碼：TIMEOUT_ERROR）😅",
                ErrorCode.LLM_TIMEOUT,
            )
        if any(k in error_str for k in ["rate limit", "429", "quota"]):
            return (
                "哎呀，發生了一些小狀況！😓 AI 模型服務超出使用限制，請通知管理員（錯誤代碼：LIMIT_EXCEEDED）😅",
                ErrorCode.LLM_RATE_LIMIT,
            )
        return (
            f"哎呀，發生了一些小狀況，我感到很抱歉！請通知管理員（錯誤代碼：{ErrorCode.INTERNAL_SERVER_ERROR.value}）😅",
            ErrorCode.INTERNAL_SERVER_ERROR,
        )

    @staticmethod
    def create_http_exception(
        error: Exception,
        error_code: Optional[ErrorCode] = None,
        request_id: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> HTTPException:
        """
        創建 HTTP 異常，使用統一錯誤體。

        Args:
            error: 原始異常
            error_code: 錯誤代碼（若未指定則根據 error 推斷）
            request_id: 請求 ID
            status_code: HTTP 狀態碼

        Returns:
            HTTPException 實例
        """
        message, code = ErrorHandler.handle_llm_error(error)
        if error_code is not None:
            code = error_code
        logger.error(
            f"Error occurred: request_id={request_id}, error_code={code}, error={str(error)}",
            exc_info=True,
        )
        detail = ChatErrorResponse(
            error_code=code,
            message=message,
            request_id=request_id,
            details={
                "error_type": type(error).__name__,
                "original_error": str(error),
            },
        )
        return HTTPException(
            status_code=status_code,
            detail=detail.model_dump(mode="json"),
        )
