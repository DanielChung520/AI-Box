# 代碼功能說明: Security 服務適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Security 服務適配器 - 重新導出 system.security 的模組"""

from system.security.config import get_security_settings, SecuritySettings
from system.security.dependencies import get_current_user, require_permission
from system.security.models import User, Role, Permission

__all__ = [
    "get_security_settings",
    "SecuritySettings",
    "get_current_user",
    "require_permission",
    "User",
    "Role",
    "Permission",
]
