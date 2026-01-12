# 代碼功能說明: Report Storage Service 報告存儲服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Report Storage Service - 報告存儲服務，實現報告的持久化存儲和管理"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.arangodb import ArangoDBClient

logger = logging.getLogger(__name__)

COLLECTION_NAME = "reports"


class ReportStorageService:
    """報告存儲服務 - 實現報告的持久化存儲和管理"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化報告存儲服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self._logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["report_id"]})
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["user_id"]})
            collection.add_index({"type": "persistent", "fields": ["created_at"]})
            collection.add_index({"type": "persistent", "fields": ["version"]})
            # 複合索引
            collection.add_index({"type": "persistent", "fields": ["report_id", "version"]})

    def save_report(
        self,
        report_id: str,
        report_data: Dict[str, Any],
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        version: int = 1,
    ) -> str:
        """
        保存報告到 ArangoDB

        Args:
            report_id: 報告 ID
            report_data: 報告數據
            user_id: 用戶 ID（可選）
            task_id: 任務 ID（可選）
            version: 報告版本（默認 1）

        Returns:
            報告文檔的 _key
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        # 構建文檔
        doc = {
            "_key": f"{report_id}_v{version}",
            "report_id": report_id,
            "version": version,
            "user_id": user_id,
            "task_id": task_id,
            "title": report_data.get("title", "Agent 執行報告"),
            "report_data": report_data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # 保存到 ArangoDB
        collection.insert(doc)
        self._logger.info(f"Saved report: {report_id} (version {version})")

        return doc["_key"]

    def get_report(self, report_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        獲取報告

        Args:
            report_id: 報告 ID
            version: 報告版本（可選，如果不提供則獲取最新版本）

        Returns:
            報告文檔，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        if version is not None:
            # 獲取指定版本
            key = f"{report_id}_v{version}"
            doc = collection.get(key)
            if doc:
                return dict(doc)
        else:
            # 獲取最新版本
            aql = """
            FOR doc IN @@collection
                FILTER doc.report_id == @report_id
                SORT doc.version DESC
                LIMIT 1
                RETURN doc
            """
            cursor = self.client.db.aql.execute(
                aql, bind_vars={"@collection": COLLECTION_NAME, "report_id": report_id}
            )
            results = list(cursor)
            if results:
                return dict(results[0])

        return None

    def list_reports(
        self,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出報告

        Args:
            user_id: 用戶 ID（可選，用於過濾）
            task_id: 任務 ID（可選，用於過濾）
            limit: 返回數量限制
            offset: 偏移量

        Returns:
            報告列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        # 構建查詢
        filters = []
        bind_vars: Dict[str, Any] = {
            "@collection": COLLECTION_NAME,
            "limit": limit,
            "offset": offset,
        }

        if user_id:
            filters.append("doc.user_id == @user_id")
            bind_vars["user_id"] = user_id

        if task_id:
            filters.append("doc.task_id == @task_id")
            bind_vars["task_id"] = task_id

        filter_clause = " AND ".join(filters) if filters else "true"

        aql = f"""
        FOR doc IN @@collection
            FILTER {filter_clause}
            SORT doc.created_at DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        return [dict(doc) for doc in cursor]

    def update_report(
        self, report_id: str, report_data: Dict[str, Any], version: Optional[int] = None
    ) -> str:
        """
        更新報告（創建新版本）

        Args:
            report_id: 報告 ID
            report_data: 新的報告數據
            version: 新版本號（可選，如果不提供則自動遞增）

        Returns:
            新版本文檔的 _key
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 獲取當前最新版本
        current_report = self.get_report(report_id)
        if current_report:
            next_version = version if version is not None else current_report.get("version", 0) + 1
            user_id = current_report.get("user_id")
            task_id = current_report.get("task_id")
        else:
            next_version = version if version is not None else 1
            user_id = report_data.get("user_id")
            task_id = report_data.get("task_id")

        # 保存新版本
        return self.save_report(
            report_id=report_id,
            report_data=report_data,
            user_id=user_id,
            task_id=task_id,
            version=next_version,
        )

    def delete_report(self, report_id: str, version: Optional[int] = None) -> bool:
        """
        刪除報告

        Args:
            report_id: 報告 ID
            version: 報告版本（可選，如果不提供則刪除所有版本）

        Returns:
            是否成功刪除
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)

        if version is not None:
            # 刪除指定版本
            key = f"{report_id}_v{version}"
            try:
                collection.delete(key)
                self._logger.info(f"Deleted report: {report_id} (version {version})")
                return True
            except Exception as e:
                self._logger.error(f"Failed to delete report: {e}")
                return False
        else:
            # 刪除所有版本
            if self.client.db.aql is None:
                raise RuntimeError("ArangoDB AQL is not available")

            aql = """
            FOR doc IN @@collection
                FILTER doc.report_id == @report_id
                REMOVE doc IN @@collection
                RETURN 1
            """
            cursor = self.client.db.aql.execute(
                aql, bind_vars={"@collection": COLLECTION_NAME, "report_id": report_id}
            )
            count = len(list(cursor))
            self._logger.info(f"Deleted {count} versions of report: {report_id}")
            return count > 0
