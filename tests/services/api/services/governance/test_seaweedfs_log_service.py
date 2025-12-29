# 代碼功能說明: SeaweedFS 日誌服務單元測試
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 日誌服務單元測試 - 測試審計日誌和系統日誌服務"""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
from botocore.exceptions import ClientError

from services.api.core.log.log_service import LogType
from services.api.models.audit_log import AuditAction, AuditLogCreate
from services.api.services.governance.seaweedfs_log_service import (
    SeaweedFSAuditLogService,
    SeaweedFSSystemLogService,
)
from storage.s3_storage import S3FileStorage


class TestSeaweedFSAuditLogService:
    """SeaweedFSAuditLogService 測試類"""

    @pytest.fixture
    def mock_storage(self):
        """創建模擬 S3FileStorage"""
        storage = MagicMock(spec=S3FileStorage)
        storage.s3_client = MagicMock()
        storage.bucket = "bucket-governance-logs"
        return storage

    @pytest.fixture
    def audit_log_service(self, mock_storage):
        """創建 SeaweedFSAuditLogService 實例"""
        # 模擬 head_bucket 成功
        mock_storage.s3_client.head_bucket.return_value = None
        return SeaweedFSAuditLogService(storage=mock_storage)

    def test_get_log_file_path(self, audit_log_service):
        """測試日誌文件路徑生成"""
        timestamp = datetime(2025, 1, 27, 12, 0, 0)
        file_path = audit_log_service._get_log_file_path(timestamp, "audit")
        assert file_path == "audit/2025/01/27.jsonl"

    def test_get_log_files_in_range(self, audit_log_service):
        """測試獲取時間範圍內的日誌文件列表"""
        start_time = datetime(2025, 1, 25, 0, 0, 0)
        end_time = datetime(2025, 1, 27, 23, 59, 59)
        files = audit_log_service._get_log_files_in_range(start_time, end_time, "audit")
        assert len(files) == 3
        assert "audit/2025/01/25.jsonl" in files
        assert "audit/2025/01/26.jsonl" in files
        assert "audit/2025/01/27.jsonl" in files

    def test_get_log_files_in_range_default(self, audit_log_service):
        """測試獲取日誌文件列表（使用默認時間範圍）"""
        files = audit_log_service._get_log_files_in_range(None, None, "audit")
        assert len(files) > 0
        assert all(f.startswith("audit/") for f in files)

    def test_matches_filters_user_id(self, audit_log_service):
        """測試日誌過濾（用戶ID）"""
        log_data = {
            "user_id": "user-123",
            "action": "file_upload",
            "timestamp": "2025-01-27T12:00:00Z",
        }
        assert audit_log_service._matches_filters(log_data, "user-123", None, None, None) is True
        assert audit_log_service._matches_filters(log_data, "user-456", None, None, None) is False

    def test_matches_filters_action(self, audit_log_service):
        """測試日誌過濾（操作類型）"""
        log_data = {
            "user_id": "user-123",
            "action": "file_upload",
            "timestamp": "2025-01-27T12:00:00Z",
        }
        assert (
            audit_log_service._matches_filters(log_data, None, AuditAction.FILE_UPLOAD, None, None)
            is True
        )
        assert (
            audit_log_service._matches_filters(log_data, None, AuditAction.FILE_DELETE, None, None)
            is False
        )

    def test_matches_filters_time_range(self, audit_log_service):
        """測試日誌過濾（時間範圍）"""
        log_data = {
            "user_id": "user-123",
            "action": "file_upload",
            "timestamp": "2025-01-27T12:00:00Z",
        }
        start_time = datetime(2025, 1, 27, 0, 0, 0)
        end_time = datetime(2025, 1, 27, 23, 59, 59)
        assert (
            audit_log_service._matches_filters(log_data, None, None, start_time, end_time) is True
        )

        start_time = datetime(2025, 1, 28, 0, 0, 0)
        assert (
            audit_log_service._matches_filters(log_data, None, None, start_time, end_time) is False
        )

    @pytest.mark.asyncio
    async def test_create_audit_log_new_file(self, audit_log_service, mock_storage):
        """測試創建審計日誌（新文件）"""
        # 模擬文件不存在
        mock_storage.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        mock_storage.s3_client.put_object.return_value = {}

        log_create = AuditLogCreate(
            user_id="user-123",
            action=AuditAction.FILE_UPLOAD,
            resource_type="file",
            resource_id="file-456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            details={"filename": "test.txt"},
        )

        log_id = await audit_log_service.create_audit_log(log_create)

        assert log_id is not None
        assert "user-123" in log_id
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "bucket-governance-logs"
        assert call_args[1]["Key"].startswith("audit/")
        assert call_args[1]["Key"].endswith(".jsonl")

    @pytest.mark.asyncio
    async def test_create_audit_log_append_existing(self, audit_log_service, mock_storage):
        """測試創建審計日誌（追加到現有文件）"""
        # 模擬現有文件內容
        existing_content = b'{"user_id": "user-456", "action": "file_delete", "timestamp": "2025-01-27T10:00:00Z"}\n'
        mock_storage.s3_client.get_object.return_value = {
            "Body": Mock(read=lambda: existing_content)
        }
        mock_storage.s3_client.put_object.return_value = {}

        log_create = AuditLogCreate(
            user_id="user-123",
            action=AuditAction.FILE_UPLOAD,
            resource_type="file",
            resource_id="file-456",
        )

        log_id = await audit_log_service.create_audit_log(log_create)

        assert log_id is not None
        # 驗證新內容包含原有內容和新日誌
        call_args = mock_storage.s3_client.put_object.call_args
        new_content = call_args[1]["Body"]
        assert existing_content in new_content
        assert b"user-123" in new_content

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, audit_log_service, mock_storage):
        """測試查詢審計日誌"""
        # 模擬日誌文件內容
        log_content = b'{"user_id": "user-123", "action": "file_upload", "timestamp": "2025-01-27T12:00:00Z", "resource_type": "file", "resource_id": "file-456"}\n'
        mock_storage.s3_client.get_object.return_value = {"Body": Mock(read=lambda: log_content)}

        logs = await audit_log_service.get_audit_logs(user_id="user-123", limit=10)

        assert len(logs) == 1
        assert logs[0].user_id == "user-123"
        assert logs[0].action == AuditAction.FILE_UPLOAD

    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self, audit_log_service, mock_storage):
        """測試查詢審計日誌（帶過濾條件）"""
        log_content = b'{"user_id": "user-123", "action": "file_upload", "timestamp": "2025-01-27T12:00:00Z"}\n{"user_id": "user-456", "action": "file_delete", "timestamp": "2025-01-27T13:00:00Z"}\n'
        mock_storage.s3_client.get_object.return_value = {"Body": Mock(read=lambda: log_content)}

        logs = await audit_log_service.get_audit_logs(
            user_id="user-123", action=AuditAction.FILE_UPLOAD, limit=10
        )

        assert len(logs) == 1
        assert logs[0].user_id == "user-123"
        assert logs[0].action == AuditAction.FILE_UPLOAD

    @pytest.mark.asyncio
    async def test_get_audit_logs_file_not_exists(self, audit_log_service, mock_storage):
        """測試查詢審計日誌（文件不存在）"""
        mock_storage.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        logs = await audit_log_service.get_audit_logs(limit=10)

        assert len(logs) == 0


class TestSeaweedFSSystemLogService:
    """SeaweedFSSystemLogService 測試類"""

    @pytest.fixture
    def mock_storage(self):
        """創建模擬 S3FileStorage"""
        storage = MagicMock(spec=S3FileStorage)
        storage.s3_client = MagicMock()
        storage.bucket = "bucket-governance-logs"
        return storage

    @pytest.fixture
    def system_log_service(self, mock_storage):
        """創建 SeaweedFSSystemLogService 實例"""
        mock_storage.s3_client.head_bucket.return_value = None
        return SeaweedFSSystemLogService(storage=mock_storage)

    def test_get_log_file_path_task(self, system_log_service):
        """測試系統日誌文件路徑生成（TASK 類型）"""
        timestamp = datetime(2025, 1, 27, 12, 0, 0)
        file_path = system_log_service._get_log_file_path(timestamp, LogType.TASK)
        assert file_path == "system/task/2025/01/27.jsonl"

    def test_get_log_file_path_audit(self, system_log_service):
        """測試系統日誌文件路徑生成（AUDIT 類型）"""
        timestamp = datetime(2025, 1, 27, 12, 0, 0)
        file_path = system_log_service._get_log_file_path(timestamp, LogType.AUDIT)
        assert file_path == "system/audit/2025/01/27.jsonl"

    def test_get_log_file_path_security(self, system_log_service):
        """測試系統日誌文件路徑生成（SECURITY 類型）"""
        timestamp = datetime(2025, 1, 27, 12, 0, 0)
        file_path = system_log_service._get_log_file_path(timestamp, LogType.SECURITY)
        assert file_path == "system/security/2025/01/27.jsonl"

    def test_get_log_files_in_range(self, system_log_service):
        """測試獲取時間範圍內的系統日誌文件列表"""
        start_time = datetime(2025, 1, 25, 0, 0, 0)
        end_time = datetime(2025, 1, 27, 23, 59, 59)
        files = system_log_service._get_log_files_in_range(start_time, end_time, LogType.TASK)
        assert len(files) == 3
        assert all(f.startswith("system/task/") for f in files)

    @pytest.mark.asyncio
    async def test_log_event(self, system_log_service, mock_storage):
        """測試記錄系統日誌事件"""
        mock_storage.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        mock_storage.s3_client.put_object.return_value = {}

        log_id = await system_log_service.log_event(
            trace_id="trace-123",
            log_type=LogType.TASK,
            agent_name="test-agent",
            actor="user-123",
            action="test-action",
            content={"key": "value"},
        )

        assert log_id is not None
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "bucket-governance-logs"
        assert call_args[1]["Key"].startswith("system/task/")

    @pytest.mark.asyncio
    async def test_log_event_with_optional_fields(self, system_log_service, mock_storage):
        """測試記錄系統日誌事件（帶可選字段）"""
        mock_storage.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        mock_storage.s3_client.put_object.return_value = {}

        log_id = await system_log_service.log_event(
            trace_id="trace-123",
            log_type=LogType.AUDIT,
            agent_name="test-agent",
            actor="user-123",
            action="test-action",
            content={"key": "value"},
            level="system",
            tenant_id="tenant-123",
            user_id="user-123",
        )

        assert log_id is not None
        call_args = mock_storage.s3_client.put_object.call_args
        content = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert content["level"] == "system"
        assert content["tenant_id"] == "tenant-123"
        assert content["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_logs_by_trace_id(self, system_log_service, mock_storage):
        """測試根據 trace_id 查詢日誌"""
        log_content = (
            b'{"trace_id": "trace-123", "type": "TASK", "timestamp": "2025-01-27T12:00:00Z"}\n'
        )
        mock_storage.s3_client.get_object.return_value = {"Body": Mock(read=lambda: log_content)}

        logs = await system_log_service.get_logs_by_trace_id("trace-123")

        assert len(logs) > 0
        assert all(log["trace_id"] == "trace-123" for log in logs)

    @pytest.mark.asyncio
    async def test_get_audit_logs(self, system_log_service, mock_storage):
        """測試查詢審計類型系統日誌"""
        log_content = b'{"type": "AUDIT", "actor": "user-123", "level": "system", "timestamp": "2025-01-27T12:00:00Z"}\n'
        mock_storage.s3_client.get_object.return_value = {"Body": Mock(read=lambda: log_content)}

        logs = await system_log_service.get_audit_logs(actor="user-123", limit=10)

        assert len(logs) == 1
        assert logs[0]["actor"] == "user-123"
        assert logs[0]["type"] == "AUDIT"

    @pytest.mark.asyncio
    async def test_get_security_logs(self, system_log_service, mock_storage):
        """測試查詢安全類型系統日誌"""
        log_content = b'{"type": "SECURITY", "actor": "user-123", "action": "login", "timestamp": "2025-01-27T12:00:00Z"}\n'
        mock_storage.s3_client.get_object.return_value = {"Body": Mock(read=lambda: log_content)}

        logs = await system_log_service.get_security_logs(
            actor="user-123", action="login", limit=10
        )

        assert len(logs) == 1
        assert logs[0]["actor"] == "user-123"
        assert logs[0]["action"] == "login"
        assert logs[0]["type"] == "SECURITY"
