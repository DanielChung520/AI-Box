# 代碼功能說明: 貨幣轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""貨幣轉換工具

支持多種貨幣之間的轉換，使用實時匯率 API。
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.cache import generate_cache_key, get_cache
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 緩存時間：1 小時（3600 秒）
CURRENCY_CACHE_TTL = 3600.0

# 免費匯率 API（無需 API Key）
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/{base_currency}"

# 支持的貨幣代碼（ISO 4217）
SUPPORTED_CURRENCIES = {
    "USD",  # 美元
    "EUR",  # 歐元
    "GBP",  # 英鎊
    "JPY",  # 日元
    "CNY",  # 人民幣
    "TWD",  # 新台幣
    "HKD",  # 港幣
    "KRW",  # 韓元
    "SGD",  # 新加坡元
    "AUD",  # 澳元
    "CAD",  # 加元
    "CHF",  # 瑞士法郎
    "INR",  # 印度盧比
    "BRL",  # 巴西雷亞爾
    "MXN",  # 墨西哥比索
    "RUB",  # 俄羅斯盧布
    "ZAR",  # 南非蘭特
    "NZD",  # 新西蘭元
    "SEK",  # 瑞典克朗
    "NOK",  # 挪威克朗
    "DKK",  # 丹麥克朗
    "PLN",  # 波蘭茲羅提
    "THB",  # 泰銖
    "MYR",  # 馬來西亞林吉特
    "IDR",  # 印尼盾
    "PHP",  # 菲律賓比索
    "VND",  # 越南盾
}


class CurrencyInput(ToolInput):
    """貨幣轉換輸入參數"""

    amount: float  # 金額
    from_currency: str  # 源貨幣代碼（如 "USD", "TWD"）
    to_currency: str  # 目標貨幣代碼


class CurrencyOutput(ToolOutput):
    """貨幣轉換輸出結果"""

    amount: float  # 轉換後的金額
    from_currency: str  # 源貨幣代碼
    to_currency: str  # 目標貨幣代碼
    original_amount: float  # 原始金額
    exchange_rate: float  # 匯率
    timestamp: Optional[float] = None  # 匯率時間戳


class CurrencyConverter(BaseTool[CurrencyInput, CurrencyOutput]):
    """貨幣轉換工具

    支持多種貨幣之間的轉換，使用實時匯率 API。
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        初始化貨幣轉換工具

        Args:
            api_key: 匯率 API Key（可選，目前使用免費 API）
        """
        self._api_key = api_key or os.getenv("EXCHANGE_RATE_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        """工具名稱"""
        return "currency_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "貨幣轉換工具，支持多種貨幣之間的轉換，使用實時匯率 API"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _normalize_currency(self, currency: str) -> str:
        """
        標準化貨幣代碼（轉為大寫）

        Args:
            currency: 貨幣代碼

        Returns:
            標準化的貨幣代碼
        """
        return currency.upper().strip()

    def _validate_currency(self, currency: str) -> None:
        """
        驗證貨幣代碼是否支持

        Args:
            currency: 貨幣代碼

        Raises:
            ToolValidationError: 貨幣代碼不支持
        """
        normalized = self._normalize_currency(currency)
        if normalized not in SUPPORTED_CURRENCIES:
            supported = ", ".join(sorted(SUPPORTED_CURRENCIES))
            raise ToolValidationError(
                f"Unsupported currency: {currency}. Supported currencies: {supported}",
                field="from_currency" if currency == currency else "to_currency",
            )

    async def _get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """
        獲取匯率

        Args:
            from_currency: 源貨幣代碼
            to_currency: 目標貨幣代碼

        Returns:
            匯率（1 from_currency = ? to_currency）

        Raises:
            ToolExecutionError: 獲取匯率失敗
        """
        # 如果相同貨幣，匯率為 1
        if from_currency == to_currency:
            return 1.0

        # 檢查緩存
        cache_key = generate_cache_key(
            "currency_rate", from_currency=from_currency, to_currency=to_currency
        )
        cache = get_cache()
        cached_rate = cache.get(cache_key)
        if cached_rate is not None:
            logger.debug("currency_rate_cache_hit", cache_key=cache_key)
            return float(cached_rate)

        try:
            # 使用免費 API 獲取匯率
            url = EXCHANGE_RATE_API_URL.format(base_currency=from_currency)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                # 提取匯率
                rates = data.get("rates", {})
                if to_currency not in rates:
                    raise ToolExecutionError(
                        f"Exchange rate not found for {to_currency}",
                        tool_name=self.name,
                    )

                rate = float(rates[to_currency])

                # 緩存匯率
                cache.set(cache_key, rate, ttl=CURRENCY_CACHE_TTL)

                logger.debug(
                    "exchange_rate_fetched",
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                )

                return rate

        except httpx.HTTPError as e:
            logger.error("exchange_rate_api_error", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to fetch exchange rate from API: {str(e)}", tool_name=self.name
            ) from e
        except Exception as e:
            logger.error("exchange_rate_fetch_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to get exchange rate: {str(e)}", tool_name=self.name
            ) from e

    async def execute(self, input_data: CurrencyInput) -> CurrencyOutput:
        """
        執行貨幣轉換

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證貨幣代碼
            from_currency = self._normalize_currency(input_data.from_currency)
            to_currency = self._normalize_currency(input_data.to_currency)

            self._validate_currency(from_currency)
            self._validate_currency(to_currency)

            # 獲取匯率
            exchange_rate = await self._get_exchange_rate(from_currency, to_currency)

            # 計算轉換後的金額
            converted_amount = input_data.amount * exchange_rate

            logger.debug(
                "currency_conversion_completed",
                original_amount=input_data.amount,
                from_currency=from_currency,
                to_currency=to_currency,
                exchange_rate=exchange_rate,
                converted_amount=converted_amount,
            )

            return CurrencyOutput(
                amount=converted_amount,
                from_currency=from_currency,
                to_currency=to_currency,
                original_amount=input_data.amount,
                exchange_rate=exchange_rate,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("currency_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert currency: {str(e)}", tool_name=self.name
            ) from e
