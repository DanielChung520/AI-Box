# 代碼功能說明: File Server 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""File Server 數據模型定義"""

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class FileType(str, Enum):
    """文件類型"""

    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    SVG = "svg"
    JSON = "json"
    CSV = "csv"
    OTHER = "other"


class AgentFileInfo(BaseModel):
    """Agent 文件信息模型"""

    file_id: str = Field(..., description="文件 ID")
    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="任務 ID")
    file_type: FileType = Field(..., description="文件類型")
    filename: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路徑")
    file_url: str = Field(..., description="文件訪問 URL")
    file_size: int = Field(..., description="文件大小（字節）")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
