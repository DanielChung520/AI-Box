# 代碼功能說明: ChatGPT 客戶端實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""ChatGPT 客戶端實現，整合 OpenAI SDK。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion
    from openai.types.completion import Completion
    from openai.types.embedding import Embedding
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment, misc]
    ChatCompletion = None  # type: ignore[assignment, misc]
    Completion = None  # type: ignore[assignment, misc]
    Embedding = None  # type: ignore[assignment, misc]

from system.infra.config.config import get_config_section

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class ChatGPTClientError(Exception):
    """ChatGPT 客戶端基礎錯誤。"""


class ChatGPTClient(BaseLLMClient):
    """ChatGPT 客戶端實現。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        初始化 ChatGPT 客戶端。

        Args:
            api_key: OpenAI API 密鑰（從環境變數或配置讀取）
            base_url: API 基礎 URL（可選，用於自定義端點）
            default_model: 默認模型名稱
            timeout: 請求超時時間（秒，可選，從配置讀取）
        """
        if AsyncOpenAI is None:
            raise ImportError(
                "OpenAI SDK is not installed. Please install it with: pip install openai"
            )

        # 從環境變數或配置讀取 API 密鑰
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                config = get_config_section("llm", "chatgpt", default={}) or {}
                api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OpenAI API key is required")

        # 從配置讀取其他參數
        config = get_config_section("llm", "chatgpt", default={}) or {}
        if base_url is None:
            base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        if default_model is None:
            default_model = config.get("default_model", "gpt-4-turbo-preview")
        if timeout is None:
            timeout = float(config.get("timeout", 60.0))

        self.api_key = api_key
        self.base_url = base_url
        self._default_model = default_model
        self.timeout = timeout

        # 創建 OpenAI 客戶端
        client_kwargs: Dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self._client = AsyncOpenAI(**client_kwargs)

    @property
    def provider_name(self) -> str:
        """返回提供商名稱。"""
        return "chatgpt"

    @property
    def default_model(self) -> str:
        """返回默認模型名稱。"""
        return self._default_model

    async def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成文本。

        Args:
            prompt: 輸入提示詞
            model: 模型名稱（可選，使用默認模型）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            生成結果字典，包含 'text' 或 'content' 字段
        """
        model = model or self.default_model

        try:
            response: Completion = await self._client.completions.create(
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # 提取文本內容
            text = response.choices[0].text if response.choices else ""

            # 構建返回結果
            result: Dict[str, Any] = {
                "text": text,
                "content": text,
                "model": model,
            }

            # 添加 token 使用量統計
            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return result

        except Exception as exc:
            logger.error(f"ChatGPT generate error: {exc}")
            raise ChatGPTClientError(f"Failed to generate text: {exc}") from exc

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        對話生成。

        Args:
            messages: 消息列表，每個消息包含 'role' 和 'content'
            model: 模型名稱（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            對話結果字典，包含 'content' 或 'message' 字段
        """
        model = model or self.default_model

        try:
            # 轉換消息格式（確保符合 OpenAI API 格式）
            formatted_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted_messages.append({"role": role, "content": content})

            response: ChatCompletion = await self._client.chat.completions.create(
                model=model,
                messages=formatted_messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # 提取消息內容
            content = ""
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if hasattr(choice, "message") and choice.message:
                    content = choice.message.content or ""

            # 構建返回結果
            result: Dict[str, Any] = {
                "content": content,
                "message": content,
                "model": model,
            }

            # 添加 token 使用量統計
            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return result

        except Exception as exc:
            logger.error(f"ChatGPT chat error: {exc}")
            raise ChatGPTClientError(f"Failed to chat: {exc}") from exc

    async def embeddings(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[float]:
        """
        生成文本嵌入向量。

        Args:
            text: 輸入文本
            model: 嵌入模型名稱（可選）
            **kwargs: 其他參數

        Returns:
            嵌入向量列表
        """
        # 默認使用 text-embedding-ada-002
        model = model or "text-embedding-ada-002"

        try:
            response = await self._client.embeddings.create(
                model=model,
                input=text,
                **kwargs,
            )

            # 提取嵌入向量
            if response.data and len(response.data) > 0:
                embedding: Embedding = response.data[0]
                return embedding.embedding

            return []

        except Exception as exc:
            logger.error(f"ChatGPT embeddings error: {exc}")
            raise ChatGPTClientError(f"Failed to generate embeddings: {exc}") from exc

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用。

        Returns:
            如果可用返回 True，否則返回 False
        """
        return self._client is not None and self.api_key is not None
