# 代碼功能說明: Ollama API 請求/響應模型
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""定義 LLM 產生、對話與嵌入的 Pydantic 模型。"""

from __future__ import annotations

from typing import List, Literal, Optional, Self, Union

from pydantic import BaseModel, Field, model_validator


class OllamaOptions(BaseModel):
    """Ollama options 欄位封裝。"""

    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=1)
    repeat_penalty: Optional[float] = Field(None, ge=0.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    num_ctx: Optional[int] = Field(None, ge=128)


class OllamaGenerateRequest(BaseModel):
    """/api/generate 請求模型。"""

    model: Optional[str] = Field(None, description="模型名稱，若未提供則取預設")
    prompt: str = Field(..., description="輸入提示")
    stream: bool = Field(False, description="是否啟用流式輸出")
    format: Optional[str] = Field(None, description="輸出格式（例如 'json'）")
    keep_alive: Optional[str] = Field(None, description="模型保活時間")
    options: Optional[OllamaOptions] = None
    idempotency_key: Optional[str] = Field(
        None, description="對應 Ollama 的 Idempotency-Key header"
    )


class ChatMessage(BaseModel):
    """Chat API 消息。"""

    role: Literal["system", "user", "assistant"]
    content: str


class OllamaChatRequest(BaseModel):
    """/api/chat 請求模型。"""

    model: Optional[str] = None
    messages: List[ChatMessage] = Field(..., min_length=1)
    stream: bool = Field(False)
    keep_alive: Optional[str] = None
    options: Optional[OllamaOptions] = None
    idempotency_key: Optional[str] = None


class OllamaEmbeddingRequest(BaseModel):
    """/api/embeddings 請求模型。"""

    model: Optional[str] = None
    text: Optional[str] = Field(None, description="單一文本")
    texts: Optional[List[str]] = Field(None, description="多個文本")

    @model_validator(mode="after")
    def ensure_inputs(self) -> Self:
        text = self.text
        texts = self.texts
        if not text and not texts:
            raise ValueError("必須提供 text 或 texts")
        if text and texts:
            self.texts = [text] + texts
        elif text and not texts:
            self.texts = [text]
        return self

    @property
    def inputs(self) -> List[str]:
        return self.texts or []
