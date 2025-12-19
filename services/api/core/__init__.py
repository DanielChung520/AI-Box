# 代碼功能說明: API 核心適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 核心適配器 - 重新導出 api.core 的模組"""

from api.core.response import APIResponse
from api.core.settings import OllamaSettings, get_ollama_settings
from api.core.version import API_PREFIX, get_version_info

__all__ = [
    "APIResponse",
    "get_version_info",
    "API_PREFIX",
    "get_ollama_settings",
    "OllamaSettings",
]
