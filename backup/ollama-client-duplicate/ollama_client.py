# 代碼功能說明: Ollama HTTP 客戶端（含節點負載均衡與錯誤處理）
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""封裝 Ollama REST API 的非同步調用。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

import httpx

from llm.router import LLMNodeRouter
from services.api.core.settings import get_ollama_settings


class OllamaClientError(Exception):
    """Ollama 客戶端基礎錯誤。"""


class OllamaTimeoutError(OllamaClientError):
    """Ollama 呼叫逾時。"""


class OllamaHTTPError(OllamaClientError):
    """Ollama 回傳非 2xx 狀態碼。"""


class OllamaClient:
    """提供生成、對話與嵌入 API 的封裝。"""

    def __init__(self):
        self.settings = get_ollama_settings()
        self._router = LLMNodeRouter(
            nodes=list(self.settings.nodes),
            strategy=self.settings.router_strategy,
            cooldown_seconds=self.settings.router_cooldown,
        )

    async def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        node = self._router.select_node()
        headers = {}
        if self.settings.api_token:
            headers["Authorization"] = f"Bearer {self.settings.api_token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(
                base_url=f"http://{node.host}:{node.port}",
                timeout=self.settings.timeout,
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
            raise OllamaTimeoutError(f"Ollama request timed out on node {node.name}") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaHTTPError(
                f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            self._router.mark_failure(node.name)
            raise OllamaClientError(f"Ollama request error on node {node.name}: {exc}") from exc

    async def generate(
        self,
        *,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        format: Optional[str] = None,
        keep_alive: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if options:
            payload["options"] = options
        if format:
            payload["format"] = format
        if keep_alive:
            payload["keep_alive"] = keep_alive
        return await self._post("/api/generate", payload, idempotency_key=idempotency_key)

    async def chat(
        self,
        *,
        model: str,
        messages: Any,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        keep_alive: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options
        if keep_alive:
            payload["keep_alive"] = keep_alive
        return await self._post("/api/chat", payload, idempotency_key=idempotency_key)

    async def embeddings(
        self,
        *,
        model: str,
        prompt: str,
    ) -> Dict[str, Any]:
        payload = {"model": model, "prompt": prompt}
        return await self._post("/api/embeddings", payload)


@lru_cache
def get_ollama_client() -> OllamaClient:
    """FastAPI 依賴注入用的單例。"""

    return OllamaClient()
