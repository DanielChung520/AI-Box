"""
代碼功能說明: GenAI Chat 非同步請求（request_id）狀態模型（queued/running/succeeded/failed/aborted）
創建日期: 2025-12-13 22:26:20 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class GenAIRequestStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    aborted = "aborted"


class GenAIChatRequestRecord(BaseModel):
    request_id: str
    tenant_id: str = "default"
    user_id: str
    session_id: str
    task_id: Optional[str] = None

    status: GenAIRequestStatus = GenAIRequestStatus.queued

    created_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)
    updated_at_ms: float = Field(default_factory=lambda: time.time() * 1000.0)

    request: Dict[str, Any]

    response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class GenAIChatRequestCreateResponse(BaseModel):
    request_id: str
    status: GenAIRequestStatus
    session_id: str


class GenAIChatRequestStateResponse(BaseModel):
    request_id: str
    status: GenAIRequestStatus
    created_at_ms: float
    updated_at_ms: float

    tenant_id: str = "default"
    session_id: str
    task_id: Optional[str] = None

    response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
