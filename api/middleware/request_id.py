# 代碼功能說明: Request ID 中間件
# 創建日期: 2025-11-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Request ID 生成和傳遞中間件"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Request ID 中間件"""

    async def dispatch(self, request: Request, call_next):
        """處理請求並生成 Request ID"""
        # 檢查請求頭中是否已有 Request ID
        request_id = request.headers.get("X-Request-ID")

        # 如果沒有，生成新的 Request ID
        if not request_id:
            request_id = str(uuid.uuid4())

        # 將 Request ID 添加到請求狀態中
        request.state.request_id = request_id

        # 處理請求
        response = await call_next(request)

        # 將 Request ID 添加到響應頭
        response.headers["X-Request-ID"] = request_id

        return response
