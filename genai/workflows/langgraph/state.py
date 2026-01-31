from __future__ import annotations
# 代碼功能說明: LangGraph狀態定義與管理
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""LangGraph狀態定義與管理 - AI-Box完整狀態結構"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息結構定義"""
    role: Literal["user", "assistant", "system"] 
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SemanticAnalysis:
    """語義分析結果"""
    query_type: str
    complexity: Literal["simple", "medium", "complex"] 
    topics: List[str] 
    sentiment: Optional[str] = None
    confidence: float = 0.0


@dataclass
class IntentDSL:
    """意圖DSL結構"""
    intent_type: str
    parameters: Dict[str, Any] 
    confidence: float = 0.0
    dsl_expression: Optional[str] = None


@dataclass
class Capability:
    """能力定義"""
    name: str
    type: str
    priority: int = 0
    requirements: Dict[str, Any] = field(default_factory=dict) 
    available: bool = True


@dataclass
class ExecutionResult:
    """執行結果"""
    agent_id: str
    status: Literal["success", "failure", "partial"] 
    timestamp: datetime = field(default_factory=datetime.now) 
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class AuditEntry:
    """審計記錄"""
    action: str
    details: Dict[str, Any] 
    timestamp: datetime = field(default_factory=datetime.now) 
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class Observation:
    """觀察記錄"""
    type: str
    data: Dict[str, Any] 
    timestamp: datetime = field(default_factory=datetime.now) 
    confidence: float = 0.0


