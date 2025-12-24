# 代碼功能說明: 上下文管理模組
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""上下文管理模組，提供上下文記錄、對話歷史管理和上下文窗口管理功能。"""

from __future__ import annotations

from genai.workflows.context.history import ConversationHistory
from genai.workflows.context.manager import ContextManager
from genai.workflows.context.models import ContextConfig, ContextMessage, ContextSession
from genai.workflows.context.persistence import ContextPersistence
from genai.workflows.context.recorder import ContextRecorder
from genai.workflows.context.storage import (
    MemoryStorageBackend,
    RedisStorageBackend,
    StorageBackend,
)
from genai.workflows.context.window import ContextWindow, TruncationStrategy

__all__ = [
    "ContextManager",
    "ContextRecorder",
    "ContextMessage",
    "ContextSession",
    "ContextConfig",
    "ConversationHistory",
    "StorageBackend",
    "RedisStorageBackend",
    "MemoryStorageBackend",
    "ContextWindow",
    "TruncationStrategy",
    "ContextPersistence",
]
