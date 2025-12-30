# 代碼功能說明: 工具註冊清單數據模型
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊清單數據模型定義

定義工具註冊清單在 ArangoDB 中的存儲結構。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolParameterInfo(BaseModel):
    """工具參數信息"""

    type: str = Field(description="參數類型")
    required: bool = Field(description="是否必填")
    default: Optional[Any] = Field(default=None, description="默認值")
    description: str = Field(description="參數說明")


class ToolInfo(BaseModel):
    """工具信息"""

    name: str = Field(description="工具名稱（唯一標識）")
    version: str = Field(description="工具版本號")
    category: str = Field(description="工具類別（如「時間與日期」、「天氣」）")
    description: str = Field(description="工具簡短描述")
    purpose: str = Field(description="工具用途說明（詳細說明工具的用途）")
    use_cases: List[str] = Field(description="使用場景列表（工具適用的場景）")
    input_parameters: Dict[str, ToolParameterInfo] = Field(description="輸入參數說明（參數名稱、類型、必填、描述）")
    output_fields: Dict[str, str] = Field(description="輸出字段說明（字段名稱和描述）")
    example_scenarios: List[str] = Field(description="示例場景（具體的使用示例）")


class ToolRegistryModel(BaseModel):
    """工具註冊清單數據模型"""

    id: Optional[str] = Field(default=None, description="工具 ID（_key，即工具名稱）")
    name: str = Field(description="工具名稱（唯一標識）")
    version: str = Field(description="工具版本號")
    category: str = Field(description="工具類別")
    description: str = Field(description="工具簡短描述")
    purpose: str = Field(description="工具用途說明")
    use_cases: List[str] = Field(description="使用場景列表")
    input_parameters: Dict[str, Dict[str, Any]] = Field(description="輸入參數說明")
    output_fields: Dict[str, str] = Field(description="輸出字段說明")
    example_scenarios: List[str] = Field(description="示例場景")
    is_active: bool = Field(default=True, description="是否啟用")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    created_by: Optional[str] = Field(default=None, description="創建者")
    updated_by: Optional[str] = Field(default=None, description="更新者")


class ToolRegistryCreate(BaseModel):
    """工具註冊清單創建請求模型"""

    name: str = Field(description="工具名稱（唯一標識）")
    version: str = Field(description="工具版本號")
    category: str = Field(description="工具類別")
    description: str = Field(description="工具簡短描述")
    purpose: str = Field(description="工具用途說明")
    use_cases: List[str] = Field(description="使用場景列表")
    input_parameters: Dict[str, Dict[str, Any]] = Field(description="輸入參數說明")
    output_fields: Dict[str, str] = Field(description="輸出字段說明")
    example_scenarios: List[str] = Field(description="示例場景")


class ToolRegistryUpdate(BaseModel):
    """工具註冊清單更新請求模型"""

    version: Optional[str] = Field(default=None, description="工具版本號")
    category: Optional[str] = Field(default=None, description="工具類別")
    description: Optional[str] = Field(default=None, description="工具簡短描述")
    purpose: Optional[str] = Field(default=None, description="工具用途說明")
    use_cases: Optional[List[str]] = Field(default=None, description="使用場景列表")
    input_parameters: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None, description="輸入參數說明"
    )
    output_fields: Optional[Dict[str, str]] = Field(default=None, description="輸出字段說明")
    example_scenarios: Optional[List[str]] = Field(default=None, description="示例場景")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")


class ToolRegistryListResponse(BaseModel):
    """工具註冊清單列表響應模型"""

    tools: List[ToolRegistryModel] = Field(description="工具列表")
    total: int = Field(description="總數")
    page: Optional[int] = Field(default=None, description="當前頁碼")
    page_size: Optional[int] = Field(default=None, description="每頁數量")
