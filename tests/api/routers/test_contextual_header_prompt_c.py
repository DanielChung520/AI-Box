# 代碼功能說明: Prompt C Contextual Header 整合員單元測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""Prompt C Contextual Header 整合員單元測試 - 測試 Contextual Header 生成功能

測試場景：
1. 正常生成 Contextual Header
2. 全局摘要整合
3. TOC 路徑整合
4. 批量處理優化
5. 回退機制
"""

from unittest.mock import AsyncMock, patch

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
def mock_moe_manager():
    """創建模擬的 MoE 管理器"""
    moe = AsyncMock()
    return moe


@pytest.fixture
def sample_global_context():
    """範例：全局背景摘要"""
    return {
        "theme": "國琿機械熱解爐操作手冊",
        "structure_outline": [
            {"chapter": "產品介紹", "core_logic": "介紹熱解爐設備和技術原理"},
            {"chapter": "安全注意事項", "core_logic": "說明操作安全規範"},
            {"chapter": "操作流程", "core_logic": "詳細步驟指引"},
            {"chapter": "維護保養", "core_logic": "設備維護指南"},
        ],
        "key_terms": ["熱解爐", "高溫熱解", "廢棄物處理", "能源轉化", "操作人員"],
        "target_audience": "技術員",
    }


@pytest.fixture
def sample_chunk():
    """範例：chunk 數據"""
    return {
        "chunk_id": "chunk-123",
        "file_id": "file-456",
        "chunk_index": 0,
        "text": "集塵器是熱解爐的重要組件，需要定期清理以確保設備正常運行。建議每週清理一次，並檢查濾網是否損壞。",
        "metadata": {
            "header_path": "維護手冊 > 集塵器清理",
            "start_position": 1000,
            "end_position": 1150,
            "strategy": "ast_driven",
        },
    }


@pytest.fixture
def sample_chunks():
    """範例：多個 chunks"""
    return [
        {
            "chunk_id": "chunk-1",
            "file_id": "file-123",
            "chunk_index": 0,
            "text": "這是第一章節的內容，討論設備的基本結構。",
            "metadata": {"header_path": "第1章 > 1.1節"},
        },
        {
            "chunk_id": "chunk-2",
            "file_id": "file-123",
            "chunk_index": 1,
            "text": "這是第二章節的內容，說明操作流程。",
            "metadata": {"header_path": "第2章 > 2.1節"},
        },
        {
            "chunk_id": "chunk-3",
            "file_id": "file-123",
            "chunk_index": 2,
            "text": "這是第三章節的內容，講解維護方法。",
            "metadata": {"header_path": "第3章 > 3.1節"},
        },
    ]


class TestContextualHeaderGenerator:
    """測試 ContextualHeaderGenerator 類"""

    @pytest.mark.asyncio
    async def test_generate_header_success(
        self, mock_moe_manager, sample_global_context, sample_chunk
    ):
        """測試正常生成 Contextual Header"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_response = "[國琿機械熱解爐操作手冊 > 維護手冊 > 集塵器清理] 說明集塵器的清理頻率與注意事項"
        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=sample_global_context,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert header is not None
        assert len(header) <= 50
        assert "集塵器" in header or "清理" in header

    @pytest.mark.asyncio
    async def test_generate_header_with_empty_context(self, mock_moe_manager, sample_chunk):
        """測試空全局背景"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_response = "[未指定背景 > 維護手冊] 相關內容"
        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=None,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert header is not None

    @pytest.mark.asyncio
    async def test_generate_header_with_empty_toc_path(
        self, mock_moe_manager, sample_global_context, sample_chunk
    ):
        """測試空 TOC 路徑"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_response = "[國琿機械熱解爐操作手冊] 相關內容"
        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=sample_global_context,
                toc_path=None,
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert header is not None

    @pytest.mark.asyncio
    async def test_generate_header_llm_exception(
        self, mock_moe_manager, sample_global_context, sample_chunk
    ):
        """測試 LLM 調用異常時的回退機制"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_moe_manager.generate = AsyncMock(side_effect=Exception("LLM 不可用"))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=sample_global_context,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert header is not None
        assert "相關內容" in header or "國琿機械" in header

    @pytest.mark.asyncio
    async def test_generate_header_empty_response(
        self, mock_moe_manager, sample_global_context, sample_chunk
    ):
        """測試 LLM 返回空結果時的回退機制"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(""))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=sample_global_context,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert header is not None

    @pytest.mark.asyncio
    async def test_generate_headers_batch(
        self, mock_moe_manager, sample_global_context, sample_chunks
    ):
        """測試批量生成 Contextual Headers"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        mock_response = "[第1章 > 1.1節] 設備基本結構說明"
        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            updated_chunks = await generator.generate_headers_batch(
                chunks=[c.copy() for c in sample_chunks],
                global_context=sample_global_context,
                file_id="file-123",
                user_id="user-456",
                concurrency=2,
            )

        assert len(updated_chunks) == len(sample_chunks)
        for chunk in updated_chunks:
            assert "contextual_header" in chunk["metadata"]
            assert chunk["metadata"]["contextual_header"] is not None


class TestContextualHeaderGeneratorSync:
    """測試同步 Contextual Header 生成方法"""

    def test_format_global_context(self, sample_global_context):
        """測試格式化全局背景"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()
        formatted = generator._format_global_context(sample_global_context)

        assert "國琿機械熱解爐操作手冊" in formatted
        assert "技術員" in formatted
        assert "熱解爐" in formatted

    def test_format_global_context_empty(self):
        """測試格式化空全局背景"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()
        formatted = generator._format_global_context({})
        assert formatted == "未指定背景"

        formatted = generator._format_global_context(None)
        assert formatted == "未指定背景"

    def test_format_toc_path(self):
        """測試格式化 TOC 路徑"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        formatted = generator._format_toc_path("維護手冊 > 集塵器清理")
        assert formatted == "維護手冊 > 集塵器清理"

        formatted = generator._format_toc_path(None)
        assert formatted == "未指定章節"

    def test_generate_header_sync(self, sample_global_context):
        """測試同步生成 Contextual Header"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        header = generator.generate_header_sync(
            global_context=sample_global_context,
            toc_path="維護手冊 > 集塵器清理",
            raw_chunk_content="這是一些內容",
        )

        assert header is not None
        assert "國琿機械熱解爐操作手冊" in header
        assert "維護手冊" in header

    def test_generate_header_sync_empty(self):
        """測試同步生成空 Contextual Header"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        header = generator.generate_header_sync(
            global_context=None,
            toc_path=None,
            raw_chunk_content="這是一些內容",
        )

        assert header == ""

    def test_truncate_to_limit(self):
        """測試截斷到指定長度"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        long_text = "這是一個非常長的文本，超過了五十個字符的限制，需要進行截斷處理"
        truncated = generator._truncate_to_limit(long_text, max_chars=30)

        assert len(truncated) <= 30

        text_with_break_point = "這是一個測試文本，有空格可以作為截斷點，超過了長度限制需要被截斷"
        truncated2 = generator._truncate_to_limit(text_with_break_point, max_chars=20)
        assert len(truncated2) <= 20

    def test_update_chunks_with_headers(self, sample_global_context, sample_chunks):
        """測試同步更新 chunks"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        updated_chunks = generator.update_chunks_with_headers(
            chunks=[c.copy() for c in sample_chunks],
            global_context=sample_global_context,
        )

        assert len(updated_chunks) == len(sample_chunks)
        for chunk in updated_chunks:
            assert "contextual_header" in chunk["metadata"]
            assert chunk["metadata"]["contextual_header"] is not None


