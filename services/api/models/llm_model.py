# 代碼功能說明: LLM 模型數據模型
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""LLM 模型數據模型 - 定義 LLM 模型相關的數據結構"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """LLM 提供商枚舉"""

    AUTO = "auto"  # 自動選擇
    OPENAI = "chatgpt"  # OpenAI (ChatGPT)
    ANTHROPIC = "anthropic"  # Anthropic (Claude)
    GOOGLE = "gemini"  # Google (Gemini)
    ALIBABA = "qwen"  # 阿里巴巴 (Qwen)
    XAI = "grok"  # xAI (Grok)
    OLLAMA = "ollama"  # Ollama (本地部署)
    SMARTQ = "smartq"  # SmartQ (自定義)
    META = "meta"  # Meta (LLaMA)
    MISTRAL = "mistral"  # Mistral AI
    DEEPSEEK = "deepseek"  # DeepSeek
    DATABRICKS = "databricks"  # Databricks (DBRX)
    COHERE = "cohere"  # Cohere
    PERPLEXITY = "perplexity"  # Perplexity
    VOLCANO = "volcano"  # 字節跳動火山引擎 (Volcano Engine / Doubao)
    CHATGLM = "chatglm"  # 智譜 AI (ChatGLM)


class ModelCapability(str, Enum):
    """模型能力枚舉"""

    CHAT = "chat"  # 對話能力
    COMPLETION = "completion"  # 文本補全
    EMBEDDING = "embedding"  # 向量嵌入
    CODE = "code"  # 代碼生成
    MULTIMODAL = "multimodal"  # 多模態（圖像、音頻等）
    REASONING = "reasoning"  # 推理能力
    FUNCTION_CALLING = "function_calling"  # 函數調用
    STREAMING = "streaming"  # 流式輸出
    VISION = "vision"  # 視覺理解


class ModelStatus(str, Enum):
    """模型狀態枚舉"""

    ACTIVE = "active"  # 啟用
    DEPRECATED = "deprecated"  # 已棄用
    MAINTENANCE = "maintenance"  # 維護中
    COMING_SOON = "coming_soon"  # 即將推出
    BETA = "beta"  # 測試版


class LLMModelBase(BaseModel):
    """LLM 模型基礎模型"""

    model_id: str = Field(..., description="模型唯一標識符（例如：gpt-4-turbo）")
    name: str = Field(..., description="模型顯示名稱（例如：GPT-4 Turbo）")
    provider: LLMProvider = Field(..., description="提供商")
    description: Optional[str] = Field(None, description="模型描述")
    capabilities: List[ModelCapability] = Field(default_factory=list, description="模型支持的能力列表")
    status: ModelStatus = Field(ModelStatus.ACTIVE, description="模型狀態")
    context_window: Optional[int] = Field(None, description="上下文窗口大小（tokens）")
    max_output_tokens: Optional[int] = Field(None, description="最大輸出 tokens")
    parameters: Optional[str] = Field(None, description="參數規模（例如：70B、1.8T）")
    release_date: Optional[str] = Field(None, description="發布日期（ISO 8601 格式）")
    license: Optional[str] = Field(None, description="許可證類型")
    languages: List[str] = Field(default_factory=lambda: ["en", "zh"], description="支持語言列表")
    icon: Optional[str] = Field(None, description="圖標 FontAwesome 類名")
    color: Optional[str] = Field(None, description="主題顏色（例如：text-green-400）")
    order: int = Field(0, description="排序順序（數字越小越靠前）")
    is_default: bool = Field(False, description="是否為提供商默認模型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    source: Optional[str] = Field(
        "database", description="模型來源: database(數據庫)/ollama_discovered(動態發現)"
    )
    ollama_endpoint: Optional[str] = Field(None, description="Ollama 服務器端點（如果是動態發現的模型）")
    ollama_node: Optional[str] = Field(None, description="Ollama 節點名稱（例如: localhost:11434）")
    is_favorite: Optional[bool] = Field(None, description="用戶是否收藏（僅在用戶查詢時填充）")
    is_active: Optional[bool] = Field(None, description="模型是否可用（根據 Provider API Key 配置和模型狀態判斷）")


class LLMModelCreate(LLMModelBase):
    """創建 LLM 模型請求模型"""

    pass


class LLMModelUpdate(BaseModel):
    """更新 LLM 模型請求模型"""

    name: Optional[str] = Field(None, description="模型顯示名稱")
    description: Optional[str] = Field(None, description="模型描述")
    capabilities: Optional[List[ModelCapability]] = Field(None, description="模型支持的能力列表")
    status: Optional[ModelStatus] = Field(None, description="模型狀態")
    context_window: Optional[int] = Field(None, description="上下文窗口大小")
    max_output_tokens: Optional[int] = Field(None, description="最大輸出 tokens")
    parameters: Optional[str] = Field(None, description="參數規模")
    release_date: Optional[str] = Field(None, description="發布日期")
    license: Optional[str] = Field(None, description="許可證類型")
    languages: Optional[List[str]] = Field(None, description="支持語言列表")
    icon: Optional[str] = Field(None, description="圖標 FontAwesome 類名")
    color: Optional[str] = Field(None, description="主題顏色")
    order: Optional[int] = Field(None, description="排序順序")
    is_default: Optional[bool] = Field(None, description="是否為提供商默認模型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")
    source: Optional[str] = Field(None, description="模型來源")
    ollama_endpoint: Optional[str] = Field(None, description="Ollama 服務器端點")
    ollama_node: Optional[str] = Field(None, description="Ollama 節點名稱")


class LLMModel(LLMModelBase):
    """LLM 模型響應模型"""

    key: str = Field(..., alias="_key", description="ArangoDB 文檔鍵")
    id: Optional[str] = Field(None, alias="_id", description="ArangoDB 文檔 ID")
    rev: Optional[str] = Field(None, alias="_rev", description="ArangoDB 文檔版本")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")

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


class LLMModelQuery(BaseModel):
    """LLM 模型查詢參數模型"""

    provider: Optional[LLMProvider] = Field(None, description="提供商篩選")
    status: Optional[ModelStatus] = Field(None, description="狀態篩選")
    capability: Optional[ModelCapability] = Field(None, description="能力篩選")
    search: Optional[str] = Field(None, description="搜索關鍵詞（名稱、描述）")
    limit: int = Field(100, ge=1, le=1000, description="返回數量限制")
    offset: int = Field(0, ge=0, description="偏移量")
