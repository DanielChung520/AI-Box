# 代碼功能說明: Capability Adapter 模組初始化
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter - 能力適配器

為 Execution Agents 建立適配器層，實現參數驗證、作用域限制、副作用審計和結果正規化。
"""

from agents.services.capability_adapter.adapter import CapabilityAdapter
from agents.services.capability_adapter.api_adapter import APIAdapter
from agents.services.capability_adapter.database_adapter import DatabaseAdapter
from agents.services.capability_adapter.file_adapter import FileAdapter
from agents.services.capability_adapter.models import AdapterResult, ValidationResult

__all__ = [
    "CapabilityAdapter",
    "FileAdapter",
    "DatabaseAdapter",
    "APIAdapter",
    "AdapterResult",
    "ValidationResult",
]
