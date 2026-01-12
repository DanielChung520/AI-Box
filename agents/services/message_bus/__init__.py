# 代碼功能說明: Message Bus 模組初始化
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Message Bus - 異步訊息總線

實現 GRO 規範的 Task Contract 模式，支持 fan-out 和 fan-in。
"""

from agents.services.message_bus.message_bus import MessageBus
from agents.services.message_bus.models import MessageType, TaskDispatch, TaskResult

__all__ = [
    "MessageBus",
    "MessageType",
    "TaskDispatch",
    "TaskResult",
]
