# 代碼功能說明: RT 服務單元測試
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RT 服務單元測試"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from services.api.services.rt_service import (
    RTService,
    OllamaRTModel,
    TransformersRTModel,
)
from services.api.models.rt_models import RelationType


class TestOllamaRTModel:
    """Ollama RT 模型測試"""

    @pytest.mark.asyncio
    async def test_classify_relation_type_mock(self):
        """測試 Ollama 關係類型分類（模擬）"""
        mock_client = Mock()
        mock_response = {
            "response": '[{"type": "WORKS_FOR", "confidence": 0.9}, {"type": "RELATED_TO", "confidence": 0.7}]'
        }
        mock_client.generate = AsyncMock(return_value=mock_response)

        model = OllamaRTModel(model_name="test-model", client=mock_client)
        assert model.is_available()

        relation_types = await model.classify_relation_type("工作於")
        assert isinstance(relation_types, list)
        if relation_types:
            assert all(isinstance(rt, RelationType) for rt in relation_types)


class TestTransformersRTModel:
    """Transformers RT 模型測試"""

    @pytest.mark.asyncio
    async def test_classify_relation_type_not_available(self):
        """測試模型不可用時的情況"""
        model = TransformersRTModel(model_name="nonexistent_model")
        assert not model.is_available()

        with pytest.raises(RuntimeError):
            await model.classify_relation_type("工作於")


class TestRTService:
    """RT 服務測試"""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """測試服務初始化"""
        with patch(
            "services.api.services.rt_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "ollama",
                "model_name": "qwen3-coder:30b",
                "classification_threshold": 0.7,
                "enable_gpu": False,
            }

            service = RTService()
            assert service.model_type == "ollama"
            assert service.model_name == "qwen3-coder:30b"

    @pytest.mark.asyncio
    async def test_classify_relation_type_no_model(self):
        """測試沒有可用模型時的情況"""
        with patch(
            "services.api.services.rt_service.get_config_section"
        ) as mock_config:
            mock_config.return_value = {
                "model_type": "nonexistent",
                "model_name": "test",
            }

            service = RTService()
            with pytest.raises(RuntimeError, match="No available RT model"):
                await service.classify_relation_type("工作於")
