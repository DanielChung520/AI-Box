# 代碼功能說明: GenAI 使用者 LLM Secrets（API Key）管理服務
# 創建日期: 2025-12-13 23:34:17 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 23:34:17 (UTC+8)

"""GenAI user LLM secrets service.

- 敏感資訊（provider API key）存於 ArangoDB collection `genai_user_llm_secrets`（加密）
- 以 tenant_id + user_id + provider 做隔離

若 ArangoDB 不可用，會退回 in-memory（僅供開發/測試）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Set

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.services.genai_secret_encryption_service import (
    GenAISecretEncryptionService,
    get_genai_secret_encryption_service,
)

logger = structlog.get_logger(__name__)

USER_SECRET_COLLECTION = "genai_user_llm_secrets"


class GenAIUserLLMSecretService:
    """GenAI 使用者 LLM API key 管理"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        encryption: Optional[GenAISecretEncryptionService] = None,
    ):
        self._logger = logger
        self._encryption = encryption or get_genai_secret_encryption_service()

        self._client = client
        self._mem: Dict[str, str] = {}

        try:
            self._client = self._client or ArangoDBClient()
            if self._client.db is None:
                raise RuntimeError("ArangoDB client is not connected")
            if not self._client.db.has_collection(USER_SECRET_COLLECTION):
                self._client.db.create_collection(USER_SECRET_COLLECTION)

            self._collection = ArangoCollection(self._client.db.collection(USER_SECRET_COLLECTION))
            self._use_db = True
        except Exception as exc:
            self._use_db = False
            self._logger.warning("user_llm_secret_service_db_disabled", error=str(exc))

    def upsert(self, tenant_id: str, user_id: str, provider: str, api_key: str) -> None:
        provider_key = provider.strip().lower()
        key = self._doc_key(tenant_id=tenant_id, user_id=user_id, provider=provider_key)
        encrypted = self._encryption.encrypt_to_b64(api_key)
        now = datetime.utcnow().isoformat()
        doc = {
            "_key": key,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "provider": provider_key,
            "encrypted_api_key": encrypted,
            "updated_at": now,
        }

        if self._use_db:
            existing = self._collection.get(key)
            if existing:
                doc["_key"] = existing.get("_key", key)
                self._collection.update(doc)
            else:
                self._collection.insert(doc)
        else:
            self._mem[key] = encrypted

    def delete(self, tenant_id: str, user_id: str, provider: str) -> None:
        provider_key = provider.strip().lower()
        key = self._doc_key(tenant_id=tenant_id, user_id=user_id, provider=provider_key)
        if self._use_db:
            existing = self._collection.get(key)
            if existing:
                self._collection.delete(key)
        else:
            self._mem.pop(key, None)

    def get_api_key(self, tenant_id: str, user_id: str, provider: str) -> Optional[str]:
        provider_key = provider.strip().lower()
        key = self._doc_key(tenant_id=tenant_id, user_id=user_id, provider=provider_key)

        if self._use_db:
            doc = self._collection.get(key)
            if not doc:
                return None
            payload = doc.get("encrypted_api_key")
            if not isinstance(payload, str) or not payload:
                return None
            return self._encryption.decrypt_from_b64(payload)

        payload = self._mem.get(key)
        if not payload:
            return None
        return self._encryption.decrypt_from_b64(payload)

    def list_configured_providers(self, tenant_id: str, user_id: str) -> Set[str]:
        if self._use_db:
            if self._client is None or self._client.db is None or self._client.db.aql is None:
                return set()
            query = """
            FOR doc IN @@collection
                FILTER doc.tenant_id == @tenant_id AND doc.user_id == @user_id
                RETURN doc.provider
            """
            bind_vars = {
                "@collection": USER_SECRET_COLLECTION,
                "tenant_id": tenant_id,
                "user_id": user_id,
            }
            cursor = self._client.db.aql.execute(query, bind_vars=bind_vars)  # type: ignore[arg-type]  # bind_vars 類型兼容
            return {str(p) for p in cursor}

        prefix = f"{tenant_id}_{user_id}_"
        providers = set()
        for k in self._mem.keys():
            if k.startswith(prefix):
                providers.add(k[len(prefix) :])
        return providers

    def _doc_key(self, *, tenant_id: str, user_id: str, provider: str) -> str:
        safe_tenant = tenant_id.replace(":", "_").replace("/", "_")
        safe_user = user_id.replace(":", "_").replace("/", "_")
        safe_provider = provider.replace(":", "_").replace("/", "_")
        return f"{safe_tenant}_{safe_user}_{safe_provider}"


_service: Optional[GenAIUserLLMSecretService] = None


def get_genai_user_llm_secret_service() -> GenAIUserLLMSecretService:
    global _service
    if _service is None:
        _service = GenAIUserLLMSecretService()
    return _service
