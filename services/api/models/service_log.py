# 代碼功能說明: 服務日誌數據模型
# 創建日期: 2026-01-17 18:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:48 UTC+8

"""服務日誌數據模型"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ServiceLog(BaseModel):
    """服務日誌模型"""

    log_id: str = Field(..., description="日誌 ID")
    service_name: str = Field(..., description="服務名稱")
    log_level: str = Field(..., description="日誌級別（DEBUG/INFO/WARNING/ERROR/CRITICAL）")
    message: str = Field(..., description="日誌消息")
    timestamp: datetime = Field(..., description="日誌時間")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="額外元數據")

    class Config:
        """Pydantic 配置"""

        json_encoders = {datetime: lambda v: v.isoformat()}
        populate_by_name = True
