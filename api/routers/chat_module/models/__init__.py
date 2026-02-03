# 代碼功能說明: Chat Module 數據模型層統一導出
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""Chat Module 模型：request、response、internal（錯誤模型）。"""

from . import internal, request, response

# Re-export 常用模型，便於 router/handler 使用
from .internal import ChatErrorResponse, ErrorCode
from .request import (
    BatchChatRequest,
    ChatRequestEnhanced,
    ExperimentalFeatures,
    PriorityLevel,
)
from .response import (
    BatchChatResponse,
    BatchResultItem,
    BatchSummary,
    ChatResponseEnhanced,
    WarningInfo,
)

__all__ = [
    "request",
    "response",
    "internal",
    "PriorityLevel",
    "ExperimentalFeatures",
    "ChatRequestEnhanced",
    "WarningInfo",
    "ChatResponseEnhanced",
    "ErrorCode",
    "ChatErrorResponse",
    "BatchChatRequest",
    "BatchChatResponse",
    "BatchResultItem",
    "BatchSummary",
]
