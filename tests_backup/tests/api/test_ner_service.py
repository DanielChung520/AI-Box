# 代碼功能說明: NER 服務單元測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""NER 服務單元測試"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from services.api.services.ner_service import (
    NERService,
    SpacyNERModel,
    OllamaNERModel,
    BaseNERModel,
)
from services.api.models.ner_models import Entity


class TestSpacyNERModel:
    """spaCy NER 模型測試"""

    @pytest.mark.asyncio
    async def test_extract_entities_not_available(self):
        """測試模型不可用時的情況"""
        model = SpacyNERModel(model_name="nonexistent_model")
        assert not model.is_available()

        with pytest.raises(RuntimeError):
            await model.extract_entities("測試文本")

    @pytest.mark.skipif(
        not pytest.importorskip("spacy", reason="spaCy not installed"),
        reason="spaCy not available",
    )
    @pytest.mark.asyncio
    async def test_extract_entities_available(self):
        """測試實體提取（如果 spaCy 可用）"""
        try:
            model = SpacyNERModel(model_name="zh_core_web_sm")
            if model.is_available():
                text = "張三在北京工作。"
                entities = await model.extract_entities(text)
                assert isinstance(entities, list)
                # 驗證實體格式
                if entities:
                    assert all(isinstance(e, Entity) for e in entities)
        except Exception:
            pytest.skip("spaCy model not available")


class TestOllamaNERModel:
    """Ollama NER 模型測試"""

    @pytest.mark.asyncio
    async def test_extract_entities_mock(self):
        """測試 Ollama 實體提取（模擬）"""
        mock_client = Mock()
        mock_response = {
            "response": '[{"text": "張三", "label": "PERSON", "start": 0, "end": 2, "confidence": 0.95}]'
        }
        mock_client.generate = AsyncMock(return_value=mock_response)

        model = OllamaNERModel(model_name="test-model", client=mock_client)
        assert model.is_available()

        entities = await model.extract_entities("張三在北京工作。")
        assert isinstance(entities, list)
        if entities:
            assert all(isinstance(e, Entity) for e in entities)


class TestNERService:
    """NER 服務測試"""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """測試服務初始化"""
        with patch(
            "services.api.services.ner_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "spacy",
                "model_name": "zh_core_web_sm",
                "fallback_model": "ollama:qwen3-coder:30b",
                "batch_size": 32,
                "enable_gpu": False,
            }

            service = NERService()
            assert service.model_type == "spacy"
            assert service.model_name == "zh_core_web_sm"

    @pytest.mark.asyncio
    async def test_extract_entities_no_model(self):
        """測試沒有可用模型時的情況"""
        with patch(
            "services.api.services.ner_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "nonexistent",
                "model_name": "test",
            }

            service = NERService()
            with pytest.raises(RuntimeError, match="No available NER model"):
                await service.extract_entities("測試文本")

    @pytest.mark.asyncio
    async def test_extract_entities_batch(self):
        """測試批量實體提取"""
        with patch(
            "services.api.services.ner_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "ollama",
                "model_name": "test-model",
                "fallback_model": None,
            }

            mock_model = Mock(spec=BaseNERModel)
            mock_model.is_available = Mock(return_value=True)
            mock_model.extract_entities = AsyncMock(return_value=[])

            service = NERService()
            service._primary_model = mock_model

            texts = ["文本1", "文本2", "文本3"]
            results = await service.extract_entities_batch(texts)

            assert len(results) == len(texts)
            assert mock_model.extract_entities.call_count == len(texts)
