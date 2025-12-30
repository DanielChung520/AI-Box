# 代碼功能說明: Web 搜索提供商基類
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Web 搜索提供商基類

定義搜索提供商的統一接口和通用功能。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class SearchProvider(Enum):
    """搜索提供商枚舉"""

    SERPER = "serper"
    SERPAPI = "serpapi"
    SCRAPER = "scraper"
    GOOGLE_CSE = "google_cse"


class SearchStatus(Enum):
    """搜索狀態"""

    SUCCESS = "success"
    FAILED = "failed"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout"
    INVALID_API_KEY = "invalid_api_key"


class SearchResultItem:
    """搜索結果項數據模型"""

    def __init__(
        self,
        title: str,
        link: str,
        snippet: str,
        result_type: str = "organic",
        position: Optional[int] = None,
    ) -> None:
        """
        初始化搜索結果項

        Args:
            title: 標題
            link: 鏈接
            snippet: 摘要
            result_type: 結果類型（organic, answer_box, news 等）
            position: 位置（排名）
        """
        self.title = title
        self.link = link
        self.snippet = snippet
        self.result_type = result_type
        self.position = position

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "type": self.result_type,
            "position": self.position,
        }


class SearchProviderBase(ABC):
    """搜索提供商抽象基類"""

    def __init__(self, api_key: str, timeout: int = 10) -> None:
        """
        初始化搜索提供商

        Args:
            api_key: API 密鑰
            timeout: 請求超時時間（秒）
        """
        self.api_key = api_key
        self.timeout = timeout
        self.name = self.__class__.__name__

    @abstractmethod
    async def search(
        self, query: str, num: int = 10, location: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        執行搜索（子類必須實現）

        Args:
            query: 搜索查詢
            num: 結果數量
            location: 地理位置（可選）
            **kwargs: 其他參數

        Returns:
            搜索結果字典，包含 status、provider、results 等字段
        """
        pass

    @abstractmethod
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析響應（統一格式）

        Args:
            response: API 響應數據

        Returns:
            統一格式的搜索結果
        """
        pass

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        通用 HTTP 請求封裝

        Args:
            url: 請求 URL
            method: HTTP 方法（GET 或 POST）
            params: URL 參數（用於 GET）
            json_data: JSON 數據（用於 POST）
            headers: 請求頭

        Returns:
            響應 JSON 數據，失敗時返回 None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "POST":
                    response = await client.post(url, json=json_data, headers=headers)
                else:
                    response = await client.get(url, params=params, headers=headers)

                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            logger.error(f"{self.name}: Request timeout", timeout=self.timeout)
            return None
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 401 or status_code == 403:
                logger.error(f"{self.name}: Invalid API key or unauthorized")
            elif status_code == 429:
                logger.error(f"{self.name}: Rate limit exceeded")
            else:
                logger.error(f"{self.name}: HTTP error - {status_code}")
            return None
        except Exception as e:
            logger.error(f"{self.name}: Unexpected error - {e}", exc_info=True)
            return None
