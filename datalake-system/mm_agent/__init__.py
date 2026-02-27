# 代碼功能說明: 庫管員Agent模塊初始化
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-20
#
# 職責：
# - 只負責意圖識別（SemanticTranslator）
# - 不負責 SQL 生成（交給 Data-Agent）

"""庫管員Agent - 庫存管理業務Agent"""

__version__ = "1.0.0"

# 導出核心組件
from .semantic_translator import SemanticTranslatorAgent
from .chain.mm_agent_chain import MMAgentChain

__all__ = ["SemanticTranslatorAgent", "MMAgentChain"]
