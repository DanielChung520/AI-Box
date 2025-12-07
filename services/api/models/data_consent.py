# 代碼功能說明: 數據使用同意數據模型
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""數據使用同意數據模型定義。"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ConsentType(str, Enum):
    """同意類型枚舉"""

    FILE_UPLOAD = "file_upload"  # 文件上傳同意
    AI_PROCESSING = "ai_processing"  # AI處理同意
    DATA_SHARING = "data_sharing"  # 數據共享同意
    TRAINING = "training"  # 訓練數據使用同意


class DataConsent(BaseModel):
    """數據使用同意模型"""

    user_id: str = Field(..., description="用戶ID")
    consent_type: ConsentType = Field(..., description="同意類型")
    purpose: str = Field(..., description="使用目的描述")
    granted: bool = Field(..., description="是否同意")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="同意時間")
    expires_at: Optional[datetime] = Field(None, description="過期時間（可選）")

    class Config:
        use_enum_values = True


class DataConsentCreate(BaseModel):
    """創建數據使用同意的請求模型"""

    consent_type: ConsentType
    purpose: str
    granted: bool
    expires_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class DataConsentResponse(BaseModel):
    """數據使用同意響應模型"""

    user_id: str
    consent_type: ConsentType
    purpose: str
    granted: bool
    timestamp: datetime
    expires_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
