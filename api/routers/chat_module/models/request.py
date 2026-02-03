# 代碼功能說明: Chat v2 可選擴展請求模型（PriorityLevel、ChatRequestEnhanced）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""v2 可選擴展：PriorityLevel、ExperimentalFeatures、ChatRequestEnhanced。"""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from services.api.models.chat import ChatRequest


# 階段三：批處理請求
BatchMode = Literal["parallel", "serial"]


class BatchChatRequest(BaseModel):
    """批處理請求體（POST /api/v2/chat/batch）。"""

    requests: List[ChatRequest] = Field(..., min_length=1, description="Chat 請求列表")
    mode: BatchMode = Field(default="parallel", description="parallel 或 serial")
    max_concurrent: int = Field(default=10, ge=1, le=100, description="並行時最大並發數")
    priority: str = Field(default="normal", description="優先級")


class PriorityLevel(str, Enum):
    """請求優先級。"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ExperimentalFeatures(BaseModel):
    """實驗性功能開關。"""

    enable_agent_v2: bool = False
    enable_streaming_v2: bool = False
    enable_cache_v2: bool = False


class ChatRequestEnhanced(ChatRequest):
    """增強的聊天請求模型（v2 可選擴展）：繼承 ChatRequest，增加 priority、timeout、cache_ttl、metadata、experimental。"""

    priority: PriorityLevel = Field(
        default=PriorityLevel.NORMAL,
        description="請求優先級",
    )
    timeout: int = Field(
        default=60,
        ge=10,
        le=600,
        description="超時時間（秒）",
    )
    cache_ttl: int = Field(
        default=300,
        ge=0,
        le=3600,
        description="緩存存活時間（秒），0 表示不緩存",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="自定義元數據",
    )
    experimental: ExperimentalFeatures = Field(
        default_factory=ExperimentalFeatures,
        description="實驗性功能開關",
    )
