# 代碼功能說明: Serper.dev 搜索提供商實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Serper.dev 搜索提供商實現

Serper.dev 是一個快速且便宜的 Google 搜索 API 服務。
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


class SerperProvider(SearchProviderBase):
    """Serper.dev 提供商"""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10) -> None:
        """
        初始化 Serper 提供商

        Args:
            api_key: API 密鑰，如果為 None 則從環境變數獲取
            timeout: 請求超時時間（秒）
        """
        api_key = api_key or os.getenv("SERPER_API_KEY")
        if not api_key:
            raise ToolConfigurationError(
                "Serper API key not provided. Set SERPER_API_KEY environment variable or pass api_key parameter.",
                tool_name="SerperProvider",
            )
        super().__init__(api_key, timeout)

    async def search(
        self, query: str, num: int = 10, location: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        執行 Serper 搜索

        Args:
            query: 搜索查詢
            num: 結果數量（1-100）
            location: 地理位置（可選）
            **kwargs: 其他參數（gl, hl 等）

        Returns:
            搜索結果字典
        """
        # 限制結果數量
        num = min(max(num, 1), 100)

        payload: Dict[str, Any] = {
            "q": query,
            "num": num,
        }

        if location:
            payload["location"] = location
            payload["gl"] = kwargs.get("gl", "tw")
            payload["hl"] = kwargs.get("hl", "zh-tw")

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

        logger.info("serper_searching", query=query, num=num)
        response = await self._make_request(
            self.BASE_URL, method="POST", json_data=payload, headers=headers
        )

        if response:
            return self._parse_response(response)
        return {
            "status": SearchStatus.FAILED,
            "provider": SearchProvider.SERPER,
            "results": [],
            "error": "Failed to fetch search results",
        }

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 Serper 響應

        Args:
            response: API 響應數據

        Returns:
            統一格式的搜索結果
        """
        results: List[SearchResultItem] = []

        # 精選摘要（答案框）
        if "answerBox" in response:
            answer_box = response["answerBox"]
            results.append(
                SearchResultItem(
                    title=answer_box.get("title", ""),
                    link=answer_box.get("link", ""),
                    snippet=answer_box.get("snippet", ""),
                    result_type="answer_box",
                    position=0,
                )
            )

        # 有機結果
        for idx, item in enumerate(response.get("organic", []), start=1):
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
            "provider": SearchProvider.SERPER,
            "results": [r.to_dict() for r in results],
            "total": len(results),
        }
