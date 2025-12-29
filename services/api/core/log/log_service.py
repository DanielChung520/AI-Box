# 代碼功能說明: LogService 統一日誌服務
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""LogService 統一日誌服務 - 提供統一的日誌記錄接口，支持任務追蹤與審計合規"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient

logger = structlog.get_logger(__name__)

# 延遲導入 SeaweedFS 服務，避免在 boto3 未安裝時導致模塊級導入錯誤
try:
    from services.api.services.governance.seaweedfs_log_service import SeaweedFSSystemLogService
except ImportError as e:
    logger.warning(
        "Failed to import SeaweedFSSystemLogService, will use ArangoDB only", error=str(e)
    )
    SeaweedFSSystemLogService = None  # type: ignore[assignment,misc]

# ArangoDB Collection 名稱
SYSTEM_LOGS_COLLECTION_NAME = "system_logs"

# 默認配置
DEFAULT_MAX_CONTENT_SIZE = 100 * 1024  # 100KB

# TTL 策略配置（按日誌類型的保留期，單位：秒）
# 注意：ArangoDB TTL 索引只能有一個，實際使用統一的 TTL 索引
# 差異化保留期可通過定期清理任務實現
TTL_POLICY = {
    "TASK": 90 * 24 * 3600,  # 90 天
    "AUDIT": 365 * 24 * 3600,  # 1 年（合規要求）
    "SECURITY": 365 * 24 * 3600,  # 1 年（安全審計）
}
# 統一 TTL（使用最長的保留期）
UNIFIED_TTL_SECONDS = max(TTL_POLICY.values())  # 1 年


class LogType(str, Enum):
    """日誌類型"""

    TASK = "TASK"  # 任務級日誌（Orchestrator）
    AUDIT = "AUDIT"  # 審計日誌（System Config Agent）
    SECURITY = "SECURITY"  # 安全日誌（Security Agent)


