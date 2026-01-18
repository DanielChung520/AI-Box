# 代碼功能說明: 用戶會話數據模型
# 創建日期: 2026-01-17 18:07 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:07 UTC+8

"""用戶會話數據模型定義"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UserSessionModel(BaseModel):
    """用戶會話模型"""

    id: Optional[str] = Field(default=None, description="會話記錄 ID（ArangoDB _key）")
    session_id: str = Field(..., description="會話 ID")
    user_id: str = Field(..., description="用戶 ID")
    access_token: Optional[str] = Field(default=None, description="JWT Access Token（可選）")
    refresh_token: Optional[str] = Field(default=None, description="Refresh Token（可選）")
    ip_address: str = Field(..., description="登錄 IP 地址")
    user_agent: str = Field(..., description="User Agent 字符串")
    device_info: Dict[str, Any] = Field(default_factory=dict, description="設備信息（類型、OS、瀏覽器等）")
    login_at: datetime = Field(..., description="登錄時間")
    last_activity_at: datetime = Field(..., description="最後活動時間")
    expires_at: datetime = Field(..., description="會話過期時間")
    is_active: bool = Field(default=True, description="是否活躍")

    class Config:
        populate_by_name = True


class UserSessionCreate(BaseModel):
    """創建用戶會話請求模型"""

    session_id: str = Field(..., description="會話 ID")
    user_id: str = Field(..., description="用戶 ID")
    access_token: Optional[str] = Field(default=None, description="JWT Access Token（可選）")
    refresh_token: Optional[str] = Field(default=None, description="Refresh Token（可選）")
    ip_address: str = Field(..., description="登錄 IP 地址")
    user_agent: str = Field(..., description="User Agent 字符串")
    device_info: Dict[str, Any] = Field(default_factory=dict, description="設備信息")
    expires_at: datetime = Field(..., description="會話過期時間")


class UserSessionUpdate(BaseModel):
    """更新用戶會話請求模型"""

    last_activity_at: Optional[datetime] = Field(default=None, description="最後活動時間")
    is_active: Optional[bool] = Field(default=None, description="是否活躍")


class UserSessionResponse(BaseModel):
    """用戶會話響應模型"""

    id: str
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    device_info: Dict[str, Any]
    login_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_active: bool
