# 代碼功能說明: Google Custom Search Engine 搜索提供商實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Google Custom Search Engine 搜索提供商實現

Google CSE 是官方的 Google 搜索 API，但價格較高且限制較多。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import structlog

from tools.utils.errors import ToolConfigurationError
from tools.web_search.providers.base import (
    SearchProvider,
    SearchProviderBase,
    SearchResultItem,
    SearchStatus,
)

logger = structlog.get_logger(__name__)


class GoogleCSEProvider(SearchProviderBase):
    """Google Custom Search Engine 提供商"""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        cx: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        """
        初始化 Google CSE 提供商

        Args:
            api_key: Google API 密鑰，如果為 None 則從環境變數獲取
            cx: Custom Search Engine ID，如果為 None 則從環境變數獲取
            timeout: 請求超時時間（秒）
        """
        api_key = api_key or os.getenv("GOOGLE_CSE_API_KEY")
        cx = cx or os.getenv("GOOGLE_CSE_CX")

        if not api_key:
            raise ToolConfigurationError(
                "Google CSE API key not provided. Set GOOGLE_CSE_API_KEY environment variable or pass api_key parameter.",
                tool_name="GoogleCSEProvider",
            )
        if not cx:
            raise ToolConfigurationError(
                "Google CSE CX (Search Engine ID) not provided. Set GOOGLE_CSE_CX environment variable or pass cx parameter.",
                tool_name="GoogleCSEProvider",
            )

        super().__init__(api_key, timeout)
        self.cx = cx

    async def search(
        self, query: str, num: int = 10, location: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        執行 Google CSE 搜索

        Args:
            query: 搜索查詢
            num: 結果數量（1-10，CSE 限制最多 10 個）
            location: 地理位置（可選，通過 cr 參數）
            **kwargs: 其他參數

        Returns:
            搜索結果字典

        Note:
            Google CSE 限制每次查詢最多返回 10 個結果。
        """
        # CSE 限制最多 10 個結果
        num = min(max(num, 1), 10)

        params: Dict[str, Any] = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": num,
        }

        if location:
            # cr 參數指定國家/地區限制
            params["cr"] = f"country{location.upper()}"

        logger.info("google_cse_searching", query=query, num=num)
        response = await self._make_request(self.BASE_URL, method="GET", params=params)

        if response:
            return self._parse_response(response)
        return {
            "status": SearchStatus.FAILED,
            "provider": SearchProvider.GOOGLE_CSE,
            "results": [],
            "error": "Failed to fetch search results",
        }

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Google CSE 響應

        Args:
            response: API 響應數據

        Returns:
            統一格式的搜索結果
        """
        results: List[SearchResultItem] = []

        # Google CSE 返回的結果在 'items' 字段中
        for idx, item in enumerate(response.get("items", []), start=1):
            results.append(
                SearchResultItem(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    result_type="organic",
                    position=idx,
                )
            )

        return {
            "status": SearchStatus.SUCCESS,
            "provider": SearchProvider.GOOGLE_CSE,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
