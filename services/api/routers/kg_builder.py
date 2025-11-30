# 代碼功能說明: KG Builder 路由適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""KG Builder 路由適配器 - 重新導出 genai.api.routers.kg_builder 的路由"""

# 從 genai 模組重新導出路由
from genai.api.routers.kg_builder import router  # noqa: F401
