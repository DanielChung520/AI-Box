# 代碼功能說明: DT-Agent 數據模型（從 data_agent/models.py 移植 V5 相關 class）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""DT-Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class V5TaskData(BaseModel):
    """v5 任務數據"""

    nlq: str = Field(..., description="自然語言查詢")
    module: str = Field("tiptop_jp", description="模塊名稱")
    return_mode: str = Field("summary", description="返回模式: summary 或 list")


class V5ExecuteRequest(BaseModel):
    """v5 執行請求"""

    task_id: str = Field(..., description="任務 ID")
    task_type: str = Field(default="simple_query", description="任務類型")
    task_data: V5TaskData


class V5ErrorDetails(BaseModel):
    """v5 錯誤詳情"""

    original_query: Optional[str] = Field(None, description="原始查詢")
    ambiguity: Optional[str] = Field(None, description="模糊之處")
    sql: Optional[str] = Field(None, description="執行的 SQL")
    error_detail: Optional[str] = Field(None, description="錯誤詳情")


class V5ExecuteResponse(BaseModel):
    """v5 執行響應"""

    success: bool = Field(..., description="是否成功")
    sql: Optional[str] = Field(None, description="生成的 SQL")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="結果數據")
    row_count: Optional[int] = Field(None, description="返回筆數")
    columns: Optional[List[str]] = Field(None, description="欄位名稱")
    pagination: Optional[Dict[str, Any]] = Field(None, description="分頁資訊")
    execution_time_ms: Optional[int] = Field(None, description="執行時間（毫秒）")
    # 錯誤相關欄位
    error_type: Optional[str] = Field(None, description="錯誤類型: pre_execution / post_execution")
    error_code: Optional[str] = Field(None, description="錯誤碼")
    message: Optional[str] = Field(None, description="訊息")
    details: Optional[V5ErrorDetails] = Field(None, description="錯誤詳情")
    clarification_needed: Optional[List[str]] = Field(None, description="需要確認的事項")
    suggestion: Optional[str] = Field(None, description="建議")
    errors: List[str] = Field(default_factory=list, description="錯誤列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="觀測性元數據（model_used, matched_intent, intent_confidence, complexity, fallback_triggered）",
    )
