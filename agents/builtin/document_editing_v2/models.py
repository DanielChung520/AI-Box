# 代碼功能說明: Document Editing Agent v2.0 數據模型
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Document Editing Agent v2.0 數據模型

定義 DocumentContext、EditIntent、PatchResponse 等核心數據模型。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentContext(BaseModel):
    """文檔上下文

    包含文檔 ID、版本 ID、文件路徑、任務 ID、用戶 ID、租戶 ID 等信息。
    """

    doc_id: str = Field(..., description="文檔 ID")
    version_id: Optional[str] = Field(None, description="版本 ID")
    file_path: str = Field(..., description="文件路徑")
    task_id: str = Field(..., description="任務 ID")
    user_id: str = Field(..., description="用戶 ID")
    tenant_id: Optional[str] = Field(None, description="租戶 ID")


class TargetSelector(BaseModel):
    """目標選擇器

    用於定位需要編輯的目標位置。
    """

    type: str = Field(..., description="選擇器類型：heading|anchor|block")
    selector: Dict[str, Any] = Field(..., description="選擇器規格")


class Action(BaseModel):
    """編輯操作

    定義編輯操作的模式、內容和位置。
    """

    mode: str = Field(..., description="操作模式：insert|update|delete|move|replace")
    content: Optional[str] = Field(None, description="Markdown 內容")
    position: Optional[str] = Field(None, description="位置：before|after|inside|start|end")


class Constraints(BaseModel):
    """約束條件

    定義編輯操作的約束條件。
    """

    max_tokens: Optional[int] = Field(None, description="最大 Token 數")
    style_guide: Optional[str] = Field(None, description="樣式指南")
    no_external_reference: Optional[bool] = Field(None, description="禁止外部參照")


class EditIntent(BaseModel):
    """編輯意圖 DSL

    定義編輯操作的結構化意圖。
    """

    intent_id: str = Field(..., description="意圖 ID")
    intent_type: str = Field(..., description="意圖類型：insert|update|delete|move|replace")
    target_selector: TargetSelector = Field(..., description="目標選擇器")
    action: Action = Field(..., description="編輯操作")
    constraints: Optional[Constraints] = Field(None, description="約束條件")


class BlockPatchOperation(BaseModel):
    """Block Patch 操作

    定義單個 Block Patch 操作。
    """

    op: str = Field(..., description="操作類型：insert|update|delete")
    block_id: Optional[str] = Field(None, description="Block ID")
    content: Optional[str] = Field(None, description="內容")
    position: Optional[str] = Field(None, description="位置")


class BlockPatch(BaseModel):
    """Block Patch

    定義 Block Patch 數據結構。
    """

    operations: List[BlockPatchOperation] = Field(..., description="操作列表")


class PatchResponse(BaseModel):
    """Patch 響應

    定義 Patch 生成結果。
    """

    patch_id: str = Field(..., description="Patch ID")
    intent_id: str = Field(..., description="Intent ID")
    block_patch: Optional[BlockPatch] = Field(None, description="Block Patch")
    text_patch: Optional[str] = Field(None, description="Text Patch (unified diff)")
    preview: Optional[str] = Field(None, description="預覽內容")
    audit_info: Dict[str, Any] = Field(..., description="審計信息")
