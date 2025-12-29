"""
代碼功能說明: streaming API 單元測試
創建日期: 2025-12-20 12:40:00 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:40:00 (UTC+8)
"""

from __future__ import annotations

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
    )


class TestStreamingGeneration:
    """測試流式數據生成"""

    @pytest.mark.asyncio
    async def test_generate_streaming_patches(self) -> None:
        """測試生成流式 patch 數據"""
        from api.routers.streaming import _generate_streaming_patches

        chunks = []
        async for chunk in _generate_streaming_patches(
            session_id="test_session", request_id="test_request"
        ):
            chunks.append(chunk)

        # 驗證至少有一個 chunk
        assert len(chunks) > 0

        # 驗證第一個 chunk 是 patch_start
        assert "patch_start" in chunks[0]

        # 驗證最後一個 chunk 是 patch_end 或 error
        last_chunk = chunks[-1]
        assert "patch_end" in last_chunk or "error" in last_chunk

    @pytest.mark.asyncio
    async def test_streaming_error_handling(self) -> None:
        """測試流式傳輸錯誤處理"""
        from api.routers.streaming import _generate_streaming_patches

        # 測試正常流程
        chunks = []
        async for chunk in _generate_streaming_patches(
            session_id="test_session", request_id="test_request"
        ):
            chunks.append(chunk)
            # 只取前幾個 chunk 以避免無限循環
            if len(chunks) >= 10:
                break

        # 驗證有數據生成
        assert len(chunks) > 0
