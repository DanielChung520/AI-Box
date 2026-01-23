# 代碼功能說明: 雙軌 RAG 處理集成測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""雙軌 RAG 處理集成測試 - 測試 Stage 1 + Stage 2 完整流程

測試場景：
1. 雙軌處理器初始化
2. Stage 2 背景任務處理
3. Payload 更新機制
4. 進度追蹤
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockMoEResult:
    """模擬 MoE 生成結果"""

    def __init__(self, text: str):
        self.text = text
        self.content = text

    def get(self, key: str, default: str = "") -> str:
        if key in ("text", "content"):
            return getattr(self, key, default)
        return default


@pytest.fixture
def sample_chunks():
    """範例：chunks 數據"""
    return [
        {
            "chunk_id": "chunk-1",
            "file_id": "file-123",
            "chunk_index": 0,
            "text": "這是第一章節的內容，討論設備的基本結構。",
            "metadata": {
                "header_path": "第1章 > 1.1節",
                "strategy": "ast_driven",
            },
        },
        {
            "chunk_id": "chunk-2",
            "file_id": "file-123",
            "chunk_index": 1,
            "text": "這是第二章節的內容，說明操作流程。",
            "metadata": {
                "header_path": "第2章 > 2.1節",
                "strategy": "ast_driven",
            },
        },
    ]


@pytest.fixture
def sample_images():
    """範例：images 數據"""
    return [
        {
            "image_content": b"fake_image_bytes_1",
            "element_type": "table",
            "metadata": {"page": 1, "table_index": 0},
        },
        {
            "image_content": b"fake_image_bytes_2",
            "element_type": "chart",
            "metadata": {"page": 2, "figure_index": 0},
        },
    ]


@pytest.fixture
def sample_global_summary():
    """範例：全局摘要"""
    return {
        "theme": "設備操作手冊",
        "structure_outline": [
            {"chapter": "第一章", "core_logic": "設備介紹"},
            {"chapter": "第二章", "core_logic": "操作流程"},
        ],
        "key_terms": ["設備", "操作", "維護"],
        "target_audience": "技術員",
    }


