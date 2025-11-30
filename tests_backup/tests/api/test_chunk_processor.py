# 代碼功能說明: 文件分塊處理器測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件分塊處理器測試"""

from services.api.processors.chunk_processor import (
    ChunkProcessor,
    ChunkStrategy,
)


def test_fixed_size_chunk():
    """測試固定大小分塊"""
    processor = ChunkProcessor(chunk_size=100, strategy=ChunkStrategy.FIXED_SIZE)
    text = "a" * 250  # 250 個字符

    chunks = processor.process(text, "test_file_id")

    assert len(chunks) == 3  # 100 + 100 + 50
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[2]["chunk_index"] == 2
    assert len(chunks[0]["text"]) == 100
    assert len(chunks[2]["text"]) == 50


def test_sliding_window_chunk():
    """測試滑動窗口分塊"""
    processor = ChunkProcessor(
        chunk_size=100, overlap=0.2, strategy=ChunkStrategy.SLIDING_WINDOW
    )
    text = "a" * 250

    chunks = processor.process(text, "test_file_id")

    # 步長為 80，應該有更多塊
    assert len(chunks) > 2
    assert chunks[0]["chunk_index"] == 0


def test_semantic_chunk():
    """測試語義分塊"""
    processor = ChunkProcessor(chunk_size=50, strategy=ChunkStrategy.SEMANTIC)
    text = "這是第一段。\n\n這是第二段。\n\n這是第三段。"

    chunks = processor.process(text, "test_file_id")

    # 應該按段落分塊
    assert len(chunks) >= 1
    assert all("chunk_id" in chunk for chunk in chunks)
    assert all("file_id" in chunk for chunk in chunks)


def test_chunk_metadata():
    """測試分塊元數據"""
    processor = ChunkProcessor(chunk_size=100)
    text = "測試文本內容"

    chunks = processor.process(text, "test_file_id", metadata={"source": "test"})

    assert len(chunks) > 0
    assert "metadata" in chunks[0]
    assert chunks[0]["metadata"]["source"] == "test"
    assert "start_position" in chunks[0]["metadata"]
    assert "end_position" in chunks[0]["metadata"]
