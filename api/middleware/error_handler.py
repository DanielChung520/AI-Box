# 代碼功能說明: 錯誤處理中間件
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 12:35 UTC+8

"""全局錯誤處理中間件"""

import logging

from fastapi import status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.core.response import APIResponse

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局錯誤處理中間件"""

    async def dispatch(self, request: Request, call_next):
        """處理請求並捕獲異常"""
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            # 记录详细的验证错误信息
            error_details = e.errors()
            # 尝试读取请求体（用于调试）
            try:
                body = await request.body()
                body_str = body.decode("utf-8")[:1000] if body else None  # 记录前1000个字符
            except Exception:
                body_str = None

            # 修改時間：2026-01-28 - 檢查是否是空查詢錯誤，返回友好錯誤消息
            # 檢查是否是 chat 端點的空查詢錯誤
            if request.url.path.endswith("/chat") and request.method == "POST":
                is_empty_query = False
                logger.debug(
                    f"Checking empty query: path={request.url.path}, "
                    f"method={request.method}, error_count={len(error_details)}"
                )
                for error in error_details:
                    error_loc = error.get("loc", [])
                    error_type = error.get("type", "")
                    error_msg = error.get("msg", "")

                    logger.debug(
                        f"Error check: loc={error_loc}, type={error_type}, "
                        f"msg={error_msg}, loc_length={len(error_loc)}"
                    )

                    # 檢查是否是 messages[].content 的 min_length 錯誤
                    # 支持 Pydantic v2 的所有可能的錯誤類型
                    if (
                        len(error_loc) >= 4
                        and error_loc[0] == "body"
                        and error_loc[1] == "messages"
                        and isinstance(error_loc[2], int)
                        and error_loc[3] == "content"
                        and (
                            "min_length" in error_type
                            or "string_too_short" in error_type
                            or "value_error" in error_type
                            or "string_type" in error_type
                            or "greater_than_equal" in error_type
                            or "less_than_equal" in error_type
                            or ("string" in error_type and "length" in error_msg.lower())
                        )
                    ):
                        is_empty_query = True
                        logger.info(
                            f"Empty query detected in middleware: error_type={error_type}, "
                            f"error_loc={error_loc}, error_msg={error_msg}"
                        )
                        break

                if is_empty_query:
                    # 使用 KA-Agent 的錯誤處理器生成友好錯誤消息
                    try:
                        from agents.builtin.ka_agent.error_handler import KAAgentErrorHandler

                        error_feedback = KAAgentErrorHandler.missing_parameter(
                            parameter="instruction",
                            context="用戶查詢為空",
                        )

                        # 返回友好錯誤消息（使用 400 而非 422）
                        return APIResponse.error(
                            message=error_feedback.user_message,
                            error_code="MISSING_PARAMETER",
                            details={
                                "error_type": error_feedback.error_type.value,
                                "suggested_action": error_feedback.suggested_action.value,
                                "clarifying_questions": error_feedback.clarifying_questions,
                            },
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
                    except Exception as feedback_error:
                        logger.warning(
                            f"Failed to generate KA-Agent error feedback: {feedback_error}",
                            exc_info=True,
                        )

            # 使用 print 确保错误信息一定会输出（即使日志级别设置不当）
            print(f"\n{'='*80}")
            print(f"❌ RequestValidationError: {request.method} {request.url.path}")
            print(f"{'='*80}")
            print(f"Request body preview: {body_str}")
            print(f"Validation errors ({len(error_details)}):")
            for i, error in enumerate(error_details, 1):
                print(f"  {i}. Location: {error.get('loc')}")
                print(f"     Type: {error.get('type')}")
                print(f"     Message: {error.get('msg')}")
                print(f"     Input: {error.get('input')}")
            print(f"{'='*80}\n")

            logger.error(
                f"Request validation error: path={request.url.path}, method={request.method}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "errors": error_details,
                    "body_preview": body_str,
                },
            )
            # 记录每个验证错误
            for error in error_details:
                logger.error(
                    f"Validation error detail: loc={error.get('loc')}, msg={error.get('msg')}, type={error.get('type')}",
                    extra={"error": error},
                )
            return APIResponse.error(
                message="Request validation failed",
                error_code="VALIDATION_ERROR",
                details={"errors": error_details},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except HTTPException as e:
            # 修改時間：2026-01-28 - 記錄詳細的 HTTPException 信息
            detail = e.detail
            if isinstance(detail, dict):
                error_code = detail.get("error_code", "HTTP_ERROR")
                original_error = detail.get("original_error", "")
                error_type = detail.get("error_type", "")
                logger.error(
                    f"HTTPException: status={e.status_code}, error_code={error_code}, "
                    f"error_type={error_type}, original_error={original_error}",
                    exc_info=True,
                )
                return APIResponse.error(
                    message=detail.get("message", str(detail)),
                    error_code=error_code,
                    status_code=e.status_code,
                    details=detail,
                )
            else:
                logger.error(f"HTTPException: status={e.status_code}, detail={detail}", exc_info=True)
                return APIResponse.error(
                    message=str(detail),
                    error_code="HTTP_ERROR",
                    status_code=e.status_code,
                )
        except Exception as e:
            logger.exception(f"Unhandled error: {e}")
            return APIResponse.error(
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                details={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
