# 代碼功能說明: Web 搜索工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Web 搜索工具實現

提供統一的 Web 搜索工具接口，支持多個搜索提供商的自動降級。
"""

from __future__ import annotations

from typing import List, Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError
from tools.utils.validator import validate_non_empty_string
from tools.web_search.search_service import WebSearchService

logger = structlog.get_logger(__name__)

# 緩存時間：30 分鐘（1800 秒）
WEB_SEARCH_CACHE_TTL = 1800.0


class SearchResult(ToolOutput):
    """搜索結果項"""

    title: str  # 標題
    link: str  # 鏈接
    snippet: str  # 摘要
    result_type: str  # 結果類型（organic, answer_box 等）
    position: Optional[int] = None  # 位置（排名）


class WebSearchInput(ToolInput):
    """Web 搜索輸入參數"""

    query: str  # 搜索查詢
    num: int = 10  # 結果數量（1-100）
    location: Optional[str] = None  # 地理位置（可選，如 "Taiwan"）


class WebSearchOutput(ToolOutput):
    """Web 搜索輸出結果"""

    query: str  # 搜索查詢
    provider: str  # 使用的提供商
    results: List[SearchResult]  # 搜索結果列表
    total: int  # 結果總數
    status: str  # 搜索狀態


class WebSearchTool(BaseTool[WebSearchInput, WebSearchOutput]):
    """Web 搜索工具

    提供統一的 Web 搜索功能，支持多個搜索提供商的自動降級。
    """

    def __init__(self, search_service: Optional[WebSearchService] = None) -> None:
        """
        初始化 Web 搜索工具

        Args:
            search_service: 搜索服務實例，如果為 None 則創建新實例
        """
        self._search_service = search_service or WebSearchService()

    @property
    def name(self) -> str:
        """工具名稱"""
        return "web_search"

    @property
    def description(self) -> str:
        """工具描述"""
        return "執行 Web 搜索，支持多個搜索提供商的自動降級（Serper -> SerpAPI -> ScraperAPI -> Google CSE）"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_input(self, input_data: WebSearchInput) -> None:
        """
        驗證輸入參數

        Args:
            input_data: 輸入參數

        Raises:
            ToolValidationError: 輸入參數驗證失敗
        """
        # 驗證 query
        validate_non_empty_string(input_data.query, "query")

        # 驗證 num
        if input_data.num < 1 or input_data.num > 100:
            raise ToolValidationError("num must be between 1 and 100", field="num")

    async def execute(self, input_data: WebSearchInput) -> WebSearchOutput:
        """
        執行 Web 搜索工具

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證輸入
            self._validate_input(input_data)

            # 生成緩存鍵
            cache_key = generate_cache_key(
                "web_search",
                query=input_data.query,
                num=input_data.num,
                location=input_data.location or "",
            )

            # 嘗試從緩存獲取
            cache = get_cache()
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("web_search_cache_hit", cache_key=cache_key)
                return WebSearchOutput(**cached_result)

            # 執行搜索
            search_result = await self._search_service.search(
                query=input_data.query,
                num=input_data.num,
                location=input_data.location,
            )

            # 轉換結果
            results = [
                SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    result_type=item.get("type", "organic"),
                    position=item.get("position"),
                )
                for item in search_result.get("results", [])
            ]

            # 處理 provider 和 status（可能是枚舉或字符串）
            provider = search_result.get("provider")
            if provider and hasattr(provider, "value"):
                provider_str = provider.value
            else:
                provider_str = str(provider) if provider else "unknown"

            status = search_result.get("status")
            if status and hasattr(status, "value"):
                status_str = status.value
            else:
                status_str = str(status) if status else "unknown"

            output = WebSearchOutput(
                query=input_data.query,
                provider=provider_str,
                results=results,
                total=search_result.get("total", 0),
                status=status_str,
            )

            # 存入緩存
            cache.set(cache_key, output.model_dump(), ttl=WEB_SEARCH_CACHE_TTL)

            return output

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("web_search_tool_execution_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to execute web search tool: {str(e)}", tool_name=self.name
            ) from e
