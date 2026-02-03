# 代碼功能說明: Chat 認證增強（細粒度權限，可掛 Depends）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""require_chat_permission：依賴項，內部可調用現有 get_current_user。"""

from system.security.models import User


def require_chat_permission(current_user: User) -> User:
    """
    依賴項：要求已登入用戶，具備 Chat 權限（目前等同 get_current_user 通過即可）。

    Args:
        current_user: 由 get_current_user 注入的當前用戶

    Returns:
        當前用戶對象
    """
    # 目前僅做 pass，後續可加：角色檢查、AI_PROCESSING consent 等
    return current_user
