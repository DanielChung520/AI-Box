# 代碼功能說明: Storage Manager Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Storage Manager Agent 數據模型定義"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class StorageType(str, Enum):
    """存儲類型"""

    MEMORY = "memory"
    DATABASE = "database"
    FILE = "file"
    VECTOR_DB = "vector_db"


class StorageStrategy(str, Enum):
    """存儲策略"""

    IMMEDIATE = "immediate"  # 立即存儲
    LAZY = "lazy"  # 延遲存儲
    CACHED = "cached"  # 緩存存儲
    DISTRIBUTED = "distributed"  # 分布式存儲


class StorageManagerRequest(BaseModel):
    """存储管理请求模型"""

    action: str = Field(
        ..., description="操作类型（store, retrieve, optimize, analyze, recommend）"
    )
    storage_type: Optional[StorageType] = Field(None, description="存储类型")
    data_key: Optional[str] = Field(None, description="数据键")
    data_value: Optional[Any] = Field(None, description="数据值")
    namespace: Optional[str] = Field(None, description="命名空间")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class StorageManagerResponse(BaseModel):
    """存储管理响应模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="执行的操作类型")
    stored: Optional[bool] = Field(None, description="是否成功存储")
    retrieved_data: Optional[Any] = Field(None, description="检索的数据")
    strategy: Optional[StorageStrategy] = Field(None, description="推荐的存储策略")
    optimization_result: Optional[Dict[str, Any]] = Field(None, description="优化结果")
    analysis: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
