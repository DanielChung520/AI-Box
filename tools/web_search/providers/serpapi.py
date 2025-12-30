# 代碼功能說明: SerpAPI 搜索提供商實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""SerpAPI 搜索提供商實現

SerpAPI 提供完整的 Google 搜索結果，包括圖片、新聞、購物等。
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


class SerpAPIProvider(SearchProviderBase):
    """SerpAPI 提供商"""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10) -> None:
        """
        初始化 SerpAPI 提供商

        Args:
            api_key: API 密鑰，如果為 None 則從環境變數獲取
            timeout: 請求超時時間（秒）
        """
        api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not api_key:
            raise ToolConfigurationError(
                "SerpAPI key not provided. Set SERPAPI_API_KEY environment variable or pass api_key parameter.",
                tool_name="SerpAPIProvider",
            )
        super().__init__(api_key, timeout)

    async def search(
        self, query: str, num: int = 10, location: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        執行 SerpAPI 搜索

        Args:
            query: 搜索查詢
            num: 結果數量（1-100）
            location: 地理位置（可選）
            **kwargs: 其他參數

        Returns:
            搜索結果字典
        """
        # 限制結果數量
        num = min(max(num, 1), 100)

        params: Dict[str, Any] = {
            "q": query,
            "num": num,
            "api_key": self.api_key,
            "engine": "google",
        }

        if location:
            params["location"] = location

        logger.info("serpapi_searching", query=query, num=num)
        response = await self._make_request(self.BASE_URL, method="GET", params=params)

        if response:
            return self._parse_response(response)
        return {
            "status": SearchStatus.FAILED,
            "provider": SearchProvider.SERPAPI,
            "results": [],
            "error": "Failed to fetch search results",
        }

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 SerpAPI 響應

        Args:
            response: API 響應數據

        Returns:
            統一格式的搜索結果
        """
        results: List[SearchResultItem] = []

        # 答案框
        if "answer_box" in response:
            answer_box = response["answer_box"]
            results.append(
                SearchResultItem(
                    title=answer_box.get("title", ""),
                    link=answer_box.get("link", ""),
                    snippet=answer_box.get("snippet", answer_box.get("answer", "")),
                    result_type="answer_box",
                    position=0,
                )
            )

        # 有機結果
        for idx, item in enumerate(response.get("organic_results", []), start=1):
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
            "provider": SearchProvider.SERPAPI,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
