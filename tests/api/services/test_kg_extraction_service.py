# 代碼功能說明: 知識圖譜提取服務測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""知識圖譜提取服務單元測試 - 測試三元組提取、圖譜構建、去重"""

from unittest.mock import AsyncMock, patch

import pytest

from services.api.services.kg_extraction_service import KGExtractionService


@pytest.fixture
def kg_extraction_service():
    """創建知識圖譜提取服務實例"""
    with patch(
        "services.api.services.kg_extraction_service.TripleExtractionService"
    ) as mock_triple, patch(
        "services.api.services.kg_extraction_service.KGBuilderService"
    ) as mock_kg_builder:
        service = KGExtractionService()
        service.triple_extraction_service = mock_triple.return_value
        service.kg_builder_service = mock_kg_builder.return_value
        yield service


@pytest.mark.asyncio
async def test_extract_triples_from_chunks_all_mode(kg_extraction_service):
    """測試從所有分塊提取三元組"""
    chunks = [
        {"text": "蘋果是一種水果", "metadata": {"chunk_index": 0}},
        {"text": "蘋果富含維生素C", "metadata": {"chunk_index": 1}},
    ]

    mock_triples = [
        {"subject": "蘋果", "predicate": "是", "object": "水果", "confidence": 0.9},
        {
            "subject": "蘋果",
            "predicate": "富含",
            "object": "維生素C",
            "confidence": 0.8,
        },
    ]

    kg_extraction_service.triple_extraction_service.extract_triples = AsyncMock(
        return_value=mock_triples
    )

    options = {
        "mode": "all_chunks",
        "min_confidence": 0.5,
    }

    result = await kg_extraction_service.extract_triples_from_chunks(chunks, options)

    assert len(result) == 2
    assert all("subject" in t and "predicate" in t and "object" in t for t in result)


@pytest.mark.asyncio
async def test_extract_triples_from_chunks_selected_mode(kg_extraction_service):
    """測試從選定分塊提取三元組"""
    chunks = [
        {"text": "蘋果是一種水果", "metadata": {"chunk_index": 0}},
        {"text": "蘋果富含維生素C", "metadata": {"chunk_index": 1}},
    ]

    mock_triples = [
        {"subject": "蘋果", "predicate": "是", "object": "水果", "confidence": 0.9},
    ]

    kg_extraction_service.triple_extraction_service.extract_triples = AsyncMock(
        return_value=mock_triples
    )

    options = {
        "mode": "selected_chunks",
        "min_confidence": 0.5,
        "selected_chunk_indices": [0],
    }

    result = await kg_extraction_service.extract_triples_from_chunks(chunks, options)

    assert len(result) == 1
    kg_extraction_service.triple_extraction_service.extract_triples.assert_called_once()


@pytest.mark.asyncio
async def test_extract_triples_deduplication(kg_extraction_service):
    """測試三元組去重"""
    chunks = [
        {"text": "蘋果是一種水果", "metadata": {"chunk_index": 0}},
    ]

    # 模擬重複的三元組（不同置信度）
    mock_triples = [
        {"subject": "蘋果", "predicate": "是", "object": "水果", "confidence": 0.8},
        {
            "subject": "蘋果",
            "predicate": "是",
            "object": "水果",
            "confidence": 0.9,
        },  # 重複但置信度更高
    ]

    kg_extraction_service.triple_extraction_service.extract_triples = AsyncMock(
        return_value=mock_triples
    )

    options = {
        "mode": "all_chunks",
        "min_confidence": 0.5,
    }

    result = await kg_extraction_service.extract_triples_from_chunks(chunks, options)

    # 應該只保留一個（置信度更高的）
    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_extract_triples_min_confidence_filter(kg_extraction_service):
    """測試最小置信度過濾"""
    chunks = [
        {"text": "測試文本", "metadata": {"chunk_index": 0}},
    ]

    mock_triples = [
        {"subject": "A", "predicate": "是", "object": "B", "confidence": 0.9},
        {
            "subject": "C",
            "predicate": "是",
            "object": "D",
            "confidence": 0.3,
        },  # 低於閾值
    ]

    kg_extraction_service.triple_extraction_service.extract_triples = AsyncMock(
        return_value=mock_triples
    )

    options = {
        "mode": "all_chunks",
        "min_confidence": 0.5,
    }

    result = await kg_extraction_service.extract_triples_from_chunks(chunks, options)

    # 應該只保留置信度 >= 0.5 的三元組
    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_build_kg_from_file(kg_extraction_service):
    """測試從文件構建知識圖譜"""
    file_id = "file_123"
    user_id = "user_456"
    triples = [
        {"subject": "蘋果", "predicate": "是", "object": "水果", "confidence": 0.9},
        {
            "subject": "蘋果",
            "predicate": "富含",
            "object": "維生素C",
            "confidence": 0.8,
        },
    ]

    mock_result = {
        "entities_count": 3,
        "relations_count": 2,
    }

    kg_extraction_service.kg_builder_service.build_kg_from_file = AsyncMock(
        return_value=mock_result
    )

    result = await kg_extraction_service.build_kg_from_file(file_id, triples, user_id)

    assert result is not None
    assert result["entities_count"] == 3
    assert result["relations_count"] == 2
    kg_extraction_service.kg_builder_service.build_kg_from_file.assert_called_once_with(
        file_id, triples, user_id
    )


@pytest.mark.asyncio
async def test_extract_and_build_kg(kg_extraction_service):
    """測試提取並構建知識圖譜的完整流程"""
    file_id = "file_123"
    user_id = "user_456"
    chunks = [
        {"text": "蘋果是一種水果", "metadata": {"chunk_index": 0}},
    ]

    mock_triples = [
        {"subject": "蘋果", "predicate": "是", "object": "水果", "confidence": 0.9},
    ]

    mock_kg_result = {
        "entities_count": 2,
        "relations_count": 1,
    }

    kg_extraction_service.triple_extraction_service.extract_triples = AsyncMock(
        return_value=mock_triples
    )
    kg_extraction_service.kg_builder_service.build_kg_from_file = AsyncMock(
        return_value=mock_kg_result
    )

    options = {
        "mode": "all_chunks",
        "min_confidence": 0.5,
    }

    result = await kg_extraction_service.extract_and_build_kg(file_id, chunks, user_id, options)

    assert result is not None
    assert result["entities_count"] == 2
    assert result["relations_count"] == 1
