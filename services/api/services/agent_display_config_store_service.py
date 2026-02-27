# 代碼功能說明: Agent Display Config 存儲服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-14 21:41 UTC+8

"""Agent Display Config 存儲服務

提供前端代理展示區配置的存儲服務，支持分類和代理的展示配置管理。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.agent_display_config import (
    AgentConfig,
    AgentDisplayConfigModel,
    CategoryConfig,
)

logger = structlog.get_logger(__name__)

AGENT_DISPLAY_CONFIGS_COLLECTION = "agent_display_configs"


def _generate_config_key(
    config_type: str,
    category_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> str:
    """生成配置的 _key"""
    if config_type == "category":
        if tenant_id:
            return f"{tenant_id}_{category_id}"
        return category_id or ""
    elif config_type == "agent":
        if tenant_id:
            return f"{tenant_id}_{agent_id}"
        return agent_id or ""
    return ""


def _document_to_model(doc: Dict[str, Any]) -> AgentDisplayConfigModel:
    """將 ArangoDB document 轉換為 AgentDisplayConfigModel"""
    return AgentDisplayConfigModel(
        key=doc.get("_key", ""),
        tenant_id=doc.get("tenant_id"),
        config_type=doc.get("config_type", ""),
        category_id=doc.get("category_id"),
        agent_id=doc.get("agent_id"),
        category_config=(
            CategoryConfig(**doc["category_config"]) if doc.get("category_config") else None
        ),
        agent_config=AgentConfig(**doc["agent_config"]) if doc.get("agent_config") else None,
        is_active=doc.get("is_active", True),
        created_at=doc.get("created_at", ""),
        updated_at=doc.get("updated_at", ""),
        created_by=doc.get("created_by"),
        updated_by=doc.get("updated_by"),
    )


class AgentDisplayConfigStoreService:
    """代理展示配置存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Agent Display Config Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(AGENT_DISPLAY_CONFIGS_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(AGENT_DISPLAY_CONFIGS_COLLECTION)

        # 創建索引
        indexes = collection.indexes()
        existing_index_fields = {
            (
                tuple(idx.get("fields", []))
                if isinstance(idx.get("fields"), list)
                else idx.get("fields")
            )
            for idx in indexes
        }

        # 租戶 + 配置類型索引
        tenant_type_fields = ("tenant_id", "config_type", "is_active")
        if tenant_type_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "config_type", "is_active"],
                    "name": "idx_agent_display_configs_tenant_type_active",
                }
            )

        # 分類查詢索引
        category_fields = ("tenant_id", "config_type", "category_id", "is_active")
        if category_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "config_type", "category_id", "is_active"],
                    "name": "idx_agent_display_configs_category",
                }
            )

        # 代理查詢索引
        agent_fields = ("tenant_id", "config_type", "agent_id", "is_active")
        if agent_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "config_type", "agent_id", "is_active"],
                    "name": "idx_agent_display_configs_agent",
                }
            )

    def get_categories(
        self, tenant_id: Optional[str] = None, include_inactive: bool = False
    ) -> List[CategoryConfig]:
        """
        獲取分類列表（按顯示順序排序）

        Args:
            tenant_id: 租戶 ID（可選，None 表示系統級）
            include_inactive: 是否包含未啟用的配置

        Returns:
            分類列表（按 display_order 排序）
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        filters = {"config_type": "category"}
        if tenant_id is not None:
            filters["tenant_id"] = tenant_id
        else:
            filters["tenant_id"] = None

        if not include_inactive:
            filters["is_active"] = True

        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.tenant_id == @tenant_id
        AND (@include_inactive OR doc.is_active == true)
        RETURN doc
        """
        bind_vars = {
            "config_type": "category",
            "tenant_id": tenant_id,
            "include_inactive": include_inactive,
        }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            categories = []
            for doc in cursor:
                if doc.get("category_config"):
                    categories.append(CategoryConfig(**doc["category_config"]))

            # 按 display_order 排序
            categories.sort(key=lambda x: x.display_order)
            return categories
        except Exception as exc:
            self._logger.error(
                "get_categories_failed",
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_agents_by_category(
        self,
        category_id: str,
        tenant_id: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[AgentConfig]:
        """
        獲取指定分類下的代理列表（按顯示順序排序）

        Args:
            category_id: 分類 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）
            include_inactive: 是否包含未啟用的配置

        Returns:
            代理列表（按 display_order 排序）
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.category_id == @category_id
        AND doc.tenant_id == @tenant_id
        AND (@include_inactive OR doc.is_active == true)
        RETURN doc
        """
        bind_vars = {
            "config_type": "agent",
            "category_id": category_id,
            "tenant_id": tenant_id,
            "include_inactive": include_inactive,
        }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            agents = []
            for doc in cursor:
                if doc.get("agent_config"):
                    agents.append(AgentConfig(**doc["agent_config"]))

            # 按 display_order 排序
            agents.sort(key=lambda x: x.display_order)
            return agents
        except Exception as exc:
            self._logger.error(
                "get_agents_by_category_failed",
                category_id=category_id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def list_all_agent_configs(
        self, tenant_id: Optional[str] = None, include_inactive: bool = False
    ) -> List[AgentDisplayConfigModel]:
        """
        列出所有 agent 類型的展示配置（不分分類）

        Args:
            tenant_id: 租戶 ID（None 表示系統級）
            include_inactive: 是否包含未啟用的配置

        Returns:
            AgentDisplayConfigModel 列表（僅包含 config_type = 'agent'）
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.tenant_id == @tenant_id
        AND (@include_inactive OR doc.is_active == true)
        RETURN doc
        """
        bind_vars = {
            "config_type": "agent",
            "tenant_id": tenant_id,
            "include_inactive": include_inactive,
        }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            results: List[AgentDisplayConfigModel] = []
            for doc in cursor:
                results.append(AgentDisplayConfigModel(**doc))
            return results
        except Exception as exc:
            self._logger.error(
                "list_all_agent_configs_failed",
                tenant_id=tenant_id,
                include_inactive=include_inactive,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_all_display_config(
        self, tenant_id: Optional[str] = None, include_inactive: bool = False
    ) -> Dict[str, Any]:
        """
        獲取完整的展示配置（分類 + 代理）

        優化：使用單次查詢獲取所有 agents，避免 N+1 查詢問題

        Args:
            tenant_id: 租戶 ID（可選，None 表示系統級）
            include_inactive: 是否包含未啟用的配置

        Returns:
            完整的展示配置字典
            {
                "categories": [
                    {
                        "id": "human-resource",
                        "name": {...},
                        "agents": [...]
                    }
                ]
            }
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 獲取所有 categories（1 次查詢）
        categories = self.get_categories(tenant_id=tenant_id, include_inactive=include_inactive)

        # 優化：一次性獲取所有 agents（1 次查詢），避免 N+1 問題
        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.tenant_id == @tenant_id
        AND (@include_inactive OR doc.is_active == true)
        RETURN doc
        """
        bind_vars = {
            "config_type": "agent",
            "tenant_id": tenant_id,
            "include_inactive": include_inactive,
        }

        try:
            # 執行單次查詢獲取所有 agents
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            all_agents = []
            for doc in cursor:
                if doc.get("agent_config"):
                    agent = AgentConfig(**doc["agent_config"])
                    # 添加 arangodb_key 到 agent 對象
                    agent.arangodb_key = doc.get("_key")
                    all_agents.append(agent)

            # 按 category_id 分組 agents
            agents_by_category: Dict[str, List[AgentConfig]] = {}
            for agent in all_agents:
                category_id = agent.category_id
                if category_id not in agents_by_category:
                    agents_by_category[category_id] = []
                agents_by_category[category_id].append(agent)

            # 對每個 category 的 agents 按 display_order 排序
            for category_id in agents_by_category:
                agents_by_category[category_id].sort(key=lambda x: x.display_order)

            # 構建結果
            result_categories = []
            for category in categories:
                agents = agents_by_category.get(category.id, [])
                result_categories.append(
                    {
                        "id": category.id,
                        "name": category.name.model_dump(),
                        "description": (
                            category.description.model_dump() if category.description else None
                        ),
                        "icon": category.icon,
                        "display_order": category.display_order,
                        "is_visible": category.is_visible,
                        "agents": [agent.model_dump() for agent in agents],
                    }
                )

            return {"categories": result_categories}
        except Exception as exc:
            self._logger.error(
                "get_all_display_config_failed",
                tenant_id=tenant_id,
                include_inactive=include_inactive,
                error=str(exc),
                exc_info=True,
            )
            raise

    def create_category(
        self,
        category_config: CategoryConfig,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """
        創建分類配置

        Args:
            category_config: 分類配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            created_by: 創建人（可選）

        Returns:
            創建的配置 _key
        """
        now = datetime.utcnow().isoformat()
        config_key = _generate_config_key(
            "category", category_id=category_config.id, tenant_id=tenant_id
        )

        doc = {
            "_key": config_key,
            "tenant_id": tenant_id,
            "config_type": "category",
            "category_id": category_config.id,
            "agent_id": None,
            "category_config": category_config.model_dump(),
            "agent_config": None,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": None,
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                "category_config_created",
                category_id=category_config.id,
                tenant_id=tenant_id,
            )
            return config_key
        except Exception as exc:
            self._logger.error(
                "create_category_failed",
                category_id=category_config.id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def update_category(
        self,
        category_id: str,
        category_config: CategoryConfig,
        tenant_id: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        更新分類配置

        Args:
            category_id: 分類 ID
            category_config: 分類配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            updated_by: 更新人（可選）

        Returns:
            是否更新成功
        """
        config_key = _generate_config_key("category", category_id=category_id, tenant_id=tenant_id)
        doc = self._collection.get(config_key)

        if doc is None:
            self._logger.warning(
                "category_config_not_found",
                category_id=category_id,
                tenant_id=tenant_id,
            )
            return False

        now = datetime.utcnow().isoformat()
        update_data = {
            "category_config": category_config.model_dump(),
            "updated_at": now,
            "updated_by": updated_by,
        }

        try:
            self._collection.update(config_key, update_data)
            self._logger.info(
                "category_config_updated",
                category_id=category_id,
                tenant_id=tenant_id,
            )
            return True
        except Exception as exc:
            self._logger.error(
                "update_category_failed",
                category_id=category_id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def create_agent(
        self,
        agent_config: AgentConfig,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """
        創建代理配置

        Args:
            agent_config: 代理配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            created_by: 創建人（可選）

        Returns:
            創建的配置 _key
        """
        now = datetime.utcnow().isoformat()
        config_key = _generate_config_key("agent", agent_id=agent_config.id, tenant_id=tenant_id)

        doc = {
            "_key": config_key,
            "tenant_id": tenant_id,
            "config_type": "agent",
            "category_id": agent_config.category_id,
            "agent_id": agent_config.id,
            "category_config": None,
            "agent_config": agent_config.model_dump(),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": None,
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                "agent_config_created",
                agent_id=agent_config.id,
                tenant_id=tenant_id,
            )
            return config_key
        except Exception as exc:
            self._logger.error(
                "create_agent_failed",
                agent_id=agent_config.id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def update_agent(
        self,
        agent_id: str,
        agent_config: AgentConfig,
        tenant_id: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        更新代理配置

        Args:
            agent_id: 代理 ID
            agent_config: 代理配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            updated_by: 更新人（可選）

        Returns:
            是否更新成功
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 使用 AQL 按 agent_id 查詢（而非 _key）
        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.tenant_id == @tenant_id
        AND doc.agent_config.id == @agent_id
        LIMIT 1
        RETURN doc
        """
        bind_vars = {
            "config_type": "agent",
            "tenant_id": tenant_id,
            "agent_id": agent_id,
        }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            if not docs:
                self._logger.warning(
                    "agent_config_not_found",
                    agent_id=agent_id,
                    tenant_id=tenant_id,
                )
                return False

            doc = docs[0]
            config_key = doc.get("_key")

            now = datetime.utcnow().isoformat()
            update_data = {
                "_key": config_key,
                "agent_config": agent_config.model_dump(),
                "updated_at": now,
                "updated_by": updated_by,
            }

            self._collection.update(update_data)
            self._logger.info(
                "agent_config_updated",
                agent_id=agent_id,
                tenant_id=tenant_id,
            )
            return True
        except Exception as exc:
            self._logger.error(
                "update_agent_failed",
                agent_id=agent_id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def delete_category(self, category_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        刪除分類配置（軟刪除）

        Args:
            category_id: 分類 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            是否刪除成功
        """
        config_key = _generate_config_key("category", category_id=category_id, tenant_id=tenant_id)
        doc = self._collection.get(config_key)

        if doc is None:
            self._logger.warning(
                "category_config_not_found",
                category_id=category_id,
                tenant_id=tenant_id,
            )
            return False

        now = datetime.utcnow().isoformat()
        doc["is_active"] = False
        doc["updated_at"] = now

        try:
            self._collection.update(doc)
            self._logger.info(
                "category_config_deleted",
                category_id=category_id,
                tenant_id=tenant_id,
            )
            return True
        except Exception as exc:
            self._logger.error(
                "delete_category_failed",
                category_id=category_id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def delete_agent(self, agent_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        刪除代理配置（軟刪除）

        Args:
            agent_id: 代理 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            是否刪除成功
        """
        config_key = _generate_config_key("agent", agent_id=agent_id, tenant_id=tenant_id)
        doc = self._collection.get(config_key)

        if doc is None:
            self._logger.warning(
                "agent_config_not_found",
                agent_id=agent_id,
                tenant_id=tenant_id,
            )
            return False

        now = datetime.utcnow().isoformat()
        doc["is_active"] = False
        doc["updated_at"] = now

        try:
            self._collection.update(doc)
            self._logger.info(
                "agent_config_deleted",
                agent_id=agent_id,
                tenant_id=tenant_id,
            )
            return True
        except Exception as exc:
            self._logger.error(
                "delete_agent_failed",
                agent_id=agent_id,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_agent_config(
        self, agent_id: str = None, tenant_id: Optional[str] = None, agent_key: str = None
    ) -> Optional[AgentConfig]:
        """
        獲取單個代理配置

        Args:
            agent_id: 代理 ID (使用 agent_config.id)
            agent_key: ArangoDB _key (唯一標識)
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            代理配置，如果不存在返回 None
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 優先使用 _key 查詢（更安全），其次用 agent_id
        if agent_key:
            aql = """
            FOR doc IN agent_display_configs
            FILTER doc.config_type == @config_type
            AND doc.tenant_id == @tenant_id
            AND doc._key == @agent_key
            AND (@include_inactive OR doc.is_active == true)
            LIMIT 1
            RETURN doc
            """
            bind_vars = {
                "config_type": "agent",
                "tenant_id": tenant_id,
                "agent_key": agent_key,
                "include_inactive": True,
            }
        else:
            aql = """
            FOR doc IN agent_display_configs
            FILTER doc.config_type == @config_type
            AND doc.tenant_id == @tenant_id
            AND doc.agent_config.id == @agent_id
            AND (@include_inactive OR doc.is_active == true)
            LIMIT 1
            RETURN doc
            """
            bind_vars = {
                "config_type": "agent",
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "include_inactive": True,
            }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            if not docs:
                return None

            doc = docs[0]
            if doc.get("agent_config"):
                agent_config = AgentConfig(**doc["agent_config"])
                # 添加 arangodb_key (從父文檔的 _key)
                agent_config.arangodb_key = doc.get("_key")
                return agent_config

            return None
        except Exception as exc:
            self._logger.error(
                "get_agent_config_failed",
                agent_id=agent_id,
                agent_key=agent_key,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_agent_config_by_name(
        self,
        display_name: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[AgentConfig]:
        """
        通過顯示名稱獲取代理配置（支持多語言名稱）

        Args:
            display_name: 代理顯示名稱（如 "經寶物料管理代理"、"mm-agent"）
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            代理配置，如果不存在返回 None
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        # 先嘗試作為 agent_id 查詢
        agent_config = self.get_agent_config(agent_id=display_name, tenant_id=tenant_id)
        if agent_config:
            return agent_config

        # 嘗試通過顯示名稱查詢（支持多語言）
        aql = """
        FOR doc IN agent_display_configs
        FILTER doc.config_type == @config_type
        AND doc.tenant_id == @tenant_id
        AND doc.is_active == true
        AND (
            doc.agent_config.id == @search_name
            OR doc._key == @search_name
            OR doc.agent_config.name.zh_TW == @search_name
            OR doc.agent_config.name.zh_CN == @search_name
            OR doc.agent_config.name.en == @search_name
        )
        LIMIT 1
        RETURN doc
        """
        bind_vars = {
            "config_type": "agent",
            "tenant_id": tenant_id,
            "search_name": display_name,
        }

        try:
            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            if not docs:
                return None

            doc = docs[0]
            if doc.get("agent_config"):
                return AgentConfig(**doc["agent_config"])

            return None
        except Exception as exc:
            self._logger.error(
                "get_agent_config_by_name_failed",
                display_name=display_name,
                tenant_id=tenant_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_category_config(
        self, category_id: str, tenant_id: Optional[str] = None
    ) -> Optional[CategoryConfig]:
        """
        獲取單個分類配置

        Args:
            category_id: 分類 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            分類配置，如果不存在返回 None
        """
        config_key = _generate_config_key("category", category_id=category_id, tenant_id=tenant_id)
        doc = self._collection.get(config_key)

        if doc is None or not doc.get("is_active", True):
            return None

        if doc.get("category_config"):
            return CategoryConfig(**doc["category_config"])

        return None
