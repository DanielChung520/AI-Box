# 代碼功能說明: RT 路由適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""RT 路由適配器 - 重新導出 genai.api.routers.rt 的路由"""

# 從 genai 模組重新導出路由
from genai.api.routers.rt import router  # noqa: F401
