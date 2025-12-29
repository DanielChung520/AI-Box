"""
代碼功能說明: editing_session API 單元測試
創建日期: 2025-12-20 12:35:31 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:35:31 (UTC+8)
"""

from __future__ import annotations

import time

import pytest

from services.api.services.editing_session_service import EditingSession, EditingSessionService


@pytest.fixture
def mock_session_service() -> EditingSessionService:
    """創建模擬的 Session 服務"""
    service = EditingSessionService(ttl_seconds=3600)
    service._redis = None  # 使用內存 fallback
    return service


@pytest.fixture
def sample_session(mock_session_service: EditingSessionService) -> EditingSession:
    """創建示例 Session"""
    return mock_session_service.create_session(
        doc_id="test_doc_123",
        user_id="test_user_123",
        tenant_id="test_tenant_123",
        metadata={"test": "data"},
    )


class TestEditingSessionService:
    """測試 EditingSessionService"""

    def test_create_session(self, mock_session_service: EditingSessionService) -> None:
        """測試創建 Session"""
        session = mock_session_service.create_session(
            doc_id="test_doc",
            user_id="test_user",
            tenant_id="test_tenant",
        )
        assert session.session_id is not None
        assert session.doc_id == "test_doc"
        assert session.user_id == "test_user"
        assert session.tenant_id == "test_tenant"
        assert session.created_at_ms > 0

    def test_get_session(
        self, mock_session_service: EditingSessionService, sample_session: EditingSession
    ) -> None:
        """測試獲取 Session"""
        retrieved = mock_session_service.get_session(session_id=sample_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id
        assert retrieved.doc_id == sample_session.doc_id

    def test_get_nonexistent_session(self, mock_session_service: EditingSessionService) -> None:
        """測試獲取不存在的 Session"""
        result = mock_session_service.get_session(session_id="nonexistent")
        assert result is None

    def test_update_session(
        self, mock_session_service: EditingSessionService, sample_session: EditingSession
    ) -> None:
        """測試更新 Session"""
        import time

        original_updated_at = sample_session.updated_at_ms
        time.sleep(0.01)  # 確保時間戳不同
        updated = mock_session_service.update_session(
            session_id=sample_session.session_id,
            metadata={"new_key": "new_value"},
        )
        assert updated is not None
        assert updated.metadata.get("new_key") == "new_value"
        # 使用 >= 因為時間戳可能相同（如果更新太快）
        assert updated.updated_at_ms >= original_updated_at
        # 驗證 metadata 已更新
        assert "new_key" in updated.metadata

    def test_delete_session(
        self, mock_session_service: EditingSessionService, sample_session: EditingSession
    ) -> None:
        """測試刪除 Session"""
        deleted = mock_session_service.delete_session(session_id=sample_session.session_id)
        assert deleted is True

        # 驗證 Session 已被刪除
        result = mock_session_service.get_session(session_id=sample_session.session_id)
        assert result is None

    def test_session_expiration(self, mock_session_service: EditingSessionService) -> None:
        """測試 Session 過期"""
        # 創建一個立即過期的 Session
        session = mock_session_service.create_session(
            doc_id="test_doc",
            user_id="test_user",
            tenant_id="test_tenant",
            ttl_seconds=0,  # 立即過期
        )
        # 設置過期時間為過去
        session.expires_at_ms = time.time() * 1000.0 - 1000

        # 保存到 fallback
        with mock_session_service._lock:
            mock_session_service._fallback[session.session_id] = session

        # 獲取應該返回 None（因為已過期）
        result = mock_session_service.get_session(session_id=session.session_id)
        assert result is None

    def test_cleanup_expired_sessions(self, mock_session_service: EditingSessionService) -> None:
        """測試清理過期 Session"""
        # 創建一個過期的 Session
        session = mock_session_service.create_session(
            doc_id="test_doc",
            user_id="test_user",
            tenant_id="test_tenant",
        )
        session.expires_at_ms = time.time() * 1000.0 - 1000

        with mock_session_service._lock:
            mock_session_service._fallback[session.session_id] = session

        # 清理過期 Session
        cleaned = mock_session_service.cleanup_expired_sessions()
        assert cleaned == 1

        # 驗證 Session 已被刪除
        with mock_session_service._lock:
            assert session.session_id not in mock_session_service._fallback
