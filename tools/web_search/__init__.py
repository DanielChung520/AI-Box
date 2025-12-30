# 代碼功能說明: Web 搜索工具模組初始化
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Web 搜索工具模組

提供統一的 Web 搜索功能，支持多個搜索提供商的自動降級。
"""

__all__ = [
    "WebSearchTool",
    "WebSearchInput",
    "WebSearchOutput",
    "SearchResult",
    "WebSearchService",
    "SearchProvider",
    "SearchProviderBase",
]

from tools.web_search.providers.base import SearchProvider, SearchProviderBase
from tools.web_search.search_service import WebSearchService
from tools.web_search.web_search_tool import (
    SearchResult,
    WebSearchInput,
    WebSearchOutput,
    WebSearchTool,
)
