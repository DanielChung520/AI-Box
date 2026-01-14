# 代碼功能說明: Agent Category 存儲服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Category 存儲服務

提供代理分類的存儲服務，用於管理代理分類（如人力資源、物流、財務等）。
分類由系統管理員管理，存儲在獨立的 collection 中。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.agent_category import AgentCategory

logger = structlog.get_logger(__name__)

AGENT_CATEGORIES_COLLECTION = "agent_categories"


class AgentCategoryStoreService:
    """代理分類存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Agent Category Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(AGENT_CATEGORIES_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(AGENT_CATEGORIES_COLLECTION)

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

        # 租戶 + 啟用狀態索引
        tenant_active_fields = ("tenant_id", "is_active")
        if tenant_active_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "is_active"],
                    "name": "idx_agent_categories_tenant_active",
                }
            )

        # 分類 ID 索引
        category_id_fields = ("tenant_id", "category.id", "is_active")
        if category_id_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["tenant_id", "category.id", "is_active"],
                    "name": "idx_agent_categories_id",
                }
            )

    def get_categories(
        self, tenant_id: Optional[str] = None, include_inactive: bool = False
    ) -> List[AgentCategory]:
        """
        獲取分類列表（按顯示順序排序）

        Args:
            tenant_id: 租戶 ID（可選，None 表示系統級）
            include_inactive: 是否包含未啟用的分類

        Returns:
            分類列表，按 display_order 排序
        """
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 構建查詢過濾條件
        filters: dict = {"tenant_id": tenant_id}
        if not include_inactive:
            filters["is_active"] = True

        # 查詢分類
        aql = """
        FOR doc IN @@collection
        FILTER doc.tenant_id == @tenant_id
        AND (@include_inactive OR doc.is_active == true)
        SORT doc.category.display_order ASC
        RETURN doc.category
        """

        cursor = self._client.db.aql.execute(
            aql,
            bind_vars={
                "@collection": AGENT_CATEGORIES_COLLECTION,
                "tenant_id": tenant_id,
                "include_inactive": include_inactive,
            },
        )

        categories = [AgentCategory(**cat) for cat in cursor]
        return categories

    def get_category(
        self, category_id: str, tenant_id: Optional[str] = None
    ) -> Optional[AgentCategory]:
        """
        獲取單個分類

        Args:
            category_id: 分類 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            分類配置，如果不存在則返回 None
        """
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 查詢分類
        aql = """
        FOR doc IN @@collection
        FILTER doc.tenant_id == @tenant_id
        AND doc.category.id == @category_id
        AND doc.is_active == true
        LIMIT 1
        RETURN doc.category
        """

        cursor = self._client.db.aql.execute(
            aql,
            bind_vars={
                "@collection": AGENT_CATEGORIES_COLLECTION,
                "tenant_id": tenant_id,
                "category_id": category_id,
            },
        )

        results = list(cursor)
        if not results:
            return None

        return AgentCategory(**results[0])

    def create_category(
        self,
        category: AgentCategory,
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """
        創建分類

        Args:
            category: 分類配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            created_by: 創建人（系統管理員）

        Returns:
            創建的分類 _key
        """
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self._client.db.collection(AGENT_CATEGORIES_COLLECTION)

        # 檢查分類是否已存在
        existing = self.get_category(category.id, tenant_id)
        if existing:
            raise ValueError(f"Category {category.id} already exists")

        # 創建文檔
        now = datetime.utcnow().isoformat()
        doc_key = category.id  # 使用分類 ID 作為 _key

        document = {
            "_key": doc_key,
            "tenant_id": tenant_id,
            "category": category.model_dump(),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": None,
        }

        collection.insert(document)
        self._logger.info(
            "agent_category_created",
            category_id=category.id,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        return doc_key

    def update_category(
        self,
        category_id: str,
        category: AgentCategory,
        tenant_id: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        更新分類

        Args:
            category_id: 分類 ID
            category: 新的分類配置
            tenant_id: 租戶 ID（可選，None 表示系統級）
            updated_by: 更新人（系統管理員）

        Returns:
            是否更新成功
        """
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self._client.db.collection(AGENT_CATEGORIES_COLLECTION)

        # 查找現有文檔
        doc_key = category_id
        existing_doc = collection.get(doc_key)

        if not existing_doc:
            return False

        # 檢查租戶 ID 是否匹配
        if existing_doc.get("tenant_id") != tenant_id:
            return False

        # 更新文檔
        now = datetime.utcnow().isoformat()
        existing_doc["category"] = category.model_dump()
        existing_doc["updated_at"] = now
        existing_doc["updated_by"] = updated_by

        collection.update(existing_doc)
        self._logger.info(
            "agent_category_updated",
            category_id=category_id,
            tenant_id=tenant_id,
            updated_by=updated_by,
        )

        return True

    def delete_category(self, category_id: str, tenant_id: Optional[str] = None) -> bool:
        """
        刪除分類（軟刪除）

        Args:
            category_id: 分類 ID
            tenant_id: 租戶 ID（可選，None 表示系統級）

        Returns:
            是否刪除成功
        """
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self._client.db.collection(AGENT_CATEGORIES_COLLECTION)

        # 查找現有文檔
        doc_key = category_id
        existing_doc = collection.get(doc_key)

        if not existing_doc:
            return False

        # 檢查租戶 ID 是否匹配
        if existing_doc.get("tenant_id") != tenant_id:
            return False

        # 軟刪除：設置 is_active = False
        now = datetime.utcnow().isoformat()
        existing_doc["is_active"] = False
        existing_doc["updated_at"] = now

        collection.update(existing_doc)
        self._logger.info(
            "agent_category_deleted",
            category_id=category_id,
            tenant_id=tenant_id,
        )

        return True
