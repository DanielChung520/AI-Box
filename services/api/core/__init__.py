# 代碼功能說明: API 核心適配器（向後兼容）
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""API 核心適配器 - 重新導出 api.core 的模組

注意：使用延遲導入避免循環導入問題。
api.core.settings 可能依賴於 llm.router，而 llm.router 可能依賴於 agents.task_analyzer，
這會導致循環導入，因此使用 __getattr__ 實現延遲導入。
"""

from typing import Any

__all__ = [
    "APIResponse",
    "get_version_info",
    "API_PREFIX",
    "get_ollama_settings",
    "OllamaSettings",
]


def __getattr__(name: str) -> Any:
    """延遲導入以避免循環導入"""
    if name == "APIResponse":
        from api.core.response import APIResponse

        return APIResponse
    elif name == "OllamaSettings":
        from api.core.settings import OllamaSettings

        return OllamaSettings
    elif name == "get_ollama_settings":
        from api.core.settings import get_ollama_settings

        return get_ollama_settings
    elif name == "API_PREFIX":
        from api.core.version import API_PREFIX

        return API_PREFIX
    elif name == "get_version_info":
        from api.core.version import get_version_info

        return get_version_info
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
