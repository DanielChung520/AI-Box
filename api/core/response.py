# 代碼功能說明: 統一響應格式
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24 22:54 UTC+8

"""統一響應格式處理"""

from typing import Any, Dict, Optional

from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


class APIResponse:
    """統一 API 響應格式"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
    ) -> JSONResponse:
        """
        成功響應

        Args:
            data: 響應數據
            message: 響應消息
            status_code: HTTP 狀態碼

        Returns:
            JSONResponse 對象
        """
        response_data = {
            "success": True,
            "message": message,
            "data": data,
        }
        return JSONResponse(content=jsonable_encoder(response_data), status_code=status_code)

    @staticmethod
    def error(
        message: str = "Error",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> JSONResponse:
        """
        錯誤響應

        Args:
            message: 錯誤消息
            error_code: 錯誤代碼
            details: 錯誤詳情
            status_code: HTTP 狀態碼

        Returns:
            JSONResponse 對象
        """
        response_data = {
            "success": False,
            "message": message,
            "error_code": error_code,
            "details": details,
        }
        return JSONResponse(content=jsonable_encoder(response_data), status_code=status_code)
