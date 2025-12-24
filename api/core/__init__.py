# 代碼功能說明: API 核心模組初始化文件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""API 核心模組 - 提供 API 響應格式、版本管理和配置"""

from .response import APIResponse
from .settings import OllamaSettings, get_ollama_settings
from .version import API_PREFIX, get_version_info

__all__ = [
    "APIResponse",
    "get_version_info",
    "API_PREFIX",
    "get_ollama_settings",
    "OllamaSettings",
]
