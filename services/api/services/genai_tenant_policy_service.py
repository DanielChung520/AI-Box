# 代碼功能說明: GenAI 租戶（Tenant/Org）政策與租戶級 Secrets 管理服務
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI Tenant policy / tenant secrets service.

- Policy（非敏感）：存於 ArangoDB collection `genai_tenant_policies`
- Secrets（敏感，例如 provider API key）：存於 ArangoDB collection `genai_tenant_secrets`（加密後）

若 ArangoDB 不可用，會退回 in-memory（僅供開發/測試）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.genai_tenant_policy import GenAITenantPolicy, GenAITenantPolicyUpdate
from services.api.services.genai_secret_encryption_service import (
    GenAISecretEncryptionService,
    get_genai_secret_encryption_service,
)

logger = structlog.get_logger(__name__)

TENANT_POLICY_COLLECTION = "genai_tenant_policies"
TENANT_SECRET_COLLECTION = "genai_tenant_secrets"


class GenAITenantPolicyService:
    """GenAI 租戶政策與租戶級 secrets 管理"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        encryption: Optional[GenAISecretEncryptionService] = None,
    ):
        self._logger = logger
        self._encryption = encryption or get_genai_secret_encryption_service()

        self._client = client
        self._policy_mem: Dict[str, Dict[str, Any]] = {}
        self._secret_mem: Dict[str, Dict[str, str]] = {}

        try:
            self._client = self._client or ArangoDBClient()
            if self._client.db is None:
                raise RuntimeError("ArangoDB client is not connected")

            if not self._client.db.has_collection(TENANT_POLICY_COLLECTION):
                self._client.db.create_collection(TENANT_POLICY_COLLECTION)
            if not self._client.db.has_collection(TENANT_SECRET_COLLECTION):
                self._client.db.create_collection(TENANT_SECRET_COLLECTION)

            self._policy_collection = ArangoCollection(
                self._client.db.collection(TENANT_POLICY_COLLECTION)
            )
            self._secret_collection = ArangoCollection(
                self._client.db.collection(TENANT_SECRET_COLLECTION)
            )
            self._use_db = True
        except Exception as exc:
            self._use_db = False
            self._logger.warning("tenant_policy_service_db_disabled", error=str(exc))

    def get_policy(self, tenant_id: str) -> Optional[GenAITenantPolicy]:
        doc = self._get_policy_doc(tenant_id=tenant_id)
        if not doc:
            return None
        return GenAITenantPolicy(
            tenant_id=tenant_id,
            allowed_providers=list(doc.get("allowed_providers") or []),
            allowed_models=dict(doc.get("allowed_models") or {}),
            default_fallback=doc.get("default_fallback"),
            model_registry_models=list(doc.get("model_registry_models") or []),
            updated_at=datetime.fromisoformat(doc.get("updated_at") or datetime.utcnow().isoformat()) if doc.get("updated_at") else datetime.utcnow(),  # type: ignore[arg-type]  # 已確保為 str 或使用默認值
        )

    def upsert_policy(self, tenant_id: str, update: GenAITenantPolicyUpdate) -> GenAITenantPolicy:
        now = datetime.utcnow().isoformat()
        payload: Dict[str, Any] = {
            "_key": tenant_id,
            "tenant_id": tenant_id,
            "updated_at": now,
        }
        if update.allowed_providers is not None:
            payload["allowed_providers"] = update.allowed_providers
        if update.allowed_models is not None:
            payload["allowed_models"] = update.allowed_models
        if update.default_fallback is not None:
            payload["default_fallback"] = update.default_fallback
        if update.model_registry_models is not None:
            payload["model_registry_models"] = update.model_registry_models

        if self._use_db:
            existing = self._policy_collection.get(tenant_id)
            if existing:
                payload["_key"] = existing.get("_key", tenant_id)
                result = self._policy_collection.update(payload)
                doc = result.get("new") or payload
            else:
                result = self._policy_collection.insert(payload)
                doc = result.get("new") or payload
        else:
            existing = self._policy_mem.get(tenant_id) or {}
            existing.update(payload)
            self._policy_mem[tenant_id] = existing
            doc = existing

        return GenAITenantPolicy(
            tenant_id=tenant_id,
            allowed_providers=list(doc.get("allowed_providers") or []),
            allowed_models=dict(doc.get("allowed_models") or {}),
            default_fallback=doc.get("default_fallback"),
            model_registry_models=list(doc.get("model_registry_models") or []),
            updated_at=datetime.fromisoformat(doc.get("updated_at") or datetime.utcnow().isoformat()) if doc.get("updated_at") else datetime.utcnow(),  # type: ignore[arg-type]  # 已確保為 str 或使用默認值
        )

    def set_tenant_secret(self, tenant_id: str, provider: str, api_key: str) -> None:
        provider_key = provider.strip().lower()
        encrypted = self._encryption.encrypt_to_b64(api_key)
        now = datetime.utcnow().isoformat()
        doc_key = f"{tenant_id}_{provider_key}"
        payload = {
            "_key": doc_key,
            "tenant_id": tenant_id,
            "provider": provider_key,
            "encrypted_api_key": encrypted,
            "updated_at": now,
        }

        if self._use_db:
            existing = self._secret_collection.get(doc_key)
            if existing:
                payload["_key"] = existing.get("_key", doc_key)
                self._secret_collection.update(payload)
            else:
                self._secret_collection.insert(payload)
        else:
            tenant_map = self._secret_mem.get(tenant_id) or {}
            tenant_map[provider_key] = encrypted
            self._secret_mem[tenant_id] = tenant_map

    def delete_tenant_secret(self, tenant_id: str, provider: str) -> None:
        provider_key = provider.strip().lower()
        doc_key = f"{tenant_id}_{provider_key}"
        if self._use_db:
            existing = self._secret_collection.get(doc_key)
            if existing:
                self._secret_collection.delete(doc_key)
        else:
            tenant_map = self._secret_mem.get(tenant_id) or {}
            tenant_map.pop(provider_key, None)
            self._secret_mem[tenant_id] = tenant_map

    def get_tenant_api_key(self, tenant_id: str, provider: str) -> Optional[str]:
        provider_key = provider.strip().lower()
        if self._use_db:
            doc_key = f"{tenant_id}_{provider_key}"
            doc = self._secret_collection.get(doc_key)
            if not doc:
                return None
            payload = doc.get("encrypted_api_key")
            if not isinstance(payload, str) or not payload:
                return None
            return self._encryption.decrypt_from_b64(payload)

        tenant_map = self._secret_mem.get(tenant_id) or {}
        payload = tenant_map.get(provider_key)
        if not payload:
            return None
        return self._encryption.decrypt_from_b64(payload)

    def _get_policy_doc(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        if self._use_db:
            return self._policy_collection.get(tenant_id)
        return self._policy_mem.get(tenant_id)


_service: Optional[GenAITenantPolicyService] = None


def get_genai_tenant_policy_service() -> GenAITenantPolicyService:
    global _service
    if _service is None:
        _service = GenAITenantPolicyService()
    return _service
