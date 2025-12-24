# 代碼功能說明: LLM / Ollama API 路由
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""提供生成、對話與嵌入端點，封裝 Ollama 服務。"""

from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status

from api.core.response import APIResponse
from api.core.settings import get_ollama_settings
from llm.clients.ollama import (
    OllamaClient,
    OllamaClientError,
    OllamaHTTPError,
    OllamaTimeoutError,
    get_ollama_client,
)
from services.api.models.ollama import (
    OllamaChatRequest,
    OllamaEmbeddingRequest,
    OllamaGenerateRequest,
)

# 嘗試導入 MoE 管理器（如果可用）
try:
    from llm.moe.moe_manager import LLMMoEManager

    _moe_manager: LLMMoEManager | None = None

    def get_moe_manager() -> LLMMoEManager | None:
        """獲取 MoE 管理器實例（單例）。"""
        global _moe_manager
        if _moe_manager is None:
            try:
                _moe_manager = LLMMoEManager()
            except Exception:
                pass
        return _moe_manager

except ImportError:

    def get_moe_manager() -> "LLMMoEManager | None":  # type: ignore[no-redef]
        """獲取 MoE 管理器實例（不可用時返回 None）。"""
        return None


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
        # 構建 kwargs，包含 options 和其他參數
        kwargs: dict = {}
        if request.options:
            kwargs["options"] = _options_dict(request.options)
        if request.format:
            kwargs["format"] = request.format
        if request.keep_alive:
            kwargs["keep_alive"] = request.keep_alive
        if request.idempotency_key:
            kwargs["idempotency_key"] = request.idempotency_key

        result = await client.generate(
            request.prompt,
            model=model,
            **kwargs,
        )
        # 新接口返回 {"text": "...", "content": "...", "model": "..."}
        # 為了向後兼容，提取 text 或 content 作為 response
        response_text = result.get("text") or result.get("content", "")
        return APIResponse.success(
            data={"model": model, "response": response_text},
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
        # 構建 kwargs
        kwargs: dict = {}
        if request.options:
            kwargs["options"] = _options_dict(request.options)
        if request.keep_alive:
            kwargs["keep_alive"] = request.keep_alive
        if request.idempotency_key:
            kwargs["idempotency_key"] = request.idempotency_key

        result = await client.chat(
            [message.model_dump() for message in request.messages],
            model=model,
            **kwargs,
        )
        # 新接口返回 {"content": "...", "message": "...", "model": "..."}
        # 為了向後兼容，提取 content 或 message 作為 response
        response_content = result.get("content") or result.get("message", "")
        return APIResponse.success(
            data={"model": model, "response": response_content},
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
            # 新接口返回 List[float]，直接使用
            embedding = await client.embeddings(text, model=model)
            embeddings.append({"text": text, "embedding": embedding})
        return APIResponse.success(
            data={"model": model, "items": embeddings},
            message="Embeddings generated",
        )
    except Exception as exc:  # noqa: BLE001
        _handle_exception(exc)


@router.get("/health", status_code=status.HTTP_200_OK)
async def llm_health_check():
    """
    LLM 服務健康檢查端點。

    Returns:
        LLM 服務健康狀態和提供商狀態
    """
    moe_manager = get_moe_manager()
    if moe_manager is None:
        return APIResponse.success(
            data={
                "status": "healthy",
                "service": "llm",
                "load_balancer": "not_configured",
                "health_check": "not_configured",
            },
            message="LLM service is healthy (basic mode)",
        )

    # 獲取健康檢查狀態
    health_status = {}
    if moe_manager.failover_manager is not None:
        health_status = moe_manager.failover_manager.get_provider_health_status()

    # 獲取負載均衡器統計
    load_balancer_stats = {}
    if moe_manager.load_balancer is not None:
        load_balancer_stats = {
            "provider_stats": moe_manager.load_balancer.get_provider_stats(),
            "overall_stats": moe_manager.load_balancer.get_overall_stats(),
        }

    return APIResponse.success(
        data={
            "status": "healthy",
            "service": "llm",
            "load_balancer": load_balancer_stats,
            "health_check": health_status,
        },
        message="LLM service is healthy",
    )


@router.get("/load-balancer/stats", status_code=status.HTTP_200_OK)
async def get_load_balancer_stats():
    """
    獲取負載均衡器統計信息。

    Returns:
        負載均衡器統計信息
    """
    moe_manager = get_moe_manager()
    if moe_manager is None or moe_manager.load_balancer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Load balancer is not configured",
        )

    stats = {
        "provider_stats": moe_manager.load_balancer.get_provider_stats(),
        "overall_stats": moe_manager.load_balancer.get_overall_stats(),
    }

    return APIResponse.success(
        data=stats,
        message="Load balancer statistics retrieved",
    )


@router.get("/health-check/status", status_code=status.HTTP_200_OK)
async def get_health_check_status():
    """
    獲取健康檢查狀態。

    Returns:
        健康檢查狀態信息
    """
    moe_manager = get_moe_manager()
    if moe_manager is None or moe_manager.failover_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check is not configured",
        )

    status_data = moe_manager.failover_manager.get_provider_health_status()

    return APIResponse.success(
        data=status_data,
        message="Health check status retrieved",
    )
