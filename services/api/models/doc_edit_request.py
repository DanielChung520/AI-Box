"""
代碼功能說明: 文件編輯（Doc Edit）request_id 狀態模型（preview/apply/rollback）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:27:19 (UTC+8)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class DocEditStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"  # preview 產生成功
    failed = "failed"
    aborted = "aborted"
    applied = "applied"  # 已套用寫回


DocFormat = Literal["md", "txt", "json"]
PatchKind = Literal["unified_diff", "json_patch"]


class DocEditCreateRequest(BaseModel):
    file_id: str = Field(..., description="目標文件 ID")
    instruction: str = Field(..., description="編輯指令")
    base_version: Optional[int] = Field(
        default=None,
        description="基底版本（避免競態）。若不提供，後端以當前版本作為 base。",
    )


class DocEditPreview(BaseModel):
    patch_kind: PatchKind
    patch: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="unified diff 字串 或 json patch ops"
    )
    summary: str = Field(default="", description="變更摘要")


class DocEditApplyResult(BaseModel):
    new_version: int


class DocEditRequestRecord(BaseModel):
    request_id: str
    tenant_id: str = "default"
    user_id: str

    file_id: str
    task_id: Optional[str] = None
    doc_format: DocFormat

    instruction: str
    base_version: int

    status: DocEditStatus = DocEditStatus.queued

    created_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)
    updated_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)

    preview: Optional[DocEditPreview] = None
    apply_result: Optional[DocEditApplyResult] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None


class DocEditCreateResponse(BaseModel):
    request_id: str
    status: DocEditStatus


class DocEditStateResponse(BaseModel):
    request_id: str
    status: DocEditStatus
    created_at_ms: float
    updated_at_ms: float

    file_id: str
    base_version: int

    preview: Optional[DocEditPreview] = None
    apply_result: Optional[DocEditApplyResult] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None
