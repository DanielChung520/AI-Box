# 代碼功能說明: 模組化文檔數據模型
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""模組化文檔數據模型 - 定義主文檔和分文檔的數據結構"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SubDocumentRef(BaseModel):
    """分文檔引用模型"""

    sub_file_id: str = Field(..., description="分文檔文件 ID")
    filename: str = Field(..., description="分文檔文件名")
    section_title: str = Field(..., description="章節標題（從 H1-H3 標題提取）")
    order: int = Field(..., description="順序（用於排序）")
    transclusion_syntax: str = Field(..., description="Transclusion 語法（例如: ![[filename.md]]）")
    header_path: Optional[str] = Field(
        None, description="標題路徑（Breadcrumbs，例如: # 系統架構 > ## 編輯器選型）"
    )

    class Config:
        from_attributes = True


class ModularDocumentBase(BaseModel):
    """模組化文檔基礎模型"""

    master_file_id: str = Field(..., description="主文檔文件 ID")
    title: str = Field(..., description="主文檔標題")
    task_id: str = Field(..., description="任務 ID（文件所屬任務工作區）")
    description: Optional[str] = Field(None, description="文檔描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定義元數據")


class ModularDocumentCreate(ModularDocumentBase):
    """創建模組化文檔請求模型"""

    doc_id: Optional[str] = Field(None, description="模組化文檔 ID（可選，系統自動生成）")
    sub_documents: List[SubDocumentRef] = Field(default_factory=list, description="分文檔引用列表")


class ModularDocumentUpdate(BaseModel):
    """更新模組化文檔請求模型"""

    title: Optional[str] = Field(None, description="主文檔標題")
    description: Optional[str] = Field(None, description="文檔描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定義元數據")
    sub_documents: Optional[List[SubDocumentRef]] = Field(None, description="分文檔引用列表")


class ModularDocument(ModularDocumentBase):
    """模組化文檔響應模型"""

    doc_id: str = Field(..., description="模組化文檔 ID")
    sub_documents: List[SubDocumentRef] = Field(default_factory=list, description="分文檔引用列表")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")

    class Config:
        from_attributes = True


class ModularDocumentAddSubDocumentRequest(BaseModel):
    """添加分文檔請求模型"""

    sub_file_id: str = Field(..., description="分文檔文件 ID")
    filename: str = Field(..., description="分文檔文件名")
    section_title: str = Field(..., description="章節標題")
    order: Optional[int] = Field(None, description="順序（可選，如果不提供則添加到末尾）")
    header_path: Optional[str] = Field(None, description="標題路徑（Breadcrumbs）")


class ModularDocumentRemoveSubDocumentRequest(BaseModel):
    """移除分文檔請求模型"""

    sub_file_id: str = Field(..., description="要移除的分文檔文件 ID")
