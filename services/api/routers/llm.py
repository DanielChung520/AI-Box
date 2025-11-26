# 代碼功能說明: LLM / Ollama API 路由
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""提供生成、對話與嵌入端點，封裝 Ollama 服務。"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from services.api.clients.ollama_client import (
    OllamaClient,
    OllamaClientError,
    OllamaHTTPError,
    OllamaTimeoutError,
    get_ollama_client,
)
from services.api.core.response import APIResponse
from services.api.core.settings import get_ollama_settings
from services.api.models.ollama import (
    OllamaChatRequest,
    OllamaEmbeddingRequest,
    OllamaGenerateRequest,
)

router = APIRouter(prefix="/llm", tags=["LLM"])

OllamaClientDep = Annotated[OllamaClient, Depends(get_ollama_client)]


def _options_dict(options) -> dict | None:
    return options.model_dump(exclude_none=True) if options else None


def _handle_exception(exc: Exception) -> None:
    if isinstance(exc, OllamaTimeoutError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    if isinstance(exc, OllamaHTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    if isinstance(exc, OllamaClientError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    raise exc


@router.post("/generate")
async def generate_text(
    request: OllamaGenerateRequest,
    client: OllamaClientDep,
):
    """文本生成端點。"""

    settings = get_ollama_settings()
    model = request.model or settings.default_model
    try:
        result = await client.generate(
            model=model,
            prompt=request.prompt,
            options=_options_dict(request.options),
            stream=request.stream,
            format=request.format,
            keep_alive=request.keep_alive,
            idempotency_key=request.idempotency_key,
        )
        return APIResponse.success(
            data={"model": model, "response": result},
            message="Generate success",
        )
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc)


@router.post("/chat")
async def chat_completion(
    request: OllamaChatRequest,
    client: OllamaClientDep,
):
    """聊天對話端點。"""

    settings = get_ollama_settings()
    model = request.model or settings.default_model
    try:
        result = await client.chat(
            model=model,
            messages=[message.model_dump() for message in request.messages],
            options=_options_dict(request.options),
            stream=request.stream,
            keep_alive=request.keep_alive,
            idempotency_key=request.idempotency_key,
        )
        return APIResponse.success(
            data={"model": model, "response": result},
            message="Chat success",
        )
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc)


@router.post("/embeddings")
async def create_embeddings(
    request: OllamaEmbeddingRequest,
    client: OllamaClientDep,
):
    """Embeddings 端點，可一次處理多筆文本。"""

    settings = get_ollama_settings()
    model = request.model or settings.embedding_model

    embeddings: List[dict] = []
    try:
        for text in request.inputs:
            result = await client.embeddings(model=model, prompt=text)
            embeddings.append({"text": text, "embedding": result.get("embedding")})
        return APIResponse.success(
            data={"model": model, "items": embeddings},
            message="Embeddings generated",
        )
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc)
