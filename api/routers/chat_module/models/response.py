# 代碼功能說明: Chat v2 可選擴展響應模型（WarningInfo、ChatResponseEnhanced）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""v2 可選擴展：WarningInfo、ChatResponseEnhanced。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.api.models.chat import (
    ObservabilityInfo,
    RoutingInfo,
)


# 階段三：批處理響應
class BatchResultItem(BaseModel):
    """單條批處理結果。"""

    index: int = Field(..., description="請求索引")
    success: bool = Field(..., description="是否成功")
    request_id: Optional[str] = Field(None, description="request_id（若有）")
    data: Optional[Dict[str, Any]] = Field(None, description="ChatResponse 或錯誤詳情")
    error: Optional[str] = Field(None, description="錯誤消息")


class BatchSummary(BaseModel):
    """批處理匯總。"""

    total: int = Field(..., description="總數")
    succeeded: int = Field(..., description="成功數")
    failed: int = Field(..., description="失敗數")
    total_time_ms: float = Field(..., description="總耗時毫秒")


class BatchChatResponse(BaseModel):
    """批處理響應（POST /api/v2/chat/batch）。"""

    batch_id: str = Field(..., description="批次 ID")
    results: List[BatchResultItem] = Field(..., description="結果列表")
    summary: BatchSummary = Field(..., description="匯總")

# 動作類型可為 dict（規格中 actions 為 List[Dict[str, Any]]）
ActionDict = Dict[str, Any]


class WarningInfo(BaseModel):
    """警告信息。"""

    code: str = Field(..., description="警告代碼")
    message: str = Field(..., description="警告消息")
    level: str = Field(default="info", description="info/warning/critical")


class ChatResponseEnhanced(BaseModel):
    """增強的聊天響應模型（v2 可選擴展）：含 cache_hit、priority、warnings。"""

    content: str = Field(..., description="模型回覆內容")
    request_id: str = Field(..., description="Request ID")
    session_id: str = Field(..., description="Session ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    routing: RoutingInfo = Field(..., description="路由結果")
    observability: Optional[ObservabilityInfo] = Field(None, description="觀測欄位")
    actions: List[ActionDict] = Field(default_factory=list, description="動作列表")
    cache_hit: bool = Field(default=False, description="是否命中緩存")
    priority: str = Field(default="normal", description="實際使用的優先級")
    warnings: List[WarningInfo] = Field(default_factory=list, description="警告列表")
