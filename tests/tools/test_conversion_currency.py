# 代碼功能說明: 貨幣轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""貨幣轉換工具測試"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tools.conversion import CurrencyConverter, CurrencyInput, CurrencyOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError


@pytest.mark.asyncio
class TestCurrencyConverter:
    """貨幣轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return CurrencyConverter()

    @pytest.mark.asyncio
    async def test_same_currency(self, tool):
        """測試相同貨幣轉換"""
        input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="USD")
        result = await tool.execute(input_data)

        assert isinstance(result, CurrencyOutput)
        assert result.amount == 100.0
        assert result.exchange_rate == 1.0
        assert result.from_currency == "USD"
        assert result.to_currency == "USD"

    @pytest.mark.asyncio
    async def test_currency_normalization(self, tool):
        """測試貨幣代碼標準化（大小寫不敏感）"""
        with patch.object(tool, "_get_exchange_rate", new_callable=AsyncMock) as mock_rate:
            mock_rate.return_value = 30.0  # 模擬匯率

            input_data = CurrencyInput(amount=100.0, from_currency="usd", to_currency="twd")
            result = await tool.execute(input_data)

            assert isinstance(result, CurrencyOutput)
            assert result.amount == 3000.0
            assert result.exchange_rate == 30.0
            # 驗證貨幣代碼被標準化為大寫
            mock_rate.assert_called_once_with("USD", "TWD")

    @pytest.mark.asyncio
    async def test_invalid_currency(self, tool):
        """測試無效貨幣代碼"""
        input_data = CurrencyInput(amount=100.0, from_currency="INVALID", to_currency="USD")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_exchange_rate_api_success(self, tool):
        """測試匯率 API 成功響應"""
        mock_response = {
            "rates": {
                "TWD": 30.0,
                "EUR": 0.85,
            },
            "base": "USD",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            result = await tool.execute(input_data)

            assert isinstance(result, CurrencyOutput)
            assert result.amount == 3000.0
            assert result.exchange_rate == 30.0

    @pytest.mark.asyncio
    async def test_exchange_rate_api_failure(self, tool):
        """測試匯率 API 失敗"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_exchange_rate_not_found(self, tool):
        """測試匯率未找到"""
        mock_response = {
            "rates": {
                "EUR": 0.85,
            },
            "base": "USD",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = AsyncMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = AsyncMock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            with pytest.raises(ToolExecutionError):
                await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_zero_amount(self, tool):
        """測試零金額"""
        input_data = CurrencyInput(amount=0.0, from_currency="USD", to_currency="USD")
        result = await tool.execute(input_data)

        assert result.amount == 0.0

    @pytest.mark.asyncio
    async def test_cache_usage(self, tool):
        """測試緩存使用"""
        with patch.object(tool, "_get_exchange_rate", new_callable=AsyncMock) as mock_rate:
            mock_rate.return_value = 30.0

            # 第一次調用
            input_data = CurrencyInput(amount=100.0, from_currency="USD", to_currency="TWD")
            result1 = await tool.execute(input_data)

            # 第二次調用（應該使用緩存）
            result2 = await tool.execute(input_data)

            # 驗證只調用一次 API
            assert mock_rate.call_count == 1
            assert result1.amount == result2.amount
