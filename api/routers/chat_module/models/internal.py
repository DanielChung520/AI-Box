# 代碼功能說明: Chat 統一錯誤模型（ErrorCode、ChatErrorResponse）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""統一錯誤模型：ErrorCode、ChatErrorResponse。"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """標準化錯誤代碼。"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    CHAT_PIPELINE_FAILED = "CHAT_PIPELINE_FAILED"


class ChatErrorResponse(BaseModel):
    """統一的錯誤響應模型。"""

    success: bool = Field(default=False, description="固定為 false")
    error_code: ErrorCode = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤描述")
    details: Optional[Dict[str, Any]] = Field(None, description="詳情")
    request_id: Optional[str] = Field(None, description="Request ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat(),
        description="時間戳",
    )
