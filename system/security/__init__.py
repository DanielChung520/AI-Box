# 代碼功能說明: 安全模組初始化文件
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:30 (UTC+8)

"""AI-Box 安全模組 - 提供身份驗證、授權和安全相關功能。

此模組為 WBS 1.6 的最小先行開發版本，提供開發模式繞過機制。
完整功能將在後續 WBS 1.6 子任務中實施。

主要組件：
- config: 安全配置管理
- auth: 認證相關功能
- dependencies: FastAPI 依賴注入
- middleware: 安全中間件
- models: 安全相關數據模型
"""

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
