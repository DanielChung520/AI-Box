# 代碼功能說明: LLM Provider 配置服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""LLM Provider 配置服務 - 實現 Provider 級別的全局配置管理（API Key 等）"""

from datetime import datetime
from typing import Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.llm_model import LLMProvider
from services.api.models.llm_provider_config import (
    LLMProviderConfig,
    LLMProviderConfigCreate,
    LLMProviderConfigStatus,
    LLMProviderConfigUpdate,
)
from services.api.services.genai_secret_encryption_service import (
    GenAISecretEncryptionService,
    get_genai_secret_encryption_service,
)

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "llm_provider_configs"


class LLMProviderConfigService:
    """LLM Provider 配置服務"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        encryption: Optional[GenAISecretEncryptionService] = None,
    ):
        """
        初始化 LLM Provider 配置服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
            encryption: 加密服務（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.encryption = encryption or get_genai_secret_encryption_service()
        self.logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保集合存在並創建索引"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["provider"], "unique": True})
            self.logger.info("collection_created", collection=COLLECTION_NAME)

    def _get_collection(self) -> ArangoCollection:
        """獲取集合封裝對象"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        return ArangoCollection(collection)

    def _document_to_config(self, doc: Dict) -> LLMProviderConfig:
        """將 ArangoDB 文檔轉換為 LLMProviderConfig 對象"""
        encrypted_api_key = doc.get("encrypted_api_key")
        has_api_key = bool(encrypted_api_key)

        # 處理 datetime 字符串轉換
        created_at = doc.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.now()

        updated_at = doc.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.now()

        return LLMProviderConfig(
            key=doc["_key"],
            id=doc.get("_id"),
            rev=doc.get("_rev"),
            provider=LLMProvider(doc["provider"]),
            base_url=doc.get("base_url"),
            api_version=doc.get("api_version"),
            timeout=doc.get("timeout"),
            max_retries=doc.get("max_retries"),
            encrypted_api_key=encrypted_api_key,
            has_api_key=has_api_key,
            metadata=doc.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
        )

    def create(self, config: LLMProviderConfigCreate) -> LLMProviderConfig:
        """
        創建 Provider 配置

        Args:
            config: 配置創建請求

        Returns:
            創建的配置對象
        """
        collection = self._get_collection()

        # 檢查 provider 是否已存在
        existing = collection.find({"provider": config.provider.value}, limit=1)
        if existing:
            raise ValueError(f"Provider config for '{config.provider.value}' already exists")

        now = datetime.now()

        # 加密 API key（如果提供）
        encrypted_api_key = None
        if config.api_key:
            encrypted_api_key = self.encryption.encrypt_to_b64(config.api_key)

        doc = {
            "_key": config.provider.value,
            "provider": config.provider.value,
            "base_url": config.base_url,
            "api_version": config.api_version,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "encrypted_api_key": encrypted_api_key,
            "metadata": config.metadata,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        collection.insert(doc)
        self.logger.info("provider_config_created", provider=config.provider.value)

        return self.get_by_provider(config.provider)

    def get_by_provider(self, provider: LLMProvider) -> Optional[LLMProviderConfig]:
        """
        根據 provider 獲取配置

        Args:
            provider: Provider

        Returns:
            配置對象或 None
        """
        collection = self._get_collection()
        doc = collection.get(provider.value)
        if not doc:
            return None
        return self._document_to_config(doc)

    def get_all(self) -> List[LLMProviderConfig]:
        """
        獲取所有 Provider 配置

        Returns:
            配置列表
        """
        collection = self._get_collection()
        docs = collection.find(sort=["provider"])
        return [self._document_to_config(doc) for doc in docs]

    def update(self, provider: LLMProvider, update: LLMProviderConfigUpdate) -> Optional[LLMProviderConfig]:
        """
        更新配置

        Args:
            provider: Provider
            update: 更新請求

        Returns:
            更新後的配置對象或 None
        """
        collection = self._get_collection()
        doc = collection.get(provider.value)
        if not doc:
            return None

        # 構建更新文檔
        update_doc: Dict = {"_key": provider.value, "updated_at": datetime.now().isoformat()}

        if update.base_url is not None:
            update_doc["base_url"] = update.base_url
        if update.api_version is not None:
            update_doc["api_version"] = update.api_version
        if update.timeout is not None:
            update_doc["timeout"] = update.timeout
        if update.max_retries is not None:
            update_doc["max_retries"] = update.max_retries
        if update.metadata is not None:
            update_doc["metadata"] = update.metadata

        # 更新 API key（如果提供）
        if update.api_key is not None:
            if update.api_key:
                # 提供新 key，加密存儲
                update_doc["encrypted_api_key"] = self.encryption.encrypt_to_b64(update.api_key)
            else:
                # 空字符串表示刪除 key
                update_doc["encrypted_api_key"] = None

        collection.update(update_doc, merge=True)
        self.logger.info("provider_config_updated", provider=provider.value)

        return self.get_by_provider(provider)

    def delete(self, provider: LLMProvider) -> bool:
        """
        刪除配置

        Args:
            provider: Provider

        Returns:
            是否成功刪除
        """
        collection = self._get_collection()
        doc = collection.get(provider.value)
        if not doc:
            return False

        collection.delete(provider.value)
        self.logger.info("provider_config_deleted", provider=provider.value)
        return True

    def set_api_key(self, provider: LLMProvider, api_key: str) -> None:
        """
        設置 API key（加密存儲）

        Args:
            provider: Provider
            api_key: API key（明文）
        """
        update = LLMProviderConfigUpdate(api_key=api_key)
        result = self.update(provider, update)
        if not result:
            # 如果配置不存在，創建新配置
            create = LLMProviderConfigCreate(provider=provider, api_key=api_key)
            self.create(create)

    def get_api_key(self, provider: LLMProvider) -> Optional[str]:
        """
        獲取 API key（解密返回）

        Args:
            provider: Provider

        Returns:
            API key（明文）或 None
        """
        config = self.get_by_provider(provider)
        if not config or not config.encrypted_api_key:
            return None

        try:
            return self.encryption.decrypt_from_b64(config.encrypted_api_key)
        except Exception as e:
            self.logger.error("api_key_decrypt_failed", provider=provider.value, error=str(e))
            return None

    def delete_api_key(self, provider: LLMProvider) -> bool:
        """
        刪除 API key

        Args:
            provider: Provider

        Returns:
            是否成功刪除
        """
        update = LLMProviderConfigUpdate(api_key="")  # 空字符串表示刪除
        result = self.update(provider, update)
        return result is not None

    def get_status(self, provider: LLMProvider) -> Optional[LLMProviderConfigStatus]:
        """
        獲取配置狀態（不包含敏感信息）

        Args:
            provider: Provider

        Returns:
            配置狀態或 None
        """
        config = self.get_by_provider(provider)
        if not config:
            return None

        return LLMProviderConfigStatus(
            provider=config.provider,
            has_api_key=config.has_api_key,
            base_url=config.base_url,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


def get_llm_provider_config_service(
    client: Optional[ArangoDBClient] = None,
    encryption: Optional[GenAISecretEncryptionService] = None,
) -> LLMProviderConfigService:
    """
    獲取 LLM Provider 配置服務實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）
        encryption: 加密服務（可選）

    Returns:
        LLMProviderConfigService 實例
    """
    return LLMProviderConfigService(client=client, encryption=encryption)

