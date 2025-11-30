# 代碼功能說明: 日誌管理模組初始化文件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""系統日誌管理模組 - 提供統一的日誌配置和管理功能"""

from .middleware import LoggingMiddleware

__all__ = ["LoggingMiddleware"]
