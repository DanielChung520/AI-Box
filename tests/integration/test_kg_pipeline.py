# 代碼功能說明: 知識圖譜流水線集成測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""知識圖譜流水線集成測試 - 測試從文本到圖譜的完整流程"""

import pytest
from unittest.mock import Mock, AsyncMock

from services.api.services.ner_service import NERService
from services.api.services.re_service import REService
from services.api.services.rt_service import RTService
from services.api.services.triple_extraction_service import TripleExtractionService
from services.api.services.kg_builder_service import KGBuilderService


class TestKGPipeline:
    """知識圖譜流水線集成測試"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """測試完整的知識圖譜構建流水線"""
        # 模擬各個服務
        mock_ner = Mock(spec=NERService)
        mock_re = Mock(spec=REService)
        mock_rt = Mock(spec=RTService)
        mock_kg = Mock(spec=KGBuilderService)

        # 設置模擬返回值
        from services.api.models.ner_models import Entity
        from services.api.models.re_models import Relation, RelationEntity
        from services.api.models.rt_models import RelationType

        mock_ner.extract_entities = AsyncMock(
            return_value=[
                Entity(text="張三", label="PERSON", start=0, end=2, confidence=0.95),
                Entity(text="微軟", label="ORG", start=5, end=7, confidence=0.90),
            ]
        )

        mock_re.extract_relations = AsyncMock(
            return_value=[
                Relation(
                    subject=RelationEntity(text="張三", label="PERSON"),
                    relation="WORKS_FOR",
                    object=RelationEntity(text="微軟", label="ORG"),
                    confidence=0.88,
                    context="張三在微軟工作",
                )
            ]
        )

        mock_rt.classify_relation_type = AsyncMock(
            return_value=[RelationType(type="WORKS_FOR", confidence=0.9)]
        )

        mock_kg.build_from_triples = AsyncMock(
            return_value={
                "entities_created": 2,
                "relations_created": 1,
                "total_triples": 1,
            }
        )

        # 創建三元組提取服務
        triple_service = TripleExtractionService(
            ner_service=mock_ner, re_service=mock_re, rt_service=mock_rt
        )

        # 執行完整流程
        text = "張三在微軟工作。"
        triples = await triple_service.extract_triples(text)

        assert len(triples) > 0

        # 構建知識圖譜
        result = await mock_kg.build_from_triples(triples)
        assert result["entities_created"] > 0
        assert result["relations_created"] > 0
