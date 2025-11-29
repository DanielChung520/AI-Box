# 代碼功能說明: Task Analyzer 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Task Analyzer 數據模型定義"""

from enum import Enum
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任務類型枚舉"""

    QUERY = "query"  # 查詢類任務
    EXECUTION = "execution"  # 執行類任務
    REVIEW = "review"  # 審查類任務
    PLANNING = "planning"  # 規劃類任務
    COMPLEX = "complex"  # 複雜任務


class WorkflowType(str, Enum):
    """工作流類型枚舉"""

    LANGCHAIN = "langchain"  # LangChain/Graph
    CREWAI = "crewai"  # CrewAI
    AUTOGEN = "autogen"  # AutoGen
    HYBRID = "hybrid"  # 混合模式


class LLMProvider(str, Enum):
    """LLM 提供商枚舉"""

    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    GROK = "grok"
    QWEN = "qwen"
    OLLAMA = "ollama"


class TaskAnalysisRequest(BaseModel):
    """任務分析請求模型"""

    task: str = Field(..., description="任務描述")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    user_id: Optional[str] = Field(None, description="用戶ID")
    session_id: Optional[str] = Field(None, description="會話ID")


class TaskAnalysisResult(BaseModel):
    """任務分析結果模型"""

    task_id: str = Field(..., description="任務ID")
    task_type: TaskType = Field(..., description="任務類型")
    workflow_type: WorkflowType = Field(..., description="工作流類型")
    llm_provider: LLMProvider = Field(..., description="LLM提供商")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    requires_agent: bool = Field(..., description="是否需要啟動Agent")
    analysis_details: Dict[str, Any] = Field(default_factory=dict, description="分析詳情")
    suggested_agents: List[str] = Field(
        default_factory=list, description="建議使用的Agent列表"
    )


class TaskClassificationResult(BaseModel):
    """任務分類結果模型"""

    task_type: TaskType = Field(..., description="任務類型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reasoning: str = Field(..., description="分類理由")


class WorkflowStrategy(BaseModel):
    """工作流策略模型"""

    mode: Literal["single", "hybrid"] = Field(..., description="模式：單一或混合")
    primary: WorkflowType = Field(..., description="主要工作流類型")
    fallback: List[WorkflowType] = Field(default_factory=list, description="備用工作流類型列表")
    switch_conditions: Dict[str, Any] = Field(
        default_factory=dict, description="切換條件配置"
    )
    reasoning: str = Field(..., description="策略選擇理由")


class WorkflowSelectionResult(BaseModel):
    """工作流選擇結果模型"""

    workflow_type: WorkflowType = Field(..., description="工作流類型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reasoning: str = Field(..., description="選擇理由")
    config: Dict[str, Any] = Field(default_factory=dict, description="工作流配置")
    strategy: Optional[WorkflowStrategy] = Field(None, description="工作流策略（混合模式時使用）")


class LLMRoutingResult(BaseModel):
    """LLM路由選擇結果模型"""

    provider: LLMProvider = Field(..., description="LLM提供商")
    model: str = Field(..., description="模型名稱")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reasoning: str = Field(..., description="選擇理由")
    fallback_providers: List[LLMProvider] = Field(
        default_factory=list, description="備用提供商列表"
    )
    target_node: Optional[str] = Field(
        None,
        description="當 provider 為本地 LLM 時指派的節點",
    )
    # 路由元數據
    routing_strategy: Optional[str] = Field(None, description="使用的路由策略名稱")
    estimated_latency: Optional[float] = Field(None, description="預估延遲時間（秒）", ge=0.0)
    estimated_cost: Optional[float] = Field(None, description="預估成本", ge=0.0)
    quality_score: Optional[float] = Field(
        None, description="質量評分（0.0-1.0）", ge=0.0, le=1.0
    )
    routing_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="路由元數據（擴展信息）"
    )
