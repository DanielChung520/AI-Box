"""
代碼功能說明: 產品級 Chat API 的請求/回應資料模型（model_selector、attachments、routing/observability）
創建日期: 2025-12-13 17:28:02 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 14:30:00 (UTC+8)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Self

from pydantic import BaseModel, Field, model_validator


ModelSelectorMode = Literal["auto", "manual", "favorite"]


class ChatMessage(BaseModel):
    """產品級 Chat Message。"""

    role: Literal["system", "user", "assistant"] = Field(..., description="訊息角色")
    content: str = Field(..., description="訊息內容", min_length=1)


class ModelSelector(BaseModel):
    """模型選擇器（Auto/Manual/Favorite）。"""

    mode: ModelSelectorMode = Field(..., description="auto/manual/favorite")
    model_id: Optional[str] = Field(
        None,
        description="manual/favorite 時必填；例如 gpt-4-turbo、qwen3-coder:30b",
    )
    policy_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="（預留）對應系統參數 json 的覆蓋，例如 cost_threshold、low_latency",
    )

    @model_validator(mode="after")
    def validate_model_id(self) -> Self:
        if self.mode in ("manual", "favorite") and not self.model_id:
            raise ValueError("model_id is required when mode is manual or favorite")
        return self


class ChatAttachment(BaseModel):
    """MVP：先支援 file reference 的附件結構。"""

    file_id: str = Field(..., description="檔案 ID")
    file_name: str = Field(..., description="檔名")
    file_path: Optional[str] = Field(None, description="檔案路徑（可選）")
    task_id: Optional[str] = Field(None, description="關聯 task_id（可選）")


class RoutingInfo(BaseModel):
    """路由結果（最小集合）。"""

    provider: str = Field(
        ..., description="實際使用的 provider，例如 chatgpt/gemini/ollama"
    )
    model: Optional[str] = Field(None, description="實際使用的 model（若可得）")
    strategy: str = Field(
        ..., description="策略名稱，例如 manual/load_balancer_xxx/xxx"
    )
    latency_ms: Optional[float] = Field(
        None, ge=0.0, description="LLM 呼叫延遲（毫秒）"
    )
    failover_used: bool = Field(False, description="是否發生 failover")
    fallback_provider: Optional[str] = Field(
        None, description="failover 後使用的 provider（若可得）"
    )


class ObservabilityInfo(BaseModel):
    """觀測欄位（MVP 先放可選欄位，逐步補齊）。"""

    request_id: Optional[str] = Field(
        None, description="Request ID（若有 middleware 注入）"
    )
    session_id: Optional[str] = Field(None, description="Session ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    token_input: Optional[int] = Field(None, ge=0, description="輸入 token（若可得）")
    token_output: Optional[int] = Field(None, ge=0, description="輸出 token（若可得）")
    cost: Optional[float] = Field(None, ge=0.0, description="成本估算（若可得）")
    memory_hit_count: Optional[int] = Field(
        None, ge=0, description="記憶命中數（若可得）"
    )
    memory_sources: Optional[List[str]] = Field(
        None, description="記憶來源（例如 vector/graph）（若可得）"
    )
    retrieval_latency_ms: Optional[float] = Field(
        None, ge=0.0, description="檢索延遲（毫秒）（若可得）"
    )
    context_message_count: Optional[int] = Field(
        None, ge=0, description="短期上下文（windowed）消息數量（若可得）"
    )


class FileCreatedAction(BaseModel):
    """Chat 動作：已建立檔案（通常由 AI 輸入意圖觸發）。"""

    type: Literal["file_created"] = Field("file_created", description="動作類型")
    file_id: str = Field(..., description="新建檔案 ID")
    filename: str = Field(..., description="檔名（含副檔名）")
    task_id: Optional[str] = Field(None, description="Task ID（若可得）")
    folder_id: Optional[str] = Field(None, description="目標資料夾 ID（若可得）")
    folder_path: Optional[str] = Field(None, description="目標資料夾路徑（若可得）")


class FileEditedAction(BaseModel):
    """Chat 動作：已編輯檔案（創建編輯請求，等待 Apply）。"""

    type: Literal["file_edited"] = Field("file_edited", description="動作類型")
    file_id: str = Field(..., description="被編輯的檔案 ID")
    filename: str = Field(..., description="檔名")
    request_id: str = Field(..., description="編輯請求 ID（用於 Apply）")
    preview: Optional[Dict[str, Any]] = Field(None, description="預覽內容（可選）")
    task_id: Optional[str] = Field(None, description="Task ID")
    is_draft: bool = Field(False, description="是否為草稿檔（前端處理）")


class ChatRequest(BaseModel):
    """產品級 Chat Request。"""

    messages: List[ChatMessage] = Field(..., min_length=1, description="訊息列表")
    session_id: Optional[str] = Field(
        None, description="Session ID（前端可生成，後端可兜底）"
    )
    task_id: Optional[str] = Field(None, description="Task ID（用於任務維度追蹤）")
    model_selector: ModelSelector = Field(..., description="模型選擇器")
    attachments: Optional[List[ChatAttachment]] = Field(None, description="附件（MVP）")


class ChatResponse(BaseModel):
    """產品級 Chat Response。"""

    content: str = Field(..., description="模型回覆內容")
    session_id: str = Field(..., description="Session ID（回傳確定值）")
    task_id: Optional[str] = Field(None, description="Task ID（若有）")
    routing: RoutingInfo = Field(..., description="路由結果")
    observability: Optional[ObservabilityInfo] = Field(None, description="觀測欄位")
    actions: Optional[List[Dict[str, Any]]] = Field(
        None, description="（可選）動作列表，例如 file_created"
    )
