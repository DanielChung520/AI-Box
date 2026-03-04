# 代碼功能說明: 外部服務客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""外部服務客戶端模組"""

from api.routers.chat_module.services.external_client.da_agent_client import (
    DAAgentClient,
    get_da_agent_client,
)
from api.routers.chat_module.services.external_client.document_agent_client import (
    DocumentAgentClient,
    get_document_agent_client,
)
from api.routers.chat_module.services.external_client.ka_agent_client import (
    KAAgentClient,
    get_ka_agent_client,
)
from api.routers.chat_module.services.external_client.mm_agent_client import (
    MMAgentClient,
    get_mm_agent_client,
)
from api.routers.chat_module.services.external_client.moe_client import (
    MoEClient,
    get_moe_client,
)
from api.routers.chat_module.services.external_client.task_orchestrator_client import (
    TaskOrchestratorClient,
    get_task_orchestrator_client,
)

__all__ = [
    # KA-Agent
    "KAAgentClient",
    "get_ka_agent_client",
    # Task Orchestrator
    "TaskOrchestratorClient",
    "get_task_orchestrator_client",
    # MM-Agent
    "MMAgentClient",
    "get_mm_agent_client",
    # DA-Agent
    "DAAgentClient",
    "get_da_agent_client",
    # Document Agent
    "DocumentAgentClient",
    "get_document_agent_client",
    # MoE
    "MoEClient",
    "get_moe_client",
]
