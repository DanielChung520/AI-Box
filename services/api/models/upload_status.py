# 代碼功能說明: 文件上傳狀態數據模型（WBS-3.7: 文件上傳流程重構）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""文件上傳狀態數據模型

定義文件上傳進度和處理狀態的數據結構。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProcessingStageStatus(BaseModel):
    """處理階段狀態"""

    status: str = Field(..., description="階段狀態 (pending, processing, completed, failed)")
    progress: int = Field(0, ge=0, le=100, description="進度百分比 (0-100)")
    message: Optional[str] = Field(None, description="狀態消息")
    started_at: Optional[datetime] = Field(None, description="開始時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    error: Optional[str] = Field(None, description="錯誤信息")


class UploadProgressModel(BaseModel):
    """文件上傳進度模型"""

    file_id: str = Field(..., description="文件ID")
    status: str = Field(..., description="上傳狀態 (uploading, completed, failed)")
    progress: int = Field(0, ge=0, le=100, description="進度百分比 (0-100)")
    message: Optional[str] = Field(None, description="狀態消息")
    file_size: Optional[int] = Field(None, description="文件大小（字節）")
    uploaded_bytes: Optional[int] = Field(None, description="已上傳字節數")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")


class ProcessingStatusModel(BaseModel):
    """文件處理狀態模型"""

    file_id: str = Field(..., description="文件ID")
    overall_status: str = Field(
        ..., description="總體狀態 (pending, processing, completed, failed)"
    )
    overall_progress: int = Field(0, ge=0, le=100, description="總體進度百分比 (0-100)")
    message: Optional[str] = Field(None, description="狀態消息")
    chunking: Optional[ProcessingStageStatus] = Field(None, description="分塊階段狀態")
    vectorization: Optional[ProcessingStageStatus] = Field(None, description="向量化階段狀態")
    storage: Optional[ProcessingStageStatus] = Field(None, description="存儲階段狀態")
    kg_extraction: Optional[ProcessingStageStatus] = Field(None, description="知識圖譜提取階段狀態")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")


class UploadProgressCreate(BaseModel):
    """創建上傳進度請求"""

    file_id: str
    status: str = "uploading"
    progress: int = 0
    message: Optional[str] = None
    file_size: Optional[int] = None
    uploaded_bytes: Optional[int] = None


class UploadProgressUpdate(BaseModel):
    """更新上傳進度請求"""

    status: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    uploaded_bytes: Optional[int] = None


class ProcessingStatusCreate(BaseModel):
    """創建處理狀態請求"""

    file_id: str
    overall_status: str = "pending"
    overall_progress: int = 0
    message: Optional[str] = None


class ProcessingStatusUpdate(BaseModel):
    """更新處理狀態請求"""

    overall_status: Optional[str] = None
    overall_progress: Optional[int] = None
    message: Optional[str] = None
    chunking: Optional[Dict[str, Any]] = None
    vectorization: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    kg_extraction: Optional[Dict[str, Any]] = None
