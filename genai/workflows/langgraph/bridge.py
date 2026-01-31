from __future__ import annotations
# 代碼功能說明: 狀態橋接層實現
# 創建日期: 2026-01-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25

"""狀態橋接層 - 實現TaskAnalyzer與LangGraph狀態的雙向轉換"""
import logging
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.state import AIBoxState, StateManager

logger = logging.getLogger(__name__)


class StateBridge:
    """狀態橋接器 - 負責不同狀態格式的轉換"""
    def __init__(self):
        self.state_manager = StateManager()
        self.logger = logging.getLogger(__name__)

    def task_analyzer_to_langgraph(self, task_result: Dict[str, Any]) -> AIBoxState:
        """
        將TaskAnalyzer結果轉換為LangGraph狀態

        Args:
            task_result: TaskAnalyzer.analyze()的返回值

        Returns:
            AIBoxState: LangGraph狀態
        """
        try:
            # 從task_result中提取基本信息
            user_id = task_result.get("user_id", "unknown")
            session_id = task_result.get("session_id", "unknown")
            task_id = task_result.get("task_id")

            # 創建初始狀態
            state = self.state_manager.create_initial_state(
                user_id=user_id,
                session_id=session_id,
                input_type="free",  # 默認自由對話，可根據task_result調整
                task_id=task_id,
            )

            # 轉換語義分析結果
            if "semantic_analysis" in task_result:
                from genai.workflows.langgraph.state import SemanticAnalysis

                semantic_data = task_result["semantic_analysis"]
                state.semantic_analysis = SemanticAnalysis(**semantic_data)

            # 轉換意圖分析結果
            if "intent_analysis" in task_result:
                from genai.workflows.langgraph.state import IntentDSL

                intent_data = task_result["intent_analysis"]
                state.intent_analysis = IntentDSL(**intent_data)

            # 轉換能力匹配結果
            if "capability_match" in task_result:
                from genai.workflows.langgraph.state import Capability

                capabilities = []
                for cap_data in task_result["capability_match"]:
                    capabilities.append(Capability(**cap_data))
                state.capability_match = capabilities

            # 轉換資源檢查結果
            if "resource_check" in task_result:
                resource_data = task_result["resource_check"]
                state.resources_available = resource_data.get("available", True)
                state.resource_details = resource_data.get("details")

            # 轉換策略驗證結果
            if "policy_check" in task_result:
                policy_data = task_result["policy_check"]
                state.policy_passed = policy_data.get("passed", True)
                state.policy_details = policy_data.get("details")

            # 轉換DAG結果為編排計劃
            if "task_dag" in task_result:
                dag_data = task_result["task_dag"]
                state.orchestration_plan = {
                    "dag": dag_data,
                    "estimated_complexity": self._estimate_complexity(dag_data),
                }

            # 設置初始審計記錄
            state.add_audit_entry(
                "state_bridge_conversion", {"source": "task_analyzer", "target": "langgraph"}
            )

            self.logger.info(
                f"Successfully converted TaskAnalyzer result to LangGraph state for user {user_id}",
            )
            return state

        except Exception as e:
            self.logger.error(f"Failed to convert TaskAnalyzer result to LangGraph state: {e}")
            raise

    def langgraph_to_task_analyzer(self, state: AIBoxState) -> Dict[str, Any]:
        """
        將LangGraph狀態轉換為TaskAnalyzer期望的格式

        Args:
            state: LangGraph狀態

        Returns:
            Dict: TaskAnalyzer可處理的格式
        """
        try:
            result = {
                "user_id": state.user_id,
                "session_id": state.session_id,
                "task_id": state.task_id,
                "request_id": state.request_id,
                "current_layer": state.current_layer,
                "input_type": state.input_type,
                "messages": [msg.__dict__ for msg in state.messages],
            }

            # 轉換語義分析
            if state.semantic_analysis:
                result["semantic_analysis"] = state.semantic_analysis.__dict__

            # 轉換意圖分析
            if state.intent_analysis:
                result["intent_analysis"] = state.intent_analysis.__dict__

            # 轉換能力匹配
            if state.capability_match:
                result["capability_match"] = [cap.__dict__ for cap in state.capability_match]

            # 轉換資源信息
            if state.resource_details:
                result["resource_check"] = {
                    "available": state.resources_available,
                    "details": state.resource_details,
                }

            # 轉換策略信息
            if state.policy_details:
                result["policy_check"] = {
                    "passed": state.policy_passed,
                    "details": state.policy_details,
                }

            # 轉換編排計劃
            if state.orchestration_plan:
                result["task_dag"] = state.orchestration_plan.get("dag")
                result["estimated_complexity"] = state.orchestration_plan.get(
                    "estimated_complexity",
                )

            # 轉換執行結果
            if state.execution_results:
                result["execution_history"] = [
                    result.__dict__ for result in state.execution_results
                ]

            # 轉換審計日誌
            if state.audit_log:
                result["audit_trail"] = [entry.__dict__ for entry in state.audit_log]

            self.logger.info(
                f"Successfully converted LangGraph state to TaskAnalyzer format for user {state.user_id}",
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to convert LangGraph state to TaskAnalyzer format: {e}")
            raise

    def _estimate_complexity(self, dag_data: Dict[str, Any]) -> str:
        """估計任務複雜度"""
        try:
            if not dag_data or "task_graph" not in dag_data:
                return "simple"

            task_count = len(dag_data["task_graph"])

            if task_count <= 2:
                return "simple"
            elif task_count <= 5:
                return "medium",
            else:
                return "complex"

        except Exception:
            return "medium"


class WorkflowStateBridge:
    """工作流狀態橋接器 - 處理AutoGen/LangGraph間的狀態同步"""
    def __init__(self):
        self.state_bridge = StateBridge()
        self.logger = logging.getLogger(__name__)

    def autogen_to_langgraph(self, autogen_plan: Dict[str, Any]) -> AIBoxState:
        """
        將AutoGen計劃轉換為LangGraph狀態

        Args:
            autogen_plan: AutoGen生成的工作流計劃

        Returns:
            AIBoxState: LangGraph狀態
        """
        try:
            # 提取基本信息
            user_id = autogen_plan.get("user_id", "unknown")
            session_id = autogen_plan.get("session_id", f"autogen_{user_id}")

            # 創建狀態
            state = self.state_bridge.state_manager.create_initial_state(
                user_id=user_id,
                session_id=session_id,
                input_type="agent",  # AutoGen通常用於複雜任務
            )

            # 轉換計劃信息
            state.orchestration_plan = {
                "source": "autogen",
                "plan": autogen_plan.get("plan", []),
                "current_step": autogen_plan.get("current_step", 0),
                "total_steps": len(autogen_plan.get("plan", [])),
            }

            # 轉換輸出
            if "outputs" in autogen_plan:
                state.execution_results = []
                for i, output in enumerate(autogen_plan["outputs"]):
                    from genai.workflows.langgraph.state import ExecutionResult

                    result = ExecutionResult(
                        agent_id=f"autogen_step_{i}", status="success", result={"output": output}
                    )
                    state.execution_results.append(result)

            state.add_audit_entry(
                "workflow_bridge_conversion", {"source": "autogen", "target": "langgraph"}
            )

            self.logger.info(f"Converted AutoGen plan to LangGraph state for user {user_id}")
            return state

        except Exception as e:
            self.logger.error(f"Failed to convert AutoGen plan to LangGraph state: {e}")
            raise

    def langgraph_to_autogen(self, state: AIBoxState) -> Dict[str, Any]:
        """
        將LangGraph狀態轉換為AutoGen期望的格式

        Args:
            state: LangGraph狀態

        Returns:
            Dict: AutoGen可處理的格式
        """
        try:
            result = {
                "user_id": state.user_id,
                "session_id": state.session_id,
                "plan": state.orchestration_plan.get("plan", [])
                if state.orchestration_plan
                else [],
                "current_step": state.orchestration_plan.get("current_step", 0)
                if state.orchestration_plan
                else 0,
                "outputs": [
                    result.result.get("output")
                    for result in state.execution_results
                    if result.result
                ],
                "context": {
                    "messages": [msg.__dict__ for msg in state.messages],
                    "current_layer": state.current_layer,
                },
            }

            self.logger.info(
                f"Converted LangGraph state to AutoGen format for user {state.user_id}",
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to convert LangGraph state to AutoGen format: {e}")
            raise


# 全局橋接器實例
_state_bridge = None
_workflow_bridge = None


def get_state_bridge() -> StateBridge:
    """獲取狀態橋接器實例"""
    global _state_bridge
    if _state_bridge is None:
        _state_bridge = StateBridge()
    return _state_bridge


def get_workflow_state_bridge() -> WorkflowStateBridge:
    """獲取工作流狀態橋接器實例"""
    global _workflow_bridge
    if _workflow_bridge is None:
        _workflow_bridge = WorkflowStateBridge()
    return _workflow_bridge