# 代碼功能說明: Task Analyzer 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Task Analyzer 數據模型定義"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """任務類型枚舉"""

    QUERY = "query"  # 查詢類任務
    EXECUTION = "execution"  # 執行類任務
    REVIEW = "review"  # 審查類任務
    PLANNING = "planning"  # 規劃類任務
    COMPLEX = "complex"  # 複雜任務
    LOG_QUERY = "log_query"  # 日誌查詢類任務


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
    suggested_agents: List[str] = Field(default_factory=list, description="建議使用的Agent列表")

    def get_intent(self) -> Optional[Any]:
        """
        獲取結構化意圖對象

        Returns:
            意圖對象（如 LogQueryIntent、ConfigIntent 等），如果沒有則返回 None
        """
        intent_data = self.analysis_details.get("intent")
        if not intent_data:
            return None

        # 根據任務類型返回對應的意圖對象
        if self.task_type == TaskType.LOG_QUERY:
            return LogQueryIntent(**intent_data)

        # 檢查是否為 ConfigIntent（根據 intent_data 中是否包含 ConfigIntent 的關鍵字段判斷）
        if isinstance(intent_data, dict) and "scope" in intent_data and "action" in intent_data:
            return ConfigIntent(**intent_data)

        return intent_data


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
    switch_conditions: Dict[str, Any] = Field(default_factory=dict, description="切換條件配置")
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
    fallback_providers: List[LLMProvider] = Field(default_factory=list, description="備用提供商列表")
    target_node: Optional[str] = Field(
        None,
        description="當 provider 為本地 LLM 時指派的節點",
    )
    # 路由元數據
    routing_strategy: Optional[str] = Field(None, description="使用的路由策略名稱")
    estimated_latency: Optional[float] = Field(None, description="預估延遲時間（秒）", ge=0.0)
    estimated_cost: Optional[float] = Field(None, description="預估成本", ge=0.0)
    quality_score: Optional[float] = Field(None, description="質量評分（0.0-1.0）", ge=0.0, le=1.0)
    routing_metadata: Dict[str, Any] = Field(default_factory=dict, description="路由元數據（擴展信息）")


class LogQueryIntent(BaseModel):
    """日誌查詢意圖模型

    用於解析自然語言日誌查詢指令，轉換為結構化查詢參數。
    支持查詢 TASK、AUDIT、SECURITY 三種類型的日誌。
    """

    log_type: Optional[str] = Field(
        None,
        description="日誌類型：TASK（任務日誌）、AUDIT（審計日誌）、SECURITY（安全日誌）",
    )
    actor: Optional[str] = Field(None, description="執行者（用戶 ID 或 Agent ID）")
    level: Optional[str] = Field(None, description="配置層級（system/tenant/user，僅 AUDIT 類型需要）")
    tenant_id: Optional[str] = Field(None, description="租戶 ID")
    user_id: Optional[str] = Field(None, description="用戶 ID")
    start_time: Optional[datetime] = Field(None, description="開始時間")
    end_time: Optional[datetime] = Field(None, description="結束時間")
    trace_id: Optional[str] = Field(None, description="追蹤 ID（用於追蹤完整請求生命週期）")
    limit: int = Field(default=100, description="返回數量限制")


class ConfigIntent(BaseModel):
    """配置操作意圖模型

    由 Task Analyzer 生成，用於解析自然語言配置操作指令，轉換為結構化配置操作參數。
    支持查詢、創建、更新、刪除、列表、回滾等操作。
    """

    action: Literal["query", "create", "update", "delete", "list", "rollback", "inspect"] = Field(
        ...,
        description="操作類型：query（查詢）、create（創建）、update（更新）、delete（刪除）、list（列表）、rollback（回滾）、inspect（巡檢）",
    )
    scope: str = Field(..., description="配置範圍，如 'genai.policy'、'llm.provider_config' 等")
    level: Optional[Literal["system", "tenant", "user"]] = Field(
        None, description="配置層級：system（系統級）、tenant（租戶級）、user（用戶級）"
    )
    tenant_id: Optional[str] = Field(None, description="租戶 ID（租戶級操作時需要）")
    user_id: Optional[str] = Field(None, description="用戶 ID（用戶級操作時需要）")
    config_data: Optional[Dict[str, Any]] = Field(None, description="配置數據（更新/創建操作時需要）")
    clarification_needed: bool = Field(default=False, description="是否需要澄清（信息不足時為 true）")
    clarification_question: Optional[str] = Field(
        None, description="澄清問題（clarification_needed=true 時生成）"
    )
    missing_slots: List[str] = Field(
        default_factory=list, description="缺失的槽位列表（如 ['level', 'config_data']）"
    )
    original_instruction: str = Field(..., description="保留原始指令")
