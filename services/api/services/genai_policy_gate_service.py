"""
代碼功能說明: GenAI Policy Gate（G6）- provider/model allowlist 與收藏模型過濾（MVP）
創建日期: 2025-12-13 21:09:37 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 23:34:17 (UTC+8)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from system.infra.config.config import get_config_section


@dataclass
class GenAIPolicy:
    allowed_providers: List[str]
    allowed_models: Dict[str, List[str]]
    default_fallback: Dict[str, Any]


class GenAIPolicyGateService:
    """集中處理 GenAI policy gate（MVP：allowlist + wildcard prefix）。"""

    def __init__(self, *, policy_override: Optional[Dict[str, Any]] = None) -> None:
        self._policy = self._load_policy(policy_override=policy_override)

    @staticmethod
    def _load_policy(*, policy_override: Optional[Dict[str, Any]] = None) -> GenAIPolicy:
        policy = (
            policy_override
            if isinstance(policy_override, dict)
            else (get_config_section("genai", "policy", default={}) or {})
        )

        allowed_providers = policy.get("allowed_providers") or []
        if not isinstance(allowed_providers, list):
            allowed_providers = []
        allowed_providers = [str(p).strip().lower() for p in allowed_providers if str(p).strip()]

        allowed_models = policy.get("allowed_models") or {}
        if not isinstance(allowed_models, dict):
            allowed_models = {}
        normalized_models: Dict[str, List[str]] = {}
        for prov, patterns in allowed_models.items():
            prov_key = str(prov).strip().lower()
            if not prov_key:
                continue
            if not isinstance(patterns, list):
                continue
            normalized_patterns = [str(x).strip() for x in patterns if str(x).strip()]
            normalized_models[prov_key] = normalized_patterns

        default_fallback = policy.get("default_fallback") or {}
        if not isinstance(default_fallback, dict):
            default_fallback = {}

        return GenAIPolicy(
            allowed_providers=allowed_providers,
            allowed_models=normalized_models,
            default_fallback=default_fallback,
        )

    @staticmethod
    def _matches(model_id: str, pattern: str) -> bool:
        m = str(model_id).strip().lower()
        p = str(pattern).strip().lower()
        if not m or not p:
            return False
        if p == "*":
            return True
        if p.endswith("*"):
            return m.startswith(p[:-1])
        return m == p

    def get_allowed_providers(self) -> List[str]:
        return list(self._policy.allowed_providers)

    def is_provider_allowed(self, provider: str) -> bool:
        prov = str(provider).strip().lower()
        if not prov:
            return False
        if not self._policy.allowed_providers:
            return True
        return prov in self._policy.allowed_providers

    def is_model_allowed(self, provider: str, model_id: Optional[str]) -> bool:
        prov = str(provider).strip().lower()
        mid = str(model_id).strip() if model_id is not None else ""

        if not self.is_provider_allowed(prov):
            return False

        patterns = self._policy.allowed_models.get(prov)
        if patterns is None:
            # 若未配置 provider 的 models allowlist：MVP 採放行（避免誤阻擋）
            return True

        if not mid:
            # auto 可能沒有 model；MVP 不阻擋
            return True

        return any(self._matches(mid, p) for p in patterns)

    def filter_favorite_models(self, model_ids: List[str]) -> List[str]:
        """去除不允許的 model_id，並去重保序。"""
        seen: set[str] = set()
        out: List[str] = []
        for raw in model_ids:
            mid = str(raw).strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)

            # 由 model_id 推導 provider（與 chat router heuristic 一致即可）
            provider = self.infer_provider_from_model_id(mid)
            if self.is_model_allowed(provider, mid):
                out.append(mid)
        return out

    @staticmethod
    def infer_provider_from_model_id(model_id: str) -> str:
        m = str(model_id).strip().lower()
        if ":" in m or m in {"llama2", "gpt-oss:20b", "qwen3-coder:30b"}:
            return "ollama"
        if m.startswith("gpt-") or m.startswith("openai") or "gpt" in m:
            return "chatgpt"
        if m.startswith("gemini"):
            return "gemini"
        if m.startswith("grok"):
            return "grok"
        if m.startswith("qwen"):
            return "qwen"
        return "ollama"


_policy_gate: Optional[GenAIPolicyGateService] = None


def get_genai_policy_gate_service() -> GenAIPolicyGateService:
    global _policy_gate
    if _policy_gate is None:
        _policy_gate = GenAIPolicyGateService()
    return _policy_gate


def reset_genai_policy_gate_service() -> None:
    global _policy_gate
    _policy_gate = None
