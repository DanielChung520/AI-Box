# 代碼功能說明: Agent 認證服務模組
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent 認證服務模組

提供內部 Agent 和外部 Agent 的認證服務。
"""

from agents.services.auth.internal_auth import (
    authenticate_internal_agent,
    validate_internal_agent_config,
)
from agents.services.auth.external_auth import (
    authenticate_external_agent,
    verify_server_certificate,
    verify_signature,
    check_ip_whitelist,
    verify_server_fingerprint,
    validate_external_agent_config,
)
from agents.services.auth.models import (
    AuthenticationStatus,
    AuthenticationResult,
    InternalAuthConfig,
    ExternalAuthConfig,
)
from agents.services.auth.secret_manager import (
    SecretManager,
    get_secret_manager,
    SecretStatus,
)

__all__ = [
    # 內部認證
    "authenticate_internal_agent",
    "validate_internal_agent_config",
    # 外部認證
    "authenticate_external_agent",
    "verify_server_certificate",
    "verify_signature",
    "check_ip_whitelist",
    "verify_server_fingerprint",
    "validate_external_agent_config",
    # Secret 管理
    "SecretManager",
    "get_secret_manager",
    "SecretStatus",
    # 模型
    "AuthenticationStatus",
    "AuthenticationResult",
    "InternalAuthConfig",
    "ExternalAuthConfig",
]
