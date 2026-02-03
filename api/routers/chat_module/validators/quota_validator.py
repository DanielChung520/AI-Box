# 代碼功能說明: Chat 配額驗證（佔位，可擴展）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""check_quota：佔位，內部 pass 或日誌；後續可接配額服務。"""

import logging

logger = logging.getLogger(__name__)


def check_quota(user_id: str) -> None:
    """
    檢查用戶 Chat 請求配額；超限則拋出異常（目前佔位不拋）。

    Args:
        user_id: 用戶 ID
    """
    # 佔位：不拋異常；後續可調用配額服務，超限時 raise HTTPException(429)
    logger.debug(f"Quota check (placeholder): user_id={user_id}")
