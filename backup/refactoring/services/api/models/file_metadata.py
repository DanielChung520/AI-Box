# 代碼功能說明: 文件元數據模型
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件元數據模型 - 定義 Pydantic Model"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FileMetadataBase(BaseModel):
    """文件元數據基礎模型"""

    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件類型（MIME 類型）")
    file_size: int = Field(..., description="文件大小（字節）")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    description: Optional[str] = Field(None, description="文件描述")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="自定義元數據")


class FileMetadataCreate(FileMetadataBase):
    """創建文件元數據請求模型"""

    file_id: str = Field(..., description="文件 ID")


class FileMetadataUpdate(BaseModel):
    """更新文件元數據請求模型"""

    tags: Optional[List[str]] = Field(None, description="標籤列表")
    description: Optional[str] = Field(None, description="文件描述")
    custom_metadata: Optional[Dict[str, Any]] = Field(None, description="自定義元數據")


class FileMetadata(FileMetadataBase):
    """文件元數據響應模型"""

    file_id: str = Field(..., description="文件 ID")
    upload_time: datetime = Field(..., description="上傳時間")
    created_at: Optional[datetime] = Field(None, description="創建時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    class Config:
        from_attributes = True
