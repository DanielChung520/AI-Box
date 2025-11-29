# 代碼功能說明: LLM 客戶端工廠實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""LLM 客戶端工廠，根據 LLMProvider 創建對應客戶端，支持單例模式。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from agents.task_analyzer.models import LLMProvider

from .base import BaseLLMClient
from .chatgpt import ChatGPTClient
from .gemini import GeminiClient
from .grok import GrokClient
from .ollama import OllamaClient
from .qwen import QwenClient

logger = logging.getLogger(__name__)

# 客戶端實例緩存（單例模式）
_client_cache: Dict[LLMProvider, BaseLLMClient] = {}


class LLMClientFactory:
    """LLM 客戶端工廠類。"""

    @staticmethod
    def create_client(
        provider: LLMProvider,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> BaseLLMClient:
        """
        創建 LLM 客戶端實例。

        Args:
            provider: LLM 提供商
            use_cache: 是否使用緩存（單例模式）
            **kwargs: 客戶端初始化參數

        Returns:
            LLM 客戶端實例

        Raises:
            ValueError: 如果提供商不支持
        """
        # 如果使用緩存且已存在實例，直接返回
        if use_cache and provider in _client_cache:
            return _client_cache[provider]

        # 根據提供商創建對應的客戶端
        client: BaseLLMClient

        if provider == LLMProvider.CHATGPT:
            client = ChatGPTClient(**kwargs)
        elif provider == LLMProvider.GEMINI:
            client = GeminiClient(**kwargs)
        elif provider == LLMProvider.GROK:
            client = GrokClient(**kwargs)
        elif provider == LLMProvider.QWEN:
            client = QwenClient(**kwargs)
        elif provider == LLMProvider.OLLAMA:
            client = OllamaClient(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # 緩存實例（如果啟用緩存）
        if use_cache:
            _client_cache[provider] = client

        logger.info(f"Created {provider.value} client (cached: {use_cache})")
        return client

    @staticmethod
    def get_cached_client(provider: LLMProvider) -> Optional[BaseLLMClient]:
        """
        獲取緩存的客戶端實例。

        Args:
            provider: LLM 提供商

        Returns:
            客戶端實例，如果不存在返回 None
        """
        return _client_cache.get(provider)

    @staticmethod
    def clear_cache(provider: Optional[LLMProvider] = None) -> None:
        """
        清除客戶端緩存。

        Args:
            provider: 要清除的提供商（如果為 None，清除所有緩存）
        """
        if provider is None:
            _client_cache.clear()
            logger.info("Cleared all LLM client cache")
        else:
            if provider in _client_cache:
                del _client_cache[provider]
                logger.info(f"Cleared {provider.value} client cache")

    @staticmethod
    def is_client_available(provider: LLMProvider) -> bool:
        """
        檢查客戶端是否可用。

        Args:
            provider: LLM 提供商

        Returns:
            如果客戶端可用返回 True
        """
        try:
            client = LLMClientFactory.create_client(provider, use_cache=True)
            return client.is_available()
        except Exception as exc:
            logger.warning(f"Client {provider.value} is not available: {exc}")
            return False


@lru_cache(maxsize=5)
def get_client(provider: LLMProvider) -> BaseLLMClient:
    """
    獲取 LLM 客戶端（使用緩存）。

    Args:
        provider: LLM 提供商

    Returns:
        LLM 客戶端實例
    """
    return LLMClientFactory.create_client(provider, use_cache=True)
