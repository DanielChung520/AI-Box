# 代碼功能說明: RT 服務適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""RT 服務適配器 - 重新導出 genai.api.services.rt_service 的服務"""

# 從 genai 模組重新導出服務
from genai.api.services.rt_service import RTService  # noqa: F401
