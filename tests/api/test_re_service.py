# 代碼功能說明: RE 服務單元測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RE 服務單元測試"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from services.api.services.re_service import (
    REService,
    TransformersREModel,
    OllamaREModel,
    BaseREModel,
)
from services.api.models.re_models import Relation
from services.api.models.ner_models import Entity


class TestTransformersREModel:
    """Transformers RE 模型測試"""

    @pytest.mark.asyncio
    async def test_extract_relations_not_available(self):
        """測試模型不可用時的情況"""
        model = TransformersREModel(model_name="nonexistent_model")
        assert not model.is_available()

        with pytest.raises(RuntimeError):
            await model.extract_relations("測試文本")


class TestOllamaREModel:
    """Ollama RE 模型測試"""

    @pytest.mark.asyncio
    async def test_extract_relations_mock(self):
        """測試 Ollama 關係抽取（模擬）"""
        mock_client = Mock()
        mock_response = {
            "response": '[{"subject": {"text": "張三", "label": "PERSON"}, "relation": "WORKS_FOR", "object": {"text": "微軟", "label": "ORG"}, "confidence": 0.88, "context": "張三在微軟工作"}]'
        }
        mock_client.generate = AsyncMock(return_value=mock_response)

        model = OllamaREModel(model_name="test-model", client=mock_client)
        assert model.is_available()

        entities = [
            Entity(text="張三", label="PERSON", start=0, end=2, confidence=0.95),
            Entity(text="微軟", label="ORG", start=5, end=7, confidence=0.90),
        ]
        relations = await model.extract_relations("張三在微軟工作。", entities)
        assert isinstance(relations, list)
        if relations:
            assert all(isinstance(r, Relation) for r in relations)


class TestREService:
    """RE 服務測試"""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """測試服務初始化"""
        with patch(
            "services.api.services.re_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "transformers",
                "model_name": "bert-base-chinese",
                "fallback_model": "ollama:qwen3-coder:30b",
                "max_relation_length": 128,
                "enable_gpu": False,
            }

            service = REService()
            assert service.model_type == "transformers"
            assert service.model_name == "bert-base-chinese"

    @pytest.mark.asyncio
    async def test_extract_relations_no_model(self):
        """測試沒有可用模型時的情況"""
        with patch(
            "services.api.services.re_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "nonexistent",
                "model_name": "test",
            }

            service = REService()
            with pytest.raises(RuntimeError, match="No available RE model"):
                await service.extract_relations("測試文本")

    @pytest.mark.asyncio
    async def test_extract_relations_batch(self):
        """測試批量關係抽取"""
        with patch(
            "services.api.services.re_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "ollama",
                "model_name": "test-model",
                "fallback_model": None,
            }

            mock_model = Mock(spec=BaseREModel)
            mock_model.is_available = Mock(return_value=True)
            mock_model.extract_relations = AsyncMock(return_value=[])

            service = REService()
            service._primary_model = mock_model

            texts = ["文本1", "文本2", "文本3"]
            results = await service.extract_relations_batch(texts)

            assert len(results) == len(texts)
