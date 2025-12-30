# 代碼功能說明: 工具註冊清單存儲服務
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊清單存儲服務

提供工具註冊清單的 CRUD 操作，存儲在 ArangoDB 中。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.tool_registry import (
    ToolRegistryCreate,
    ToolRegistryModel,
    ToolRegistryUpdate,
)

logger = structlog.get_logger(__name__)

TOOLS_REGISTRY_COLLECTION = "tools_registry"


def _document_to_model(doc: Dict[str, Any]) -> ToolRegistryModel:
    """將 ArangoDB document 轉換為 ToolRegistryModel"""
    return ToolRegistryModel(
        id=doc.get("_key"),
        name=doc.get("name"),
        version=doc.get("version"),
        category=doc.get("category"),
        description=doc.get("description"),
        purpose=doc.get("purpose"),
        use_cases=doc.get("use_cases", []),
        input_parameters=doc.get("input_parameters", {}),
        output_fields=doc.get("output_fields", {}),
        example_scenarios=doc.get("example_scenarios", []),
        is_active=doc.get("is_active", True),
        created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
        updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        created_by=doc.get("created_by"),
        updated_by=doc.get("updated_by"),
    )


class ToolRegistryStoreService:
    """工具註冊清單存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Tool Registry Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(TOOLS_REGISTRY_COLLECTION)
        self._collection = ArangoCollection(collection)

    def create_tool(
        self, tool: ToolRegistryCreate, created_by: Optional[str] = None
    ) -> ToolRegistryModel:
        """
        創建工具註冊記錄

        Args:
            tool: 工具創建數據
            created_by: 創建者（用戶 ID）

        Returns:
            創建的工具註冊記錄

        Raises:
            ValueError: 如果工具名稱已存在
        """
        # 檢查工具是否已存在
        existing = self._collection.get(tool.name)
        if existing is not None:
            raise ValueError(f"Tool '{tool.name}' already exists")

        now = datetime.utcnow().isoformat()
        doc: Dict[str, Any] = {
            "_key": tool.name,
            "name": tool.name,
            "version": tool.version,
            "category": tool.category,
            "description": tool.description,
            "purpose": tool.purpose,
            "use_cases": tool.use_cases,
            "input_parameters": tool.input_parameters,
            "output_fields": tool.output_fields,
            "example_scenarios": tool.example_scenarios,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "updated_by": created_by,
        }

        try:
            self._collection.insert(doc)
            self._logger.info("tool_registry_created", tool_name=tool.name, version=tool.version)
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error("tool_registry_create_failed", tool_name=tool.name, error=str(exc))
            raise

    def get_tool(self, tool_name: str) -> Optional[ToolRegistryModel]:
        """
        獲取工具註冊記錄

        Args:
            tool_name: 工具名稱

        Returns:
            工具註冊記錄，如果不存在返回 None
        """
        doc = self._collection.get(tool_name)
        if doc is None:
            return None
        return _document_to_model(doc)

    def update_tool(
        self, tool_name: str, tool: ToolRegistryUpdate, updated_by: Optional[str] = None
    ) -> ToolRegistryModel:
        """
        更新工具註冊記錄

        Args:
            tool_name: 工具名稱
            tool: 工具更新數據
            updated_by: 更新者（用戶 ID）

        Returns:
            更新後的工具註冊記錄

        Raises:
            ValueError: 如果工具不存在
        """
        existing_doc = self._collection.get(tool_name)
        if existing_doc is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        # 構建更新數據
        update_data: Dict[str, Any] = {
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": updated_by,
        }

        # 只更新提供的字段
        if tool.version is not None:
            update_data["version"] = tool.version
        if tool.category is not None:
            update_data["category"] = tool.category
        if tool.description is not None:
            update_data["description"] = tool.description
        if tool.purpose is not None:
            update_data["purpose"] = tool.purpose
        if tool.use_cases is not None:
            update_data["use_cases"] = tool.use_cases
        if tool.input_parameters is not None:
            update_data["input_parameters"] = tool.input_parameters
        if tool.output_fields is not None:
            update_data["output_fields"] = tool.output_fields
        if tool.example_scenarios is not None:
            update_data["example_scenarios"] = tool.example_scenarios
        if tool.is_active is not None:
            update_data["is_active"] = tool.is_active

        try:
            self._collection.update(tool_name, update_data)
            self._logger.info("tool_registry_updated", tool_name=tool_name)
            # 獲取更新後的文檔
            updated_doc = self._collection.get(tool_name)
            if updated_doc is None:
                raise RuntimeError(f"Failed to retrieve updated tool '{tool_name}'")
            return _document_to_model(updated_doc)
        except Exception as exc:
            self._logger.error("tool_registry_update_failed", tool_name=tool_name, error=str(exc))
            raise

    def delete_tool(self, tool_name: str) -> bool:
        """
        刪除工具註冊記錄（軟刪除）

        Args:
            tool_name: 工具名稱

        Returns:
            是否成功刪除

        Raises:
            ValueError: 如果工具不存在
        """
        existing_doc = self._collection.get(tool_name)
        if existing_doc is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        # 軟刪除：設置 is_active = False
        update_data = {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            self._collection.update(tool_name, update_data)
            self._logger.info("tool_registry_deleted", tool_name=tool_name)
            return True
        except Exception as exc:
            self._logger.error("tool_registry_delete_failed", tool_name=tool_name, error=str(exc))
            raise

    def list_tools(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ToolRegistryModel]:
        """
        列出工具註冊記錄

        Args:
            category: 工具類別（可選，用於過濾）
            is_active: 是否只返回啟用的工具（默認 True）
            page: 頁碼（可選，用於分頁）
            page_size: 每頁數量（可選，用於分頁）

        Returns:
            工具註冊記錄列表
        """
        filters: Dict[str, Any] = {}
        if is_active is not None:
            filters["is_active"] = is_active
        if category:
            filters["category"] = category

        try:
            # 構建 AQL 查詢
            aql = """
                FOR doc IN tools_registry
                    FILTER doc.is_active == @is_active
            """
            bind_vars: Dict[str, Any] = {"is_active": is_active if is_active is not None else True}

            if category:
                aql += " AND doc.category == @category"
                bind_vars["category"] = category

            aql += " SORT doc.name ASC"

            # 分頁
            if page is not None and page_size is not None:
                offset = (page - 1) * page_size
                aql += f" LIMIT {offset}, {page_size}"

            aql += " RETURN doc"

            if self._client.db is None or self._client.db.aql is None:
                raise RuntimeError("AQL is not available")

            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = [doc for doc in cursor]

            return [_document_to_model(doc) for doc in docs]
        except Exception as exc:
            self._logger.error("tool_registry_list_failed", error=str(exc))
            raise

    def count_tools(self, category: Optional[str] = None, is_active: Optional[bool] = True) -> int:
        """
        統計工具數量

        Args:
            category: 工具類別（可選，用於過濾）
            is_active: 是否只統計啟用的工具（默認 True）

        Returns:
            工具數量
        """
        try:
            aql = """
                FOR doc IN tools_registry
                    FILTER doc.is_active == @is_active
            """
            bind_vars: Dict[str, Any] = {"is_active": is_active if is_active is not None else True}

            if category:
                aql += " AND doc.category == @category"
                bind_vars["category"] = category

            aql += " COLLECT WITH COUNT INTO total RETURN total"

            if self._client.db is None or self._client.db.aql is None:
                raise RuntimeError("AQL is not available")

            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            result = list(cursor)
            return result[0] if result else 0
        except Exception as exc:
            self._logger.error("tool_registry_count_failed", error=str(exc))
            raise

    def search_tools(
        self,
        keyword: str,
        is_active: Optional[bool] = True,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ToolRegistryModel]:
        """
        搜索工具（根據關鍵字搜索名稱、描述、用途、使用場景）

        Args:
            keyword: 搜索關鍵字
            is_active: 是否只返回啟用的工具（默認 True）
            page: 頁碼（可選，用於分頁）
            page_size: 每頁數量（可選，用於分頁）

        Returns:
            匹配的工具註冊記錄列表
        """
        try:
            aql = """
                FOR doc IN tools_registry
                    FILTER doc.is_active == @is_active
                    AND (
                        doc.name LIKE @keyword_pattern
                        OR doc.description LIKE @keyword_pattern
                        OR doc.purpose LIKE @keyword_pattern
                        OR doc.category LIKE @keyword_pattern
                    )
            """
            bind_vars: Dict[str, Any] = {
                "is_active": is_active if is_active is not None else True,
                "keyword_pattern": f"%{keyword}%",
            }

            aql += " SORT doc.name ASC"

            # 分頁
            if page is not None and page_size is not None:
                offset = (page - 1) * page_size
                aql += f" LIMIT {offset}, {page_size}"

            aql += " RETURN doc"

            if self._client.db is None or self._client.db.aql is None:
                raise RuntimeError("AQL is not available")

            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = [doc for doc in cursor]

            return [_document_to_model(doc) for doc in docs]
        except Exception as exc:
            self._logger.error("tool_registry_search_failed", keyword=keyword, error=str(exc))
            raise


# 全局服務實例（單例模式）
_tool_registry_store_service: Optional[ToolRegistryStoreService] = None


def get_tool_registry_store_service() -> ToolRegistryStoreService:
    """
    獲取工具註冊清單存儲服務實例（單例模式）

    Returns:
        ToolRegistryStoreService 實例
    """
    global _tool_registry_store_service
    if _tool_registry_store_service is None:
        _tool_registry_store_service = ToolRegistryStoreService()
    return _tool_registry_store_service