@dataclass
class AIBoxState:
    """AI-Box完整狀態定義 - LangGraph狀態結構"""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    current_layer: str = "input" 
    messages: List[Message] = field(default_factory=list) 
    task_id: Optional[str] = None
    request_id: Optional[str] = None

    # === 輸入分類狀態 ===
    input_type: Literal["free", "assistant", "agent"] = "free" 
    injected_context: Optional[Dict[str, Any]] = None
    selected_assistant: Optional[str] = None
    selected_agent: Optional[str] = None
    assistant_config: Optional[Dict[str, Any]] = None
    agent_config: Optional[Dict[str, Any]] = None

    # === 處理狀態 ===
    semantic_analysis: Optional[Any] = None
    intent_analysis: Optional[Any] = None
    capability_analysis: Optional[Any] = None
    capability_match: List[Capability] = field(default_factory=list) 
    resources_available: bool = True
    resource_details: Optional[Dict[str, Any]] = None
    resource_allocation: Optional[Any] = None
    policy_passed: bool = True
    policy_details: Optional[Dict[str, Any]] = None
    policy_verification: Optional[Any] = None
    simple_response: Optional[Any] = None
    user_confirmation: Optional[Any] = None  # 新增
    clarification_details: Optional[Any] = None

    # === 編排狀態 ===
    dispatched_agents: List[str] = field(default_factory=list) 
    execution_results: List[ExecutionResult] = field(default_factory=list) 
    current_agent: Optional[str] = None
    orchestration_plan: Optional[Dict[str, Any]] = None
    task_orchestration: Optional[Any] = None
    task_management: Optional[Any] = None
    workspace_management: Optional[Any] = None
    performance_optimization: Optional[Any] = None
    system_observation: Optional[Any] = None
    error_handling: Optional[Any] = None  # 新增
    task_execution: Optional[Any] = None

    # === 文件處理狀態 ===
    file_ids: List[str] = field(default_factory=list) 
    processing_files: bool = False
    file_processing_status: Dict[str, str] = field(default_factory=dict) 
    retrieval_needed: bool = False
    retrieval_context: Optional[Dict[str, Any]] = None
    vision_analysis: List[Dict[str, Any]] = field(default_factory=list)

    # === 模型調用狀態 ===
    selected_model: Optional[str] = None
    model_configuration: Optional[Dict[str, Any]] = None
    model_response: Optional[str] = None
    model_metadata: Optional[Dict[str, Any]] = None

    # === 審計狀態 ===
    audit_log: List[AuditEntry] = field(default_factory=list) 
    observations: List[Observation] = field(default_factory=list)

    # === 最終輸出 ===
    final_response: Optional[str] = None
    confidence_score: float = 0.0
    response_metadata: Optional[Dict[str, Any]] = None
    execution_status: str = "pending"

    # === 時間戳 ===
    created_at: datetime = field(default_factory=datetime.now) 
    updated_at: datetime = field(default_factory=datetime.now)

    def update_timestamp(self) -> None:
        """更新時間戳"""
        self.updated_at = datetime.now()

    def add_message(
        self, role: Literal["user", "assistant", "system"], content: str, **metadata,
    ) -> None:
        """添加消息到狀態"""
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.update_timestamp()

    def add_audit_entry(
        self,
        action: str ,
        details: Dict[str, Any] 
        user_id: Optional[str] = None ,
        session_id: Optional[str] = None ,
    ) -> None:
        """添加審計記錄"""
        entry = AuditEntry(
            action=action,
            details=details,
            user_id=user_id or self.user_id,
            session_id=session_id or self.session_id,
        )
        self.audit_log.append(entry)

    def add_observation(
        self, observation_type: str, data: Dict[str, Any], confidence: float = 0.0,
    ) -> None:
        """添加觀察記錄"""
        observation = Observation(type=observation_type, data=data, confidence=confidence)
        self.observations.append(observation)

    def add_execution_result(
        self,
        agent_id: str ,
        status: Literal["success", "failure", "partial"] 
        result: Optional[Dict[str, Any]] = None ,
        error: Optional[str] = None ,
        duration: float = 0.0 ,
    ) -> None:
        """添加執行結果"""
        exec_result = ExecutionResult(
            agent_id=agent_id, status=status, result=result, error=error, duration=duration,
        )
        self.execution_results.append(exec_result)

    def update_layer(self, layer_name: str) -> None:
        """更新當前執行層次"""
        self.add_audit_entry("layer_transition", {"from": self.current_layer, "to": layer_name})
        self.current_layer = layer_name
        self.update_timestamp()

    def validate_state(self) -> bool:
        """驗證狀態完整性"""
        if not self.session_id or not self.user_id:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典以進行持久化"""
        def serialize_datetime(dt):
            """序列化 datetime 對象"""
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return dt

        def serialize_value(value):
            """遞歸序列化值"""
            if value is None:
                return None
            if isinstance(value, datetime):
                return serialize_datetime(value)
            if isinstance(value, (str, int, float, bool)):
                return value
            if isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [serialize_value(item) for item in value]
            # 處理 dataclass 對象
            if hasattr(value, "__dict__"):
                return {
                    k: serialize_value(v)
                    for k, v in value.__dict__.items()
                    if not k.startswith("_")
                }
            # 處理其他對象（嘗試轉換為字符串）
            try:
                return str(value)
            except Exception:
                return None

        def serialize_dataclass(obj):
            """序列化 dataclass 對象"""
            if obj is None:
                return None
            if hasattr(obj, "__dict__"):
                result = {}
                for k, v in obj.__dict__.items():
                    if not k.startswith("_"):
                        result[k] = serialize_value(v)
                return result
            return serialize_value(obj)

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "current_layer": self.current_layer,
            "messages": [serialize_dataclass(msg) for msg in self.messages],
            "task_id": self.task_id,
            "request_id": self.request_id,
            # === 輸入分類狀態 ===
            "input_type": self.input_type,
            "injected_context": serialize_value(self.injected_context),
            "selected_assistant": self.selected_assistant,
            "selected_agent": self.selected_agent,
            "assistant_config": serialize_value(self.assistant_config),
            "agent_config": serialize_value(self.agent_config),
            # === 處理狀態 ===
            "semantic_analysis": serialize_dataclass(self.semantic_analysis),
            "intent_analysis": serialize_dataclass(self.intent_analysis),
            "capability_analysis": serialize_dataclass(self.capability_analysis),
            "capability_match": [serialize_dataclass(cap) for cap in self.capability_match],
            "resources_available": self.resources_available,
            "resource_details": serialize_value(self.resource_details),
            "resource_allocation": serialize_dataclass(self.resource_allocation),
            "policy_passed": self.policy_passed,
            "policy_details": serialize_value(self.policy_details),
            "policy_verification": serialize_dataclass(self.policy_verification),
            "simple_response": serialize_dataclass(self.simple_response),
            "user_confirmation": serialize_dataclass(self.user_confirmation),
            "clarification_details": serialize_dataclass(self.clarification_details),
            # === 編排狀態 ===
            "dispatched_agents": self.dispatched_agents,
            "execution_results": [serialize_dataclass(result) for result in self.execution_results],
            "current_agent": self.current_agent,
            "orchestration_plan": serialize_value(self.orchestration_plan),
            "task_orchestration": serialize_dataclass(self.task_orchestration),
            "task_management": serialize_dataclass(self.task_management),
            "workspace_management": serialize_dataclass(self.workspace_management),
            "performance_optimization": serialize_dataclass(self.performance_optimization),
            "system_observation": serialize_dataclass(self.system_observation),
            "error_handling": serialize_dataclass(self.error_handling),
            "task_execution": serialize_dataclass(self.task_execution),
            # === 文件處理狀態 ===
            "file_ids": self.file_ids,
            "processing_files": self.processing_files,
            "file_processing_status": serialize_value(self.file_processing_status),
            "retrieval_needed": self.retrieval_needed,
            "retrieval_context": serialize_value(self.retrieval_context),
            "vision_analysis": serialize_value(self.vision_analysis),
            # === 模型調用狀態 ===
            "selected_model": self.selected_model,
            "model_configuration": serialize_value(self.model_configuration),
            "model_response": self.model_response,
            "model_metadata": serialize_value(self.model_metadata),
            # === 審計狀態 ===
            "audit_log": [serialize_dataclass(entry) for entry in self.audit_log],
            "observations": [serialize_dataclass(obs) for obs in self.observations],
            # === 最終輸出 ===
            "final_response": self.final_response,
            "confidence_score": self.confidence_score,
            "response_metadata": serialize_value(self.response_metadata),
            "execution_status": self.execution_status,
            # === 時間戳 ===
            "created_at": serialize_datetime(self.created_at),
            "updated_at": serialize_datetime(self.updated_at),
        }

    def to_json(self) -> str:
        """轉換為JSON字符串"""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AIBoxState:
        """從字典創建狀態"""
        # 處理嵌套對象的反序列化
        messages = [Message(**msg) for msg in data.get("messages", [])]
        execution_results = [
            ExecutionResult(**result) for result in data.get("execution_results", [])
        ]
        audit_log = [AuditEntry(**entry) for entry in data.get("audit_log", [])]
        observations = [Observation(**obs) for obs in data.get("observations", [])]

        return cls(
            session_id=data.get("session_id")
            user_id=data.get("user_id")
            current_layer=data.get("current_layer", "input"),
            messages=messages,
            task_id=data.get("task_id")
            request_id=data.get("request_id")
            input_type=data.get("input_type", "free"),
            injected_context=data.get("injected_context")
            execution_results=execution_results,
            audit_log=audit_log,
            observations=observations,
            final_response=data.get("final_response")
            confidence_score=data.get("confidence_score", 0.0),
            response_metadata=data.get("response_metadata")
            execution_status=data.get("execution_status", "pending"),
        )

    def clone_state(self, state: AIBoxState) -> AIBoxState:
        """克隆狀態 - 用於狀態分支"""
        cloned_data = state.to_dict()
        cloned_data["audit_log"] = []  # 重置審計日誌
        cloned_data["observations"] = []  # 重置觀察記錄

        cloned = AIBoxState.from_dict(cloned_data)
        cloned.add_audit_entry("state_cloned", {"from_state": state.session_id}))

        return cloned