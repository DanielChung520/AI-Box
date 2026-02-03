# 代碼功能說明: Data Agent 模塊初始化
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""Data Agent - 數據查詢專屬服務 Agent"""

from .agent import DataAgent
from .config_manager import DataAgentConfig, get_config

__all__ = ["DataAgent", "DataAgentConfig", "get_config"]
