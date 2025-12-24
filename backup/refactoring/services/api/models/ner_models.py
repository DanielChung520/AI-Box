# 代碼功能說明: NER 模型適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""NER 模型適配器 - 重新導出 genai.api.models.ner_models 的模型"""

# 從 genai 模組重新導出模型
from genai.api.models.ner_models import *  # noqa: F403, F401
