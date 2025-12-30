# 代碼功能說明: 審計日誌服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""審計日誌服務 - 管理審計日誌記錄。"""

from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.audit_log import AuditAction, AuditLog, AuditLogCreate

logger = structlog.get_logger(__name__)

# 延遲導入 SeaweedFS 服務，避免在 boto3 未安裝時導致模塊級導入錯誤
try:
    from services.api.services.governance.seaweedfs_log_service import SeaweedFSAuditLogService
except ImportError as e:
    logger.warning(
        "Failed to import SeaweedFSAuditLogService, will use ArangoDB only", error=str(e)
    )
    SeaweedFSAuditLogService = None  # type: ignore[assignment,misc]

# ArangoDB 集合名稱
AUDIT_LOG_COLLECTION_NAME = "audit_logs"


class AuditLogService:
    """審計日誌服務類（適配器模式：優先使用 SeaweedFS，fallback 到 ArangoDB）"""

    collection: Optional[ArangoCollection]

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """初始化審計日誌服務。

        Args:
            client: ArangoDB 客戶端，如果不提供則創建新實例
        """
        self.client = client or ArangoDBClient()

        # 嘗試初始化 SeaweedFS 服務（優先使用）
        self._seaweedfs_service: Optional[Any] = None
        if SeaweedFSAuditLogService is not None:
            try:
                self._seaweedfs_service = SeaweedFSAuditLogService()
                logger.info("SeaweedFS audit log service initialized")
            except Exception as e:
                logger.warning(
                    "Failed to initialize SeaweedFS audit log service, will use ArangoDB fallback",
                    error=str(e),
                )
        else:
            logger.info(
                "SeaweedFSAuditLogService not available (boto3 not installed), using ArangoDB only"
            )

        # 初始化 ArangoDB 集合（fallback）
        # 確保集合存在
        if self.client.db is not None:
            if not self.client.db.has_collection(AUDIT_LOG_COLLECTION_NAME):
                self.client.db.create_collection(AUDIT_LOG_COLLECTION_NAME)
                logger.info("Created collection", collection=AUDIT_LOG_COLLECTION_NAME)

                # 創建索引以提高查詢性能
                collection = self.client.db.collection(AUDIT_LOG_COLLECTION_NAME)
                collection.add_index({"type": "persistent", "fields": ["user_id"]})
                collection.add_index({"type": "persistent", "fields": ["action"]})
                collection.add_index({"type": "persistent", "fields": ["timestamp"]})
                collection.add_index(
                    {"type": "persistent", "fields": ["resource_type", "resource_id"]}
                )
                logger.info("Created indexes for audit logs collection")
        else:
            logger.warning("ArangoDB client is not connected, only SeaweedFS will be available")

        # 獲取集合
        if self.client.db is not None:
            collection = self.client.db.collection(AUDIT_LOG_COLLECTION_NAME)
            self.collection = ArangoCollection(collection)
        else:
            self.collection = None

    def log(
        self,
        log_create: AuditLogCreate,
        async_mode: bool = True,
    ) -> None:
        """記錄審計日誌。

        此方法支持異步模式，在異步模式下不會阻塞主流程。
        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            log_create: 審計日誌創建請求
            async_mode: 是否使用異步模式（默認為 True）
        """
        if async_mode:
            # 異步執行，不阻塞
            asyncio.create_task(self._log_async(log_create))
        else:
            # 同步執行
            asyncio.run(self._log_async(log_create))

    async def _log_async(self, log_create: AuditLogCreate) -> None:
        """異步記錄審計日誌。

        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            log_create: 審計日誌創建請求
        """
        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                await self._seaweedfs_service.create_audit_log(log_create)
                return
            except Exception as e:
                logger.warning(
                    "Failed to log audit event to SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        try:
            self._log_sync(log_create)
        except Exception as e:
            logger.error("Failed to log audit event asynchronously", error=str(e))

    def _log_sync(self, log_create: AuditLogCreate) -> None:
        """同步記錄審計日誌。

        Args:
            log_create: 審計日誌創建請求
        """
        if self.collection is None:
            logger.warning("ArangoDB collection is not available, cannot log audit event")
            return

        try:
            log_data = {
                "user_id": log_create.user_id,
                "action": log_create.action.value,
                "resource_type": log_create.resource_type,
                "resource_id": log_create.resource_id,
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": log_create.ip_address,
                "user_agent": log_create.user_agent,
                "details": (json.dumps(log_create.details) if log_create.details else "{}"),
            }

            # 生成唯一 key（使用時間戳和用戶ID）
            key = f"{log_create.user_id}_{int(datetime.utcnow().timestamp() * 1000000)}"
            log_data["_key"] = key

            self.collection.insert(log_data)
            logger.debug(
                "Audit log recorded",
                user_id=log_create.user_id,
                action=log_create.action.value,
            )
        except Exception as e:
            logger.error("Failed to log audit event", error=str(e))
            # 不要拋出異常，避免影響主流程

    def query_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[AuditLog], int]:
        """查詢審計日誌。

        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            user_id: 用戶ID（可選）
            action: 操作類型（可選）
            resource_type: 資源類型（可選）
            resource_id: 資源ID（可選）
            start_date: 開始時間（可選）
            end_date: 結束時間（可選）
            limit: 返回記錄數限制
            offset: 偏移量

        Returns:
            (審計日誌列表, 總記錄數)
        """
        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                logs = asyncio.run(
                    self._seaweedfs_service.get_audit_logs(
                        user_id=user_id,
                        action=action,
                        start_time=start_date,
                        end_time=end_date,
                        limit=limit + offset,  # 為了支持 offset，我們需要獲取更多記錄
                    )
                )
                # 應用 offset
                logs = logs[offset:]
                # 應用 resource_type 和 resource_id 過濾（SeaweedFS 服務目前不支持這些過濾）
                if resource_type:
                    logs = [log for log in logs if log.resource_type == resource_type]
                if resource_id:
                    logs = [log for log in logs if log.resource_id == resource_id]
                # 限制返回數量
                logs = logs[:limit]
                # SeaweedFS 不返回總數，使用列表長度作為近似值
                return logs, len(logs)
            except Exception as e:
                logger.warning(
                    "Failed to query audit logs from SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 構建 AQL 查詢
        filters = []
        bind_vars: Dict[str, Any] = {
            "@collection": AUDIT_LOG_COLLECTION_NAME,
        }

        if user_id:
            filters.append("log.user_id == @user_id")
            bind_vars["user_id"] = user_id

        if action:
            filters.append("log.action == @action")
            bind_vars["action"] = action.value

        if resource_type:
            filters.append("log.resource_type == @resource_type")
            bind_vars["resource_type"] = resource_type

        if resource_id:
            filters.append("log.resource_id == @resource_id")
            bind_vars["resource_id"] = resource_id

        if start_date:
            filters.append("log.timestamp >= @start_date")
            bind_vars["start_date"] = start_date.isoformat()

        if end_date:
            filters.append("log.timestamp <= @end_date")
            bind_vars["end_date"] = end_date.isoformat()

        filter_clause = " AND ".join(filters) if filters else "true"

        # 構建查詢語句
        query = f"""
        FOR log IN @@collection
            FILTER {filter_clause}
            SORT log.timestamp DESC
            LIMIT @offset, @limit
            RETURN log
        """

        count_query = f"""
        FOR log IN @@collection
            FILTER {filter_clause}
            COLLECT WITH COUNT INTO total
            RETURN total
        """

        bind_vars["offset"] = offset
        bind_vars["limit"] = limit

        # 執行查詢
        cursor = self.client.db.aql.execute(query, bind_vars=bind_vars)
        results = [doc for doc in cursor] if cursor else []  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代

        # 獲取總數
        count_cursor = self.client.db.aql.execute(count_query, bind_vars=bind_vars)
        total = next(count_cursor, 0) if count_cursor else 0  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代

        # 轉換為 AuditLog 對象
        logs = [self._document_to_log(doc) for doc in results]

        return logs, total

    def export_logs(
        self,
        format: str = "json",
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
    ) -> str:
        """導出審計日誌。

        Args:
            format: 導出格式（"json" 或 "csv"）
            user_id: 用戶ID（可選）
            action: 操作類型（可選）
            start_date: 開始時間（可選）
            end_date: 結束時間（可選）
            limit: 導出記錄數限制

        Returns:
            導出的日誌字符串
        """
        logs, _ = self.query_logs(
            user_id=user_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=0,
        )

        if format.lower() == "csv":
            return self._export_csv(logs)
        else:
            return self._export_json(logs)

    def _export_json(self, logs: List[AuditLog]) -> str:
        """導出為 JSON 格式。

        Args:
            logs: 審計日誌列表

        Returns:
            JSON 字符串
        """
        data = [
            {
                "user_id": log.user_id,
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
            }
            for log in logs
        ]
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _export_csv(self, logs: List[AuditLog]) -> str:
        """導出為 CSV 格式。

        Args:
            logs: 審計日誌列表

        Returns:
            CSV 字符串
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # 寫入標題行
        writer.writerow(
            [
                "user_id",
                "action",
                "resource_type",
                "resource_id",
                "timestamp",
                "ip_address",
                "user_agent",
                "details",
            ]
        )

        # 寫入數據行
        for log in logs:
            writer.writerow(
                [
                    log.user_id,
                    log.action.value,
                    log.resource_type,
                    log.resource_id or "",
                    log.timestamp.isoformat(),
                    log.ip_address,
                    log.user_agent,
                    json.dumps(log.details) if log.details else "",
                ]
            )

        return output.getvalue()

    @staticmethod
    def _document_to_log(doc: Dict[str, Any]) -> AuditLog:
        """將 ArangoDB 文檔轉換為 AuditLog 對象。

        Args:
            doc: ArangoDB 文檔

        Returns:
            AuditLog 對象
        """
        # 處理時間字段
        timestamp = doc.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.utcnow()

        # 處理 details 字段
        details = doc.get("details", {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        return AuditLog(
            user_id=doc["user_id"],
            action=AuditAction(doc["action"]),
            resource_type=doc["resource_type"],
            resource_id=doc.get("resource_id"),
            timestamp=timestamp,
            ip_address=doc["ip_address"],
            user_agent=doc["user_agent"],
            details=details,
        )


# 全局服務實例（單例模式）
_audit_log_service: Optional[AuditLogService] = None


def get_audit_log_service() -> AuditLogService:
    """獲取審計日誌服務實例（單例模式）。

    Returns:
        AuditLogService 實例
    """
    global _audit_log_service

    if _audit_log_service is None:
        _audit_log_service = AuditLogService()

    return _audit_log_service
