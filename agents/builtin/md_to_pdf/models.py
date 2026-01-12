# 代碼功能說明: Markdown 轉 PDF Agent 數據模型
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Markdown 轉 PDF Agent 數據模型

定義轉換配置和響應模型。
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConversionConfig(BaseModel):
    """轉換配置

    定義 Markdown 到 PDF 的轉換配置。
    """

    conversion_id: str = Field(..., description="轉換 ID")
    output_file_name: str = Field(..., description="輸出文件名")
    template: Optional[str] = Field("default", description="模板：default|academic|business|custom")
    options: Optional[Dict[str, Any]] = Field(
        None,
        description="轉換選項（page_size, margin, font, header, footer, toc 等）",
    )


class ConversionResponse(BaseModel):
    """轉換響應

    定義轉換結果。
    """

    conversion_id: str = Field(..., description="轉換 ID")
    source_doc_id: str = Field(..., description="源文檔 ID")
    output_doc_id: Optional[str] = Field(None, description="輸出文檔 ID")
    output_file_path: Optional[str] = Field(None, description="輸出文件路徑")
    status: str = Field(..., description="狀態：success|failed")
    message: Optional[str] = Field(None, description="消息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")
    audit_info: Dict[str, Any] = Field(..., description="審計信息")
