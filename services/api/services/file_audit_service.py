# 代碼功能說明: 文件訪問審計服務 (WBS-4.4.2)
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件訪問審計服務 - 提供文件訪問日誌查詢和統計功能"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from services.api.models.audit_log import AuditAction
from services.api.services.audit_log_service import AuditLogService, get_audit_log_service
from services.api.services.file_metadata_service import FileMetadataService, get_metadata_service

logger = structlog.get_logger(__name__)


class FileAuditService:
    """文件訪問審計服務

    提供文件訪問日誌查詢、用戶訪問日誌查詢和訪問統計功能。
    """

    def __init__(
        self,
        audit_log_service: Optional[AuditLogService] = None,
        metadata_service: Optional[FileMetadataService] = None,
    ):
        """
        初始化文件審計服務

        Args:
            audit_log_service: 審計日誌服務（可選，如果不提供則自動創建）
            metadata_service: 文件元數據服務（可選，如果不提供則自動創建）
        """
        self.audit_log_service = audit_log_service or get_audit_log_service()
        self.metadata_service = metadata_service or get_metadata_service()
        self.logger = logger

    def get_file_access_logs(
        self,
        file_id: str,
        user_id: Optional[str] = None,
        granted: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """查詢指定文件的訪問日誌 (WBS-4.4.2)

        Args:
            file_id: 文件 ID
            user_id: 用戶 ID（可選，用於過濾特定用戶的訪問）
            granted: 是否授權（可選，True 表示授權，False 表示拒絕）
            start_date: 開始時間（可選）
            end_date: 結束時間（可選）
            limit: 返回記錄數限制
            offset: 偏移量

        Returns:
            (訪問日誌列表, 總記錄數)
        """
        # 使用 AuditLogService 查詢文件訪問日誌
        logs, total = self.audit_log_service.query_logs(
            user_id=user_id,
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id=file_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        # 如果指定了 granted 過濾，進一步過濾結果
        if granted is not None:
            filtered_logs = [log for log in logs if log.details.get("granted") == granted]
            # 重新計算總數（這是一個近似值，因為我們已經應用了 limit）
            total = len(filtered_logs)
            logs = filtered_logs[:limit]

        # 轉換為字典格式，方便返回（確保 timestamp 可序列化）
        result = []
        for log in logs:
            log_dict = {
                "user_id": log.user_id,
                "action": log.action.value if hasattr(log.action, "value") else log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "timestamp": log.timestamp.isoformat() if isinstance(log.timestamp, datetime) else log.timestamp,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
            }
            result.append(log_dict)

        return result, total

    def get_user_access_logs(
        self,
        user_id: str,
        file_id: Optional[str] = None,
        granted: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """查詢指定用戶的文件訪問日誌 (WBS-4.4.2)

        Args:
            user_id: 用戶 ID
            file_id: 文件 ID（可選，用於過濾特定文件的訪問）
            granted: 是否授權（可選，True 表示授權，False 表示拒絕）
            start_date: 開始時間（可選）
            end_date: 結束時間（可選）
            limit: 返回記錄數限制
            offset: 偏移量

        Returns:
            (訪問日誌列表, 總記錄數)
        """
        # 使用 AuditLogService 查詢用戶訪問日誌
        logs, total = self.audit_log_service.query_logs(
            user_id=user_id,
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id=file_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        # 如果指定了 granted 過濾，進一步過濾結果
        if granted is not None:
            filtered_logs = [log for log in logs if log.details.get("granted") == granted]
            # 重新計算總數（這是一個近似值，因為我們已經應用了 limit）
            total = len(filtered_logs)
            logs = filtered_logs[:limit]

        # 轉換為字典格式，方便返回（確保 timestamp 可序列化）
        result = []
        for log in logs:
            log_dict = {
                "user_id": log.user_id,
                "action": log.action.value if hasattr(log.action, "value") else log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "timestamp": log.timestamp.isoformat() if isinstance(log.timestamp, datetime) else log.timestamp,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": log.details,
            }
            result.append(log_dict)

        return result, total

    def get_access_statistics(
        self,
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """生成訪問統計信息 (WBS-4.4.2)

        Args:
            file_id: 文件 ID（可選，如果提供則統計該文件的訪問）
            user_id: 用戶 ID（可選，如果提供則統計該用戶的訪問）
            start_date: 開始時間（可選）
            end_date: 結束時間（可選）

        Returns:
            統計信息字典，包含：
            - total_accesses: 總訪問次數
            - granted_accesses: 授權訪問次數
            - denied_accesses: 拒絕訪問次數
            - by_file: 按文件統計（如果未指定 file_id）
            - by_user: 按用戶統計（如果未指定 user_id）
            - by_access_level: 按訪問級別統計
            - by_data_classification: 按數據分類統計
        """
        # 查詢所有相關的訪問日誌（不限制數量，用於統計）
        logs, _ = self.audit_log_service.query_logs(
            user_id=user_id,
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id=file_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # 使用較大的限制，實際統計時可能需要分批查詢
            offset=0,
        )

        # 統計信息
        total_accesses = len(logs)
        granted_accesses = sum(1 for log in logs if log.details.get("granted") is True)
        denied_accesses = total_accesses - granted_accesses

        # 按文件統計（如果未指定 file_id）
        by_file: Dict[str, int] = {}
        if not file_id:
            for log in logs:
                file_id_key = log.resource_id or "unknown"
                by_file[file_id_key] = by_file.get(file_id_key, 0) + 1

        # 按用戶統計（如果未指定 user_id）
        by_user: Dict[str, int] = {}
        if not user_id:
            for log in logs:
                user_id_key = log.user_id
                by_user[user_id_key] = by_user.get(user_id_key, 0) + 1

        # 按訪問級別統計
        by_access_level: Dict[str, int] = {}
        for log in logs:
            access_level = log.details.get("access_level", "unknown")
            by_access_level[access_level] = by_access_level.get(access_level, 0) + 1

        # 按數據分類統計
        by_data_classification: Dict[str, int] = {}
        for log in logs:
            data_classification = log.details.get("data_classification", "unknown")
            by_data_classification[data_classification] = (
                by_data_classification.get(data_classification, 0) + 1
            )

        return {
            "total_accesses": total_accesses,
            "granted_accesses": granted_accesses,
            "denied_accesses": denied_accesses,
            "by_file": by_file,
            "by_user": by_user,
            "by_access_level": by_access_level,
            "by_data_classification": by_data_classification,
        }


# 全局服務實例（懶加載）
_file_audit_service: Optional[FileAuditService] = None


def get_file_audit_service() -> FileAuditService:
    """獲取文件審計服務實例（單例模式）"""
    global _file_audit_service
    if _file_audit_service is None:
        _file_audit_service = FileAuditService()
    return _file_audit_service
