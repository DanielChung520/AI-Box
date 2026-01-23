# 代碼功能說明: Gemini 客戶端實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-22

"""Gemini 客戶端實現，整合 Google Gemini API。"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerateContentResponse
except ImportError:
    genai = None  # type: ignore[assignment, misc]
    GenerateContentResponse = None  # type: ignore[assignment, misc]

from system.infra.config.config import get_config_section

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    """Gemini 客戶端基礎錯誤。"""


class GeminiClient(BaseLLMClient):
    """Gemini 客戶端實現。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        初始化 Gemini 客戶端。

        Args:
            api_key: Google API 密鑰（從環境變數或配置讀取）
            default_model: 默認模型名稱
            timeout: 請求超時時間（秒，可選，從配置讀取）
        """
        if genai is None:
            raise ImportError(
                "Google Generative AI SDK is not installed. "
                "Please install it with: pip install google-generativeai"
            )

        # 從環境變數或配置讀取 API 密鑰
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                config = get_config_section("llm", "gemini", default={}) or {}
                api_key = config.get("api_key") or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key is required")

        # 從配置讀取其他參數
        config = get_config_section("llm", "gemini", default={}) or {}
        if default_model is None:
            default_model = config.get("default_model", "gemini-3-pro-preview")
        if timeout is None:
            timeout = float(config.get("timeout", 60.0))

        self.api_key = api_key
        self._default_model = default_model
        self.timeout = timeout

        # 配置 Gemini API
        genai.configure(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        """返回提供商名稱。"""
        return "gemini"

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
            # 創建模型實例
            gen_model = genai.GenerativeModel(model)

            # 構建生成配置
            generation_config: Dict[str, Any] = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            # 過濾掉不相關的 kwarg（如 model_id）
            for k, v in kwargs.items():
                if k not in ("model", "model_id"):
                    generation_config[k] = v

            # 生成內容
            response: GenerateContentResponse = await gen_model.generate_content_async(
                prompt, generation_config=generation_config
            )

            # 提取文本內容
            text = response.text if hasattr(response, "text") and response.text else ""

            # 構建返回結果
            result: Dict[str, Any] = {
                "text": text,
                "content": text,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                result["usage"] = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            return result

        except Exception as exc:
            logger.error(f"Gemini generate error: {exc}")
            raise GeminiClientError(f"Failed to generate text: {exc}") from exc

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
            # 創建模型實例
            gen_model = genai.GenerativeModel(model)

            # 構建生成配置
            generation_config: Dict[str, Any] = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if max_tokens is not None:
                generation_config["max_output_tokens"] = max_tokens
            # 過濾掉不相關的 kwarg（如 model_id）
            for k, v in kwargs.items():
                if k not in ("model", "model_id"):
                    generation_config[k] = v

            # 轉換消息格式為 Gemini 格式
            # Gemini 使用 parts 格式，但我們可以簡化為純文本
            chat_history = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
                elif role == "system":
                    # Gemini 不支持 system 消息，可以作為第一個 user 消息
                    if not chat_history:
                        chat_history.append({"role": "user", "parts": [content]})

            # 開始聊天會話
            chat = gen_model.start_chat(history=chat_history[:-1] if len(chat_history) > 1 else [])

            # 發送最後一條消息
            last_message = chat_history[-1]["parts"][0] if chat_history else ""
            response = await chat.send_message_async(
                last_message, generation_config=generation_config
            )

            # 提取消息內容
            content = response.text if hasattr(response, "text") and response.text else ""

            # 構建返回結果
            result: Dict[str, Any] = {
                "content": content,
                "message": content,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                result["usage"] = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    ),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            return result

        except Exception as exc:
            logger.error(f"Gemini chat error: {exc}")
            raise GeminiClientError(f"Failed to chat: {exc}") from exc

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
        # Gemini 使用 text-embedding-004 或 embedding-001
        model = model or "models/text-embedding-004"

        try:
            # 使用 embedding API
            result = await genai.embed_content_async(
                model=model,
                content=text,
                **kwargs,
            )

            # 提取嵌入向量
            if hasattr(result, "embedding") and result.embedding:
                return result.embedding

            return []

        except Exception as exc:
            logger.error(f"Gemini embeddings error: {exc}")
            raise GeminiClientError(f"Failed to generate embeddings: {exc}") from exc

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用。

        Returns:
            如果可用返回 True，否則返回 False
        """
        return genai is not None and self.api_key is not None
