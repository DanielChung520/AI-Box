# 代碼功能說明: Execution Agent 適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""Execution Agent 適配器 - 重新導出 agents.core.execution 的模組"""

# 從 agents.core 模組重新導出
from agents.core.execution import (  # noqa: F401
    ExecutionAgent,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)

__all__ = [
    "ExecutionAgent",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
]
