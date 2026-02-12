# 代碼功能說明: 庫管員Agent數據模型
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""庫管員Agent數據模型定義"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SemanticAnalysisResult(BaseModel):
    """語義分析結果"""

    intent: Optional[str] = Field(None, description="識別的意圖")
    confidence: float = Field(0.0, description="置信度（0-1）")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="提取的參數")
    original_instruction: str = Field(..., description="原始指令")
    clarification_needed: bool = Field(False, description="是否需要澄清")
    clarification_questions: List[str] = Field(default_factory=list, description="澄清問題列表")


class Responsibility(BaseModel):
    """職責定義"""

    type: str = Field(..., description="職責類型")
    description: str = Field(..., description="職責描述")
    steps: List[str] = Field(default_factory=list, description="執行步驟")
    required_data: List[str] = Field(default_factory=list, description="必需的數據")
    optional_data: List[str] = Field(default_factory=list, description="可選的數據")
    clarification_questions: List[str] = Field(
        default_factory=list, description="澄清問題（如果需要）"
    )


class ConversationContext(BaseModel):
    """對話上下文"""

    session_id: str = Field(..., description="會話ID")
    user_id: Optional[str] = Field(None, description="用戶ID")
    tenant_id: Optional[str] = Field(None, description="租戶ID")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="歷史對話記錄")
    current_query: Optional[Dict[str, Any]] = Field(None, description="當前查詢信息")
    last_result: Optional[Dict[str, Any]] = Field(None, description="上次查詢結果")
    entities: Dict[str, Any] = Field(
        default_factory=dict, description="實體映射，如 {'last_part_number': 'ABC-123'}"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")


class StockStatus(BaseModel):
    """庫存狀態"""

    status: str = Field(..., description="庫存狀態（normal/low/shortage）")
    current_stock: int = Field(..., description="當前庫存")
    safety_stock: int = Field(..., description="安全庫存")
    shortage_quantity: int = Field(0, description="缺料數量")
    is_shortage: bool = Field(False, description="是否缺料")


class ValidationResult(BaseModel):
    """驗證結果"""

    valid: bool = Field(..., description="是否有效")
    issues: List[str] = Field(default_factory=list, description="問題列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class WarehouseAgentResponse(BaseModel):
    """庫管員Agent響應模型"""

    success: bool = Field(..., description="是否成功")
    task_type: str = Field(..., description="任務類型")
    response: Optional[str] = Field(None, description="格式化回覆（用戶友善的消息）")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果（原始數據）")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元數據")
    semantic_analysis: Optional[Dict[str, Any]] = Field(default=None, description="語義分析結果")
    responsibility: Optional[str] = Field(default=None, description="履行的職責")
    data_queries: List[Dict[str, Any]] = Field(default_factory=list, description="數據查詢記錄")
    validation: Optional[Dict[str, Any]] = Field(default=None, description="數據驗證結果")
    anomalies: List[str] = Field(default_factory=list, description="異常情況列表")


class PurchaseOrder(BaseModel):
    """採購單模型"""

    purchase_order_id: str = Field(..., description="採購單ID")
    part_number: str = Field(..., description="料號")
    part_name: Optional[str] = Field(None, description="物料名稱")
    quantity: int = Field(..., description="採購數量")
    supplier: Optional[str] = Field(None, description="供應商")
    unit_price: Optional[float] = Field(None, description="單價")
    total_amount: Optional[float] = Field(None, description="總金額")
    status: str = Field("虛擬生成", description="狀態")
    created_at: str = Field(..., description="創建時間（ISO格式）")
    created_by: str = Field("mm_agent", description="創建者")
    note: Optional[str] = Field(None, description="備註")
