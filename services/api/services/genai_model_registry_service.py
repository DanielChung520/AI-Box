"""
代碼功能說明: GenAI Model Registry（JSON）- 提供可用模型清單（config 靜態 + Ollama tags 動態發現，可快取）
創建日期: 2025-12-13 23:06:09 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:12:15 (UTC+8)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional

import httpx
import structlog

from api.core.settings import get_ollama_settings
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)


@dataclass
class ModelRegistryItem:
    provider: str
    model_id: str
    display_name: Optional[str] = None
    capabilities: Optional[List[str]] = None  # chat/vision/embedding
    source: str = "config"  # config/ollama_tags

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "display_name": self.display_name or self.model_id,
            "capabilities": self.capabilities or ["chat"],
            "source": self.source,
        }


class GenAIModelRegistryService:
    """模型清單來源：

    - config: genai.model_registry.models
    - ollama: 以 /api/tags 發現（可選、可快取）

    注意：此 service 不處理權限/allowlist，讓上層 API 決定是否過濾。
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: Dict[str, Any] = {
            "ollama_models": [],
            "ollama_cached_at": 0.0,
        }

    def list_config_models(self) -> List[ModelRegistryItem]:
        cfg = get_config_section("genai", "model_registry", default={}) or {}
        raw = cfg.get("models")
        if not isinstance(raw, list):
            return []

        out: List[ModelRegistryItem] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider", "")).strip().lower()
            model_id = str(item.get("model_id", "")).strip()
            if not provider or not model_id:
                continue
            display_name = item.get("display_name")
            if display_name is not None:
                display_name = str(display_name)
            caps = item.get("capabilities")
            if isinstance(caps, list):
                capabilities = [str(x).strip().lower() for x in caps if str(x).strip()]
            else:
                capabilities = None
            out.append(
                ModelRegistryItem(
                    provider=provider,
                    model_id=model_id,
                    display_name=display_name,
                    capabilities=capabilities,
                    source="config",
                )
            )
        return out

    def _is_discovery_enabled(self) -> bool:
        cfg = get_config_section("genai", "model_registry", default={}) or {}
        return bool(cfg.get("enable_ollama_discovery", False))

    def _cache_ttl_seconds(self) -> int:
        cfg = get_config_section("genai", "model_registry", default={}) or {}
        ttl = cfg.get("cache_ttl_seconds", 60)
        try:
            return max(int(ttl), 5)
        except Exception:  # noqa: BLE001
            return 60

    async def list_ollama_models(self, *, refresh: bool = False) -> List[ModelRegistryItem]:
        if not self._is_discovery_enabled():
            return []

        ttl = self._cache_ttl_seconds()
        now = time.time()

        with self._lock:
            cached_at = float(self._cache.get("ollama_cached_at") or 0.0)
            cached = self._cache.get("ollama_models") or []
            if not refresh and (now - cached_at) < ttl and isinstance(cached, list):
                return [ModelRegistryItem(**x) for x in cached if isinstance(x, dict)]

        settings = get_ollama_settings()
        names: set[str] = set()

        async with httpx.AsyncClient(timeout=float(settings.health_timeout)) as client:
            for node in settings.nodes:
                base = f"{settings.scheme}://{node.host}:{node.port}"
                try:
                    r = await client.get(f"{base}/api/tags")
                    r.raise_for_status()
                    data = r.json()
                    models = data.get("models") if isinstance(data, dict) else None
                    if isinstance(models, list):
                        for m in models:
                            if isinstance(m, dict) and m.get("name"):
                                names.add(str(m["name"]))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "ollama_tags_fetch_failed",
                        host=node.host,
                        port=node.port,
                        error=str(exc),
                    )

        discovered: List[ModelRegistryItem] = []
        for name in sorted(names):
            caps = ["chat"]
            lower = name.lower()
            if "vl" in lower or "vision" in lower:
                caps = ["chat", "vision"]
            discovered.append(
                ModelRegistryItem(
                    provider="ollama",
                    model_id=name,
                    display_name=name,
                    capabilities=caps,
                    source="ollama_tags",
                )
            )

        with self._lock:
            self._cache["ollama_models"] = [d.__dict__ for d in discovered]
            self._cache["ollama_cached_at"] = now

        return discovered

    async def list_models(self, *, refresh: bool = False) -> List[Dict[str, Any]]:
        items: List[ModelRegistryItem] = []
        items.extend(self.list_config_models())
        items.extend(await self.list_ollama_models(refresh=refresh))

        # 去重（provider+model_id），保留先出現者（config 優先）
        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for it in items:
            key = f"{it.provider}:{it.model_id}".lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(it.to_dict())
        return out


_registry: Optional[GenAIModelRegistryService] = None


def get_genai_model_registry_service() -> GenAIModelRegistryService:
    global _registry
    if _registry is None:
        _registry = GenAIModelRegistryService()
    return _registry


def reset_genai_model_registry_service() -> None:
    global _registry
    _registry = None
