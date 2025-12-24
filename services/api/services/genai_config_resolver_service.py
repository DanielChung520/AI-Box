# 代碼功能說明: GenAI 多租戶（Tenant/Org）+ 使用者配置解析器（Policy/Secrets）
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI config resolver.

合併優先序（由低到高）：
- system（config/config.json）
- tenant/org（DB：tenant policy）
- user（DB：user secrets / user config；本階段先做 secrets）
- request（單次請求 overrides；目前僅允許收斂，不擴權）

目標：
- 提供「effective policy gate」（allowlist）
- 提供「effective credentials」（provider API key）：user > tenant > env
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.api.services.genai_policy_gate_service import GenAIPolicyGateService
from services.api.services.genai_tenant_policy_service import (
    GenAITenantPolicyService,
    get_genai_tenant_policy_service,
)
from services.api.services.genai_user_llm_secret_service import (
    GenAIUserLLMSecretService,
    get_genai_user_llm_secret_service,
)
from system.infra.config.config import get_config_section


def _normalize_provider(value: str) -> str:
    return str(value).strip().lower()


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


def _pattern_is_subset_of_any(pattern: str, supersets: List[str]) -> bool:
    """保守判斷 pattern 是否不會擴權（是否被 system pattern 覆蓋）。"""

    p = str(pattern).strip().lower()
    if not p:
        return False
    for s in supersets:
        sp = str(s).strip().lower()
        if not sp:
            continue
        if sp == "*":
            return True
        if sp.endswith("*"):
            # system: gpt-* 覆蓋 tenant: gpt-4o / gpt-4* / gpt-4o-mini
            if p.startswith(sp[:-1]):
                return True
        else:
            # system exact
            if p == sp:
                return True
            # system exact 視為只能允許該模型（不允許 tenant pattern 擴大）
    return False


class GenAIConfigResolverService:
    """GenAI multi-tenant config resolver service."""

    def __init__(
        self,
        tenant_policy: Optional[GenAITenantPolicyService] = None,
        user_secrets: Optional[GenAIUserLLMSecretService] = None,
    ):
        self._tenant_policy = tenant_policy or get_genai_tenant_policy_service()
        self._user_secrets = user_secrets or get_genai_user_llm_secret_service()

    def get_effective_policy_gate(self, *, tenant_id: str, user_id: str) -> GenAIPolicyGateService:
        system_policy = get_config_section("genai", "policy", default={}) or {}
        tenant = self._tenant_policy.get_policy(tenant_id)

        # 先以 system policy 為底
        merged: Dict[str, Any] = {
            "allowed_providers": system_policy.get("allowed_providers") or [],
            "allowed_models": system_policy.get("allowed_models") or {},
            "default_fallback": system_policy.get("default_fallback") or {},
        }

        # tenant policy 只能收斂（不擴權）
        if tenant is not None:
            sys_allowed_providers = [
                _normalize_provider(p) for p in (merged.get("allowed_providers") or [])
            ]
            tenant_allowed_providers = [_normalize_provider(p) for p in tenant.allowed_providers]

            if tenant_allowed_providers:
                if sys_allowed_providers:
                    merged["allowed_providers"] = [
                        p for p in tenant_allowed_providers if p in sys_allowed_providers
                    ]
                else:
                    merged["allowed_providers"] = tenant_allowed_providers

            # allowed_models：若 tenant 有提供則以「不擴權」方式覆寫每個 provider
            sys_allowed_models = merged.get("allowed_models") or {}
            if isinstance(sys_allowed_models, dict) and tenant.allowed_models:
                new_allowed_models: Dict[str, List[str]] = dict(sys_allowed_models)
                for prov, patterns in tenant.allowed_models.items():
                    prov_key = _normalize_provider(prov)
                    if not prov_key or not isinstance(patterns, list):
                        continue
                    sys_patterns_raw = sys_allowed_models.get(prov_key)
                    sys_patterns = (
                        [str(x).strip() for x in sys_patterns_raw]
                        if isinstance(sys_patterns_raw, list)
                        else []
                    )
                    # 只接受被 system 覆蓋的 patterns
                    filtered = [
                        str(p).strip()
                        for p in patterns
                        if str(p).strip()
                        and (not sys_patterns or _pattern_is_subset_of_any(str(p), sys_patterns))
                    ]
                    new_allowed_models[prov_key] = filtered
                merged["allowed_models"] = new_allowed_models

            # default_fallback：允許 tenant 覆蓋（但仍需符合 provider allowlist）
            if tenant.default_fallback is not None:
                merged["default_fallback"] = dict(tenant.default_fallback)

        # user 層：此階段先不提供 user policy（避免擴權）；保留擴展點
        _ = user_id

        return GenAIPolicyGateService(policy_override=merged)

    def resolve_api_key(self, *, tenant_id: str, user_id: str, provider: str) -> Optional[str]:
        prov = _normalize_provider(provider)
        user_key = self._user_secrets.get_api_key(
            tenant_id=tenant_id, user_id=user_id, provider=prov
        )
        if user_key:
            return user_key
        tenant_key = self._tenant_policy.get_tenant_api_key(tenant_id=tenant_id, provider=prov)
        if tenant_key:
            return tenant_key
        return None

    def resolve_api_keys_map(
        self, *, tenant_id: str, user_id: str, providers: List[str]
    ) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for raw in providers:
            prov = _normalize_provider(raw)
            if not prov:
                continue
            key = self.resolve_api_key(tenant_id=tenant_id, user_id=user_id, provider=prov)
            if key:
                out[prov] = key
        return out


_service: Optional[GenAIConfigResolverService] = None


def get_genai_config_resolver_service() -> GenAIConfigResolverService:
    global _service
    if _service is None:
        _service = GenAIConfigResolverService()
    return _service
