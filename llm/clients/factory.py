# 代碼功能說明: LLM 客戶端工廠實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""LLM 客戶端工廠，根據 LLMProvider 創建對應客戶端，支持單例模式和資源訪問控制。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from agents.services.resource_controller import get_resource_controller
from agents.task_analyzer.models import LLMProvider

from .base import BaseLLMClient
from .chatglm import ChatGLMClient
from .chatgpt import ChatGPTClient
from .gemini import GeminiClient
from .grok import GrokClient
from .ollama import OllamaClient
from .qwen import QwenClient
from .volcano import VolcanoClient

logger = logging.getLogger(__name__)

# 客戶端實例緩存（單例模式）
_client_cache: Dict[LLMProvider, BaseLLMClient] = {}


class ResourceControlledLLMClient(BaseLLMClient):
    """帶資源訪問控制的 LLM Client 包裝器"""

    def __init__(self, client: BaseLLMClient, agent_id: Optional[str] = None):
        """
        初始化資源訪問控制包裝器

        Args:
            client: 底層 LLM Client
            agent_id: Agent ID（可選，用於權限檢查）
        """
        self._client = client
        self._agent_id = agent_id
        self._resource_controller = get_resource_controller()

    def _check_access(self, provider_name: str) -> bool:
        """
        檢查 Agent 是否有權限訪問 LLM Provider

        Args:
            provider_name: LLM Provider 名稱

        Returns:
            是否有權限
        """
        if not self._agent_id:
            # 如果未提供 agent_id，跳過權限檢查（假設是內部調用）
            return True

        return self._resource_controller.check_llm_access(self._agent_id, provider_name)

    async def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """生成文本（帶權限檢查）"""
        provider_name = self._client.provider_name
        if not self._check_access(provider_name):
            raise PermissionError(
                f"Agent '{self._agent_id}' does not have permission to use LLM provider '{provider_name}'"
            )
        return await self._client.generate(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """對話生成（帶權限檢查）"""
        provider_name = self._client.provider_name
        if not self._check_access(provider_name):
            raise PermissionError(
                f"Agent '{self._agent_id}' does not have permission to use LLM provider '{provider_name}'"
            )
        return await self._client.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def embeddings(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[float]:
        """生成嵌入向量（帶權限檢查）"""
        provider_name = self._client.provider_name
        if not self._check_access(provider_name):
            raise PermissionError(
                f"Agent '{self._agent_id}' does not have permission to use LLM provider '{provider_name}'"
            )
        return await self._client.embeddings(text, model=model, **kwargs)

    @property
    def provider_name(self) -> str:
        """返回提供商名稱"""
        return self._client.provider_name

    @property
    def default_model(self) -> str:
        """返回默認模型名稱"""
        return self._client.default_model

    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        return self._client.is_available()


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
        # 若提供了 api_key（多租戶/使用者自帶 key），不可使用全域單例 cache
        if kwargs.get("api_key"):
            use_cache = False

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
        elif provider == LLMProvider.VOLCANO:
            client = VolcanoClient(**kwargs)
        elif provider == LLMProvider.CHATGLM:
            client = ChatGLMClient(**kwargs)
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
def get_client(provider: LLMProvider, agent_id: Optional[str] = None) -> BaseLLMClient:
    """
    獲取 LLM 客戶端（使用緩存，帶資源訪問控制）。

    Args:
        provider: LLM 提供商
        agent_id: Agent ID（可選，用於權限檢查）

    Returns:
        LLM 客戶端實例（如果提供了 agent_id，則返回帶權限檢查的包裝器）
    """
    client = LLMClientFactory.create_client(provider, use_cache=True)

    # 如果提供了 agent_id，返回帶權限檢查的包裝器
    if agent_id:
        return ResourceControlledLLMClient(client, agent_id=agent_id)

    return client
