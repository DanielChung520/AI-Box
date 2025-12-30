# 代碼功能說明: Web 搜索服務抽象層
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Web 搜索服務抽象層

提供統一的 Web 搜索接口，支持多個搜索提供商的自動降級（Fallback）。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import structlog

from tools.utils.errors import ToolConfigurationError
from tools.web_search.providers.base import SearchStatus
from tools.web_search.providers.google_cse import GoogleCSEProvider
from tools.web_search.providers.scraper import ScraperProvider
from tools.web_search.providers.serpapi import SerpAPIProvider
from tools.web_search.providers.serper import SerperProvider

logger = structlog.get_logger(__name__)


class WebSearchService:
    """統一的 Web 搜索服務（抽象層）

    支持多個搜索提供商的自動降級，按優先級順序嘗試：
    1. Serper.dev（首選，便宜快速）
    2. SerpAPI（備用，功能全）
    3. ScraperAPI（備用，大量爬取）
    4. Google CSE（最後，官方但貴）
    """

    def __init__(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """
        初始化搜索服務

        Args:
            config: 提供商配置字典，如果為 None 則從環境變數讀取

        config 示例:
        {
            'serper': {'api_key': 'xxx', 'enabled': True},
            'serpapi': {'api_key': 'xxx', 'enabled': True},
            'scraper': {'api_key': 'xxx', 'enabled': False},
            'google_cse': {'api_key': 'xxx', 'cx': 'xxx', 'enabled': False}
        }
        """
        if config is None:
            config = self._load_config_from_env()

        self.providers: List[Any] = []
        self._init_providers(config)

        if not self.providers:
            raise ToolConfigurationError(
                "至少需要配置一個搜索提供商",
                tool_name="WebSearchService",
            )

    def _load_config_from_env(self) -> Dict[str, Dict[str, Any]]:
        """
        從環境變數加載配置

        Returns:
            提供商配置字典
        """
        config: Dict[str, Dict[str, Any]] = {}

        # Serper
        serper_key = os.getenv("SERPER_API_KEY")
        if serper_key:
            config["serper"] = {"api_key": serper_key, "enabled": True}

        # SerpAPI
        serpapi_key = os.getenv("SERPAPI_API_KEY")
        if serpapi_key:
            config["serpapi"] = {"api_key": serpapi_key, "enabled": True}

        # ScraperAPI
        scraper_key = os.getenv("SCRAPER_API_KEY")
        if scraper_key:
            config["scraper"] = {"api_key": scraper_key, "enabled": True}

        # Google CSE
        google_key = os.getenv("GOOGLE_CSE_API_KEY")
        google_cx = os.getenv("GOOGLE_CSE_CX")
        if google_key and google_cx:
            config["google_cse"] = {
                "api_key": google_key,
                "cx": google_cx,
                "enabled": True,
            }

        return config

    def _init_providers(self, config: Dict[str, Dict[str, Any]]) -> None:
        """
        初始化提供商（按優先級）

        Args:
            config: 提供商配置字典
        """
        # 優先級順序
        priority = [
            ("serper", SerperProvider),
            ("serpapi", SerpAPIProvider),
            ("scraper", ScraperProvider),
            ("google_cse", GoogleCSEProvider),
        ]

        for name, provider_class in priority:
            if name in config and config[name].get("enabled", False):
                try:
                    if name == "google_cse":
                        provider = provider_class(
                            api_key=config[name]["api_key"],
                            cx=config[name]["cx"],
                        )
                    else:
                        provider = provider_class(api_key=config[name]["api_key"])
                    self.providers.append(provider)
                    logger.info("provider_initialized", provider=name)
                except Exception as e:
                    logger.error(
                        "provider_init_failed",
                        provider=name,
                        error=str(e),
                        exc_info=True,
                    )

    async def search(
        self, query: str, num: int = 10, location: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        執行搜索（自動降級）

        Args:
            query: 搜索查詢
            num: 結果數量
            location: 地理位置（可選）
            **kwargs: 其他參數

        Returns:
            統一格式的搜索結果
        """
        for provider in self.providers:
            logger.info("trying_provider", provider=provider.name)
            try:
                result = await provider.search(query, num=num, location=location, **kwargs)

                if result.get("status") == SearchStatus.SUCCESS:
                    logger.info("search_success", provider=provider.name)
                    return result
                else:
                    logger.warning(
                        "provider_failed",
                        provider=provider.name,
                        status=result.get("status"),
                    )
            except Exception as e:
                logger.error(
                    "provider_error",
                    provider=provider.name,
                    error=str(e),
                    exc_info=True,
                )

        # 所有提供商都失敗
        logger.error("all_providers_failed")
        return {
            "status": SearchStatus.FAILED,
            "provider": None,
            "results": [],
            "error": "所有搜索提供商都失敗",
        }

    def get_available_providers(self) -> List[str]:
        """
        獲取可用的提供商列表

        Returns:
            提供商名稱列表
        """
        return [p.name for p in self.providers]
