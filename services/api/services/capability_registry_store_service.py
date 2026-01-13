# 代碼功能說明: Capability Registry 存儲服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Capability Registry 存儲服務

提供 Capability 的 CRUD 操作，存儲在 ArangoDB 中。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from database.arangodb import ArangoCollection, ArangoDBClient

from agents.task_analyzer.models import (
    Capability,
    CapabilityCreate,
    CapabilityUpdate,
)

logger = structlog.get_logger(__name__)

CAPABILITY_REGISTRY_COLLECTION = "capability_registry"


def _document_to_model(doc: Dict[str, Any]) -> Capability:
    """將 ArangoDB document 轉換為 Capability"""
    return Capability(
        name=doc.get("name"),
        agent=doc.get("agent"),
        input=doc.get("input"),
        output=doc.get("output"),
        constraints=doc.get("constraints", {}),
        version=doc.get("version", "1.0.0"),
        is_active=doc.get("is_active", True),
        description=doc.get("description"),
        metadata=doc.get("metadata", {}),
    )


class CapabilityRegistryStoreService:
    """Capability Registry 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Capability Registry Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(CAPABILITY_REGISTRY_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def create_capability(
        self, capability: CapabilityCreate, created_by: Optional[str] = None
    ) -> Capability:
        """
        創建 Capability

        Args:
            capability: Capability 創建數據
            created_by: 創建者（用戶 ID）

        Returns:
            創建的 Capability

        Raises:
            ValueError: 如果 Capability 已存在
        """
        # 檢查 Capability 是否已存在
        key = f"{capability.agent}-{capability.name}"
        existing = self._collection.get(key)
        if existing is not None:
            raise ValueError(
                f"Capability '{capability.name}' for agent '{capability.agent}' already exists"
            )

        now = datetime.utcnow().isoformat()
        doc: Dict[str, Any] = {
            "_key": key,
            "name": capability.name,
            "agent": capability.agent,
            "input": capability.input,
            "output": capability.output,
            "constraints": capability.constraints,
            "version": capability.version,
            "is_active": True,
            "description": capability.description,
            "metadata": capability.metadata,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": created_by,
        }

        try:
            self._collection.insert(doc)
            self._logger.info(
                "capability_created",
                capability_name=capability.name,
                agent=capability.agent,
                version=capability.version,
            )
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                "capability_create_failed",
                capability_name=capability.name,
                agent=capability.agent,
                error=str(exc),
            )
            raise

    def get_capability(self, name: str, agent: str) -> Optional[Capability]:
        """
        獲取 Capability

        Args:
            name: Capability 名稱
            agent: Agent 名稱

        Returns:
            Capability，如果不存在返回 None
        """
        key = f"{agent}-{name}"
        doc = self._collection.get(key)
        if doc is None:
            return None
        return _document_to_model(doc)

    def list_capabilities(
        self, agent: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[Capability]:
        """
        列出符合條件的 Capability

        Args:
            agent: Agent 名稱（可選）
            is_active: 是否啟用（可選）

        Returns:
            Capability 列表
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        filters = []
        bind_vars: Dict[str, Any] = {}

        if agent is not None:
            filters.append("doc.agent == @agent")
            bind_vars["agent"] = agent

        if is_active is not None:
            filters.append("doc.is_active == @is_active")
            bind_vars["is_active"] = is_active

        filter_clause = " AND ".join(filters) if filters else "true"

        aql = f"""
        FOR doc IN capability_registry
        FILTER {filter_clause}
        SORT doc.agent, doc.name
        RETURN doc
        """
        cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
        results = list(cursor)
        return [_document_to_model(doc) for doc in results]

    def update_capability(
        self,
        name: str,
        agent: str,
        capability: CapabilityUpdate,
        updated_by: Optional[str] = None,
    ) -> Capability:
        """
        更新 Capability

        Args:
            name: Capability 名稱
            agent: Agent 名稱
            capability: Capability 更新數據
            updated_by: 更新者（用戶 ID）

        Returns:
            更新後的 Capability

        Raises:
            ValueError: 如果 Capability 不存在
        """
        key = f"{agent}-{name}"
        existing_doc = self._collection.get(key)
        if existing_doc is None:
            raise ValueError(f"Capability '{name}' for agent '{agent}' not found")

        # 構建更新數據
        update_data: Dict[str, Any] = {
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": updated_by,
        }

        # 只更新提供的字段
        if capability.input is not None:
            update_data["input"] = capability.input
        if capability.output is not None:
            update_data["output"] = capability.output
        if capability.constraints is not None:
            update_data["constraints"] = capability.constraints
        if capability.is_active is not None:
            update_data["is_active"] = capability.is_active
        if capability.description is not None:
            update_data["description"] = capability.description
        if capability.metadata is not None:
            update_data["metadata"] = capability.metadata

        try:
            self._collection.update(key, update_data)
            self._logger.info("capability_updated", capability_name=name, agent=agent)
            # 獲取更新後的文檔
            updated_doc = self._collection.get(key)
            if updated_doc is None:
                raise RuntimeError(f"Failed to retrieve updated capability '{name}' for agent '{agent}'")
            return _document_to_model(updated_doc)
        except Exception as exc:
            self._logger.error("capability_update_failed", capability_name=name, agent=agent, error=str(exc))
            raise

    def delete_capability(self, name: str, agent: str) -> bool:
        """
        刪除 Capability（軟刪除）

        Args:
            name: Capability 名稱
            agent: Agent 名稱

        Returns:
            是否成功刪除
        """
        key = f"{agent}-{name}"
        existing_doc = self._collection.get(key)
        if existing_doc is None:
            return False

        # 軟刪除：設置 is_active = False
        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self._collection.update(key, update_data)
            self._logger.info("capability_deleted", capability_name=name, agent=agent)
            return True
        except Exception as exc:
            self._logger.error("capability_delete_failed", capability_name=name, agent=agent, error=str(exc))
            return False

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(CAPABILITY_REGISTRY_COLLECTION)

        # 獲取現有索引
        indexes = collection.indexes()
        existing_index_fields = {
            tuple(idx.get("fields", []))
            if isinstance(idx.get("fields"), list)
            else idx.get("fields")
            for idx in indexes
        }

        # 唯一索引：agent + name
        agent_name_fields = ("agent", "name")
        if agent_name_fields not in existing_index_fields:
            collection.add_index(
                {"type": "persistent", "fields": ["agent", "name"], "unique": True}
            )

        # 索引：agent + is_active（按 Agent 查詢）
        agent_is_active_fields = ("agent", "is_active")
        if agent_is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["agent", "is_active"]})

        # 索引：is_active（查詢啟用的 Capability）
        is_active_fields = ("is_active",)
        if is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["is_active"]})


def get_capability_registry_store_service(
    client: Optional[ArangoDBClient] = None,
) -> CapabilityRegistryStoreService:
    """
    獲取 Capability Registry Store Service 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        Capability Registry Store Service 實例
    """
    global _capability_registry_store_service_instance
    if _capability_registry_store_service_instance is None:
        _capability_registry_store_service_instance = CapabilityRegistryStoreService(client)
    return _capability_registry_store_service_instance


# 全局單例實例
_capability_registry_store_service_instance: Optional[CapabilityRegistryStoreService] = None
