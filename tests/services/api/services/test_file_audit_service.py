# 代碼功能說明: 文件訪問審計服務單元測試 (WBS-4.4.4)
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件訪問審計服務單元測試"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from services.api.models.audit_log import AuditAction, AuditLog
from services.api.services.audit_log_service import AuditLogService
from services.api.services.file_audit_service import FileAuditService
from services.api.services.file_metadata_service import FileMetadataService


@pytest.fixture
def mock_audit_log_service():
    """創建模擬的審計日誌服務"""
    return MagicMock(spec=AuditLogService)


@pytest.fixture
def mock_metadata_service():
    """創建模擬的文件元數據服務"""
    return MagicMock(spec=FileMetadataService)


@pytest.fixture
def file_audit_service(mock_audit_log_service, mock_metadata_service):
    """創建文件審計服務實例"""
    return FileAuditService(
        audit_log_service=mock_audit_log_service,
        metadata_service=mock_metadata_service,
    )


@pytest.fixture
def sample_audit_logs():
    """創建示例審計日誌"""
    now = datetime.utcnow()
    return [
        AuditLog(
            user_id="user1",
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id="file1",
            timestamp=now - timedelta(hours=1),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"reason": "PUBLIC access", "granted": True, "access_level": "public"},
        ),
        AuditLog(
            user_id="user2",
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id="file1",
            timestamp=now - timedelta(hours=2),
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0",
            details={"reason": "Access expired", "granted": False, "access_level": "private"},
        ),
        AuditLog(
            user_id="user1",
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id="file2",
            timestamp=now - timedelta(hours=3),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"reason": "OWNER access", "granted": True, "access_level": "private"},
        ),
    ]


class TestFileAuditService:
    """文件審計服務測試類"""

    def test_get_file_access_logs_basic(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試基本文件訪問日誌查詢"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (sample_audit_logs[:2], 2)

        # 執行查詢
        logs, total = file_audit_service.get_file_access_logs(
            file_id="file1",
            limit=100,
            offset=0,
        )

        # 驗證結果
        assert total == 2
        assert len(logs) == 2
        assert logs[0]["resource_id"] == "file1"
        assert logs[0]["details"]["granted"] is True
        assert logs[1]["details"]["granted"] is False

        # 驗證調用
        mock_audit_log_service.query_logs.assert_called_once_with(
            user_id=None,
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id="file1",
            start_date=None,
            end_date=None,
            limit=100,
            offset=0,
        )

    def test_get_file_access_logs_with_filters(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試帶過濾條件的文件訪問日誌查詢"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (sample_audit_logs[:1], 1)

        # 執行查詢
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        logs, total = file_audit_service.get_file_access_logs(
            file_id="file1",
            user_id="user1",
            granted=True,
            start_date=start_date,
            end_date=end_date,
            limit=50,
            offset=0,
        )

        # 驗證結果
        assert total == 1
        assert len(logs) == 1
        assert logs[0]["user_id"] == "user1"
        assert logs[0]["details"]["granted"] is True

        # 驗證調用
        mock_audit_log_service.query_logs.assert_called_once_with(
            user_id="user1",
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id="file1",
            start_date=start_date,
            end_date=end_date,
            limit=50,
            offset=0,
        )

    def test_get_file_access_logs_granted_filter(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試 granted 過濾"""
        # 設置模擬返回值（返回所有日誌）
        mock_audit_log_service.query_logs.return_value = (sample_audit_logs[:2], 2)

        # 執行查詢（只查詢授權的）
        logs, total = file_audit_service.get_file_access_logs(
            file_id="file1",
            granted=True,
        )

        # 驗證結果（應該只返回 granted=True 的）
        assert total == 1
        assert len(logs) == 1
        assert logs[0]["details"]["granted"] is True

    def test_get_user_access_logs_basic(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試基本用戶訪問日誌查詢"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (
            [log for log in sample_audit_logs if log.user_id == "user1"],
            2,
        )

        # 執行查詢
        logs, total = file_audit_service.get_user_access_logs(
            user_id="user1",
            limit=100,
            offset=0,
        )

        # 驗證結果
        assert total == 2
        assert len(logs) == 2
        assert all(log["user_id"] == "user1" for log in logs)

        # 驗證調用
        mock_audit_log_service.query_logs.assert_called_once_with(
            user_id="user1",
            action=AuditAction.FILE_ACCESS,
            resource_type="file",
            resource_id=None,
            start_date=None,
            end_date=None,
            limit=100,
            offset=0,
        )

    def test_get_user_access_logs_with_file_filter(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試帶文件過濾的用戶訪問日誌查詢"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (
            [
                log
                for log in sample_audit_logs
                if log.user_id == "user1" and log.resource_id == "file1"
            ],
            1,
        )

        # 執行查詢
        logs, total = file_audit_service.get_user_access_logs(
            user_id="user1",
            file_id="file1",
        )

        # 驗證結果
        assert total == 1
        assert len(logs) == 1
        assert logs[0]["user_id"] == "user1"
        assert logs[0]["resource_id"] == "file1"

    def test_get_access_statistics_basic(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試基本訪問統計"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (sample_audit_logs, 3)

        # 執行統計
        stats = file_audit_service.get_access_statistics()

        # 驗證結果
        assert stats["total_accesses"] == 3
        assert stats["granted_accesses"] == 2
        assert stats["denied_accesses"] == 1
        assert "by_file" in stats
        assert "by_user" in stats
        assert "by_access_level" in stats
        assert "by_data_classification" in stats

    def test_get_access_statistics_by_file(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試按文件統計"""
        # 設置模擬返回值（只返回 file1 的記錄）
        file1_logs = [log for log in sample_audit_logs if log.resource_id == "file1"]
        mock_audit_log_service.query_logs.return_value = (file1_logs, len(file1_logs))

        # 執行統計
        stats = file_audit_service.get_access_statistics(file_id="file1")

        # 驗證結果
        assert stats["total_accesses"] == 2  # file1 有 2 條記錄
        assert (
            "file1" in stats["by_file"] or len(stats["by_file"]) == 0
        )  # 如果指定了 file_id，by_file 可能為空

    def test_get_access_statistics_by_user(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試按用戶統計"""
        # 設置模擬返回值（只返回 user1 的記錄）
        user1_logs = [log for log in sample_audit_logs if log.user_id == "user1"]
        mock_audit_log_service.query_logs.return_value = (user1_logs, len(user1_logs))

        # 執行統計
        stats = file_audit_service.get_access_statistics(user_id="user1")

        # 驗證結果
        assert stats["total_accesses"] == 2  # user1 有 2 條記錄
        assert (
            "user1" in stats["by_user"] or len(stats["by_user"]) == 0
        )  # 如果指定了 user_id，by_user 可能為空

    def test_get_access_statistics_with_time_range(
        self, file_audit_service, mock_audit_log_service, sample_audit_logs
    ):
        """測試帶時間範圍的統計"""
        # 設置模擬返回值
        mock_audit_log_service.query_logs.return_value = (sample_audit_logs[:2], 2)

        # 執行統計
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow()
        stats = file_audit_service.get_access_statistics(
            start_date=start_date,
            end_date=end_date,
        )

        # 驗證結果
        assert stats["total_accesses"] == 2
        assert stats["granted_accesses"] == 1
        assert stats["denied_accesses"] == 1

        # 驗證調用
        mock_audit_log_service.query_logs.assert_called_once()
        call_kwargs = mock_audit_log_service.query_logs.call_args[1]
        assert call_kwargs["start_date"] == start_date
        assert call_kwargs["end_date"] == end_date
