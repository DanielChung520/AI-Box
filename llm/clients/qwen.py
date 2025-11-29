# 代碼功能說明: Qwen 客戶端實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""Qwen 客戶端實現，整合阿里雲 Qwen API。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment, misc]

from core.config import get_config_section

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class QwenClientError(Exception):
    """Qwen 客戶端基礎錯誤。"""


class QwenClient(BaseLLMClient):
    """Qwen 客戶端實現。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        初始化 Qwen 客戶端。

        Args:
            api_key: 阿里雲 API 密鑰（從環境變數或配置讀取）
            base_url: API 基礎 URL（可選）
            default_model: 默認模型名稱
            timeout: 請求超時時間（秒，可選，從配置讀取）
        """
        if httpx is None:
            raise ImportError(
                "httpx is not installed. Please install it with: pip install httpx"
            )

        # 從環境變數或配置讀取 API 密鑰
        if api_key is None:
            api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                config = get_config_section("llm", "qwen", default={}) or {}
                api_key = config.get("api_key") or os.getenv("QWEN_API_KEY")

        if not api_key:
            raise ValueError("Qwen API key is required")

        # 從配置讀取其他參數
        config = get_config_section("llm", "qwen", default={}) or {}
        if base_url is None:
            base_url = config.get("base_url", "https://dashscope.aliyuncs.com/api/v1")
        if default_model is None:
            default_model = config.get("default_model", "qwen-turbo")
        if timeout is None:
            timeout = float(config.get("timeout", 60.0))

        self.api_key = api_key
        self.base_url = base_url
        self._default_model = default_model
        self.timeout = timeout

        # 創建 HTTP 客戶端
        self._client: Optional[httpx.AsyncClient] = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    @property
    def provider_name(self) -> str:
        """返回提供商名稱。"""
        return "qwen"

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

        if self._client is None:
            raise QwenClientError("Client has been closed")

        try:
            # Qwen API 使用 chat completions 端點
            payload: Dict[str, Any] = {
                "model": model,
                "input": {
                    "messages": [{"role": "user", "content": prompt}],
                },
            }

            parameters: Dict[str, Any] = {}
            if temperature is not None:
                parameters["temperature"] = temperature
            if max_tokens is not None:
                parameters["max_tokens"] = max_tokens
            parameters.update(kwargs)

            if parameters:
                payload["parameters"] = parameters

            response = await self._client.post(
                "/services/aigc/text-generation/generation", json=payload
            )
            response.raise_for_status()
            data = response.json()

            # 提取文本內容
            text = ""
            if "output" in data and "choices" in data["output"]:
                choices = data["output"]["choices"]
                if len(choices) > 0 and "message" in choices[0]:
                    text = choices[0]["message"].get("content", "")

            # 構建返回結果
            result: Dict[str, Any] = {
                "text": text,
                "content": text,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if "usage" in data:
                result["usage"] = data["usage"]

            return result

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Qwen HTTP error: {exc.response.status_code} - {exc.response.text}"
            )
            raise QwenClientError(f"Qwen API error: {exc}") from exc
        except Exception as exc:
            logger.error(f"Qwen generate error: {exc}")
            raise QwenClientError(f"Failed to generate text: {exc}") from exc

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

        if self._client is None:
            raise QwenClientError("Client has been closed")

        try:
            # 轉換消息格式
            formatted_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted_messages.append({"role": role, "content": content})

            payload: Dict[str, Any] = {
                "model": model,
                "input": {
                    "messages": formatted_messages,
                },
            }

            parameters: Dict[str, Any] = {}
            if temperature is not None:
                parameters["temperature"] = temperature
            if max_tokens is not None:
                parameters["max_tokens"] = max_tokens
            parameters.update(kwargs)

            if parameters:
                payload["parameters"] = parameters

            response = await self._client.post(
                "/services/aigc/text-generation/generation", json=payload
            )
            response.raise_for_status()
            data = response.json()

            # 提取消息內容
            content = ""
            if "output" in data and "choices" in data["output"]:
                choices = data["output"]["choices"]
                if len(choices) > 0 and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")

            # 構建返回結果
            result: Dict[str, Any] = {
                "content": content,
                "message": content,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if "usage" in data:
                result["usage"] = data["usage"]

            return result

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Qwen HTTP error: {exc.response.status_code} - {exc.response.text}"
            )
            raise QwenClientError(f"Qwen API error: {exc}") from exc
        except Exception as exc:
            logger.error(f"Qwen chat error: {exc}")
            raise QwenClientError(f"Failed to chat: {exc}") from exc

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
        # Qwen 使用 text-embedding-v1 或 text-embedding-v2
        model = model or "text-embedding-v1"

        if self._client is None:
            raise QwenClientError("Client has been closed")

        try:
            payload: Dict[str, Any] = {
                "model": model,
                "input": {
                    "texts": [text],
                },
            }
            payload.update(kwargs)

            response = await self._client.post(
                "/services/embeddings/text-embedding/text-embedding", json=payload
            )
            response.raise_for_status()
            data = response.json()

            # 提取嵌入向量
            if "output" in data and "embeddings" in data["output"]:
                embeddings = data["output"]["embeddings"]
                if len(embeddings) > 0 and "embedding" in embeddings[0]:
                    return embeddings[0]["embedding"]

            return []

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"Qwen HTTP error: {exc.response.status_code} - {exc.response.text}"
            )
            raise QwenClientError(f"Qwen API error: {exc}") from exc
        except Exception as exc:
            logger.error(f"Qwen embeddings error: {exc}")
            raise QwenClientError(f"Failed to generate embeddings: {exc}") from exc

    async def __aenter__(self) -> "QwenClient":
        """
        異步上下文管理器入口。

        Returns:
            QwenClient 實例
        """
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """
        異步上下文管理器出口，關閉 HTTP 客戶端。

        Args:
            exc_type: 異常類型
            exc_val: 異常值
            exc_tb: 異常追蹤
        """
        await self.aclose()

    async def aclose(self) -> None:
        """
        關閉 HTTP 客戶端，釋放資源。
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用。

        Returns:
            如果可用返回 True，否則返回 False
        """
        return self._client is not None and self.api_key is not None
