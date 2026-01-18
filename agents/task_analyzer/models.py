# 代碼功能說明: Task Analyzer 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

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
    VOLCANO = "volcano"  # 字節跳動火山引擎 (Volcano Engine / Doubao)
    CHATGLM = "chatglm"  # 智譜 AI (ChatGLM)


class TaskAnalysisRequest(BaseModel):
    """任務分析請求模型"""

    task: str = Field(..., description="任務描述")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    user_id: Optional[str] = Field(None, description="用戶ID")
    session_id: Optional[str] = Field(None, description="會話ID")
    specified_agent_id: Optional[str] = Field(
        None, description="前端指定的Agent ID（可選，如果指定則驗證該Agent是否可用）"
    )


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
    router_decision: Optional["RouterDecision"] = Field(None, description="Router 決策")
    decision_result: Optional["DecisionResult"] = Field(None, description="決策引擎結果")
    suggested_tools: List[str] = Field(default_factory=list, description="建議使用的工具列表")

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


class RouterInput(BaseModel):
    """Router LLM 輸入模型"""

    user_query: str = Field(..., description="用戶查詢")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="會話上下文")
    system_constraints: Optional[Dict[str, Any]] = Field(default_factory=dict, description="系統約束")


class SemanticUnderstandingOutput(BaseModel):
    """L1 層級輸出：語義理解結果（v4.0 純語義理解輸出）

    此模型是 v4.0 架構中 L1 語義理解層的純輸出，只包含語義理解信息，
    不包含 intent、agent 選擇等決策信息（這些在 L2/L3 層級處理）。
    """

    topics: List[str] = Field(..., description="主題列表，如 ['document', 'system_design']")
    entities: List[str] = Field(..., description="實體列表，如 ['Document Editing Agent', 'API Spec']")
    action_signals: List[str] = Field(..., description="動作信號，如 ['design', 'refine', 'structure']")
    modality: Literal["instruction", "question", "conversation", "command"] = Field(
        ..., description="模態類型"
    )
    certainty: float = Field(..., ge=0.0, le=1.0, description="確定性分數 (0.0-1.0)")


class RouterDecision(BaseModel):
    """Router 決策輸出模型（v4 擴展：包含語義理解輸出）

    注意：此模型已擴展為包含語義理解字段（topics, entities, action_signals, modality），
    同時保留 intent_type 作為過渡期兼容。
    """

    # v4 新增字段：語義理解輸出
    topics: List[str] = Field(
        default_factory=list, description="主題列表，如 ['document', 'system_design']"
    )
    entities: List[str] = Field(
        default_factory=list, description="實體列表，如 ['Document Editing Agent', 'API Spec']"
    )
    action_signals: List[str] = Field(
        default_factory=list, description="動作信號，如 ['design', 'refine', 'structure']"
    )
    modality: Literal["instruction", "question", "conversation", "command"] = Field(
        default="conversation", description="模態類型"
    )

    # 過渡期兼容字段（保留原有字段）
    intent_type: Literal["conversation", "retrieval", "analysis", "execution"] = Field(
        default="conversation",
        description="意圖類型（過渡期兼容，L2 層級會基於語義理解匹配 Intent）",
    )
    complexity: Literal["low", "mid", "high"] = Field(..., description="複雜度")
    needs_agent: bool = Field(..., description="是否需要 Agent")
    needs_tools: bool = Field(..., description="是否需要工具")
    determinism_required: bool = Field(..., description="是否需要確定性執行")
    risk_level: Literal["low", "mid", "high"] = Field(..., description="風險等級")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")


class DecisionResult(BaseModel):
    """決策結果模型"""

    router_result: RouterDecision = Field(..., description="Router 決策結果")
    chosen_agent: Optional[str] = Field(None, description="選擇的 Agent")
    chosen_tools: List[str] = Field(default_factory=list, description="選擇的工具列表")
    chosen_model: Optional[str] = Field(None, description="選擇的模型")
    score: float = Field(..., description="評分", ge=0.0, le=1.0)
    fallback_used: bool = Field(default=False, description="是否使用了 Fallback")
    reasoning: str = Field(..., description="決策理由")


class DecisionLog(BaseModel):
    """決策日誌模型（舊版，已棄用）

    注意：此模型已棄用，請使用 GroDecisionLog 模型（符合 GRO 規範）。
    保留此模型僅用於向後兼容。
    """

    decision_id: str = Field(..., description="決策 ID")
    timestamp: datetime = Field(..., description="時間戳")
    query: Dict[str, Any] = Field(..., description="查詢信息（text, embedding optional）")
    router_output: RouterDecision = Field(..., description="Router 輸出")
    decision_engine: DecisionResult = Field(..., description="決策引擎結果")
    execution_result: Optional[Dict[str, Any]] = Field(
        None, description="執行結果（success, latency_ms, cost）"
    )


