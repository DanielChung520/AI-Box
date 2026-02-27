# 代碼功能說明: Data Agent 模塊初始化
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-20
#
# 廢棄說明:
# - agent.py, text_to_sql.py 已廢棄，使用 schema_driven_query 模組
# - 此模組不再導出這些廢棄的類

"""Data Agent - 數據查詢專屬服務 Agent

當前使用的模組：
- services/schema_driven_query/ - Schema 驅動查詢
- routers/data_agent_jp/ - JP 查詢 API
"""

# 當前配置
from .config_manager import DataAgentConfig, get_config

__all__ = ["DataAgentConfig", "get_config"]
