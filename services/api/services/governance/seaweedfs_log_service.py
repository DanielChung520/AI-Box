# 代碼功能說明: SeaweedFS 日誌服務 - 審計日誌和系統日誌存儲服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 日誌服務 - 使用 SeaweedFS 存儲審計日誌和系統日誌"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

from services.api.models.audit_log import AuditAction, AuditLog, AuditLogCreate

logger = structlog.get_logger(__name__)

# 定義 LogType 枚舉（避免循環導入）
# 注意：這個定義應該與 log_service.py 中的 LogType 保持一致


class LogType(str, Enum):
    """日誌類型（本地定義，避免循環導入）"""

    TASK = "TASK"
    AUDIT = "AUDIT"
    SECURITY = "SECURITY"


# 延遲導入 boto3 相關模塊，避免在 boto3 未安裝時導致模塊級導入錯誤
try:
    from botocore.exceptions import ClientError
except ImportError:
    ClientError = Exception  # type: ignore[assignment,misc]

try:
    from storage.file_storage import create_storage_from_config
    from storage.s3_storage import S3FileStorage
except ImportError as e:
    # 如果 boto3 未安裝，S3FileStorage 無法導入
    logger.warning(
        "Failed to import S3FileStorage, SeaweedFS features will be disabled", error=str(e)
    )
    S3FileStorage = None  # type: ignore[assignment,misc]
    create_storage_from_config = None  # type: ignore[assignment]


def _get_seaweedfs_storage() -> "S3FileStorage":
    """
    獲取 SeaweedFS 存儲實例（用於治理服務）

    Returns:
        S3FileStorage 實例（AI-Box 服務）

    Raises:
        ImportError: 如果 boto3 未安裝或 S3FileStorage 無法導入
        ValueError: 如果 SeaweedFS 配置不完整
    """
    if S3FileStorage is None or create_storage_from_config is None:
        raise ImportError("boto3 is not installed. Please install it with: pip install boto3")

    config: Dict[str, Any] = {}
    storage = create_storage_from_config(config, service_type="ai_box")
    if not isinstance(storage, S3FileStorage):
        raise ValueError("Failed to create S3FileStorage instance. Check SeaweedFS configuration.")
    return storage


