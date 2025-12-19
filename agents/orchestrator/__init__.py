# 代碼功能說明: Orchestrator 服務適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""Orchestrator 服務適配器 - 重新導出 agents.services.orchestrator 的模組"""

from agents.services.orchestrator.models import AgentRegistrationRequest  # noqa: F401

# 從 agents.services 模組重新導出
from agents.services.orchestrator.orchestrator import AgentOrchestrator  # noqa: F401

# AgentStatus 從 registry.models 導入（因為 orchestrator.models 中沒有 AgentStatus）
from agents.services.registry.models import AgentStatus  # noqa: F401

__all__ = ["AgentOrchestrator", "AgentRegistrationRequest", "AgentStatus"]
