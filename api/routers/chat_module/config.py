# 代碼功能說明: Chat v2 配置類
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""Chat v2 配置模組"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StreamMode(str, Enum):
    """處理模式"""

    SYNC = "sync"  # 同步非流式
    STREAM = "stream"  # 流式 SSE
    ASYNC = "async"  # 異步 202


class IntentStrategy(str, Enum):
    """意圖處理策略"""

    DIRECT_RESPONSE = "direct_response"
    KNOWLEDGE_RAG = "knowledge_rag"
    ROUTE_TO_AGENT = "route_to_agent"
    ROUTE_TO_SPECIFIC_AGENT = "route_to_specific_agent"
    LLM_FALLBACK = "llm_fallback"


class ChatConfig(BaseModel):
    """Chat v2 配置類"""

    # 處理模式
    stream: bool = Field(default=False, description="流式響應")
    async_mode: bool = Field(default=False, description="異步執行")
    timeout: int = Field(default=120, ge=10, le=600, description="超時秒數")

    # 意圖分類
    intent_rag_enabled: bool = Field(default=True, description="使用 OrchestratorIntentRAG")
    intent_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="意圖置信度閾值")

    # LLM 配置
    default_model: str = Field(default="auto", description="默認模型")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="溫度")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="最大 token 數")

    # Agent 配置
    default_agent: Optional[str] = Field(default=None, description="默認 Agent")
    allowed_agents: Optional[List[str]] = Field(default=None, description="允許的 Agent 列表")

    def get_stream_mode(self) -> StreamMode:
        """根據配置獲取處理模式"""
        if self.async_mode:
            return StreamMode.ASYNC
        elif self.stream:
            return StreamMode.STREAM
        else:
            return StreamMode.SYNC


class IntentResult(BaseModel):
    """意圖分類結果"""

    intent_name: str = Field(..., description="意圖名稱")
    description: str = Field(default="", description="意圖描述")
    priority: int = Field(default=99, description="優先級")
    action_strategy: IntentStrategy = Field(..., description="處理策略")
    response_template: str = Field(default="", description="回覆模板")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度")


# 全局配置實例
_chat_config: Optional[ChatConfig] = None


def get_chat_config() -> ChatConfig:
    """獲取全局 Chat 配置"""
    global _chat_config
    if _chat_config is None:
        _chat_config = ChatConfig()
    return _chat_config


def update_chat_config(config: ChatConfig) -> None:
    """更新全局 Chat 配置"""
    global _chat_config
    _chat_config = config
