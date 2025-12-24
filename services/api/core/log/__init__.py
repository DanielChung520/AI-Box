# 代碼功能說明: LogService 模組導出
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""LogService 統一日誌服務模組"""

from .log_service import LogService, LogType, get_log_service

__all__ = ["LogService", "LogType", "get_log_service"]

