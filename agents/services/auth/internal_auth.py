# 代碼功能說明: 內部 Agent 認證服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""內部 Agent 認證服務 - 實現寬鬆的內部認證機制"""

import logging
from typing import Optional

from agents.services.auth.models import (
    AuthenticationResult,
    AuthenticationStatus,
    InternalAuthConfig,
)
from agents.services.registry.registry import get_agent_registry

logger = logging.getLogger(__name__)


async def authenticate_internal_agent(
    agent_id: str, service_identity: Optional[str] = None
) -> AuthenticationResult:
    """
    認證內部 Agent

    內部 Agent 使用寬鬆的認證機制：
    1. 檢查 Agent 是否為內部 Agent（is_internal=True）
    2. 可選：驗證服務標識（如果提供）

    Args:
        agent_id: Agent ID
        service_identity: 服務標識（可選，用於額外驗證）

    Returns:
        認證結果
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if not agent_info:
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                agent_id=agent_id,
                message="Agent not found",
                error=f"Agent '{agent_id}' is not registered",
            )

        # 檢查是否為內部 Agent
        if not agent_info.endpoints.is_internal:
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                agent_id=agent_id,
                message="Not an internal agent",
                error=f"Agent '{agent_id}' is not marked as internal agent",
            )

        # 如果提供了服務標識，進行額外驗證
        if service_identity:
            # 檢查 Agent 的權限配置中是否有服務標識
            # 如果 Agent 配置了服務標識，則必須匹配
            if (
                hasattr(agent_info.permissions, "service_identity")
                and agent_info.permissions.service_identity
            ):
                if service_identity != agent_info.permissions.service_identity:
                    return AuthenticationResult(
                        status=AuthenticationStatus.FAILED,
                        agent_id=agent_id,
                        message="Service identity mismatch",
                        error=f"Service identity '{service_identity}' does not match registered identity",
                    )
            logger.debug(f"Service identity verified for agent '{agent_id}': {service_identity}")

        return AuthenticationResult(
            status=AuthenticationStatus.SUCCESS,
            agent_id=agent_id,
            message="Internal agent authenticated successfully",
            error=None,
        )

    except Exception as e:
        logger.error(f"Internal agent authentication error for '{agent_id}': {e}")
        return AuthenticationResult(
            status=AuthenticationStatus.ERROR,
            agent_id=agent_id,
            message=None,  # type: ignore[call-arg]  # message 有默認值
            error=str(e),
        )


def validate_internal_agent_config(config: InternalAuthConfig) -> bool:
    """
    驗證內部 Agent 認證配置

    Args:
        config: 內部認證配置

    Returns:
        配置是否有效
    """
    # 如果要求服務標識，則必須提供
    if config.require_identity and not config.service_identity:
        return False
    return True