class TestPromptCSpecificationCompliance:
    """測試 Prompt C 規格遵循"""

    @pytest.mark.asyncio
    async def test_header_length_limit(self, mock_moe_manager, sample_global_context, sample_chunk):
        """測試 Header 長度限制在 50 字以內"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        long_header = "這是一個非常長的標題，超過了五十個字符的限制，需要被截斷以符合規格要求"
        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(long_header))

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            header = await generator.generate_header(
                global_context=sample_global_context,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert len(header) <= 50

    @pytest.mark.asyncio
    async def test_prompt_contains_all_required_fields(
        self, mock_moe_manager, sample_global_context, sample_chunk
    ):
        """測試 Prompt 包含所有必要字段"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        captured_prompt = None

        async def capture_prompt(*args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = args[0] if args else kwargs.get("prompt", "")
            return MockMoEResult("[測試] 內容")

        mock_moe_manager.generate = AsyncMock(side_effect=capture_prompt)

        with patch(
            "services.api.processors.contextual_header_generator.LLMMoEManager",
            return_value=mock_moe_manager,
        ):
            generator = ContextualHeaderGenerator(moe_manager=mock_moe_manager)

            await generator.generate_header(
                global_context=sample_global_context,
                toc_path="維護手冊 > 集塵器清理",
                raw_chunk_content=sample_chunk["text"],
                file_id="file-123",
                user_id="user-456",
            )

        assert captured_prompt is not None
        assert "全局背景" in captured_prompt or "global_context" in captured_prompt
        assert "目錄路徑" in captured_prompt or "toc_path" in captured_prompt
        assert "段落內容" in captured_prompt or "chunk_content" in captured_prompt
        assert "50" in captured_prompt or "五十" in captured_prompt

    def test_fallback_header_format(self, sample_global_context):
        """測試回退 Header 格式"""
        from services.api.processors.contextual_header_generator import ContextualHeaderGenerator

        generator = ContextualHeaderGenerator()

        fallback = generator._generate_fallback_header(
            global_context=sample_global_context,
            toc_path="維護手冊 > 集塵器清理",
        )

        assert "國琿機械熱解爐操作手冊" in fallback
        assert "維護手冊" in fallback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
