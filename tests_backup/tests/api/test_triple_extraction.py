# 代碼功能說明: 三元組提取服務單元測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""三元組提取服務單元測試"""

import pytest
from unittest.mock import Mock, AsyncMock

from services.api.services.triple_extraction_service import TripleExtractionService
from services.api.models.triple_models import Triple
from services.api.models.ner_models import Entity
from services.api.models.re_models import Relation, RelationEntity
from services.api.models.rt_models import RelationType


class TestTripleExtractionService:
    """三元組提取服務測試"""

    @pytest.mark.asyncio
    async def test_extract_triples_no_entities(self):
        """測試沒有實體時的情況"""
        mock_ner = Mock()
        mock_ner.extract_entities = AsyncMock(return_value=[])

        mock_re = Mock()
        mock_rt = Mock()

        service = TripleExtractionService(
            ner_service=mock_ner, re_service=mock_re, rt_service=mock_rt
        )

        triples = await service.extract_triples("測試文本")
        assert triples == []

    @pytest.mark.asyncio
    async def test_extract_triples_with_entities(self):
        """測試有實體時的三元組提取"""
        entities = [
            Entity(text="張三", label="PERSON", start=0, end=2, confidence=0.95),
            Entity(text="微軟", label="ORG", start=5, end=7, confidence=0.90),
        ]

        relation = Relation(
            subject=RelationEntity(text="張三", label="PERSON"),
            relation="WORKS_FOR",
            object=RelationEntity(text="微軟", label="ORG"),
            confidence=0.88,
            context="張三在微軟工作",
        )

        relation_types = [RelationType(type="WORKS_FOR", confidence=0.9)]

        mock_ner = Mock()
        mock_ner.extract_entities = AsyncMock(return_value=entities)

        mock_re = Mock()
        mock_re.extract_relations = AsyncMock(return_value=[relation])

        mock_rt = Mock()
        mock_rt.classify_relation_type = AsyncMock(return_value=relation_types)

        service = TripleExtractionService(
            ner_service=mock_ner, re_service=mock_re, rt_service=mock_rt
        )

        triples = await service.extract_triples("張三在微軟工作。")
        assert len(triples) > 0
        assert all(isinstance(t, Triple) for t in triples)

    @pytest.mark.asyncio
    async def test_extract_triples_batch(self):
        """測試批量三元組提取"""
        mock_ner = Mock()
        mock_ner.extract_entities = AsyncMock(return_value=[])

        mock_re = Mock()
        mock_re.extract_relations = AsyncMock(return_value=[])

        mock_rt = Mock()

        service = TripleExtractionService(
            ner_service=mock_ner, re_service=mock_re, rt_service=mock_rt
        )

        texts = ["文本1", "文本2", "文本3"]
        results = await service.extract_triples_batch(texts)

        assert len(results) == len(texts)
