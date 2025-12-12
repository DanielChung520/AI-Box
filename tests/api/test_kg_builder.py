# 代碼功能說明: 知識圖譜構建服務單元測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""知識圖譜構建服務單元測試"""

import pytest
from unittest.mock import Mock

from services.api.services.kg_builder_service import KGBuilderService
from services.api.models.triple_models import Triple, TripleEntity, TripleRelation


class TestKGBuilderService:
    """知識圖譜構建服務測試"""

    @pytest.fixture
    def mock_client(self):
        """創建模擬 ArangoDB 客戶端"""
        client = Mock()
        db = Mock()
        client.db = db

        # 模擬集合
        entities_collection = Mock()
        relations_collection = Mock()

        db.has_collection = Mock(
            side_effect=lambda name: name in ["entities", "relations"]
        )
        db.create_collection = Mock()
        db.collection = Mock(
            side_effect=lambda name: (
                entities_collection if name == "entities" else relations_collection
            )
        )

        entities_collection.get = Mock(return_value=None)
        entities_collection.insert = Mock()
        entities_collection.update = Mock()

        relations_collection.get = Mock(return_value=None)
        relations_collection.insert = Mock()
        relations_collection.update = Mock()

        db.aql = Mock()
        db.aql.execute = Mock(return_value=Mock(results=[]))

        return client

    @pytest.mark.asyncio
    async def test_build_from_triples(self, mock_client):
        """測試從三元組構建圖譜"""
        service = KGBuilderService(client=mock_client)

        triples = [
            Triple(
                subject=TripleEntity(text="張三", type="PERSON", start=0, end=2),
                relation=TripleRelation(type="WORKS_FOR", confidence=0.9),
                object=TripleEntity(text="微軟", type="ORG", start=5, end=7),
                confidence=0.85,
                source_text="張三在微軟工作",
                context="張三在微軟工作",
            )
        ]

        result = await service.build_from_triples(triples)
        assert result["total_triples"] == 1
        assert result["entities_created"] > 0
        assert result["relations_created"] > 0

    def test_get_entity(self, mock_client):
        """測試查詢實體"""
        service = KGBuilderService(client=mock_client)

        # 模擬實體存在
        mock_client.db.collection.return_value.get.return_value = {
            "_key": "test_key",
            "name": "測試實體",
            "type": "PERSON",
        }

        entity = service.get_entity("entities/test_key")
        assert entity is not None
        assert entity["name"] == "測試實體"

    def test_list_entities(self, mock_client):
        """測試查詢實體列表"""
        service = KGBuilderService(client=mock_client)

        # 模擬 AQL 查詢結果
        mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(
            return_value=iter([{"_key": "test1"}, {"_key": "test2"}])
        )
        mock_client.db.aql.execute.return_value = mock_cursor

        entities = service.list_entities()
        assert len(entities) == 2
