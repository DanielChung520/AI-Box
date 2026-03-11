# 代碼功能說明: InputValidator 單元測試
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

"""InputValidator.validate_and_correct 單元測試。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from api.routers.chat_module.services.input_validator import (
    InputValidator,
    ValidationResult,
)


@pytest.fixture()
def validator() -> InputValidator:
    """建立 InputValidator，直接將 _moe 替換為 AsyncMock。"""
    v = InputValidator()
    # 不管原生 MoE 是否載入成功，直接覆蓋為 mock
    v._moe = AsyncMock()
    return v


class TestInputValidatorValidateAndCorrect:
    """InputValidator.validate_and_correct 測試。"""

    @pytest.mark.asyncio
    async def test_validate_correct_input(self, validator: InputValidator) -> None:
        """MoE 回傳無校正結果，驗證 corrected_text、is_complete、corrections。"""
        moe_response = {
            "content": json.dumps(
                {
                    "corrected_text": "hello",
                    "is_complete": True,
                    "corrections": [],
                },
            ),
        }
        validator._moe.chat = AsyncMock(return_value=moe_response)

        result: ValidationResult = await validator.validate_and_correct("hello")

        assert result.corrected_text == "hello"
        assert result.is_complete is True
        assert result.corrections == []
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_typo_correction(self, validator: InputValidator) -> None:
        """MoE 偵測到錯字並修正，corrections 應包含 1 筆記錄。"""
        moe_response = {
            "content": json.dumps(
                {
                    "corrected_text": "查詢庫存",
                    "is_complete": True,
                    "corrections": ["cha询 → 查詢"],
                },
            ),
        }
        validator._moe.chat = AsyncMock(return_value=moe_response)

        result: ValidationResult = await validator.validate_and_correct("cha询庫存")

        assert result.corrected_text == "查詢庫存"
        assert result.is_complete is True
        assert len(result.corrections) == 1
        assert "查詢" in result.corrections[0]
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_incomplete_input(self, validator: InputValidator) -> None:
        """MoE 判斷輸入不完整，is_complete 應為 False。"""
        moe_response = {
            "content": json.dumps(
                {
                    "corrected_text": "查詢",
                    "is_complete": False,
                    "corrections": [],
                },
            ),
        }
        validator._moe.chat = AsyncMock(return_value=moe_response)

        result: ValidationResult = await validator.validate_and_correct("查詢")

        assert result.corrected_text == "查詢"
        assert result.is_complete is False
        assert result.corrections == []

    @pytest.mark.asyncio
    async def test_validate_moe_unavailable(self) -> None:
        """MoE 不可用（_moe=None），應回傳原文並帶 error。"""
        validator = InputValidator()
        # 強制設定 _moe 為 None 模擬 MoE 不可用
        validator._moe = None

        result: ValidationResult = await validator.validate_and_correct("test input")

        assert result.corrected_text == "test input"
        assert result.is_complete is True
        assert result.corrections == []
        assert result.error == "MoE not available"
