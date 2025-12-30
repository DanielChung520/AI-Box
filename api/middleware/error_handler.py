# 代碼功能說明: 錯誤處理中間件
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

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
            logger.error(f"HTTP error: {e.detail}")
            return APIResponse.error(
                message=e.detail,
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
