# 代碼功能說明: 上下文管理模組適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""上下文管理模組適配器 - 重新導出 genai.workflows.context 的模組"""

# 從 genai 模組重新導出
from genai.workflows.context.history import ConversationHistory  # noqa: F401
from genai.workflows.context.manager import ContextManager  # noqa: F401
from genai.workflows.context.models import (  # noqa: F401
    ContextConfig,
    ContextMessage,
    ContextSession,
)
from genai.workflows.context.persistence import ContextPersistence  # noqa: F401
from genai.workflows.context.recorder import ContextRecorder  # noqa: F401
from genai.workflows.context.storage import (  # noqa: F401
    MemoryStorageBackend,
    RedisStorageBackend,
    StorageBackend,
)
from genai.workflows.context.window import ContextWindow, TruncationStrategy  # noqa: F401

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
