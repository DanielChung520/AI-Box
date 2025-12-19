# 代碼功能說明: Agent Registry Adapter 適配器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry Adapter - 適配新舊 Agent 模型，保持向後兼容"""

from agents.services.orchestrator.models import AgentInfo as LegacyAgentInfo

# LegacyAgentStatus 從 registry.models 導入（因為 orchestrator.models 中沒有 AgentStatus）
from agents.services.registry.models import AgentRegistryInfo
from agents.services.registry.models import AgentStatus
from agents.services.registry.models import AgentStatus as LegacyAgentStatus

logger = None
try:
    import logging

    logger = logging.getLogger(__name__)
except Exception:
    pass


def convert_to_legacy_agent_info(registry_info: AgentRegistryInfo) -> LegacyAgentInfo:
    """
    將新的 AgentRegistryInfo 轉換為舊的 AgentInfo（向後兼容）

    Args:
        registry_info: 新的 Agent 註冊信息

    Returns:
        舊的 AgentInfo 模型
    """
    # 狀態映射
    status_mapping = {
        AgentStatus.ACTIVE: LegacyAgentStatus.IDLE,  # 活躍 -> 空閒（用於任務分配）
        AgentStatus.INACTIVE: LegacyAgentStatus.OFFLINE,
        AgentStatus.PENDING: LegacyAgentStatus.IDLE,
        AgentStatus.SUSPENDED: LegacyAgentStatus.OFFLINE,
        AgentStatus.OFFLINE: LegacyAgentStatus.OFFLINE,
        AgentStatus.IDLE: LegacyAgentStatus.IDLE,  # IDLE -> IDLE
        AgentStatus.BUSY: (
            LegacyAgentStatus.BUSY if hasattr(LegacyAgentStatus, "BUSY") else LegacyAgentStatus.IDLE
        ),  # BUSY -> BUSY 或 IDLE
    }

    legacy_status = status_mapping.get(registry_info.status, LegacyAgentStatus.OFFLINE)

    return LegacyAgentInfo(
        agent_id=registry_info.agent_id,
        agent_type=registry_info.agent_type,
        name=registry_info.name,  # type: ignore[call-arg]  # name 有默認值
        status=legacy_status,
        endpoints=registry_info.endpoints,  # type: ignore[call-arg]  # endpoints 有默認值
        capabilities=registry_info.capabilities,
        load=registry_info.load if hasattr(registry_info, "load") else 0,  # type: ignore[call-arg]  # load 有默認值
        metadata=registry_info.metadata,  # 直接使用 AgentMetadata 對象
        registered_at=registry_info.registered_at,
        last_heartbeat=registry_info.last_heartbeat,
    )
