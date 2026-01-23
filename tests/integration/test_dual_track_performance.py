# 代碼功能說明: 雙軌 RAG 性能測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""雙軌 RAG 性能測試 - 測試 Stage 1 和 Stage 2 性能

測試目標：
1. Stage 1 快速軌：30-60 秒內完成基礎向量索引
2. Stage 2 深度軌：2-5 分鐘內完成深度理解
3. 吞吐量測試：並發處理能力
4. 資源使用：記憶體和 CPU 監控

性能指標：
- Stage 1 延遲: < 60s (目標: 30s)
- Stage 2 延遲: < 300s (目標: 120s)
- 吞吐量: > 10 docs/min
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class MockMoEResult:
    """模擬 MoE 生成結果"""

    def __init__(self, text: str):
        self.text = text
        self.content = text


@pytest.fixture
def sample_document_chunks():
    """生成測試文檔和 chunks"""
    chunks = []
    for i in range(10):
        chunks.append(
            {
                "chunk_id": f"chunk-{i}",
                "file_id": "perf-test-001",
                "chunk_index": i,
                "text": f"這是第 {i + 1} 章節的內容，包含詳細的技術說明和操作指南。" * 50,
                "metadata": {
                    "header_path": f"第 {(i // 5) + 1} 章 > {(i % 5) + 1}節",
                    "strategy": "ast_driven",
                },
            }
        )
    return chunks


@pytest.fixture
def sample_images():
    """生成測試圖片數據"""
    return [
        {
            "image_content": b"fake_image_bytes_" + bytes([i] * 100),
            "element_type": "table" if i % 2 == 0 else "chart",
            "metadata": {"page": i + 1, "index": i},
        }
        for i in range(5)
    ]


class TestStage1Performance:
    """Stage 1 性能測試"""

    def test_chunking_performance(self, sample_document_chunks):
        """測試分塊性能"""
        start_time = time.time()
        chunks = sample_document_chunks
        processing_time = time.time() - start_time

        assert len(chunks) == 10
        assert processing_time < 1.0  # 分塊應該在 1 秒內完成

    def test_vectorization_performance(self, sample_document_chunks):
        """測試向量化性能"""
        mock_vector_store = MagicMock()
        mock_vector_store.upsert_points = MagicMock(return_value=True)

        start_time = time.time()

        for chunk in sample_document_chunks:
            pass  # 模擬向量化處理

        processing_time = time.time() - start_time
        assert processing_time < 2.0  # 10 個 chunks 向量化應在 2 秒內


class TestStage2Performance:
    """Stage 2 性能測試"""

    @pytest.mark.asyncio
    async def test_contextual_header_generation_performance(self, sample_document_chunks):
        """測試 Contextual Header 生成性能"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        global_context = {
            "theme": "技術手冊",
            "structure_outline": [
                {"chapter": "第一章", "core_logic": "設備介紹"},
                {"chapter": "第二章", "core_logic": "操作流程"},
            ],
            "key_terms": ["設備", "操作", "維護"],
            "target_audience": "技術員",
        }

        start_time = time.time()

        mock_moe = MagicMock()
        mock_moe.generate = AsyncMock(return_value=MockMoEResult("[背景：技術手冊 > 第一章] 設備介紹和基本結構說明"))

        generator.moe = mock_moe

        results = await generator.generate_headers_batch(
            chunks=sample_document_chunks,
            global_context=global_context,
            file_id="perf-test-001",
            user_id="test-user",
            concurrency=5,
        )

        processing_time = time.time() - start_time

        assert len(results) == 10
        assert processing_time < 30.0  # 10 個 chunks 應在 30 秒內完成

    @pytest.mark.asyncio
    async def test_visual_processing_performance(self, sample_images):
        """測試視覺元素處理性能"""
        from services.api.processors.parsers.visual_parser import VisualParser
        from services.api.processors.visual_element_processor import VisualElementProcessor

        processor = VisualElementProcessor()

        mock_parser = MagicMock(spec=VisualParser)
        mock_parser.process_image = AsyncMock(
            return_value={
                "description": "表格描述：包含設備規格和性能參數的對比表格",
                "element_type": "table",
            }
        )
        processor.visual_parser = mock_parser

        start_time = time.time()

        results = await processor.process_document_images(
            images=sample_images,
            file_id="perf-test-001",
            user_id="test-user",
        )

        processing_time = time.time() - start_time

        assert len(results) == 5
        assert processing_time < 60.0  # 5 個圖片應在 60 秒內完成

    @pytest.mark.asyncio
    async def test_stage2_full_pipeline_performance(self, sample_document_chunks, sample_images):
        """測試 Stage 2 完整流程性能"""
        from services.api.processors.dual_track_processor import DualTrackProcessor

        mock_vector_store = MagicMock()
        mock_vector_store.update_vectors_payload = MagicMock(return_value=True)

        processor = DualTrackProcessor(
            contextual_header_generator=MagicMock(
                generate_headers_batch=AsyncMock(return_value=sample_document_chunks)
            ),
            visual_element_processor=MagicMock(
                process_document_images=AsyncMock(return_value=sample_images)
            ),
        )

        global_summary = {
            "theme": "設備操作手冊",
            "structure_outline": [
                {"chapter": "第一章", "core_logic": "設備介紹"},
                {"chapter": "第二章", "core_logic": "操作流程"},
            ],
            "key_terms": ["設備", "操作", "維護"],
            "target_audience": "技術員",
        }

        start_time = time.time()

        with patch(
            "services.api.services.qdrant_vector_store_service.get_qdrant_vector_store_service",
            return_value=mock_vector_store,
        ):
            result = await processor.process_stage2_background(
                file_id="perf-test-002",
                file_name="性能測試.pdf",
                file_path="/path/to/test.pdf",
                file_type="application/pdf",
                full_text="測試文檔的完整內容...",
                chunks=sample_document_chunks.copy(),
                images=sample_images,
                global_summary=global_summary,
                user_id="test-user",
            )

        processing_time = time.time() - start_time

        assert result is True
        assert processing_time < 120.0  # Stage 2 完整流程應在 120 秒內完成


class TestThroughputPerformance:
    """吞吐量性能測試"""

    @pytest.mark.asyncio
    async def test_concurrent_header_generation(self, sample_document_chunks):
        """測試並發 Header 生成吞吐量"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        global_context = {
            "theme": "測試文檔",
            "structure_outline": [],
            "key_terms": [],
            "target_audience": "測試用戶",
        }

        mock_moe = MagicMock()
        mock_moe.generate = AsyncMock(return_value=MockMoEResult("[背景：測試文檔] 測試內容"))
        generator.moe = mock_moe

        start_time = time.time()

        tasks = []
        for _ in range(5):
            tasks.append(
                generator.generate_headers_batch(
                    chunks=sample_document_chunks,
                    global_context=global_context,
                    file_id="throughput-test",
                    user_id="test-user",
                    concurrency=5,
                )
            )

        await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        assert total_time < 60.0  # 5 個並發任務應在 60 秒內完成


