# 代碼功能說明: MoE Agent 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""MoE Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MoEAgentRequest(BaseModel):
    """MoE Agent 請求模型"""

    action: str = Field(..., description="操作類型（generate/chat/chat_stream/embeddings/get_metrics）")
    prompt: Optional[str] = Field(None, description="提示詞（generate 操作需要）")
    messages: Optional[List[Dict[str, Any]]] = Field(
        None, description="消息列表（chat/chat_stream 操作需要）"
    )
    text: Optional[str] = Field(None, description="文本（embeddings 操作需要）")
    provider: Optional[str] = Field(None, description="指定的 LLM 提供商（可選）")
    model: Optional[str] = Field(None, description="模型名稱（可選）")
    temperature: Optional[float] = Field(None, description="溫度參數（可選）")
    max_tokens: Optional[int] = Field(None, description="最大 token 數（可選）")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息（可選）")
    task_classification: Optional[Dict[str, Any]] = Field(None, description="任務分類結果（可選）")


class MoEAgentResponse(BaseModel):
    """MoE Agent 響應模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="操作類型")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class RoutingMetrics(BaseModel):
    """路由指標模型"""

    provider_metrics: Dict[str, Any] = Field(default_factory=dict, description="提供商指標")
    strategy_metrics: Dict[str, Any] = Field(default_factory=dict, description="策略指標")
    recommendations: List[str] = Field(default_factory=list, description="推薦建議")
    load_balancer: Optional[Dict[str, Any]] = Field(None, description="負載均衡器統計")
    health_status: Optional[Dict[str, Any]] = Field(None, description="健康狀態")
