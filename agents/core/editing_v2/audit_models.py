# 代碼功能說明: 審計事件模型
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""審計事件模型

定義審計事件的數據模型。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """審計事件類型"""

    INTENT_RECEIVED = "intent_received"  # Intent 接收
    INTENT_VALIDATED = "intent_validated"  # Intent 驗證
    TARGET_LOCATED = "target_located"  # 目標定位
    CONTEXT_ASSEMBLED = "context_assembled"  # 上下文裝配
    CONTENT_GENERATED = "content_generated"  # 內容生成
    PATCH_GENERATED = "patch_generated"  # Patch 生成
    VALIDATION_PASSED = "validation_passed"  # 驗證通過
    VALIDATION_FAILED = "validation_failed"  # 驗證失敗
    PATCH_APPLIED = "patch_applied"  # Patch 應用


class AuditEvent(BaseModel):
    """審計事件

    表示一個審計事件。
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    intent_id: Optional[str] = None
    patch_id: Optional[str] = None
    doc_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration: Optional[float] = None  # 持續時間（秒）
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    class Config:
        """Pydantic 配置"""

        use_enum_values = True


class PatchStorage(BaseModel):
    """Patch 存儲

    表示一個不可變的 Patch 存儲記錄。
    """

    patch_id: str
    intent_id: str
    doc_id: str
    block_patch: Dict[str, Any]
    text_patch: str
    content_hash: str  # SHA-256 哈希
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "md-editor-v2.0"


class IntentStorage(BaseModel):
    """Intent 存儲

    表示一個不可變的 Intent 存儲記錄。
    """

    intent_id: str
    doc_id: str
    intent_data: Dict[str, Any]
    content_hash: str  # SHA-256 哈希
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "md-editor-v2.0"
