# 代碼功能說明: LLM Provider 配置數據模型
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24 23:19 UTC+8

"""LLM Provider 配置數據模型 - 定義 Provider 級別的全局配置（API Key 等）"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from services.api.models.llm_model import LLMProvider


class LLMProviderModelConfig(BaseModel):
    """Provider 默認模型配置"""

    model_id: str = Field(..., description="模型 ID")
    max_tokens: Optional[int] = Field(None, description="最大輸出 tokens")
    temperature: Optional[float] = Field(None, description="溫度參數 (0.0-2.0)")
    context_window: Optional[int] = Field(None, description="上下文窗口大小（tokens）")
    top_p: Optional[float] = Field(None, description="Top-p 參數")
    frequency_penalty: Optional[float] = Field(None, description="頻率懲罰")
    presence_penalty: Optional[float] = Field(None, description="存在懲罰")


class LLMProviderConfigBase(BaseModel):
    """LLM Provider 配置基礎模型"""

    provider: LLMProvider = Field(..., description="提供商")
    base_url: Optional[str] = Field(None, description="API 基礎 URL")
    api_version: Optional[str] = Field(None, description="API 版本")
    timeout: Optional[float] = Field(None, description="請求超時時間（秒）")
    max_retries: Optional[int] = Field(None, description="最大重試次數")
    default_model: Optional[LLMProviderModelConfig] = Field(None, description="默認模型配置")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class LLMProviderConfigCreate(LLMProviderConfigBase):
    """創建 LLM Provider 配置請求模型"""

    api_key: Optional[str] = Field(None, description="API Key（明文，將被加密存儲）")


class LLMProviderConfigUpdate(BaseModel):
    """更新 LLM Provider 配置請求模型"""

    base_url: Optional[str] = Field(None, description="API 基礎 URL")
    api_version: Optional[str] = Field(None, description="API 版本")
    timeout: Optional[float] = Field(None, description="請求超時時間（秒）")
    max_retries: Optional[int] = Field(None, description="最大重試次數")
    api_key: Optional[str] = Field(None, description="API Key（明文，將被加密存儲）")
    default_model: Optional[LLMProviderModelConfig] = Field(None, description="默認模型配置")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


class LLMProviderConfig(LLMProviderConfigBase):
    """LLM Provider 配置響應模型"""

    key: str = Field(..., alias="_key", description="ArangoDB 文檔鍵")
    id: Optional[str] = Field(None, alias="_id", description="ArangoDB 文檔 ID")
    rev: Optional[str] = Field(None, alias="_rev", description="ArangoDB 文檔版本")
    encrypted_api_key: Optional[str] = Field(None, description="加密的 API Key（不返回給客戶端）")
    has_api_key: bool = Field(False, description="是否有配置 API Key")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    created_by: Optional[str] = Field(None, description="創建人 ID")
    updated_by: Optional[str] = Field(None, description="更新人 ID")

    class Config:
        from_attributes = True
        populate_by_name = True

    @property
    def _key(self) -> str:
        """兼容舊接口"""
        return self.key

    @property
    def _id(self) -> Optional[str]:
        """兼容舊接口"""
        return self.id

    @property
    def _rev(self) -> Optional[str]:
        """兼容舊接口"""
        return self.rev


class LLMProviderConfigStatus(BaseModel):
    """Provider 配置狀態（不包含敏感信息）"""

    provider: LLMProvider = Field(..., description="提供商")
    has_api_key: bool = Field(..., description="是否已配置 API Key")
    base_url: Optional[str] = Field(None, description="API 基礎 URL")
    default_model: Optional[LLMProviderModelConfig] = Field(None, description="默認模型配置")
    created_at: Optional[datetime] = Field(None, description="創建時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")
    created_by: Optional[str] = Field(None, description="創建人 ID")
    updated_by: Optional[str] = Field(None, description="更新人 ID")