class SeaweedFSAuditLogService:
    """SeaweedFS 審計日誌服務"""

    def __init__(self, storage: Optional["S3FileStorage"] = None):
        """
        初始化 SeaweedFS 審計日誌服務

        Args:
            storage: S3FileStorage 實例（如果不提供則自動創建）

        Raises:
            ImportError: 如果 boto3 未安裝
            ValueError: 如果 SeaweedFS 配置不完整
            Exception: 如果 Bucket 創建失敗
        """
        if S3FileStorage is None:
            raise ImportError("boto3 is not installed. Please install it with: pip install boto3")

        try:
            self.storage = storage or _get_seaweedfs_storage()
        except (ImportError, ValueError) as e:
            logger.error("Failed to initialize SeaweedFS storage", error=str(e))
            raise

        self.bucket = "bucket-governance-logs"
        self.logger = logger.bind(service="SeaweedFSAuditLogService", bucket=self.bucket)

        # 確保 Bucket 存在
        try:
            self._ensure_bucket_exists()
        except Exception as e:
            logger.error("Failed to ensure bucket exists", bucket=self.bucket, error=str(e))
            raise

    def _ensure_bucket_exists(self) -> None:
        """確保 Bucket 存在"""
        try:
            self.storage.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.debug("Bucket already exists", bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                try:
                    self.storage.s3_client.create_bucket(Bucket=self.bucket)
                    self.logger.info("Bucket created", bucket=self.bucket)
                except ClientError as create_error:
                    self.logger.error(
                        "Failed to create bucket",
                        bucket=self.bucket,
                        error=str(create_error),
                    )
                    raise
            else:
                self.logger.error(
                    "Failed to check bucket existence",
                    bucket=self.bucket,
                    error=str(e),
                )
                raise

    def _get_log_file_path(self, timestamp: datetime, log_type: str = "audit") -> str:
        """
        生成日誌文件路徑（按天分片）

        Args:
            timestamp: 時間戳
            log_type: 日誌類型（默認為 "audit"）

        Returns:
            文件路徑（例如：audit/2025/01/27.jsonl）
        """
        date_str = timestamp.strftime("%Y/%m/%d")
        return f"{log_type}/{date_str}.jsonl"

    def _get_log_files_in_range(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        log_type: str = "audit",
    ) -> List[str]:
        """
        獲取時間範圍內的所有日誌文件路徑

        Args:
            start_time: 開始時間（可選，如果為 None 則從最早開始）
            end_time: 結束時間（可選，如果為 None 則到最新）
            log_type: 日誌類型（默認為 "audit"）

        Returns:
            文件路徑列表
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=365)  # 默認查詢最近一年
        if end_time is None:
            end_time = datetime.utcnow()

        files: List[str] = []
        current_date = start_time.date()

        while current_date <= end_time.date():
            file_path = self._get_log_file_path(
                datetime.combine(current_date, datetime.min.time()), log_type
            )
            files.append(file_path)
            current_date += timedelta(days=1)

        return files

    def _matches_filters(
        self,
        log_data: Dict[str, Any],
        user_id: Optional[str],
        action: Optional[AuditAction],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> bool:
        """
        檢查日誌記錄是否匹配過濾條件

        Args:
            log_data: 日誌數據
            user_id: 用戶 ID 過濾
            action: 操作類型過濾
            start_time: 開始時間過濾
            end_time: 結束時間過濾

        Returns:
            是否匹配
        """
        if user_id and log_data.get("user_id") != user_id:
            return False

        if action and log_data.get("action") != action.value:
            return False

        log_timestamp_str = log_data.get("timestamp")
        if log_timestamp_str:
            try:
                if isinstance(log_timestamp_str, str):
                    log_timestamp = datetime.fromisoformat(log_timestamp_str.replace("Z", "+00:00"))
                else:
                    log_timestamp = log_timestamp_str

                if start_time and log_timestamp < start_time:
                    return False
                if end_time and log_timestamp > end_time:
                    return False
            except Exception:
                # 如果時間解析失敗，跳過時間過濾
                pass

        return True

    async def create_audit_log(self, log: AuditLogCreate) -> str:
        """
        追加審計日誌到 JSON Lines 文件

        Args:
            log: 審計日誌創建請求

        Returns:
            日誌 ID
        """
        timestamp = datetime.utcnow()
        file_path = self._get_log_file_path(timestamp, "audit")

        # 轉換為 AuditLog 對象
        audit_log = AuditLog(
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            timestamp=timestamp,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
        )

        # 讀取現有文件（如果存在）
        existing_content = None
        try:
            response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
            existing_content = response["Body"].read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                self.logger.error(
                    "Failed to read existing log file",
                    file_path=file_path,
                    error=str(e),
                )
                raise
            # 文件不存在，這是正常的（第一次寫入）

        # 追加新日誌（JSON Lines 格式）
        log_line = json.dumps(audit_log.dict(), ensure_ascii=False, default=str) + "\n"
        new_content = (existing_content or b"") + log_line.encode("utf-8")

        # 寫回 SeaweedFS
        try:
            self.storage.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=new_content,
                ContentType="application/x-ndjson",
            )
            log_id = f"{log.user_id}_{int(timestamp.timestamp() * 1000000)}"
            self.logger.debug(
                "Audit log appended",
                log_id=log_id,
                file_path=file_path,
                user_id=log.user_id,
                action=log.action.value,
            )
            return log_id
        except ClientError as e:
            self.logger.error(
                "Failed to write audit log",
                file_path=file_path,
                error=str(e),
            )
            raise RuntimeError(f"Failed to write audit log: {e}") from e

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        查詢審計日誌

        Args:
            user_id: 用戶 ID（可選）
            action: 操作類型（可選）
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            limit: 返回記錄數限制

        Returns:
            審計日誌列表
        """
        # 1. 根據時間範圍確定需要讀取的文件列表
        files = self._get_log_files_in_range(start_time, end_time, "audit")

        # 2. 讀取文件並過濾
        logs: List[AuditLog] = []
        for file_path in files:
            try:
                response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
                content = response["Body"].read()
                if content:
                    for line in content.decode("utf-8").split("\n"):
                        if line.strip():
                            try:
                                log_data = json.loads(line)
                                if self._matches_filters(
                                    log_data, user_id, action, start_time, end_time
                                ):
                                    logs.append(AuditLog(**log_data))
                            except (json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to parse log line",
                                    file_path=file_path,
                                    line=line[:100],
                                    error=str(e),
                                )
                                continue
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                    # 文件不存在，跳過
                    continue
                self.logger.warning(
                    "Failed to read log file",
                    file_path=file_path,
                    error=str(e),
                )
                continue

        # 3. 排序和分頁
        sorted_logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
        return sorted_logs[:limit]


class SeaweedFSSystemLogService:
    """SeaweedFS 系統日誌服務"""

    def __init__(self, storage: Optional["S3FileStorage"] = None):
        """
        初始化 SeaweedFS 系統日誌服務

        Args:
            storage: S3FileStorage 實例（如果不提供則自動創建）

        Raises:
            ImportError: 如果 boto3 未安裝
            ValueError: 如果 SeaweedFS 配置不完整
            Exception: 如果 Bucket 創建失敗
        """
        if S3FileStorage is None:
            raise ImportError("boto3 is not installed. Please install it with: pip install boto3")

        try:
            self.storage = storage or _get_seaweedfs_storage()
        except (ImportError, ValueError) as e:
            logger.error("Failed to initialize SeaweedFS storage", error=str(e))
            raise

        self.bucket = "bucket-governance-logs"
        self.logger = logger.bind(service="SeaweedFSSystemLogService", bucket=self.bucket)

        # 確保 Bucket 存在
        try:
            self._ensure_bucket_exists()
        except Exception as e:
            logger.error("Failed to ensure bucket exists", bucket=self.bucket, error=str(e))
            raise

    def _ensure_bucket_exists(self) -> None:
        """確保 Bucket 存在"""
        try:
            self.storage.s3_client.head_bucket(Bucket=self.bucket)
            self.logger.debug("Bucket already exists", bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                try:
                    self.storage.s3_client.create_bucket(Bucket=self.bucket)
                    self.logger.info("Bucket created", bucket=self.bucket)
                except ClientError as create_error:
                    self.logger.error(
                        "Failed to create bucket",
                        bucket=self.bucket,
                        error=str(create_error),
                    )
                    raise
            else:
                self.logger.error(
                    "Failed to check bucket existence",
                    bucket=self.bucket,
                    error=str(e),
                )
                raise

    def _get_log_file_path(self, timestamp: datetime, log_type: LogType) -> str:
        """
        生成系統日誌文件路徑（按天分片）

        Args:
            timestamp: 時間戳
            log_type: 日誌類型（TASK, AUDIT, SECURITY）

        Returns:
            文件路徑（例如：system/task/2025/01/27.jsonl）
        """
        date_str = timestamp.strftime("%Y/%m/%d")
        log_type_str = log_type.value.lower()
        return f"system/{log_type_str}/{date_str}.jsonl"

    def _get_log_files_in_range(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        log_type: LogType,
    ) -> List[str]:
        """
        獲取時間範圍內的所有日誌文件路徑

        Args:
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            log_type: 日誌類型

        Returns:
            文件路徑列表
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=90)  # 默認查詢最近90天
        if end_time is None:
            end_time = datetime.utcnow()

        files: List[str] = []
        current_date = start_time.date()

        while current_date <= end_time.date():
            file_path = self._get_log_file_path(
                datetime.combine(current_date, datetime.min.time()), log_type
            )
            files.append(file_path)
            current_date += timedelta(days=1)

        return files

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
        追加系統日誌到 JSON Lines 文件

        Args:
            trace_id: 追蹤 ID
            log_type: 日誌類型
            agent_name: Agent 名稱
            actor: 執行者
            action: 操作類型
            content: 日誌內容
            level: 配置層級（可選）
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）

        Returns:
            日誌 ID
        """
        timestamp = datetime.utcnow()
        file_path = self._get_log_file_path(timestamp, log_type)

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

        if level is not None:
            log_entry["level"] = level
        if tenant_id is not None:
            log_entry["tenant_id"] = tenant_id
        if user_id is not None:
            log_entry["user_id"] = user_id

        # 讀取現有文件（如果存在）
        existing_content = None
        try:
            response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
            existing_content = response["Body"].read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "NoSuchKey":
                self.logger.error(
                    "Failed to read existing log file",
                    file_path=file_path,
                    error=str(e),
                )
                raise
            # 文件不存在，這是正常的（第一次寫入）

        # 追加新日誌（JSON Lines 格式）
        log_line = json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"
        new_content = (existing_content or b"") + log_line.encode("utf-8")

        # 寫回 SeaweedFS
        try:
            self.storage.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=new_content,
                ContentType="application/x-ndjson",
            )
            log_id = log_entry["_key"]
            self.logger.debug(
                "System log appended",
                log_id=log_id,
                file_path=file_path,
                trace_id=trace_id,
                log_type=log_type.value,
            )
            return log_id
        except ClientError as e:
            self.logger.error(
                "Failed to write system log",
                file_path=file_path,
                error=str(e),
            )
            raise RuntimeError(f"Failed to write system log: {e}") from e

    async def get_logs_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        根據 trace_id 查詢日誌

        Args:
            trace_id: 追蹤 ID

        Returns:
            日誌列表
        """
        logs: List[Dict[str, Any]] = []

        # 在所有日誌類型中查找
        for log_type in LogType:
            # 查詢最近90天的日誌
            start_time = datetime.utcnow() - timedelta(days=90)
            files = self._get_log_files_in_range(start_time, None, log_type)

            for file_path in files:
                try:
                    response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
                    content = response["Body"].read()
                    if content:
                        for line in content.decode("utf-8").split("\n"):
                            if line.strip():
                                try:
                                    log_data = json.loads(line)
                                    if log_data.get("trace_id") == trace_id:
                                        logs.append(log_data)
                                except (json.JSONDecodeError, Exception) as e:
                                    self.logger.warning(
                                        "Failed to parse log line",
                                        file_path=file_path,
                                        error=str(e),
                                    )
                                    continue
                except ClientError as e:
                    if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                        continue
                    self.logger.warning(
                        "Failed to read log file",
                        file_path=file_path,
                        error=str(e),
                    )
                    continue

        # 按時間排序
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs

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
        查詢審計類型系統日誌

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
        files = self._get_log_files_in_range(start_time, end_time, LogType.AUDIT)
        logs: List[Dict[str, Any]] = []

        for file_path in files:
            try:
                response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
                content = response["Body"].read()
                if content:
                    for line in content.decode("utf-8").split("\n"):
                        if line.strip():
                            try:
                                log_data = json.loads(line)
                                # 過濾條件
                                if actor and log_data.get("actor") != actor:
                                    continue
                                if level and log_data.get("level") != level:
                                    continue
                                if tenant_id and log_data.get("tenant_id") != tenant_id:
                                    continue
                                if start_time or end_time:
                                    log_timestamp_str = log_data.get("timestamp", "")
                                    if log_timestamp_str:
                                        try:
                                            log_timestamp = datetime.fromisoformat(
                                                log_timestamp_str.replace("Z", "+00:00")
                                            )
                                            if start_time and log_timestamp < start_time:
                                                continue
                                            if end_time and log_timestamp > end_time:
                                                continue
                                        except Exception:
                                            continue
                                logs.append(log_data)
                            except (json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to parse log line",
                                    file_path=file_path,
                                    error=str(e),
                                )
                                continue
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                    continue
                self.logger.warning(
                    "Failed to read log file",
                    file_path=file_path,
                    error=str(e),
                )
                continue

        # 排序和分頁
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]

    async def get_security_logs(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢安全類型系統日誌

        Args:
            actor: 執行者（可選）
            action: 操作類型（可選）
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）
            limit: 返回數量限制

        Returns:
            安全日誌列表
        """
        files = self._get_log_files_in_range(start_time, end_time, LogType.SECURITY)
        logs: List[Dict[str, Any]] = []

        for file_path in files:
            try:
                response = self.storage.s3_client.get_object(Bucket=self.bucket, Key=file_path)
                content = response["Body"].read()
                if content:
                    for line in content.decode("utf-8").split("\n"):
                        if line.strip():
                            try:
                                log_data = json.loads(line)
                                # 過濾條件
                                if actor and log_data.get("actor") != actor:
                                    continue
                                if action and log_data.get("action") != action:
                                    continue
                                if start_time or end_time:
                                    log_timestamp_str = log_data.get("timestamp", "")
                                    if log_timestamp_str:
                                        try:
                                            log_timestamp = datetime.fromisoformat(
                                                log_timestamp_str.replace("Z", "+00:00")
                                            )
                                            if start_time and log_timestamp < start_time:
                                                continue
                                            if end_time and log_timestamp > end_time:
                                                continue
                                        except Exception:
                                            continue
                                logs.append(log_data)
                            except (json.JSONDecodeError, Exception) as e:
                                self.logger.warning(
                                    "Failed to parse log line",
                                    file_path=file_path,
                                    error=str(e),
                                )
                                continue
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                    continue
                self.logger.warning(
                    "Failed to read log file",
                    file_path=file_path,
                    error=str(e),
                )
                continue

        # 排序和分頁
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]
