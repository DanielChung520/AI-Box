# 代碼功能說明: Ollama 客戶端實現（實現 BaseLLMClient 接口）
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""Ollama 客戶端實現，整合 Ollama API，實現 BaseLLMClient 接口。"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx

from llm.router import LLMNodeRouter

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaClientError(Exception):
    """Ollama 客戶端基礎錯誤。"""


class OllamaTimeoutError(OllamaClientError):
    """Ollama 呼叫逾時。"""


class OllamaHTTPError(OllamaClientError):
    """Ollama 回傳非 2xx 狀態碼。"""


class OllamaClient(BaseLLMClient):
    """Ollama 客戶端實現，支持節點負載均衡。"""

    def __init__(
        self,
        router: Optional[LLMNodeRouter] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        初始化 Ollama 客戶端。

        Args:
            router: LLM 節點路由器（可選，從配置自動創建）
            default_model: 默認模型名稱（可選，從配置讀取）
            timeout: 請求超時時間（可選，從配置讀取）
        """
        # 延迟导入，避免循环导入
        from api.core.settings import get_ollama_settings

        self.settings = get_ollama_settings()

        # 使用提供的 router 或從設置創建
        if router is None:
            self._router = LLMNodeRouter(
                nodes=list(self.settings.nodes),
                strategy=self.settings.router_strategy,
                cooldown_seconds=self.settings.router_cooldown,
            )
        else:
            self._router = router

        # 設置默認模型和超時
        self._default_model = default_model or self.settings.default_model
        self.timeout = timeout or self.settings.timeout

    @property
    def provider_name(self) -> str:
        """返回提供商名稱。"""
        return "ollama"

    @property
    def default_model(self) -> str:
        """返回默認模型名稱。"""
        return self._default_model

    async def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        發送 POST 請求到 Ollama API。

        Args:
            path: API 路徑
            payload: 請求負載
            idempotency_key: 冪等性鍵（可選）

        Returns:
            響應數據字典

        Raises:
            OllamaTimeoutError: 請求超時
            OllamaHTTPError: HTTP 錯誤
            OllamaClientError: 其他錯誤
        """
        node = self._router.select_node()
        headers: Dict[str, str] = {}
        if self.settings.api_token:
            headers["Authorization"] = f"Bearer {self.settings.api_token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(
                base_url=f"http://{node.host}:{node.port}",
                timeout=self.timeout,
            ) as client:
                response = await client.post(
                    path,
                    json=payload,
                    headers=headers or None,
                )
                response.raise_for_status()
                self._router.mark_success(node.name)
                return response.json()
        except httpx.TimeoutException as exc:
            self._router.mark_failure(node.name)
            raise OllamaTimeoutError(
                f"Ollama request timed out on node {node.name}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._router.mark_failure(node.name)
            raise OllamaHTTPError(
                f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            self._router.mark_failure(node.name)
            raise OllamaClientError(
                f"Ollama request error on node {node.name}: {exc}"
            ) from exc

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

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        # 構建 options
        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        options.update(kwargs.get("options", {}))

        if options:
            payload["options"] = options

        # 處理其他參數
        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        if "keep_alive" in kwargs:
            payload["keep_alive"] = kwargs["keep_alive"]

        try:
            response = await self._post("/api/generate", payload)

            # 提取文本內容
            text = response.get("response", "")

            # 構建返回結果
            result: Dict[str, Any] = {
                "text": text,
                "content": text,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if "prompt_eval_count" in response or "eval_count" in response:
                result["usage"] = {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0)
                    + response.get("eval_count", 0),
                }

            return result

        except Exception as exc:
            logger.error(f"Ollama generate error: {exc}")
            raise OllamaClientError(f"Failed to generate text: {exc}") from exc

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

        # 轉換消息格式為 Ollama 格式
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
        }

        # 構建 options
        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        options.update(kwargs.get("options", {}))

        if options:
            payload["options"] = options

        # 處理其他參數
        if "keep_alive" in kwargs:
            payload["keep_alive"] = kwargs["keep_alive"]

        try:
            response = await self._post("/api/chat", payload)

            # 提取消息內容
            content = ""
            if "message" in response and "content" in response["message"]:
                content = response["message"]["content"]

            # 構建返回結果
            result: Dict[str, Any] = {
                "content": content,
                "message": content,
                "model": model,
            }

            # 添加 token 使用量統計（如果可用）
            if "prompt_eval_count" in response or "eval_count" in response:
                result["usage"] = {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0)
                    + response.get("eval_count", 0),
                }

            return result

        except Exception as exc:
            logger.error(f"Ollama chat error: {exc}")
            raise OllamaClientError(f"Failed to chat: {exc}") from exc

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
        # 使用默認嵌入模型或提供的模型
        model = model or self.settings.embedding_model

        payload: Dict[str, Any] = {"model": model, "prompt": text}
        payload.update(kwargs)

        try:
            response = await self._post("/api/embeddings", payload)

            # 提取嵌入向量
            if "embedding" in response:
                return response["embedding"]

            return []

        except Exception as exc:
            logger.error(f"Ollama embeddings error: {exc}")
            raise OllamaClientError(f"Failed to generate embeddings: {exc}") from exc

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用。

        Returns:
            如果可用返回 True，否則返回 False
        """
        return self._router is not None and len(self._router.get_nodes()) > 0


# 為了向後兼容，提供 get_ollama_client() 函數
@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """
    FastAPI 依賴注入用的單例函數（向後兼容）。

    Returns:
        OllamaClient 實例
    """
    return OllamaClient()
