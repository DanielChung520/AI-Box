# 代碼功能說明: 模型使用日誌數據模型
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""模型使用日誌數據模型 - 定義模型使用追蹤相關的數據結構"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class ModelPurpose(str, Enum):
    """模型使用目的類型枚舉"""

    EMBEDDING = "embedding"  # 向量化
    NER = "ner"  # 命名實體識別
    RE = "re"  # 關係抽取
    RT = "rt"  # 關係類型分類
    GENERATION = "generation"  # 文本生成
    ANALYSIS = "analysis"  # 分析
    CHAT = "chat"  # 對話
    OTHER = "other"  # 其他


class ModelUsageBase(BaseModel):
    """模型使用日誌基礎模型"""

    model_name: str = Field(..., description="模型名稱")
    model_version: Optional[str] = Field(None, description="模型版本")
    user_id: str = Field(..., description="用戶ID")
    file_id: Optional[str] = Field(None, description="文件ID（如果適用）")
    task_id: Optional[str] = Field(None, description="任務ID（如果適用）")
    input_length: int = Field(..., description="輸入長度（字符數或token數）")
    output_length: int = Field(..., description="輸出長度（字符數或token數）")
    purpose: ModelPurpose = Field(..., description="使用目的")
    cost: Optional[float] = Field(None, description="使用成本（如果適用）")
    latency_ms: int = Field(..., description="延遲時間（毫秒）")
    success: bool = Field(True, description="是否成功")
    error_message: Optional[str] = Field(None, description="錯誤消息（如果失敗）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class ModelUsageCreate(ModelUsageBase):
    """創建模型使用日誌請求模型"""

    pass


class ModelUsage(ModelUsageBase):
    """模型使用日誌響應模型"""

    usage_id: str = Field(..., description="使用記錄ID")
    timestamp: datetime = Field(..., description="使用時間")
    created_at: Optional[datetime] = Field(None, description="創建時間")

    class Config:
        from_attributes = True


class ModelUsageStats(BaseModel):
    """模型使用統計模型"""

    model_name: str = Field(..., description="模型名稱")
    total_calls: int = Field(..., description="總調用次數")
    total_users: int = Field(..., description="總用戶數")
    total_input_length: int = Field(..., description="總輸入長度")
    total_output_length: int = Field(..., description="總輸出長度")
    total_latency_ms: int = Field(..., description="總延遲時間（毫秒）")
    avg_latency_ms: float = Field(..., description="平均延遲時間（毫秒）")
    success_rate: float = Field(..., description="成功率")
    total_cost: Optional[float] = Field(None, description="總成本")
    purposes: Dict[str, int] = Field(default_factory=dict, description="使用目的統計")


class ModelUsageQuery(BaseModel):
    """模型使用查詢參數模型"""

    model_name: Optional[str] = Field(None, description="模型名稱篩選")
    user_id: Optional[str] = Field(None, description="用戶ID篩選")
    file_id: Optional[str] = Field(None, description="文件ID篩選")
    task_id: Optional[str] = Field(None, description="任務ID篩選")
    purpose: Optional[ModelPurpose] = Field(None, description="使用目的篩選")
    start_time: Optional[datetime] = Field(None, description="開始時間")
    end_time: Optional[datetime] = Field(None, description="結束時間")
    limit: int = Field(100, ge=1, le=1000, description="返回數量限制")
    offset: int = Field(0, ge=0, description="偏移量")
