# 代碼功能說明: LLM 模型服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""LLM 模型服務 - 實現 ArangoDB CRUD 操作"""

from datetime import datetime
from typing import Dict, List, Optional

import httpx
import structlog

from api.core.settings import get_ollama_settings
from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.llm_model import (
    LLMModel,
    LLMModelCreate,
    LLMModelQuery,
    LLMModelUpdate,
    LLMProvider,
    ModelCapability,
    ModelStatus,
)

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "llm_models"


class LLMModelService:
    """LLM 模型服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 LLM 模型服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
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
            collection.add_index({"type": "persistent", "fields": ["model_id"], "unique": True})
            collection.add_index({"type": "persistent", "fields": ["provider"]})
            collection.add_index({"type": "persistent", "fields": ["status"]})
            collection.add_index({"type": "persistent", "fields": ["capabilities[*]"]})
            collection.add_index({"type": "persistent", "fields": ["order"]})
            collection.add_index({"type": "persistent", "fields": ["is_default"]})
            self.logger.info("collection_created", collection=COLLECTION_NAME)

    def _get_collection(self) -> ArangoCollection:
        """獲取集合封裝對象"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        return ArangoCollection(collection)

    def _document_to_model(self, doc: Dict) -> LLMModel:
        """將 ArangoDB 文檔轉換為 LLMModel 對象"""
        # 轉換 capabilities 列表
        capabilities = []
        if "capabilities" in doc:
            for cap in doc["capabilities"]:
                try:
                    capabilities.append(ModelCapability(cap))
                except ValueError:
                    # 忽略無效的 capability
                    pass

        return LLMModel(
            key=doc["_key"],
            id=doc.get("_id"),
            rev=doc.get("_rev"),
            model_id=doc["model_id"],
            name=doc["name"],
            provider=LLMProvider(doc["provider"]),
            description=doc.get("description"),
            capabilities=capabilities,
            status=ModelStatus(doc.get("status", "active")),
            context_window=doc.get("context_window"),
            max_output_tokens=doc.get("max_output_tokens"),
            parameters=doc.get("parameters"),
            release_date=doc.get("release_date"),
            license=doc.get("license"),
            languages=doc.get("languages", ["en", "zh"]),
            icon=doc.get("icon"),
            color=doc.get("color"),
            order=doc.get("order", 0),
            is_default=doc.get("is_default", False),
            metadata=doc.get("metadata", {}),
            source=doc.get("source", "database"),
            ollama_endpoint=doc.get("ollama_endpoint"),
            ollama_node=doc.get("ollama_node"),
            is_favorite=doc.get("is_favorite"),  # 查詢時可能設置
            created_at=(
                datetime.fromisoformat(doc["created_at"])
                if doc.get("created_at")
                else datetime.now()
            ),
            updated_at=(
                datetime.fromisoformat(doc["updated_at"])
                if doc.get("updated_at")
                else datetime.now()
            ),
        )

    def create(self, model: LLMModelCreate) -> LLMModel:
        """
        創建 LLM 模型

        Args:
            model: 模型創建請求

        Returns:
            創建的模型對象
        """
        collection = self._get_collection()

        # 檢查 model_id 是否已存在
        existing = collection.find({"model_id": model.model_id}, limit=1)
        if existing:
            raise ValueError(f"Model with model_id '{model.model_id}' already exists")

        now = datetime.now().isoformat()  # 轉換為 ISO 8601 字符串格式
        doc = {
            "_key": model.model_id,  # 使用 model_id 作為 _key
            "model_id": model.model_id,
            "name": model.name,
            "provider": model.provider.value,
            "description": model.description,
            "capabilities": [cap.value for cap in model.capabilities],
            "status": model.status.value,
            "context_window": model.context_window,
            "max_output_tokens": model.max_output_tokens,
            "parameters": model.parameters,
            "release_date": model.release_date,
            "license": model.license,
            "languages": model.languages,
            "icon": model.icon,
            "color": model.color,
            "order": model.order,
            "is_default": model.is_default,
            "metadata": model.metadata,
            "source": model.source or "database",
            "ollama_endpoint": model.ollama_endpoint,
            "ollama_node": model.ollama_node,
            "created_at": now,
            "updated_at": now,
        }

        collection.insert(doc)
        self.logger.info("model_created", model_id=model.model_id)

        return self.get_by_id(model.model_id)

    def get_by_id(self, model_id: str) -> Optional[LLMModel]:
        """
        根據 model_id 獲取模型

        Args:
            model_id: 模型 ID

        Returns:
            模型對象或 None
        """
        collection = self._get_collection()
        doc = collection.get(model_id)
        if not doc:
            return None
        return self._document_to_model(doc)

    def get_all(
        self,
        query: Optional[LLMModelQuery] = None,
    ) -> List[LLMModel]:
        """
        獲取所有模型（支持篩選和排序）

        Args:
            query: 查詢參數

        Returns:
            模型列表
        """
        collection = self._get_collection()
        filters: Dict = {}

        if query:
            if query.provider:
                filters["provider"] = query.provider.value
            if query.status:
                filters["status"] = query.status.value
            if query.capability:
                filters["capabilities"] = query.capability.value

        # 執行查詢
        docs = collection.find(filters=filters if filters else None, sort=["order", "name"])

        # 如果有搜索關鍵詞，在應用層過濾
        if query and query.search:
            search_lower = query.search.lower()
            docs = [
                doc
                for doc in docs
                if search_lower in doc.get("name", "").lower()
                or search_lower in doc.get("description", "").lower()
            ]

        # 應用 limit 和 offset
        if query:
            if query.offset > 0:
                docs = docs[query.offset :]
            if query.limit < len(docs):
                docs = docs[: query.limit]

        return [self._document_to_model(doc) for doc in docs]

    def update(self, model_id: str, update: LLMModelUpdate) -> Optional[LLMModel]:
        """
        更新模型

        Args:
            model_id: 模型 ID
            update: 更新請求

        Returns:
            更新後的模型對象或 None
        """
        collection = self._get_collection()
        doc = collection.get(model_id)
        if not doc:
            return None

        # 構建更新文檔
        update_doc: Dict = {"_key": model_id, "updated_at": datetime.now().isoformat()}

        if update.name is not None:
            update_doc["name"] = update.name
        if update.description is not None:
            update_doc["description"] = update.description
        if update.capabilities is not None:
            update_doc["capabilities"] = [cap.value for cap in update.capabilities]
        if update.status is not None:
            update_doc["status"] = update.status.value
        if update.context_window is not None:
            update_doc["context_window"] = update.context_window
        if update.max_output_tokens is not None:
            update_doc["max_output_tokens"] = update.max_output_tokens
        if update.parameters is not None:
            update_doc["parameters"] = update.parameters
        if update.release_date is not None:
            update_doc["release_date"] = update.release_date
        if update.license is not None:
            update_doc["license"] = update.license
        if update.languages is not None:
            update_doc["languages"] = update.languages
        if update.icon is not None:
            update_doc["icon"] = update.icon
        if update.color is not None:
            update_doc["color"] = update.color
        if update.order is not None:
            update_doc["order"] = update.order
        if update.is_default is not None:
            update_doc["is_default"] = update.is_default
        if update.metadata is not None:
            update_doc["metadata"] = update.metadata
        if update.source is not None:
            update_doc["source"] = update.source
        if update.ollama_endpoint is not None:
            update_doc["ollama_endpoint"] = update.ollama_endpoint
        if update.ollama_node is not None:
            update_doc["ollama_node"] = update.ollama_node

        collection.update(update_doc, merge=True)
        self.logger.info("model_updated", model_id=model_id)

        return self.get_by_id(model_id)

    def delete(self, model_id: str) -> bool:
        """
        刪除模型

        Args:
            model_id: 模型 ID

        Returns:
            是否成功刪除
        """
        collection = self._get_collection()
        doc = collection.get(model_id)
        if not doc:
            return False

        collection.delete(model_id)
        self.logger.info("model_deleted", model_id=model_id)
        return True

    def get_by_provider(
        self, provider: LLMProvider, status: Optional[ModelStatus] = None
    ) -> List[LLMModel]:
        """
        根據提供商獲取模型列表

        Args:
            provider: 提供商
            status: 狀態篩選（可選）

        Returns:
            模型列表
        """
        query = LLMModelQuery(provider=provider, status=status, limit=1000)
        return self.get_all(query)

    async def discover_ollama_models(self) -> List[LLMModel]:
        """
        動態發現所有 Ollama 節點的可用模型

        Returns:
            發現的模型列表
        """
        settings = get_ollama_settings()
        discovered_models: List[LLMModel] = []
        seen_models: set[str] = set()  # 使用 model_name 去重（跨節點）

        async with httpx.AsyncClient(timeout=10.0) as client:
            for node in settings.nodes:
                base_url = f"{settings.scheme}://{node.host}:{node.port}"
                try:
                    # 嘗試調用 Ollama /api/tags 端點（原生 Ollama API）
                    try:
                        response = await client.get(f"{base_url}/api/tags", timeout=10.0)
                        response.raise_for_status()
                        data = response.json()
                        models = data.get("models", [])
                    except Exception as e1:
                        # 如果失敗，嘗試 OpenAI 兼容格式 /v1/models
                        try:
                            response = await client.get(f"{base_url}/v1/models", timeout=10.0)
                            response.raise_for_status()
                            data = response.json()
                            # OpenAI 格式: {"object": "list", "data": [{"id": "...", ...}]}
                            models_data = data.get("data", [])
                            models = []
                            for model_item in models_data:
                                # 轉換為 Ollama 格式
                                models.append(
                                    {
                                        "name": model_item.get("id", ""),
                                        "size": None,
                                        "modified_at": model_item.get("created"),
                                    }
                                )
                        except Exception as e2:
                            # 兩種格式都失敗，記錄錯誤並跳過
                            self.logger.warning(
                                "ollama_discovery_failed",
                                node=node.name,
                                endpoint=base_url,
                                error=f"Both /api/tags ({e1}) and /v1/models ({e2}) failed",
                            )
                            continue

                    for model_info in models:
                        if not isinstance(model_info, dict):
                            continue

                        # 獲取模型名稱（兩種格式都使用 "name" 字段）
                        model_name = model_info.get("name", "")
                        if not model_name:
                            continue

                        # 構建唯一的 model_id（包含節點信息）
                        model_id = f"ollama:{node.host}:{node.port}:{model_name}"

                        # 判斷能力
                        capabilities = [ModelCapability.CHAT]
                        model_name_lower = model_name.lower()
                        if "vl" in model_name_lower or "vision" in model_name_lower:
                            capabilities.append(ModelCapability.VISION)
                        if "embed" in model_name_lower:
                            capabilities.append(ModelCapability.EMBEDDING)
                        if "code" in model_name_lower or "coder" in model_name_lower:
                            capabilities.append(ModelCapability.CODE)

                        # 構建顯示名稱
                        display_name = f"{model_name}"
                        if len(settings.nodes) > 1:
                            display_name = f"{model_name} ({node.host}:{node.port})"

                        now = datetime.now()
                        model = LLMModel(
                            key=model_id,
                            model_id=model_id,
                            name=display_name,
                            provider=LLMProvider.OLLAMA,
                            description=f"Ollama model from {node.host}:{node.port}",
                            capabilities=capabilities,
                            status=ModelStatus.ACTIVE,
                            source="ollama_discovered",
                            ollama_endpoint=base_url,
                            ollama_node=f"{node.host}:{node.port}",
                            metadata={
                                "ollama_model_name": model_name,
                                "node_name": node.name,
                                "model_size": model_info.get("size"),
                                "modified_at": model_info.get("modified_at"),
                            },
                            created_at=now,
                            updated_at=now,
                        )
                        discovered_models.append(model)
                        seen_models.add(model_name)

                except Exception as e:
                    self.logger.warning(
                        "ollama_discovery_failed",
                        node=node.name,
                        endpoint=base_url,
                        error=str(e),
                    )

        return discovered_models

    async def get_all_with_discovery(
        self,
        query: Optional[LLMModelQuery] = None,
        user_id: Optional[str] = None,
        include_favorite_status: bool = False,
        include_discovered: bool = True,
    ) -> List[LLMModel]:
        """
        獲取所有模型（包括數據庫模型和動態發現的 Ollama 模型）

        Args:
            query: 查詢參數
            user_id: 用戶ID（用於標記收藏狀態）
            include_favorite_status: 是否包含收藏狀態
            include_discovered: 是否包含動態發現的模型

        Returns:
            合併後的模型列表
        """
        # 1. 從數據庫獲取模型
        db_models = self.get_all(query)

        # 2. 動態發現 Ollama 模型（如果需要）
        discovered_models: List[LLMModel] = []
        if include_discovered:
            try:
                discovered_models = await self.discover_ollama_models()

                # 如果查詢指定了 provider，過濾發現的模型
                if query and query.provider:
                    if query.provider == LLMProvider.OLLAMA:
                        # 只返回發現的模型（已經過濾了 db_models）
                        all_models = discovered_models
                    else:
                        # 只返回數據庫模型
                        all_models = db_models
                else:
                    # 合併並去重（數據庫優先，相同的 model_id 保留數據庫版本）
                    db_model_ids = {m.model_id for m in db_models}
                    filtered_discovered = [
                        m for m in discovered_models if m.model_id not in db_model_ids
                    ]
                    all_models = list(db_models) + filtered_discovered
            except Exception as e:
                self.logger.warning("ollama_discovery_error", error=str(e))
                # 發現失敗時，只返回數據庫模型
                all_models = db_models
        else:
            all_models = db_models

        # 3. 如果請求用戶收藏狀態，標記收藏的模型
        if include_favorite_status and user_id:
            try:
                from services.api.services.user_preference_service import (
                    get_user_preference_service,
                )

                pref_service = get_user_preference_service()
                favorite_ids = set(pref_service.get_favorite_models(user_id=user_id))

                # 為每個模型標記收藏狀態
                for i, model in enumerate(all_models):
                    is_favorite = False

                    # 檢查完整 model_id
                    if model.model_id in favorite_ids:
                        is_favorite = True
                    # 對於 Ollama 模型，檢查簡化的 model_name
                    elif model.source == "ollama_discovered" and model.metadata.get(
                        "ollama_model_name"
                    ):
                        ollama_name = model.metadata.get("ollama_model_name")
                        if ollama_name in favorite_ids:
                            is_favorite = True
                        # 支持模糊匹配（例如用戶收藏 "llama3.1:8b"，匹配 "ollama:*:llama3.1:8b"）
                        else:
                            for fav_id in favorite_ids:
                                if fav_id in model.model_id or model.model_id.endswith(
                                    f":{fav_id}"
                                ):
                                    is_favorite = True
                                    break

                    # 直接設置模型的 is_favorite 屬性（Pydantic 允許設置可選字段）
                    if is_favorite:
                        # 使用 model_copy 更新（Pydantic v2）
                        try:
                            all_models[i] = model.model_copy(update={"is_favorite": True})
                        except (AttributeError, TypeError):
                            # Fallback: 直接設置屬性（如果模型允許）
                            model.is_favorite = True
                            all_models[i] = model

            except Exception as e:
                self.logger.warning("favorite_status_error", user_id=user_id, error=str(e))

        # 4. 標記模型的 Active 狀態（根據 Provider API Key 配置）
        try:
            from services.api.services.llm_provider_config_service import (
                get_llm_provider_config_service,
            )

            config_service = get_llm_provider_config_service()
            # 緩存每個 provider 的 API key 狀態
            provider_status_cache: Dict[LLMProvider, bool] = {}

            for i, model in enumerate(all_models):
                is_active = True  # 默認為 True

                # 對於需要 API key 的 provider，檢查是否已配置
                # 注意：檢查 provider 是否為 AUTO（自動選擇）或 OLLAMA（本地模型，不需要 API key）
                if model.provider not in (LLMProvider.AUTO, LLMProvider.OLLAMA):
                    # 檢查緩存
                    if model.provider not in provider_status_cache:
                        status_obj = config_service.get_status(model.provider)
                        provider_status_cache[model.provider] = (
                            status_obj.has_api_key if status_obj else False
                        )

                    is_active = provider_status_cache[model.provider]
                # Ollama 模型默認可用（不需要 API key）
                elif model.provider == LLMProvider.OLLAMA:
                    is_active = True
                # Auto 模型默認可用
                elif model.provider == LLMProvider.AUTO:
                    is_active = True

                # 同時考慮模型的 status 字段
                if model.status != ModelStatus.ACTIVE:
                    is_active = False

                # 更新模型的 is_active 字段
                try:
                    all_models[i] = model.model_copy(update={"is_active": is_active})
                except (AttributeError, TypeError):
                    # Fallback: 直接設置屬性
                    model.is_active = is_active
                    all_models[i] = model

        except Exception as e:
            self.logger.warning("active_status_error", error=str(e))

        return all_models


def get_llm_model_service(client: Optional[ArangoDBClient] = None) -> LLMModelService:
    """
    獲取 LLM 模型服務實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        LLMModelService 實例
    """
    return LLMModelService(client=client)
