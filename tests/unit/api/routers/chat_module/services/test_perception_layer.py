# 代碼功能說明: PerceptionLayer 單元測試
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

"""PerceptionLayer.perceive 單元測試。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@dataclass
class _FakeCorefResult:
    """模擬 EntityMemoryService.resolve_coreference 回傳的物件。"""

    resolved_query: str


@pytest.fixture()
def _patch_imports():
    """
    統一 patch PerceptionLayer 內部的 EntityMemoryService 和 InputValidator，
    避免真正載入外部依賴。
    """
    with (
        patch(
            "api.routers.chat_module.services.perception_layer.EntityMemoryService",
        ) as mock_ems_cls,
        patch(
            "api.routers.chat_module.services.perception_layer.InputValidator",
        ) as mock_iv_cls,
    ):
        yield mock_ems_cls, mock_iv_cls


class TestPerceptionLayerPerceive:
    """PerceptionLayer.perceive 測試。"""

    @pytest.mark.asyncio
    async def test_perceive_happy_path(self, _patch_imports: Any) -> None:
        """正常路徑：指代消解 + 輸入校正均成功，驗證所有 PerceptionResult 欄位。"""
        mock_ems_cls, mock_iv_cls = _patch_imports

        # 設定 EntityMemoryService mock
        mock_ems_instance = MagicMock()
        mock_ems_instance.resolve_coreference = AsyncMock(
            return_value=_FakeCorefResult(resolved_query="resolved hello"),
        )
        mock_ems_cls.return_value = mock_ems_instance

        # 設定 InputValidator mock
        mock_iv_instance = MagicMock()
        from api.routers.chat_module.services.input_validator import ValidationResult

        mock_iv_instance.validate_and_correct = AsyncMock(
            return_value=ValidationResult(
                corrected_text="corrected hello",
                is_complete=True,
                corrections=["typo fix"],
                error=None,
            ),
        )
        mock_iv_cls.return_value = mock_iv_instance

        from api.routers.chat_module.services.perception_layer import PerceptionLayer

        layer = PerceptionLayer()
        result = await layer.perceive("hello", session_id="s1", user_id="u1")

        assert result.original_text == "hello"
        assert result.resolved_text == "resolved hello"
        assert result.corrected_text == "corrected hello"
        assert result.is_complete is True
        assert isinstance(result.perception_metadata, dict)
        assert result.perception_metadata["corrections"] == ["typo fix"]
        assert result.perception_metadata["errors"] == []
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_perceive_entity_memory_failure(self, _patch_imports: Any) -> None:
        """EntityMemoryService.resolve_coreference 拋出異常，resolved_text 回退原文。"""
        mock_ems_cls, mock_iv_cls = _patch_imports

        # EntityMemoryService 初始化成功，但 resolve_coreference 拋異常
        mock_ems_instance = MagicMock()
        mock_ems_instance.resolve_coreference = AsyncMock(
            side_effect=RuntimeError("coref boom"),
        )
        mock_ems_cls.return_value = mock_ems_instance

        # InputValidator 正常
        from api.routers.chat_module.services.input_validator import ValidationResult

        mock_iv_instance = MagicMock()
        mock_iv_instance.validate_and_correct = AsyncMock(
            return_value=ValidationResult(
                corrected_text="原始文字",
                is_complete=True,
                corrections=[],
                error=None,
            ),
        )
        mock_iv_cls.return_value = mock_iv_instance

        from api.routers.chat_module.services.perception_layer import PerceptionLayer

        layer = PerceptionLayer()
        # 繞過 _resolve_coreference 內部 try/except，直接讓外層 perceive() 捕獲異常
        layer._resolve_coreference = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("coref boom"),
        )
        result = await layer.perceive("原始文字", session_id="s1", user_id="u1")

        # resolved_text 回退到原文
        assert result.resolved_text == "原始文字"
        errors = result.perception_metadata["errors"]
        assert any("coreference_step_error" in e for e in errors)

    @pytest.mark.asyncio
    async def test_perceive_input_validator_failure(self, _patch_imports: Any) -> None:
        """InputValidator.validate_and_correct 拋出異常，corrected_text 回退到 resolved_text。"""
        mock_ems_cls, mock_iv_cls = _patch_imports

        # EntityMemoryService 正常
        mock_ems_instance = MagicMock()
        mock_ems_instance.resolve_coreference = AsyncMock(
            return_value=_FakeCorefResult(resolved_query="resolved text"),
        )
        mock_ems_cls.return_value = mock_ems_instance

        # InputValidator 拋異常
        mock_iv_instance = MagicMock()
        mock_iv_instance.validate_and_correct = AsyncMock(
            side_effect=RuntimeError("validator boom"),
        )
        mock_iv_cls.return_value = mock_iv_instance

        from api.routers.chat_module.services.perception_layer import PerceptionLayer

        layer = PerceptionLayer()
        # 繞過 _validate_input 內部 try/except，直接讓外層 perceive() 捕獲異常
        layer._validate_input = AsyncMock(  # type: ignore[method-assign]
            side_effect=RuntimeError("validator boom"),
        )
        result = await layer.perceive("raw", session_id="s1", user_id="u1")

        # corrected_text 回退到 resolved_text
        assert result.corrected_text == "resolved text"
        errors = result.perception_metadata["errors"]
        assert any("validation_step_error" in e for e in errors)

    @pytest.mark.asyncio
    async def test_perceive_latency_under_1000ms(self, _patch_imports: Any) -> None:
        """mock 條件下 latency_ms 應低於 1000ms。"""
        mock_ems_cls, mock_iv_cls = _patch_imports

        mock_ems_instance = MagicMock()
        mock_ems_instance.resolve_coreference = AsyncMock(
            return_value=_FakeCorefResult(resolved_query="ok"),
        )
        mock_ems_cls.return_value = mock_ems_instance

        from api.routers.chat_module.services.input_validator import ValidationResult

        mock_iv_instance = MagicMock()
        mock_iv_instance.validate_and_correct = AsyncMock(
            return_value=ValidationResult(
                corrected_text="ok",
                is_complete=True,
                corrections=[],
                error=None,
            ),
        )
        mock_iv_cls.return_value = mock_iv_instance

        from api.routers.chat_module.services.perception_layer import PerceptionLayer

        layer = PerceptionLayer()
        result = await layer.perceive("ok", session_id="s1", user_id="u1")

        assert result.latency_ms < 1000
