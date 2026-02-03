# 代碼功能說明: Dashboard 服務模組
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-29 UTC+8

"""Dashboard 服務模組"""

from .data_access import DataLakeClient
from .data_agent_client import call_data_agent

__all__ = ["DataLakeClient", "call_data_agent"]
