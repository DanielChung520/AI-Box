# 代碼功能說明: 服務日誌存儲服務
# 創建日期: 2026-01-17 18:48 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 12:10 UTC+8

"""服務日誌存儲服務 - 提供服務日誌的存儲、查詢和管理功能"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from database.arangodb import ArangoDBClient
from services.api.models.service_log import ServiceLog

logger = logging.getLogger(__name__)

COLLECTION_NAME = "service_logs"


class ServiceLogStoreService:
    """服務日誌存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化服務日誌存儲服務

        Args:
            client: ArangoDB 客戶端
        """
        self.client = client or ArangoDBClient()
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保 collection 和索引存在"""
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected, skipping collection setup")
            return

        try:
            # 檢查並創建 collection
            if not self.client.db.has_collection(COLLECTION_NAME):
                self.client.db.create_collection(COLLECTION_NAME)
                logger.info(f"Created collection: {COLLECTION_NAME}")

            collection = self.client.db.collection(COLLECTION_NAME)

            # 獲取現有索引
            existing_indexes = {idx.get("name") for idx in collection.indexes()}

            # 創建 service_name 索引
            if "idx_service_logs_service_name" not in existing_indexes:
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["service_name"],
                        "name": "idx_service_logs_service_name",
                    }
                )
                logger.info("Created index: service_name")

            # 創建 timestamp 索引
            if "idx_service_logs_timestamp" not in existing_indexes:
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["timestamp"],
                        "name": "idx_service_logs_timestamp",
                    }
                )
                logger.info("Created index: timestamp")

            # 創建 log_level 索引
            if "idx_service_logs_log_level" not in existing_indexes:
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["log_level"],
                        "name": "idx_service_logs_log_level",
                    }
                )
                logger.info("Created index: log_level")

            # 創建 TTL 索引（7 天自動清理）
            if "idx_service_logs_ttl" not in existing_indexes:
                try:
                    collection.add_index(
                        {
                            "type": "ttl",
                            "fields": ["timestamp"],
                            "expireAfter": 604800,  # 7 天（秒）
                            "name": "idx_service_logs_ttl",
                        }
                    )
                    logger.info("Created TTL index: 7 days")
                except Exception as e:
                    logger.warning(f"Failed to create TTL index: {e}")

        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}", exc_info=True)

    def create_log(
        self,
        service_name: str,
        log_level: str,
        message: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> ServiceLog:
        """
        創建服務日誌

        Args:
            service_name: 服務名稱
            log_level: 日誌級別
            message: 日誌消息
            timestamp: 日誌時間
            metadata: 額外元數據

        Returns:
            創建的服務日誌
        """
        try:
            if self.client.db is None:
                raise RuntimeError("ArangoDB client is not connected")

            collection = self.client.db.collection(COLLECTION_NAME)

            log_id = f"log_{int(datetime.utcnow().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"
            timestamp = timestamp or datetime.utcnow()

            doc = {
                "_key": log_id,
                "log_id": log_id,
                "service_name": service_name,
                "log_level": log_level.upper(),
                "message": message,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {},
            }

            collection.insert(doc)

            return ServiceLog(**doc, timestamp=timestamp)

        except Exception as e:
            logger.error(
                f"Failed to create service log: service_name={service_name}, error={str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to create service log: {e}") from e

    def get_service_logs(
        self,
        service_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        log_level: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 100,
    ) -> List[ServiceLog]:
        """
        查詢服務日誌

        Args:
            service_name: 服務名稱
            start_time: 開始時間
            end_time: 結束時間
            log_level: 日誌級別
            keyword: 關鍵字搜索
            limit: 限制返回數量

        Returns:
            服務日誌列表
        """
        try:
            if self.client.db is None or self.client.db.aql is None:
                raise RuntimeError("ArangoDB AQL is not available")

            # 構建過濾條件
            filters = ["doc.service_name == @service_name"]
            bind_vars = {"service_name": service_name}

            if start_time:
                filters.append("doc.timestamp >= @start_time")
                bind_vars["start_time"] = start_time.isoformat()

            if end_time:
                filters.append("doc.timestamp <= @end_time")
                bind_vars["end_time"] = end_time.isoformat()

            if log_level:
                filters.append("doc.log_level == @log_level")
                bind_vars["log_level"] = log_level.upper()

            if keyword:
                filters.append("CONTAINS(doc.message, @keyword)")
                bind_vars["keyword"] = keyword

            filter_clause = " AND ".join(filters)

            aql = f"""
                FOR doc IN {COLLECTION_NAME}
                    FILTER {filter_clause}
                    SORT doc.timestamp DESC
                    LIMIT @limit
                    RETURN doc
            """

            bind_vars["limit"] = limit

            cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            logs = []
            for doc in docs:
                # 解析時間字符串
                timestamp = datetime.fromisoformat(doc["timestamp"].replace("Z", "+00:00"))
                logs.append(ServiceLog(**doc, timestamp=timestamp))

            logger.info(f"Service logs retrieved: service_name={service_name}, count={len(logs)}")

            return logs

        except Exception as e:
            logger.error(
                f"Failed to get service logs: service_name={service_name}, error={str(e)}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to get service logs: {e}") from e

    def batch_create_logs(self, logs: List[dict]) -> int:
        """
        批量創建服務日誌

        Args:
            logs: 日誌列表

        Returns:
            創建的日誌數量
        """
        try:
            if self.client.db is None:
                raise RuntimeError("ArangoDB client is not connected")

            collection = self.client.db.collection(COLLECTION_NAME)

            docs = []
            for log_data in logs:
                log_id = (
                    f"log_{int(datetime.utcnow().timestamp() * 1000000)}_{uuid.uuid4().hex[:8]}"
                )
                timestamp = log_data.get("timestamp") or datetime.utcnow()

                doc = {
                    "_key": log_id,
                    "log_id": log_id,
                    "service_name": log_data["service_name"],
                    "log_level": log_data["log_level"].upper(),
                    "message": log_data["message"],
                    "timestamp": (
                        timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
                    ),
                    "metadata": log_data.get("metadata") or {},
                }
                docs.append(doc)

            if docs:
                collection.insert_many(docs)

            logger.info(f"Batch created service logs: count={len(docs)}")

            return len(docs)

        except Exception as e:
            logger.error(f"Failed to batch create service logs: error={str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to batch create service logs: {e}") from e


# 單例服務
_service: Optional[ServiceLogStoreService] = None


def get_service_log_store_service() -> ServiceLogStoreService:
    """獲取服務日誌存儲服務單例"""
    global _service
    if _service is None:
        _service = ServiceLogStoreService()
    return _service
