# 代碼功能說明: LLM Provider 配置服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24 23:33 UTC+8

"""LLM Provider 配置服務 - 實現 Provider 級別的全局配置管理（API Key 等）"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.llm_model import LLMProvider
from services.api.models.llm_provider_config import (
    LLMProviderConfig,
    LLMProviderConfigCreate,
    LLMProviderModelConfig,
    LLMProviderConfigStatus,
    LLMProviderConfigUpdate,
)
from services.api.services.genai_secret_encryption_service import (
    GenAISecretEncryptionService,
    get_genai_secret_encryption_service,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "llm_provider_configs"

# Provider 預設 Base URL
DEFAULT_BASE_URLS = {
    "chatgpt": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1",
    "grok": "https://api.x.ai/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "chatglm": "https://open.bigmodel.cn/api/paas/v4",
    "volcano": "https://ark.cn-beijing.volces.com/api/v3",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "databricks": "https://workspace.cloud.databricks.com/serving-endpoints",
    "cohere": "https://api.cohere.ai/v1",
    "perplexity": "https://api.perplexity.ai",
}


def get_default_base_url(provider: LLMProvider) -> Optional[str]:
    """獲取 Provider 的預設 Base URL"""
    return DEFAULT_BASE_URLS.get(provider.value)


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
            logger.info(f"collection_created: collection={COLLECTION_NAME}")

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

        # 處理 default_model
        default_model = None
        if doc.get("default_model"):
            model_data = doc["default_model"]
            if isinstance(model_data, dict):
                default_model = LLMProviderModelConfig(**model_data)

        return LLMProviderConfig(
            _key=doc["_key"],
            _id=doc.get("_id"),
            _rev=doc.get("_rev"),
            provider=LLMProvider(doc["provider"]),
            base_url=doc.get("base_url"),
            api_version=doc.get("api_version"),
            timeout=doc.get("timeout"),
            max_retries=doc.get("max_retries"),
            default_model=default_model,
            encrypted_api_key=encrypted_api_key,
            has_api_key=has_api_key,
            metadata=doc.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
            created_by=doc.get("created_by"),
            updated_by=doc.get("updated_by"),
        )

    def create(
        self, config: LLMProviderConfigCreate, user_id: Optional[str] = None
    ) -> LLMProviderConfig:
        """
        創建 Provider 配置

        Args:
            config: 配置創建請求
            user_id: 創建人 ID

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

        # 如果沒有提供 base_url，使用預設值
        base_url = config.base_url or get_default_base_url(config.provider)

        doc = {
            "_key": config.provider.value,
            "provider": config.provider.value,
            "base_url": base_url,
            "api_version": config.api_version,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "encrypted_api_key": encrypted_api_key,
            "default_model": config.default_model.model_dump() if config.default_model else None,
            "metadata": config.metadata,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": user_id,
            "updated_by": user_id,
        }

        collection.insert(doc)
        logger.info(f"provider_config_created: provider={config.provider.value}, user_id={user_id}")

        result = self.get_by_provider(config.provider)
        if result is None:
            raise RuntimeError(f"Failed to retrieve created config for {config.provider}")
        return result

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

    def update(
        self,
        provider: LLMProvider,
        update: LLMProviderConfigUpdate,
        user_id: Optional[str] = None,
    ) -> Optional[LLMProviderConfig]:
        """
        更新配置

        Args:
            provider: Provider
            update: 更新請求
            user_id: 更新人 ID

        Returns:
            更新後的配置對象或 None
        """
        collection = self._get_collection()
        doc = collection.get(provider.value)
        if not doc:
            return None

        # 構建更新文檔
        update_doc: Dict = {
            "_key": provider.value,
            "updated_at": datetime.now().isoformat(),
            "updated_by": user_id,
        }

        if update.base_url is not None:
            update_doc["base_url"] = update.base_url
        if update.api_version is not None:
            update_doc["api_version"] = update.api_version
        if update.timeout is not None:
            update_doc["timeout"] = update.timeout
        if update.max_retries is not None:
            update_doc["max_retries"] = update.max_retries
        if update.default_model is not None:
            update_doc["default_model"] = update.default_model.model_dump()
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
        logger.info(f"provider_config_updated: provider={provider.value}, user_id={user_id}")

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
        logger.info(f"provider_config_deleted: provider={provider.value}")
        return True

    def set_api_key(
        self, provider: LLMProvider, api_key: str, user_id: Optional[str] = None
    ) -> None:
        """
        設置 API key（加密存儲）

        Args:
            provider: Provider
            api_key: API key（明文）
            user_id: 操作人 ID
        """
        update = LLMProviderConfigUpdate(
            api_key=api_key,
            base_url=None,
            api_version=None,
            timeout=None,
            max_retries=None,
            default_model=None,
            metadata=None,
        )
        result = self.update(provider, update, user_id=user_id)
        if not result:
            # 如果配置不存在，創建新配置
            create = LLMProviderConfigCreate(
                provider=provider,
                api_key=api_key,
                base_url=None,
                api_version=None,
                timeout=None,
                max_retries=None,
                default_model=None,
            )
            self.create(create, user_id=user_id)

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
            logger.error(f"api_key_decrypt_failed: provider={provider.value}, error={str(e)}")
            return None

    def delete_api_key(self, provider: LLMProvider, user_id: Optional[str] = None) -> bool:
        """
        刪除 API key

        Args:
            provider: Provider
            user_id: 操作人 ID

        Returns:
            是否成功刪除
        """
        update = LLMProviderConfigUpdate(
            api_key="",
            base_url=None,
            api_version=None,
            timeout=None,
            max_retries=None,
            default_model=None,
            metadata=None,
        )  # 空字符串表示刪除
        result = self.update(provider, update, user_id=user_id)
        return result is not None

    def get_status(self, provider: LLMProvider) -> Optional[LLMProviderConfigStatus]:
        """
        獲取配置狀態（不包含敏感信息）
        如果配置不存在，自動創建包含默認 base_url 的配置

        Args:
            provider: Provider

        Returns:
            配置狀態（如果不存在則自動創建）
        """
        config = self.get_by_provider(provider)
        if not config:
            # 如果配置不存在，自動創建包含默認 base_url 的配置
            default_base_url = get_default_base_url(provider)
            if default_base_url:
                try:
                    create_config = LLMProviderConfigCreate(
                        provider=provider,
                        base_url=default_base_url,
                        api_key=None,  # 不設置 API key
                        api_version=None,
                        timeout=None,
                        max_retries=None,
                        default_model=None,
                    )
                    # 自動創建時 user_id 設為 systemAdmin
                    config = self.create(create_config, user_id="systemAdmin")
                    logger.info(
                        f"auto_created_provider_config: provider={provider.value}, base_url={default_base_url}"
                    )
                except Exception as e:
                    # 如果創建失敗（可能因為並發創建或其他錯誤），重新獲取
                    logger.warning(f"Failed to auto-create config for {provider.value}: {str(e)}")
                    config = self.get_by_provider(provider)
                    if not config:
                        return None

        if not config:
            return None

        return LLMProviderConfigStatus(
            provider=config.provider,
            has_api_key=config.has_api_key,
            base_url=config.base_url,
            default_model=config.default_model,
            created_at=config.created_at,
            updated_at=config.updated_at,
            created_by=config.created_by,
            updated_by=config.updated_by,
        )

    async def verify_provider_config(
        self, provider: LLMProvider, api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        驗證 Provider 配置（測試連通性）

        Args:
            provider: Provider
            api_key: 要測試的 API key（可選，如果提供則測試此 key，否則測試已存儲的 key）

        Returns:
            驗證結果字典
        """
        from llm.clients.factory import LLMClientFactory

        # 如果沒有提供 api_key，嘗試獲取已存儲的 key
        test_key = api_key
        if not test_key:
            test_key = self.get_api_key(provider)

        if not test_key:
            return {"success": False, "message": "未配置 API Key，無法驗證"}

        try:
            # 獲取配置以獲取 base_url 等參數
            config = self.get_by_provider(provider)
            client_kwargs: Dict[str, Any] = {"api_key": test_key}
            if config and config.base_url:
                client_kwargs["base_url"] = config.base_url
            if config and config.api_version:
                client_kwargs["api_version"] = config.api_version

            # 創建客戶端
            client = LLMClientFactory.create_client(provider, use_cache=False, **client_kwargs)

            # 執行連通性測試
            # 大多數客戶端可以通過獲取模型列表或發送一個微型請求來測試
            if hasattr(client, "verify_connectivity"):
                # 如果客戶端實現了專門的驗證方法
                success, message = await client.verify_connectivity()
                return {"success": success, "message": message}
            else:
                # 否則嘗試發送一個簡單的 chat 請求
                try:
                    await client.chat(
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=5,
                    )
                    return {"success": True, "message": "連通性驗證成功"}
                except Exception as e:
                    return {"success": False, "message": f"連通性驗證失敗: {str(e)}"}

        except Exception as e:
            logger.error(f"Failed to verify provider {provider.value}: {str(e)}", exc_info=True)
            return {"success": False, "message": f"驗證過程中出錯: {str(e)}"}


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
