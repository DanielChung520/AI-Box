# 代碼功能說明: Intent Registry - Intent DSL 註冊表服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Intent Registry - Intent DSL 註冊表服務

提供 Intent 的存儲和查詢接口，支持版本管理。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from database.arangodb import ArangoCollection, ArangoDBClient

from agents.task_analyzer.models import IntentCreate, IntentDSL, IntentQuery, IntentUpdate

logger = structlog.get_logger(__name__)

INTENT_REGISTRY_COLLECTION = "intent_registry"


def _document_to_model(doc: Dict[str, Any]) -> IntentDSL:
    """將 ArangoDB document 轉換為 IntentDSL"""
    return IntentDSL(
        name=doc.get("name"),
        domain=doc.get("domain"),
        target=doc.get("target"),
        output_format=doc.get("output_format", []),
        depth=doc.get("depth"),
        version=doc.get("version"),
        default_version=doc.get("default_version", False),
        is_active=doc.get("is_active", True),
        description=doc.get("description"),
        metadata=doc.get("metadata", {}),
    )


class IntentRegistry:
    """Intent Registry 類

    提供 Intent 的 CRUD 操作和版本管理。
    """

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Intent Registry

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(INTENT_REGISTRY_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def create_intent(
        self, intent: IntentCreate, created_by: Optional[str] = None
    ) -> IntentDSL:
        """
        創建 Intent

        Args:
            intent: Intent 創建數據
            created_by: 創建者（用戶 ID）

        Returns:
            創建的 Intent

        Raises:
            ValueError: 如果 Intent 名稱和版本已存在
        """
        # 檢查 Intent 是否已存在
        key = f"{intent.name}-{intent.version}"
        existing = self._collection.get(key)
        if existing is not None:
            raise ValueError(f"Intent '{intent.name}' version '{intent.version}' already exists")

        # 如果設置為默認版本，需要先取消其他版本的默認標記
        if intent.default_version:
            self._unset_default_version(intent.name)

        now = datetime.utcnow().isoformat()
        doc: Dict[str, Any] = {
            "_key": key,
            "name": intent.name,
            "domain": intent.domain,
            "target": intent.target,
            "output_format": intent.output_format,
            "depth": intent.depth,
            "version": intent.version,
            "default_version": intent.default_version,
            "is_active": True,
            "description": intent.description,
            "metadata": intent.metadata,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": created_by,
        }

        try:
            self._collection.insert(doc)
            self._logger.info("intent_created", intent_name=intent.name, version=intent.version)
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error("intent_create_failed", intent_name=intent.name, error=str(exc))
            raise

    def get_intent(self, name: str, version: Optional[str] = None) -> Optional[IntentDSL]:
        """
        獲取 Intent

        Args:
            name: Intent 名稱
            version: 版本號（如果為 None 則獲取默認版本）

        Returns:
            Intent，如果不存在返回 None
        """
        if version is None:
            # 獲取默認版本
            return self.get_intent_by_name(name)

        key = f"{name}-{version}"
        doc = self._collection.get(key)
        if doc is None:
            return None
        return _document_to_model(doc)

    def get_intent_by_name(self, name: str) -> Optional[IntentDSL]:
        """
        獲取默認版本的 Intent

        Args:
            name: Intent 名稱

        Returns:
            默認版本的 Intent，如果不存在返回 None
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        aql = """
        FOR doc IN intent_registry
        FILTER doc.name == @name
        AND doc.default_version == true
        AND doc.is_active == true
        LIMIT 1
        RETURN doc
        """
        cursor = self._client.db.aql.execute(aql, bind_vars={"name": name})
        results = list(cursor)
        if not results:
            return None
        return _document_to_model(results[0])

    def list_intents(
        self,
        domain: Optional[str] = None,
        is_active: Optional[bool] = None,
        default_version: Optional[bool] = None,
    ) -> List[IntentDSL]:
        """
        列出符合條件的 Intent

        Args:
            domain: 領域（可選）
            is_active: 是否啟用（可選）
            default_version: 是否為默認版本（可選）

        Returns:
            Intent 列表
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        filters = []
        bind_vars: Dict[str, Any] = {}

        if domain is not None:
            filters.append("doc.domain == @domain")
            bind_vars["domain"] = domain

        if is_active is not None:
            filters.append("doc.is_active == @is_active")
            bind_vars["is_active"] = is_active

        if default_version is not None:
            filters.append("doc.default_version == @default_version")
            bind_vars["default_version"] = default_version

        filter_clause = " AND ".join(filters) if filters else "true"

        aql = f"""
        FOR doc IN intent_registry
        FILTER {filter_clause}
        SORT doc.name, doc.version DESC
        RETURN doc
        """
        cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
        results = list(cursor)
        return [_document_to_model(doc) for doc in results]

    def update_intent(
        self,
        name: str,
        version: str,
        intent: IntentUpdate,
        updated_by: Optional[str] = None,
    ) -> IntentDSL:
        """
        更新 Intent

        Args:
            name: Intent 名稱
            version: 版本號
            intent: Intent 更新數據
            updated_by: 更新者（用戶 ID）

        Returns:
            更新後的 Intent

        Raises:
            ValueError: 如果 Intent 不存在
        """
        key = f"{name}-{version}"
        existing_doc = self._collection.get(key)
        if existing_doc is None:
            raise ValueError(f"Intent '{name}' version '{version}' not found")

        # 構建更新數據
        update_data: Dict[str, Any] = {
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": updated_by,
        }

        # 只更新提供的字段
        if intent.domain is not None:
            update_data["domain"] = intent.domain
        if intent.target is not None:
            update_data["target"] = intent.target
        if intent.output_format is not None:
            update_data["output_format"] = intent.output_format
        if intent.depth is not None:
            update_data["depth"] = intent.depth
        if intent.default_version is not None:
            update_data["default_version"] = intent.default_version
            # 如果設置為默認版本，需要先取消其他版本的默認標記
            if intent.default_version:
                self._unset_default_version(name, exclude_version=version)
        if intent.is_active is not None:
            update_data["is_active"] = intent.is_active
        if intent.description is not None:
            update_data["description"] = intent.description
        if intent.metadata is not None:
            update_data["metadata"] = intent.metadata

        try:
            self._collection.update(key, update_data)
            self._logger.info("intent_updated", intent_name=name, version=version)
            # 獲取更新後的文檔
            updated_doc = self._collection.get(key)
            if updated_doc is None:
                raise RuntimeError(f"Failed to retrieve updated intent '{name}' version '{version}'")
            return _document_to_model(updated_doc)
        except Exception as exc:
            self._logger.error("intent_update_failed", intent_name=name, error=str(exc))
            raise

    def set_default_version(self, name: str, version: str) -> IntentDSL:
        """
        設置默認版本

        Args:
            name: Intent 名稱
            version: 版本號

        Returns:
            更新後的 Intent

        Raises:
            ValueError: 如果 Intent 不存在
        """
        # 先取消其他版本的默認標記
        self._unset_default_version(name, exclude_version=version)

        # 設置指定版本為默認版本
        key = f"{name}-{version}"
        existing_doc = self._collection.get(key)
        if existing_doc is None:
            raise ValueError(f"Intent '{name}' version '{version}' not found")

        update_data = {
            "default_version": True,
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self._collection.update(key, update_data)
            self._logger.info("intent_default_version_set", intent_name=name, version=version)
            updated_doc = self._collection.get(key)
            if updated_doc is None:
                raise RuntimeError(f"Failed to retrieve updated intent '{name}' version '{version}'")
            return _document_to_model(updated_doc)
        except Exception as exc:
            self._logger.error("intent_set_default_version_failed", intent_name=name, error=str(exc))
            raise

    def _unset_default_version(self, name: str, exclude_version: Optional[str] = None) -> None:
        """
        取消指定 Intent 的所有版本的默認標記（除了 exclude_version）

        Args:
            name: Intent 名稱
            exclude_version: 要排除的版本號（不取消此版本的默認標記）
        """
        if self._client.db is None or self._client.db.aql is None:
            raise RuntimeError("AQL is not available")

        bind_vars: Dict[str, Any] = {"name": name}
        if exclude_version:
            aql = """
            FOR doc IN intent_registry
            FILTER doc.name == @name
            AND doc.default_version == true
            AND doc.version != @exclude_version
            UPDATE doc WITH { default_version: false, updated_at: @updated_at } IN intent_registry
            """
            bind_vars["exclude_version"] = exclude_version
        else:
            aql = """
            FOR doc IN intent_registry
            FILTER doc.name == @name
            AND doc.default_version == true
            UPDATE doc WITH { default_version: false, updated_at: @updated_at } IN intent_registry
            """
        bind_vars["updated_at"] = datetime.utcnow().isoformat()

        try:
            self._client.db.aql.execute(aql, bind_vars=bind_vars)
        except Exception as exc:
            self._logger.warning("intent_unset_default_version_failed", intent_name=name, error=str(exc))

    def delete_intent(self, name: str, version: str) -> bool:
        """
        刪除 Intent（軟刪除）

        Args:
            name: Intent 名稱
            version: 版本號

        Returns:
            是否成功刪除
        """
        key = f"{name}-{version}"
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
            self._logger.info("intent_deleted", intent_name=name, version=version)
            return True
        except Exception as exc:
            self._logger.error("intent_delete_failed", intent_name=name, error=str(exc))
            return False

    def query_intents(self, query: IntentQuery) -> List[IntentDSL]:
        """
        查詢 Intent

        Args:
            query: 查詢條件

        Returns:
            Intent 列表
        """
        return self.list_intents(
            domain=query.domain,
            is_active=query.is_active,
            default_version=query.default_version,
        )

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(INTENT_REGISTRY_COLLECTION)

        # 獲取現有索引
        indexes = collection.indexes()
        existing_index_fields = {
            tuple(idx.get("fields", []))
            if isinstance(idx.get("fields"), list)
            else idx.get("fields")
            for idx in indexes
        }

        # 唯一索引：name + version
        name_version_fields = ("name", "version")
        if name_version_fields not in existing_index_fields:
            collection.add_index(
                {"type": "persistent", "fields": ["name", "version"], "unique": True}
            )

        # 索引：name + default_version（查詢默認版本）
        name_default_fields = ("name", "default_version")
        if name_default_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["name", "default_version"]})

        # 索引：domain + is_active（按領域查詢）
        domain_is_active_fields = ("domain", "is_active")
        if domain_is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["domain", "is_active"]})

        # 索引：is_active（查詢啟用的 Intent）
        is_active_fields = ("is_active",)
        if is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["is_active"]})


def get_intent_registry(client: Optional[ArangoDBClient] = None) -> IntentRegistry:
    """
    獲取 Intent Registry 實例（單例模式）

    Args:
        client: ArangoDB 客戶端（可選）

    Returns:
        Intent Registry 實例
    """
    global _intent_registry_instance
    if _intent_registry_instance is None:
        _intent_registry_instance = IntentRegistry(client)
    return _intent_registry_instance


# 全局單例實例
_intent_registry_instance: Optional[IntentRegistry] = None