# GRO 規範相關模型
class ReactStateType(str, Enum):
    """ReAct 狀態類型枚舉（符合 GRO 規範）"""

    AWARENESS = "AWARENESS"
    PLANNING = "PLANNING"
    DELEGATION = "DELEGATION"
    OBSERVATION = "OBSERVATION"
    DECISION = "DECISION"


class DecisionAction(str, Enum):
    """決策動作枚舉（符合 GRO 規範）"""

    COMPLETE = "complete"
    RETRY = "retry"
    EXTEND_PLAN = "extend_plan"
    ESCALATE = "escalate"


class DecisionOutcome(str, Enum):
    """決策結果枚舉（符合 GRO 規範）"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class GroDecision(BaseModel):
    """GRO 決策模型（符合 GRO 規範）"""

    action: DecisionAction = Field(..., description="決策動作")
    reason: Optional[str] = Field(None, description="決策理由")
    next_state: ReactStateType = Field(..., description="下一個狀態")


class GroDecisionLog(BaseModel):
    """GRO Decision Log 模型（符合 GRO 規範）

    符合 GRO Decision Log Schema（參考架構規格書 9.1.5 節）：
    - react_id: ReAct session 主鍵
    - iteration: 迭代次數
    - state: 當前狀態（AWARENESS/PLANNING/DELEGATION/OBSERVATION/DECISION）
    - input_signature: 輸入簽名（命令分類、風險等級等）
    - decision: 決策結果（action, next_state）
    - outcome: 結果（success/failure/partial）
    - observations: 觀察結果（可選）
    - correlation_id: 關聯ID（可選，用於跨系統追蹤）
    """

    react_id: str = Field(..., description="ReAct session ID", min_length=8)
    iteration: int = Field(..., description="迭代次數", ge=0)
    state: ReactStateType = Field(..., description="狀態")
    input_signature: Dict[str, Any] = Field(default_factory=dict, description="輸入簽名（命令分類、風險等級等）")
    observations: Optional[Dict[str, Any]] = Field(None, description="觀察結果")
    decision: GroDecision = Field(..., description="決策結果")
    outcome: DecisionOutcome = Field(..., description="決策結果（success/failure/partial）")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="時間戳")
    correlation_id: Optional[str] = Field(None, description="關聯 ID（用於跨系統追蹤）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於持久化）"""
        return {
            "react_id": self.react_id,
            "iteration": self.iteration,
            "state": self.state.value,
            "input_signature": self.input_signature,
            "observations": self.observations,
            "decision": {
                "action": self.decision.action.value,
                "reason": self.decision.reason,
                "next_state": self.decision.next_state.value,
            },
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroDecisionLog":
        """從字典創建 GroDecisionLog 對象"""
        # 解析 decision
        decision_data = data["decision"]
        decision = GroDecision(
            action=DecisionAction(decision_data["action"]),
            reason=decision_data.get("reason"),
            next_state=ReactStateType(decision_data["next_state"]),
        )

        # 解析 timestamp
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            react_id=data["react_id"],
            iteration=data["iteration"],
            state=ReactStateType(data["state"]),
            input_signature=data.get("input_signature", {}),
            observations=data.get("observations"),
            decision=decision,
            outcome=DecisionOutcome(data["outcome"]),
            timestamp=timestamp,
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_legacy_decision_log(
        cls, legacy_log: DecisionLog, react_id: str, iteration: int
    ) -> "GroDecisionLog":
        """從舊版 DecisionLog 轉換為 GroDecisionLog（向後兼容）"""
        # 從舊版 DecisionLog 提取信息構建 input_signature
        input_signature = {
            "intent_type": legacy_log.router_output.intent_type,
            "complexity": legacy_log.router_output.complexity,
            "risk_level": legacy_log.router_output.risk_level,
            "query": legacy_log.query,
        }

        # 從 execution_result 判斷 outcome
        outcome = DecisionOutcome.SUCCESS
        if legacy_log.execution_result:
            success = legacy_log.execution_result.get("success", False)
            if not success:
                outcome = DecisionOutcome.FAILURE
            # 可以根據實際情況判斷是否為 PARTIAL

        # 構建 decision（從 decision_engine 提取信息）
        # 注意：舊版 DecisionLog 沒有明確的 decision action，需要推斷
        # 這裡假設為 COMPLETE（實際使用時應根據業務邏輯判斷）
        decision = GroDecision(
            action=DecisionAction.COMPLETE,
            reason=legacy_log.decision_engine.reasoning,
            next_state=ReactStateType.DECISION,
        )

        return cls(
            react_id=react_id,
            iteration=iteration,
            state=ReactStateType.DECISION,
            input_signature=input_signature,
            observations=None,
            decision=decision,
            outcome=outcome,
            timestamp=legacy_log.timestamp,
            correlation_id=None,
            metadata={
                "legacy_decision_id": legacy_log.decision_id,
                "chosen_agent": legacy_log.decision_engine.chosen_agent,
                "chosen_model": legacy_log.decision_engine.chosen_model,
                "execution_result": legacy_log.execution_result,
            },
        )


class CapabilityMatch(BaseModel):
    """能力匹配結果模型"""

    candidate_id: str = Field(..., description="候選 ID（Agent/Tool/Model）")
    candidate_type: Literal["agent", "tool", "model"] = Field(..., description="候選類型")
    capability_match: float = Field(..., description="能力匹配度", ge=0.0, le=1.0)
    cost_score: float = Field(..., description="成本評分", ge=0.0, le=1.0)
    latency_score: float = Field(..., description="延遲評分", ge=0.0, le=1.0)
    success_history: float = Field(..., description="歷史成功率", ge=0.0, le=1.0)
    stability: float = Field(..., description="穩定度", ge=0.0, le=1.0)
    total_score: float = Field(..., description="總評分", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


# ============================================================================
# Intent DSL 相關模型（v4.0 新增）
# ============================================================================


class IntentDSL(BaseModel):
    """Intent DSL 定義模型

    用於定義結構化的 Intent，支持版本管理。
    """

    name: str = Field(..., description="Intent 名稱，如 'modify_document'")
    domain: str = Field(..., description="領域，如 'system_architecture'")
    target: Optional[str] = Field(None, description="目標 Agent，如 'Document Editing Agent'")
    output_format: List[str] = Field(
        default_factory=list, description="輸出格式，如 ['Engineering Spec']"
    )
    depth: Literal["Basic", "Intermediate", "Advanced"] = Field(..., description="深度級別")
    version: str = Field(..., description="版本號，語義化版本，如 '1.0.0'")
    default_version: bool = Field(default=False, description="是否為默認版本")
    is_active: bool = Field(default=True, description="是否啟用")
    description: Optional[str] = Field(None, description="Intent 描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class IntentCreate(BaseModel):
    """創建 Intent 請求模型"""

    name: str = Field(..., description="Intent 名稱")
    domain: str = Field(..., description="領域")
    target: Optional[str] = Field(None, description="目標 Agent")
    output_format: List[str] = Field(default_factory=list, description="輸出格式列表")
    depth: Literal["Basic", "Intermediate", "Advanced"] = Field(..., description="深度級別")
    version: str = Field(..., description="版本號")
    default_version: bool = Field(default=False, description="是否為默認版本")
    description: Optional[str] = Field(None, description="Intent 描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class IntentUpdate(BaseModel):
    """更新 Intent 請求模型"""

    domain: Optional[str] = Field(None, description="領域")
    target: Optional[str] = Field(None, description="目標 Agent")
    output_format: Optional[List[str]] = Field(None, description="輸出格式列表")
    depth: Optional[Literal["Basic", "Intermediate", "Advanced"]] = Field(None, description="深度級別")
    default_version: Optional[bool] = Field(None, description="是否為默認版本")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    description: Optional[str] = Field(None, description="Intent 描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


class IntentQuery(BaseModel):
    """查詢 Intent 請求模型"""

    name: Optional[str] = Field(None, description="Intent 名稱")
    domain: Optional[str] = Field(None, description="領域")
    version: Optional[str] = Field(None, description="版本號（如果為 None 則查詢默認版本）")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    default_version: Optional[bool] = Field(None, description="是否為默認版本")


# ============================================================================
# Capability 相關模型（v4.0 新增）
# ============================================================================


class Capability(BaseModel):
    """Capability 定義模型

    用於定義 Agent 的能力，包括輸入輸出類型和約束條件。
    """

    name: str = Field(..., description="能力名稱，如 'generate_patch_design'")
    agent: str = Field(..., description="所屬 Agent，如 'DocumentEditingAgent'")
    input: str = Field(..., description="輸入類型，如 'SemanticSpec'")
    output: str = Field(..., description="輸出類型，如 'PatchPlan'")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="約束條件")
    version: str = Field(default="1.0.0", description="版本號")
    is_active: bool = Field(default=True, description="是否啟用")
    description: Optional[str] = Field(None, description="能力描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class CapabilityCreate(BaseModel):
    """創建 Capability 請求模型"""

    name: str = Field(..., description="能力名稱")
    agent: str = Field(..., description="所屬 Agent")
    input: str = Field(..., description="輸入類型")
    output: str = Field(..., description="輸出類型")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="約束條件")
    version: str = Field(default="1.0.0", description="版本號")
    description: Optional[str] = Field(None, description="能力描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class CapabilityUpdate(BaseModel):
    """更新 Capability 請求模型"""

    input: Optional[str] = Field(None, description="輸入類型")
    output: Optional[str] = Field(None, description="輸出類型")
    constraints: Optional[Dict[str, Any]] = Field(None, description="約束條件")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    description: Optional[str] = Field(None, description="能力描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="額外元數據")


# ============================================================================
# RAG Chunk 相關模型（v4.0 新增）
# ============================================================================


class ArchitectureAwarenessChunk(BaseModel):
    """RAG-1: Architecture Awareness Chunk Schema

    用於存儲系統架構和拓撲信息。
    """

    chunk_id: str = Field(..., description="Chunk 唯一標識")
    namespace: Literal["rag_architecture_awareness"] = Field(
        default="rag_architecture_awareness", description="Namespace ID"
    )
    content: str = Field(..., description="文本內容")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="元數據（doc_type, doc_id, section, created_at）",
    )
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")


class CapabilityDiscoveryChunk(BaseModel):
    """RAG-2: Capability Discovery Chunk Schema（最重要）

    用於存儲 Agent Capability 信息，是能力發現的唯一來源。
    """

    chunk_id: str = Field(..., description="Chunk 唯一標識")
    namespace: Literal["rag_capability_discovery"] = Field(
        default="rag_capability_discovery", description="Namespace ID"
    )
    content: str = Field(..., description="結構化 Capability 描述文本")
    metadata: Dict[str, Any] = Field(
        ...,
        description="Capability 元數據（agent, capability_name, input_type, output_type, constraints, is_active, version）",
    )
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")


class PolicyConstraintChunk(BaseModel):
    """RAG-3: Policy & Constraint Chunk Schema

    用於存儲策略和約束知識。
    """

    chunk_id: str = Field(..., description="Chunk 唯一標識")
    namespace: Literal["rag_policy_constraint"] = Field(
        default="rag_policy_constraint", description="Namespace ID"
    )
    content: str = Field(..., description="策略或約束描述文本")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="策略元數據（policy_type, risk_level, scope, conditions, created_at）",
    )
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")


# ============================================================================
# Policy & Constraint 相關模型（v4.0 新增）
# ============================================================================


class PolicyValidationResult(BaseModel):
    """L4 層級輸出：策略驗證結果"""

    allowed: bool = Field(..., description="是否允許執行")
    requires_confirmation: bool = Field(default=False, description="是否需要用戶確認")
    risk_level: Literal["low", "mid", "high"] = Field(..., description="風險等級")
    reasons: List[str] = Field(default_factory=list, description="拒絕或需要確認的原因")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class PolicyRule(BaseModel):
    """策略規則模型"""

    rule_id: str = Field(..., description="規則 ID")
    rule_type: Literal["permission", "risk", "resource"] = Field(..., description="規則類型")
    conditions: Dict[str, Any] = Field(..., description="觸發條件")
    action: Literal["allow", "deny", "require_confirmation"] = Field(..., description="動作")
    risk_level: Optional[Literal["low", "mid", "high"]] = Field(None, description="風險等級")
    description: Optional[str] = Field(None, description="規則描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


# ============================================================================
# Task DAG 相關模型（v4.0 新增）
# ============================================================================


class TaskNode(BaseModel):
    """任務節點模型"""

    id: str = Field(..., description="任務 ID，如 'T1'")
    capability: str = Field(..., description="使用的 Capability 名稱")
    agent: str = Field(..., description="所屬 Agent 名稱")
    depends_on: List[str] = Field(default_factory=list, description="依賴的任務 ID 列表")
    description: Optional[str] = Field(None, description="任務描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class TaskDAG(BaseModel):
    """任務 DAG 模型"""

    task_graph: List[TaskNode] = Field(..., description="任務圖節點列表")
    reasoning: Optional[str] = Field(None, description="規劃理由")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
