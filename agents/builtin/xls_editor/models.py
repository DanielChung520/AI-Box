# 代碼功能說明: Excel 編輯器 Agent 數據模型
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel 編輯器 Agent 數據模型

定義 Excel 特定的數據模型，包括 Excel Target Selector、Structured Patch 等。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExcelTargetSelector(BaseModel):
    """Excel 目標選擇器

    用於定位需要編輯的 Excel 目標位置。
    """

    type: str = Field(..., description="選擇器類型：worksheet|range|cell|row|column")
    selector: Dict[str, Any] = Field(..., description="選擇器規格")


class ExcelAction(BaseModel):
    """Excel 編輯操作

    定義 Excel 編輯操作的模式、內容和位置。
    """

    mode: str = Field(
        ...,
        description="操作模式：insert|update|delete|move|replace|insert_row|delete_row|insert_column|delete_column",
    )
    content: Optional[Dict[str, Any]] = Field(
        None,
        description="Excel 內容（values, formulas, styles, format）",
    )
    position: Optional[str] = Field(None, description="位置：before|after|inside|start|end")


class ExcelConstraints(BaseModel):
    """Excel 約束條件

    定義 Excel 編輯操作的約束條件。
    """

    max_cells: Optional[int] = Field(None, description="最大單元格數")
    preserve_formulas: Optional[bool] = Field(None, description="保留公式")
    preserve_styles: Optional[bool] = Field(None, description="保留樣式")
    no_external_reference: Optional[bool] = Field(None, description="禁止外部參照")


class ExcelEditIntent(BaseModel):
    """Excel 編輯意圖 DSL

    定義 Excel 編輯操作的結構化意圖。
    """

    intent_id: str = Field(..., description="意圖 ID")
    intent_type: str = Field(
        ...,
        description="意圖類型：insert|update|delete|move|replace|insert_row|delete_row|insert_column|delete_column",
    )
    target_selector: ExcelTargetSelector = Field(..., description="目標選擇器")
    action: ExcelAction = Field(..., description="編輯操作")
    constraints: Optional[ExcelConstraints] = Field(None, description="約束條件")


class StructuredPatchOperation(BaseModel):
    """Structured Patch 操作

    定義單個 Structured Patch 操作。
    """

    op: str = Field(
        ...,
        description="操作類型：update|insert|delete|insert_row|delete_row|insert_column|delete_column",
    )
    target: str = Field(..., description="目標位置（如 Sheet1!B5 或 Sheet1!A1:C10）")
    old_value: Optional[Any] = Field(None, description="舊值")
    new_value: Optional[Any] = Field(None, description="新值")


class StructuredPatch(BaseModel):
    """Structured Patch

    定義 Structured Patch 數據結構。
    """

    operations: List[StructuredPatchOperation] = Field(..., description="操作列表")


class ExcelPatchResponse(BaseModel):
    """Excel Patch 響應

    定義 Excel Patch 生成結果。
    """

    patch_id: str = Field(..., description="Patch ID")
    intent_id: str = Field(..., description="Intent ID")
    structured_patch: Optional[StructuredPatch] = Field(None, description="Structured Patch")
    preview: Optional[Dict[str, Any]] = Field(None, description="預覽數據")
    audit_info: Dict[str, Any] = Field(..., description="審計信息")
