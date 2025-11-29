# 代碼功能說明: 請求日誌中間件
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""請求日誌記錄中間件"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """請求日誌記錄中間件"""

    async def dispatch(self, request: Request, call_next):
        """處理請求並記錄日誌"""
        start_time = time.time()

        # 記錄請求信息
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        # 處理請求
        response = await call_next(request)

        # 計算處理時間
        process_time = time.time() - start_time

        # 記錄響應信息
        logger.info(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        # 添加處理時間到響應頭
        response.headers["X-Process-Time"] = str(process_time)

        return response
