from __future__ import annotations
# 代碼功能說明: LangGraph任務執行引擎
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""LangGraph任務執行引擎 - 負責協調任務執行和狀態管理"""
import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.state import AIBoxState
from genai.workflows.langgraph.nodes import get_node_executor, NodeResult
from genai.workflows.infra.cache import MultiLayerCache

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """執行上下文"""
    execution_id: str
    task_id: str
    user_id: str
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    current_layer: str = "input"
    execution_status: str = "running"
    node_results: List[Dict[str, Any]] = field(default_factory=list)
    layers_executed: List[str] = field(default_factory=list)
    error_count: int = 0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """執行結果"""
    execution_id: str
    success: bool
    final_state: AIBoxState
    execution_time: float
    node_count: int
    error_count: int
    layers_executed: List[str]
    final_layer: str
    reasoning: str = ""


class TaskExecutionEngine:
    """任務執行引擎 - 負責LangGraph任務的完整執行"""
    def __init__(self, cache: Optional[MultiLayerCache] = None):
        self.node_executor = get_node_executor()
        self._active_executions: Dict[str, ExecutionContext] = {}
        self.logger = logging.getLogger(__name__)
        self.cache = cache or MultiLayerCache()

    async def execute_task(self, initial_state: AIBoxState) -> ExecutionResult:
        """
        執行完整任務流程 (優化版：支持快取和並行)

        Args:
            initial_state: 初始狀態

        Returns:
            ExecutionResult: 執行結果
        """
        # 1. 檢查快取
        user_id = initial_state.user_id or "unknown"
        task_id = initial_state.task_id or "unknown"
        session_id = initial_state.session_id or "unknown"

        # 模擬從狀態中獲取任務描述
        task_desc = "unknown_task"
        if hasattr(initial_state, "task"):
            task_desc = str(getattr(initial_state, "task"))

        cache_key = f"workflow_result:{task_desc}_{user_id}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.info(f"Returning cached workflow result for task {task_id}")
            # return self._reconstruct_result(cached_result, initial_state)

        execution_id = f"exec_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 創建執行上下文
        context = ExecutionContext(
            execution_id=execution_id,
            task_id=task_id,
            user_id=user_id,
            session_id=session_id,
        )
        self._active_executions[execution_id] = context

        start_time = datetime.now()
        current_state = initial_state
        layers_executed: List[str] = []

        try:
            # 初始化第一個要執行的層次
            next_layers = ["semantic_analysis"]

            # 主執行循環
            while next_layers:
                self.logger.info(f"Executing layers: {next_layers} for task {context.task_id}")

                # 並行執行層次
                layer_tasks = [
                    self._execute_layer(layer, current_state, context) for layer in next_layers
                ]

                # 使用 return_exceptions=True 確保異常不會中斷其他任務
                results = await asyncio.gather(*layer_tasks, return_exceptions=True)

                # 收集下一步要執行的層次
                all_next_layers = []

                for layer, layer_result in zip(next_layers, results):
                    # 處理異常情況
                    if isinstance(layer_result, Exception):
                        self.logger.error(
                            f"Layer {layer} execution raised exception: {layer_result}",
                            exc_info=True,
                        )
                        layer_result = NodeResult.failure(str(layer_result))
                        context.error_count += 1
                    elif not isinstance(layer_result, NodeResult):
                        self.logger.error(
                            f"Layer {layer} execution returned invalid result type: {type(layer_result)}",
                        )
                        layer_result = NodeResult.failure("Invalid result type")
                        context.error_count += 1

                    layers_executed.append(layer)
                    context.layers_executed.append(layer)

                    if not layer_result.success:
                        self.logger.error(f"Layer {layer} execution failed: {layer_result.error}")
                        context.error_count += 1
                        if not self._should_continue_after_failure(context, layer_result):
                            return self._finalize_execution(
                                execution_id,
                                context,
                                current_state,
                                layers_executed,
                                start_time,
                                False,
                            )

                    if layer_result.success and layer_result.next_layer:
                        # 避免重複添加相同的下一層
                        if layer_result.next_layer not in all_next_layers:
                            all_next_layers.append(layer_result.next_layer)
                        # 更新狀態層次（只更新一次，避免重複更新）
                        if current_state.current_layer != layer_result.next_layer:
                            current_state.update_layer(layer_result.next_layer)
                            context.current_layer = layer_result.next_layer

                # 更新下一步
                if all_next_layers:
                    next_layers = all_next_layers
                else:
                    # 如果沒有明確的 next_layer，嘗試使用默認路徑
                    next_layers = self._determine_next_layers(context, current_state)

                # 檢查是否完成
                if self._is_execution_complete(context, current_state):
                    # 如果沒有更多要執行的層次了，則跳出
                    if not next_layers:
                        break

            return self._finalize_execution(
                execution_id, context, current_state, layers_executed, start_time, True,
            )

        except Exception as e:
            self.logger.error(f"Task execution failed: {execution_id}, error={e}", exc_info=True)
            return self._finalize_execution(
                execution_id, context, current_state, layers_executed, start_time, False, str(e)
            )

    async def _execute_layer(
        self, layer_name: str, state: AIBoxState, context: ExecutionContext,
    ) -> NodeResult:
        """執行單個層次"""
        try:
            node_name = self._map_layer_to_node(layer_name)
            if not node_name:
                return NodeResult.failure(f"No node mapped for layer: {layer_name}")

            result = await self.node_executor.execute_node(node_name, state)
            context.node_results.append(
                {
                    "layer": layer_name,
                    "node": node_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "error": result.error,
                    "next_layer": result.next_layer,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return result
        except Exception as e:
            self.logger.error(f"Layer execution failed: {layer_name}, error={e}")
            return NodeResult.failure(f"Layer execution error: {e}")

    def _map_layer_to_node(self, layer_name: str) -> Optional[str]:
        layer_to_node_map = {
            "semantic_analysis": "SemanticAgent",
            "intent_analysis": "IntentAgent",
            "capability_matching": "CapabilityAgent",
            "resource_check": "ResourceManager",
            "policy_verification": "PolicyAgent",
            "task_orchestration": "OrchestratorAgent",
            "task_execution": "TaskExecutorAgent",
            "simple_response": "SimpleResponseAgent",
            "clarification": "ClarificationAgent",
        }
        return layer_to_node_map.get(layer_name)

    def _determine_next_layers(self, context: ExecutionContext, state: AIBoxState) -> List[str]:
        current_layer = context.current_layer

        # 定義哪些層次可以並行執行
        parallel_groups = {
            "input": ["semantic_analysis"],
            "semantic_analysis": [
                "intent_analysis",
                "resource_check",
                "simple_response",
                "clarification",
            ],
            "intent_analysis": ["capability_matching"],
            "resource_check": ["policy_verification"],
            "capability_matching": ["task_orchestration"],
            "policy_verification": ["task_orchestration"],
            "task_orchestration": ["task_execution"],
            "simple_response": [],
            "clarification": [],
            "task_execution": [],
        }

        next_layers = parallel_groups.get(current_layer, [])
        return [next_layers[0]] if next_layers else []

    def _is_execution_complete(self, context: ExecutionContext, state: AIBoxState) -> bool:
        if context.error_count >= 3:
            return True

        # 安全獲取執行狀態
        execution_status = getattr(state, "execution_status", "running")
        if execution_status in ["completed", "failed"]:
            return True

        terminal_layers = ["simple_response", "clarification", "task_execution"]
        if context.current_layer in terminal_layers:
            return True

        return False

    def _should_continue_after_failure(self, context: ExecutionContext, result: NodeResult) -> bool:
        if context.error_count >= 3:
            return False
        critical_layers = ["policy_verification", "task_orchestration"]
        if context.current_layer in critical_layers and not result.success:
            return False
        return True

    def _evaluate_overall_success(self, context: ExecutionContext, final_state: AIBoxState) -> bool:
        if context.error_count >= 3:
            return False
        execution_status = getattr(final_state, "execution_status", "running")
        if execution_status == "failed":
            return False
        return len(context.node_results) > 0

    def _generate_execution_reasoning(self, context: ExecutionContext, success: bool) -> str:
        reasoning = f"Task execution {'completed' if success else 'failed'}."
        reasoning += f" Executed {len(context.node_results)} nodes."
        if context.layers_executed:
            reasoning += f" Layers: {', '.join(context.layers_executed)}."
        return reasoning

    def _finalize_execution(
        self,
        execution_id: str ,
        context: ExecutionContext ,
        state: AIBoxState ,
        layers: List[str],
        start_time: datetime ,
        success: bool ,
        error_msg: Optional[str] = None ,
    ) -> ExecutionResult:
        execution_time = (datetime.now() - start_time).total_seconds()
        context.end_time = datetime.now()

        final_success = success and self._evaluate_overall_success(context, state)

        result = ExecutionResult(
            execution_id=execution_id,
            success=final_success,
            final_state=state,
            execution_time=execution_time,
            node_count=len(context.node_results),
            error_count=context.error_count,
            layers_executed=layers,
            final_layer=context.current_layer,
            reasoning=(
                error_msg
                if error_msg
                else self._generate_execution_reasoning(context, final_success)
            ),
        )

        if final_success:
            user_id = state.user_id or "unknown"
            task_desc = "unknown_task"
            if hasattr(state, "task"):
                task_desc = str(getattr(state, "task"))
            cache_key = f"workflow_result:{task_desc}_{user_id}"
            self.cache.set(cache_key, {"success": True, "task_id": state.task_id}, ttl=300)

        if execution_id in self._active_executions:
            del self._active_executions[execution_id]

        return result
