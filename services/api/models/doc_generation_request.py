"""
代碼功能說明: 文件生成（Doc Generation）request_id 狀態模型（preview/apply）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:27:19 (UTC+8)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DocGenStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"  # preview 生成成功
    failed = "failed"
    aborted = "aborted"
    applied = "applied"  # 已建立檔案


DocFormat = Literal["md", "txt", "json"]


class DocGenCreateRequest(BaseModel):
    task_id: str = Field(..., description="目標任務工作區 task_id")
    filename: str = Field(..., description="檔名（建議含副檔名 .md/.txt/.json）")
    doc_format: DocFormat = Field(..., description="md/txt/json")
    instruction: str = Field(..., description="生成指令")


class DocGenPreview(BaseModel):
    content: str = Field(..., description="生成內容（preview）")


class DocGenApplyResult(BaseModel):
    file_id: str


class DocGenRequestRecord(BaseModel):
    request_id: str
    tenant_id: str = "default"
    user_id: str

    task_id: str
    filename: str
    doc_format: DocFormat
    instruction: str

    status: DocGenStatus = DocGenStatus.queued

    created_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)
    updated_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)

    preview: Optional[DocGenPreview] = None
    apply_result: Optional[DocGenApplyResult] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None


class DocGenCreateResponse(BaseModel):
    request_id: str
    status: DocGenStatus


class DocGenStateResponse(BaseModel):
    request_id: str
    status: DocGenStatus
    created_at_ms: float
    updated_at_ms: float

    task_id: str
    filename: str
    doc_format: DocFormat

    preview: Optional[DocGenPreview] = None
    apply_result: Optional[DocGenApplyResult] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None
