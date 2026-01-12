# 代碼功能說明: Capability Adapter 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 數據模型定義

適配器的輸入輸出模型。
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """驗證結果模型"""

    valid: bool = Field(..., description="驗證是否通過")
    reason: Optional[str] = Field(None, description="驗證失敗的原因（如果驗證失敗）")


class AdapterResult(BaseModel):
    """適配器結果模型"""

    success: bool = Field(..., description="是否成功")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    audit_log: Optional[Dict[str, Any]] = Field(None, description="審計日誌")
