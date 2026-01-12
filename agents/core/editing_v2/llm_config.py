# 代碼功能說明: LLM 可重現配置
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""LLM 可重現配置

定義 LLM 配置模型和配置驗證功能。
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM 配置模型

    定義固定的 LLM 參數以保證可重現性。
    """

    model_version: str = Field(default="gpt-4-turbo-preview-2026-01-09", description="模型版本")
    temperature: float = Field(default=0.0, description="溫度參數")
    seed: Optional[int] = Field(default=None, description="隨機種子")
    max_tokens: Optional[int] = Field(default=None, description="最大 Token 數")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """
        驗證溫度參數

        Args:
            v: 溫度值

        Returns:
            驗證後的溫度值

        Raises:
            ValueError: 溫度值不在 [0, 2] 範圍內
        """
        if not 0 <= v <= 2:
            raise ValueError("temperature 必須在 [0, 2] 範圍內")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """
        驗證最大 Token 數

        Args:
            v: 最大 Token 數

        Returns:
            驗證後的最大 Token 數

        Raises:
            ValueError: 最大 Token 數小於 1
        """
        if v is not None and v < 1:
            raise ValueError("max_tokens 必須大於 0")
        return v

    def to_llm_params(self) -> dict:
        """
        轉換為 LLM 調用參數

        Returns:
            LLM 參數字典
        """
        params = {
            "model": self.model_version,
            "temperature": self.temperature,
        }
        if self.seed is not None:
            params["seed"] = self.seed
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        return params


# 默認配置
DEFAULT_LLM_CONFIG = LLMConfig()
