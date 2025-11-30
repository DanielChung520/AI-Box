# 代碼功能說明: Agent Registry Adapter 適配器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry Adapter - 適配新舊 Agent 模型，保持向後兼容"""

from agents.services.orchestrator.models import (
    AgentInfo as LegacyAgentInfo,
    AgentStatus as LegacyAgentStatus,
)
from agents.services.registry.models import AgentRegistryInfo, AgentStatus

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
    }

    legacy_status = status_mapping.get(registry_info.status, LegacyAgentStatus.OFFLINE)

    return LegacyAgentInfo(
        agent_id=registry_info.agent_id,
        agent_type=registry_info.agent_type,
        status=legacy_status,
        capabilities=registry_info.capabilities,
        metadata={
            "purpose": registry_info.metadata.purpose,
            "category": registry_info.metadata.category,
            "version": registry_info.metadata.version,
            "mcp_endpoint": registry_info.endpoints.mcp_endpoint,
            "health_endpoint": registry_info.endpoints.health_endpoint,
            **registry_info.extra,
        },
        registered_at=registry_info.registered_at,
        last_heartbeat=registry_info.last_heartbeat,
    )
