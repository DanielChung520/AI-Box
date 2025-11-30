# 代碼功能說明: API 服務適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 服務適配器 - 重新導出 api 模組的內容"""

# 重新導出 main 應用
from api.main import app

__all__ = ["app"]