class LogService:
    """統一日誌服務，支援任務追蹤與審計合規（適配器模式：優先使用 SeaweedFS，fallback 到 ArangoDB）"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        max_content_size: int = DEFAULT_MAX_CONTENT_SIZE,
    ):
        """
        初始化日誌服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則使用默認客戶端）
            max_content_size: content 字段最大大小（字節），默認 100KB
        """
        self.client = client or ArangoDBClient()
        self.max_content_size = max_content_size

        # 嘗試初始化 SeaweedFS 服務（優先使用）
        self._seaweedfs_service: Optional[Any] = None
        if SeaweedFSSystemLogService is not None:
            try:
                self._seaweedfs_service = SeaweedFSSystemLogService()
                logger.info("SeaweedFS system log service initialized")
            except Exception as e:
                logger.warning(
                    "Failed to initialize SeaweedFS system log service, will use ArangoDB fallback",
                    error=str(e),
                )
        else:
            logger.info(
                "SeaweedFSSystemLogService not available (boto3 not installed), using ArangoDB only"
            )

        self._collection_ensured = False
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保 system_logs Collection 存在並創建必要的索引"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        if self._collection_ensured:
            return

        collection_created = False
        if not self.client.db.has_collection(SYSTEM_LOGS_COLLECTION_NAME):
            self.client.db.create_collection(SYSTEM_LOGS_COLLECTION_NAME)
            logger.info("Created collection", collection=SYSTEM_LOGS_COLLECTION_NAME)
            collection_created = True

        # 獲取 Collection 並創建索引
        collection = self.client.db.collection(SYSTEM_LOGS_COLLECTION_NAME)

        # 創建索引（如果 Collection 是新創建的，或者索引不存在）
        if collection_created:
            try:
                # 1. trace_id + timestamp 複合索引（用於追蹤完整請求）
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["trace_id", "timestamp"],
                        "name": "idx_system_logs_trace_timestamp",
                    }
                )

                # 2. type + timestamp 複合索引（用於按類型查詢）
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["type", "timestamp"],
                        "name": "idx_system_logs_type_timestamp",
                    }
                )

                # 3. actor + timestamp 複合索引（用於查詢特定用戶操作）
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["actor", "timestamp"],
                        "name": "idx_system_logs_actor_timestamp",
                    }
                )

                # 4. 審計日誌複合索引（用於審計查詢）
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["type", "level", "tenant_id", "timestamp"],
                        "name": "idx_system_logs_audit_query",
                    }
                )

                # 5. 時間範圍查詢索引
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["timestamp"],
                        "name": "idx_system_logs_timestamp",
                    }
                )

                # 6. TTL 索引（可選：自動清理舊日誌，1年）
                collection.add_index(
                    {
                        "type": "ttl",
                        "fields": ["timestamp"],
                        "expireAfter": 31536000,  # 1 年（秒）
                        "name": "idx_system_logs_ttl",
                    }
                )

                logger.info("Created indexes for system_logs collection")
            except Exception as e:
                logger.warning("Failed to create some indexes", error=str(e))

        self._collection_ensured = True

    def _truncate_content(
        self, content: Dict[str, Any], max_size: int, log_type: LogType
    ) -> Dict[str, Any]:
        """
        截斷過大的 content 字段，保留關鍵信息

        Args:
            content: 原始 content 字典
            max_size: 最大大小（字節）
            log_type: 日誌類型（用於決定保留哪些關鍵字段）

        Returns:
            截斷後的 content 字典
        """
        # 序列化檢查大小
        content_str = json.dumps(content, ensure_ascii=False)
        content_size = len(content_str.encode("utf-8"))

        if content_size <= max_size:
            return content

        # 根據日誌類型定義關鍵字段
        key_fields_map = {
            LogType.TASK: ["instruction", "final_status", "total_duration_ms"],
            LogType.AUDIT: ["scope", "before", "after", "changes", "aql_query"],
            LogType.SECURITY: [
                "permission_check",
                "risk_assessment",
                "audit_context",
            ],
        }

        key_fields = key_fields_map.get(log_type, [])

        # 創建截斷後的 content，只保留關鍵字段
        truncated_content: Dict[str, Any] = {}

        for key in key_fields:
            if key in content:
                truncated_content[key] = content[key]

        # 添加截斷標記
        truncated_content["_truncated"] = True
        truncated_content["_original_size"] = content_size
        truncated_content["_truncated_fields"] = [k for k in content.keys() if k not in key_fields]

        # 檢查截斷後的大小
        truncated_str = json.dumps(truncated_content, ensure_ascii=False)
        truncated_size = len(truncated_str.encode("utf-8"))

        if truncated_size > max_size:
            # 如果關鍵字段仍然太大，進一步截斷 before/after 等大字段
            if "before" in truncated_content:
                truncated_content["before"] = {
                    "_too_large": True,
                    "_original_keys": list(truncated_content["before"].keys())
                    if isinstance(truncated_content["before"], dict)
                    else None,
                }
            if "after" in truncated_content:
                truncated_content["after"] = {
                    "_too_large": True,
                    "_original_keys": list(truncated_content["after"].keys())
                    if isinstance(truncated_content["after"], dict)
                    else None,
                }

        return truncated_content

    async def log_event(
        self,
        trace_id: str,
        log_type: LogType,
        agent_name: str,
        actor: str,
        action: str,
        content: Dict[str, Any],
        level: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        記錄日誌事件（統一接口）

        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            trace_id: 追蹤 ID（用於串聯整個請求）
            log_type: 日誌類型（TASK/AUDIT/SECURITY）
            agent_name: Agent 名稱（如 "Orchestrator", "SystemConfigAgent"）
            actor: 執行者（用戶 ID 或 Agent ID）
            action: 操作類型（如 "update_config", "check_permission"）
            content: 日誌內容（包含 before/after、決策邏輯等）
            level: 配置層級（system/tenant/user，僅 AUDIT 類型需要）
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）

        Returns:
            log_id: 日誌記錄 ID
        """
        # 檢查並截斷過大的 content
        content_str = json.dumps(content, ensure_ascii=False)
        content_size = len(content_str.encode("utf-8"))

        if content_size > self.max_content_size:
            content = self._truncate_content(content, self.max_content_size, log_type)
            logger.warning(
                "Log content too large, truncated",
                trace_id=trace_id,
                log_type=log_type.value,
                original_size=content_size,
                max_size=self.max_content_size,
            )

        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                return await self._seaweedfs_service.log_event(
                    trace_id=trace_id,
                    log_type=log_type,
                    agent_name=agent_name,
                    actor=actor,
                    action=action,
                    content=content,
                    level=level,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to log event to SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        timestamp = datetime.utcnow()
        log_entry = {
            "_key": f"{trace_id}_{log_type.value}_{int(timestamp.timestamp() * 1000)}",
            "trace_id": trace_id,
            "type": log_type.value,
            "agent_name": agent_name,
            "actor": actor,
            "action": action,
            "content": content,
            "timestamp": timestamp.isoformat() + "Z",
        }

        # 可選字段
        if level is not None:
            log_entry["level"] = level
        if tenant_id is not None:
            log_entry["tenant_id"] = tenant_id
        if user_id is not None:
            log_entry["user_id"] = user_id

        # 執行 AQL 寫入 system_logs Collection
        collection = self.client.db.collection(SYSTEM_LOGS_COLLECTION_NAME)
        try:
            result = collection.insert(log_entry)
            if isinstance(result, dict) and "_key" in result:
                return result["_key"]
            raise RuntimeError("Failed to get log entry key from insert result")
        except Exception as e:
            logger.error("Failed to log event", error=str(e), log_type=log_type.value)
            raise

    async def log_task(
        self,
        trace_id: str,
        actor: str,
        action: str,
        content: Dict[str, Any],
    ) -> str:
        """
        記錄任務級日誌（Orchestrator 專用）

        Args:
            trace_id: 追蹤 ID
            actor: 執行者（用戶 ID）
            action: 操作類型（如 "task_routing", "agent_selection"）
            content: 日誌內容（包含任務路由路徑、決策邏輯等）

        Returns:
            log_id: 日誌記錄 ID
        """
        return await self.log_event(
            trace_id=trace_id,
            log_type=LogType.TASK,
            agent_name="Orchestrator",
            actor=actor,
            action=action,
            content=content,
        )

    async def log_audit(
        self,
        trace_id: str,
        actor: str,
        action: str,
        content: Dict[str, Any],
        level: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        記錄審計日誌（System Config Agent 專用）

        Args:
            trace_id: 追蹤 ID
            actor: 執行者（用戶 ID）
            action: 操作類型（如 "update_config", "delete_config"）
            content: 日誌內容（必須包含 before/after、AQL 語法等）
            level: 配置層級（system/tenant/user）
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）

        Returns:
            log_id: 日誌記錄 ID
        """
        return await self.log_event(
            trace_id=trace_id,
            log_type=LogType.AUDIT,
            agent_name="SystemConfigAgent",
            actor=actor,
            action=action,
            content=content,
            level=level,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    async def log_security(
        self,
        trace_id: str,
        actor: str,
        action: str,
        content: Dict[str, Any],
    ) -> str:
        """
        記錄安全日誌（Security Agent 專用）

        Args:
            trace_id: 追蹤 ID
            actor: 執行者（用戶 ID）
            action: 操作類型（如 "check_permission", "assess_risk"）
            content: 日誌內容（包含權限檢查結果、風險評估分數、攔截記錄等）

        Returns:
            log_id: 日誌記錄 ID
        """
        return await self.log_event(
            trace_id=trace_id,
            log_type=LogType.SECURITY,
            agent_name="SecurityAgent",
            actor=actor,
            action=action,
            content=content,
        )

    async def get_logs_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        根據 trace_id 查詢所有相關日誌

        用於追蹤整個請求的生命週期
        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            trace_id: 追蹤 ID

        Returns:
            日誌列表（按時間排序）
        """
        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                return await self._seaweedfs_service.get_logs_by_trace_id(trace_id)
            except Exception as e:
                logger.warning(
                    "Failed to get logs from SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        if self.client.db is None or self.client.db.aql is None:
            raise RuntimeError("ArangoDB client or AQL is not available")

        aql = """
            FOR log IN system_logs
                FILTER log.trace_id == @trace_id
                SORT log.timestamp ASC
                RETURN log
        """
        try:
            cursor = self.client.db.aql.execute(aql, bind_vars={"trace_id": trace_id})
            if cursor is not None:
                return list(cursor)  # type: ignore[arg-type]
            return []
        except Exception as e:
            logger.error("Failed to get logs by trace_id", error=str(e), trace_id=trace_id)
            raise

    async def get_audit_logs(
        self,
        actor: Optional[str] = None,
        level: Optional[str] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢審計日誌

        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            actor: 執行者（可選）
            level: 配置層級（可選）
            tenant_id: 租戶 ID（可選）
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            limit: 返回數量限制

        Returns:
            審計日誌列表
        """
        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                return await self._seaweedfs_service.get_audit_logs(
                    actor=actor,
                    level=level,
                    tenant_id=tenant_id,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(
                    "Failed to get audit logs from SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        if self.client.db is None or self.client.db.aql is None:
            raise RuntimeError("ArangoDB client or AQL is not available")

        aql = """
            FOR log IN system_logs
                FILTER log.type == "AUDIT"
                FILTER (@actor == null OR log.actor == @actor)
                FILTER (@level == null OR log.level == @level)
                FILTER (@tenant_id == null OR log.tenant_id == @tenant_id)
                FILTER (@start_time == null OR log.timestamp >= @start_time)
                FILTER (@end_time == null OR log.timestamp <= @end_time)
                SORT log.timestamp DESC
                LIMIT @limit
                RETURN log
        """
        bind_vars: Dict[str, Any] = {
            "actor": actor,
            "level": level,
            "tenant_id": tenant_id,
            "start_time": start_time.isoformat() + "Z" if start_time else None,
            "end_time": end_time.isoformat() + "Z" if end_time else None,
            "limit": limit,
        }
        try:
            cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
            if cursor is not None:
                return list(cursor)  # type: ignore[arg-type]
            return []
        except Exception as e:
            logger.error("Failed to get audit logs", error=str(e))
            raise

    async def get_security_logs(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢安全日誌

        優先使用 SeaweedFS，如果失敗則 fallback 到 ArangoDB。

        Args:
            actor: 執行者（可選）
            action: 操作類型（可選）
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            limit: 返回數量限制

        Returns:
            安全日誌列表
        """
        # 優先使用 SeaweedFS
        if self._seaweedfs_service:
            try:
                return await self._seaweedfs_service.get_security_logs(
                    actor=actor,
                    action=action,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(
                    "Failed to get security logs from SeaweedFS, falling back to ArangoDB",
                    error=str(e),
                )

        # Fallback 到 ArangoDB
        if self.client.db is None or self.client.db.aql is None:
            raise RuntimeError("ArangoDB client or AQL is not available")

        aql = """
            FOR log IN system_logs
                FILTER log.type == "SECURITY"
                FILTER (@actor == null OR log.actor == @actor)
                FILTER (@action == null OR log.action == @action)
                FILTER (@start_time == null OR log.timestamp >= @start_time)
                FILTER (@end_time == null OR log.timestamp <= @end_time)
                SORT log.timestamp DESC
                LIMIT @limit
                RETURN log
        """
        bind_vars: Dict[str, Any] = {
            "actor": actor,
            "action": action,
            "start_time": start_time.isoformat() + "Z" if start_time else None,
            "end_time": end_time.isoformat() + "Z" if end_time else None,
            "limit": limit,
        }
        try:
            cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
            if cursor is not None:
                return list(cursor)  # type: ignore[arg-type]
            return []
        except Exception as e:
            logger.error("Failed to get security logs", error=str(e))
            raise

    async def _cleanup_expired_logs(
        self,
        log_type: LogType,
        cutoff_date: Optional[datetime] = None,
    ) -> int:
        """
        清理過期的日誌（用於實現差異化保留期）

        由於 ArangoDB TTL 索引只能有一個，我們使用統一的 TTL（最長保留期），
        然後通過此方法定期清理早於特定時間的日誌。

        Args:
            log_type: 日誌類型
            cutoff_date: 截止日期（默認根據 TTL_POLICY 計算）

        Returns:
            清理的日誌數量
        """
        if self.client.db is None or self.client.db.aql is None:
            raise RuntimeError("ArangoDB client or AQL is not available")

        if cutoff_date is None:
            # 根據 TTL_POLICY 計算截止日期
            ttl_seconds = TTL_POLICY.get(log_type.value, UNIFIED_TTL_SECONDS)
            cutoff_date = datetime.utcnow() - timedelta(seconds=ttl_seconds)

        cutoff_str = cutoff_date.isoformat() + "Z"

        # 刪除早於截止日期的日誌
        aql = """
            FOR log IN system_logs
                FILTER log.type == @log_type
                FILTER log.timestamp < @cutoff_date
                REMOVE log IN system_logs
                RETURN OLD._key
        """
        try:
            cursor = self.client.db.aql.execute(
                aql, bind_vars={"log_type": log_type.value, "cutoff_date": cutoff_str}
            )
            deleted_keys = list(cursor) if cursor is not None else []  # type: ignore[arg-type]
            return len(deleted_keys)
        except Exception as e:
            logger.error(
                "Failed to cleanup expired logs",
                error=str(e),
                log_type=log_type.value,
            )
            raise

    async def get_log_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        獲取日誌統計信息

        Args:
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）

        Returns:
            統計信息字典，包含：
            - total_count: 總日誌數量
            - count_by_type: 按類型統計
            - count_by_agent: 按 Agent 統計
            - average_size_bytes: 平均日誌大小（字節）
            - storage_estimate_bytes: 存儲使用估算（字節）
        """
        if self.client.db is None or self.client.db.aql is None:
            raise RuntimeError("ArangoDB client or AQL is not available")

        # 構建時間過濾條件
        time_filter = ""
        bind_vars: Dict[str, Any] = {}
        if start_time:
            time_filter += " FILTER log.timestamp >= @start_time"
            bind_vars["start_time"] = start_time.isoformat() + "Z"
        if end_time:
            time_filter += " FILTER log.timestamp <= @end_time"
            bind_vars["end_time"] = end_time.isoformat() + "Z"

        # 總數統計
        total_aql = f"""
            FOR log IN system_logs
                {time_filter}
                COLLECT WITH COUNT INTO total
                RETURN total
        """
        total_cursor = self.client.db.aql.execute(total_aql, bind_vars=bind_vars)
        total_count = list(total_cursor)[0] if total_cursor else 0  # type: ignore[arg-type,index]

        # 按類型統計
        type_aql = f"""
            FOR log IN system_logs
                {time_filter}
                COLLECT type = log.type INTO groups
                RETURN {{
                    type: type,
                    count: LENGTH(groups)
                }}
        """
        type_cursor = self.client.db.aql.execute(type_aql, bind_vars=bind_vars)
        count_by_type = {
            item["type"]: item["count"]
            for item in (list(type_cursor) if type_cursor else [])  # type: ignore[arg-type]
        }

        # 按 Agent 統計
        agent_aql = f"""
            FOR log IN system_logs
                {time_filter}
                COLLECT agent = log.agent_name INTO groups
                RETURN {{
                    agent: agent,
                    count: LENGTH(groups)
                }}
        """
        agent_cursor = self.client.db.aql.execute(agent_aql, bind_vars=bind_vars)
        count_by_agent = {
            item["agent"]: item["count"]
            for item in (list(agent_cursor) if agent_cursor else [])  # type: ignore[arg-type]
        }

        # 估算平均大小（採樣）
        sample_aql = f"""
            FOR log IN system_logs
                {time_filter}
                LIMIT 100
                RETURN log
        """
        sample_cursor = self.client.db.aql.execute(sample_aql, bind_vars=bind_vars)
        samples = list(sample_cursor) if sample_cursor else []  # type: ignore[arg-type]

        average_size = 0
        if samples:
            total_size = sum(
                len(json.dumps(log, ensure_ascii=False).encode("utf-8")) for log in samples
            )
            average_size = total_size // len(samples)

        storage_estimate = total_count * average_size if average_size > 0 else 0

        return {
            "total_count": total_count,
            "count_by_type": count_by_type,
            "count_by_agent": count_by_agent,
            "average_size_bytes": average_size,
            "storage_estimate_bytes": storage_estimate,
            "period": {
                "start_time": start_time.isoformat() + "Z" if start_time else None,
                "end_time": end_time.isoformat() + "Z" if end_time else None,
            },
        }


# 全局 LogService 實例
_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    """
    獲取 LogService 實例（單例模式）

    Returns:
        LogService: LogService 實例
    """
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service