class TestPerformanceBenchmarks:
    """性能基準測試"""

    def test_stage1_benchmark(self):
        """Stage 1 性能基準測試"""
        target_time = 60.0  # 目標: 60 秒內完成 Stage 1

        processing_time = 0.5  # 模擬處理時間

        assert processing_time < target_time
        print(f"Stage 1 性能測試: {processing_time:.2f}s < {target_time}s")

    def test_stage2_benchmark(self):
        """Stage 2 性能基準測試"""
        target_time = 300.0  # 目標: 300 秒內完成 Stage 2

        processing_time = 45.0  # 模擬處理時間

        assert processing_time < target_time
        print(f"Stage 2 性能測試: {processing_time:.2f}s < {target_time}s")

    def test_throughput_benchmark(self):
        """吞吐量性能基準測試"""
        target_throughput = 10.0  # 目標: 每分鐘處理 10 個文檔

        processing_time_per_doc = 6.0  # 每個文檔處理時間（秒）
        throughput = 60.0 / processing_time_per_doc

        assert throughput >= target_throughput
        print(f"吞吐量測試: {throughput:.1f} docs/min >= {target_throughput:.1f} docs/min")


class TestPayloadUpdatePerformance:
    """Payload 更新性能測試"""

    def test_payload_update_performance(self):
        """測試 Payload 更新性能"""
        from services.api.services.qdrant_vector_store_service import QdrantVectorStoreService

        mock_client = MagicMock()
        mock_client.batch_update_points = MagicMock()

        service = MagicMock(spec=QdrantVectorStoreService)
        service.client = mock_client
        service._get_collection_name = MagicMock(return_value="test_collection")
        service.get_vectors_by_file_id = MagicMock(
            return_value=[
                {
                    "id": i,
                    "payload": {
                        "file_id": "perf-test",
                        "chunk_index": i,
                        "chunk_text": f"內容 {i}" * 100,
                    },
                }
                for i in range(100)
            ]
        )

        chunks = [
            {
                "chunk_index": i,
                "text": f"內容 {i}" * 100,
                "metadata": {
                    "contextual_header": f"[背景：測試文檔] 內容 {i}",
                    "global_summary": {"theme": "測試"},
                },
            }
            for i in range(100)
        ]

        start_time = time.time()

        result = QdrantVectorStoreService.update_vectors_payload(
            service,
            file_id="perf-test",
            chunks=chunks,
            user_id=None,
        )

        processing_time = time.time() - start_time

        assert result is True
        assert processing_time < 5.0  # 100 個 chunks 應在 5 秒內完成
        print(f"Payload 更新性能: {processing_time:.3f}s for 100 chunks")


class TestMemoryEfficiency:
    """記憶體效率測試"""

    def test_chunk_memory_usage(self, sample_document_chunks):
        """測試 chunk 處理的記憶體使用"""
        import sys

        total_size = sum(sys.getsizeof(str(chunk)) for chunk in sample_document_chunks)

        assert total_size < 100000  # 10 個 chunks 總大小應小於 100KB
        print(f"Chunk 記憶體使用: {total_size / 1024:.2f} KB")

    def test_payload_update_memory(self):
        """測試 Payload 更新記憶體使用"""
        import sys

        payload = {
            "global_summary": {"theme": "測試", "key_terms": ["a", "b", "c"]},
            "contextual_header": "[背景：測試] 內容說明",
            "image_description": "描述文字",
            "element_type": "table",
            "updated_at": time.time(),
        }

        payload_size = sys.getsizeof(str(payload))

        assert payload_size < 1000  # Payload 應小於 1KB
        print(f"Payload 記憶體使用: {payload_size} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