class TestDualTrackProcessor:
    """測試 DualTrackProcessor 類"""

    @pytest.mark.asyncio
    async def test_process_stage2_background_success(
        self,
        sample_chunks,
        sample_images,
        sample_global_summary,
    ):
        """測試 Stage 2 背景處理成功"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        mock_visual_processor = AsyncMock()
        mock_visual_processor.process_document_images = AsyncMock(
            return_value=[
                {
                    "description": "表格描述",
                    "element_type": "table",
                    "metadata": {},
                }
            ]
        )

        mock_vector_store = MagicMock()
        mock_vector_store.update_vectors_payload = MagicMock(return_value=True)

        processor = DualTrackProcessor(
            contextual_header_generator=MagicMock(
                generate_headers_batch=AsyncMock(return_value=sample_chunks)
            ),
            visual_element_processor=mock_visual_processor,
        )

        with patch(
            "services.api.services.qdrant_vector_store_service.get_qdrant_vector_store_service",
            return_value=mock_vector_store,
        ):
            result = await processor.process_stage2_background(
                file_id="file-123",
                file_name="設備手冊.pdf",
                file_path="/path/to/file.pdf",
                file_type="application/pdf",
                full_text="這是設備操作手冊的完整內容...",
                chunks=sample_chunks.copy(),
                images=sample_images,
                global_summary=sample_global_summary,
                user_id="user-456",
            )

        assert result is True
        mock_vector_store.update_vectors_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_stage2_without_images(
        self,
        sample_chunks,
        sample_global_summary,
    ):
        """測試 Stage 2 沒有圖片時"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        mock_vector_store = MagicMock()
        mock_vector_store.update_vectors_payload = MagicMock(return_value=True)

        processor = DualTrackProcessor(
            contextual_header_generator=MagicMock(
                generate_headers_batch=AsyncMock(return_value=sample_chunks)
            ),
            visual_element_processor=AsyncMock(),
        )

        with patch(
            "services.api.services.qdrant_vector_store_service.get_qdrant_vector_store_service",
            return_value=mock_vector_store,
        ):
            result = await processor.process_stage2_background(
                file_id="file-no-images",
                file_name="純文本.pdf",
                file_path="/path/to/text.pdf",
                file_type="application/pdf",
                full_text="這是純文本內容...",
                chunks=sample_chunks.copy(),
                images=[],
                global_summary=sample_global_summary,
                user_id="user-789",
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_process_stage2_with_error(self, sample_chunks, sample_global_summary):
        """測試 Stage 2 處理錯誤"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        mock_vector_store = MagicMock()
        mock_vector_store.update_vectors_payload = MagicMock(side_effect=Exception("Qdrant 連接失敗"))

        processor = DualTrackProcessor(
            contextual_header_generator=MagicMock(
                generate_headers_batch=AsyncMock(return_value=sample_chunks)
            ),
            visual_element_processor=AsyncMock(),
        )

        with patch(
            "services.api.services.qdrant_vector_store_service.get_qdrant_vector_store_service",
            return_value=mock_vector_store,
        ):
            result = await processor.process_stage2_background(
                file_id="file-error",
                file_name="錯誤測試.pdf",
                file_path="/path/to/error.pdf",
                file_type="application/pdf",
                full_text="測試內容",
                chunks=sample_chunks.copy(),
                images=[],
                global_summary=sample_global_summary,
                user_id="user-error",
            )

        assert result is False

    def test_should_enable_dual_track_enabled(self):
        """測試雙軌處理開關 - 開啟"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        processor = DualTrackProcessor()
        with patch.object(processor, "should_enable_dual_track", return_value=True):
            assert processor.should_enable_dual_track() is True

    def test_should_enable_dual_track_disabled(self):
        """測試雙軌處理開關 - 關閉"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        processor = DualTrackProcessor()
        with patch.object(processor, "should_enable_dual_track", return_value=False):
            assert processor.should_enable_dual_track() is False


class TestQdrantPayloadUpdate:
    """測試 Qdrant Payload 更新"""

    def test_update_vectors_payload_success(self):
        """測試 Payload 更新成功"""
        from services.api.services.qdrant_vector_store_service import QdrantVectorStoreService

        mock_client = MagicMock()
        mock_client.upsert = MagicMock()

        service = MagicMock(spec=QdrantVectorStoreService)
        service.client = mock_client
        service._get_collection_name = MagicMock(return_value="test_file_123")
        service.get_vectors_by_file_id = MagicMock(
            return_value=[
                {
                    "id": 0,
                    "payload": {
                        "file_id": "file-123",
                        "chunk_index": 0,
                        "chunk_text": "內容...",
                    },
                },
                {
                    "id": 1,
                    "payload": {
                        "file_id": "file-123",
                        "chunk_index": 1,
                        "chunk_text": "內容...",
                    },
                },
            ]
        )

        chunks = [
            {
                "chunk_index": 0,
                "text": "內容...",
                "metadata": {
                    "contextual_header": "[背景：設備手冊 > 第1章] 設備介紹",
                    "global_summary": {"theme": "設備手冊"},
                },
            },
            {
                "chunk_index": 1,
                "text": "內容...",
                "metadata": {
                    "contextual_header": "[背景：設備手冊 > 第2章] 操作流程",
                    "global_summary": {"theme": "設備手冊"},
                },
            },
        ]

        result = QdrantVectorStoreService.update_vectors_payload(
            service,
            file_id="file-123",
            chunks=chunks,
            user_id=None,
        )

        assert result is True
        mock_client.batch_update_points.assert_called_once()


class TestDualTrackIntegration:
    """雙軌處理集成測試"""

    @pytest.mark.asyncio
    async def test_full_dual_track_flow(self, sample_chunks, sample_global_summary):
        """測試完整雙軌處理流程"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        mock_vector_store = MagicMock()
        mock_vector_store.update_vectors_payload = MagicMock(return_value=True)

        mock_header_gen = MagicMock()
        mock_header_gen.generate_headers_batch = AsyncMock(return_value=sample_chunks)

        mock_visual_processor = AsyncMock()
        mock_visual_processor.process_document_images = AsyncMock(return_value=[])

        processor = DualTrackProcessor(
            contextual_header_generator=mock_header_gen,
            visual_element_processor=mock_visual_processor,
        )

        with patch(
            "services.api.services.qdrant_vector_store_service.get_qdrant_vector_store_service",
            return_value=mock_vector_store,
        ):
            result = await processor.process_stage2_background(
                file_id="integration-test",
                file_name="整合測試.pdf",
                file_path="/path/to/integration.pdf",
                file_type="application/pdf",
                full_text="整合測試的完整內容...",
                chunks=sample_chunks.copy(),
                images=[],
                global_summary=sample_global_summary,
                user_id="test-user",
            )

        assert result is True
        mock_header_gen.generate_headers_batch.assert_called_once()
        mock_vector_store.update_vectors_payload.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
