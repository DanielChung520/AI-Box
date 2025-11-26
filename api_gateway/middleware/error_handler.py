# 代碼功能說明: 錯誤處理中間件
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""全局錯誤處理中間件"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from api_gateway.core.response import APIResponse

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局錯誤處理中間件"""

    async def dispatch(self, request: Request, call_next):
        """處理請求並捕獲異常"""
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            logger.error(f"Validation error: {e}")
            return APIResponse.error(
                message="Request validation failed",
                error_code="VALIDATION_ERROR",
                details={"errors": e.errors()},
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
