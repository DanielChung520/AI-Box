# 代碼功能說明: Agent Registry 服務適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""Agent Registry 服務適配器 - 重新導出 agents.services.registry 的模組"""

# 從 agents.services 模組重新導出
from agents.services.registry import (  # noqa: F401
    AgentMetadata,
    AgentPermission,
    AgentRegistry,
    AgentRegistryInfo,
)

__all__ = [
    "AgentRegistry",
    "AgentRegistryInfo",
    "AgentPermission",
    "AgentMetadata",
]
