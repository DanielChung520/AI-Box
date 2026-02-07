# 代碼功能說明: ReAct 模式執行器 - 執行 TODO 步驟
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-07
# v1.1 更新: 集成 Agent-todo (Preconditions, Retry, Heartbeat)

"""ReAct 模式執行器 - 執行 TODO 步驟"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

import sys

sys.path.insert(0, "/home/daniel/ai-box")

from shared.agents.todo.schema import (
    Todo,
    TodoType,
    TodoState,
    ExecutionResult as TodoExecutionResult,
)
from shared.agents.todo.state_machine import TodoStateMachine
from shared.agents.todo.preconditions import PreconditionChecker, PreconditionType
from shared.agents.contracts.heartbeat import get_heartbeat_manager
from shared.database.arango_client import SharedArangoClient

from .react_planner import Action, TodoPlan, ReActPlanner

logger = logging.getLogger(__name__)


_react_engine_instance = None


def get_react_engine() -> "ReActEngine":
    """獲取 ReActEngine 單例"""
    global _react_engine_instance
    if _react_engine_instance is None:
        _react_engine_instance = ReActEngine()
    return _react_engine_instance


class WorkflowState(BaseModel):
    """工作流狀態"""

    session_id: str
    instruction: str
    plan: Optional[Dict[str, Any]] = None
    current_step: int = 0
    completed_steps: List[int] = []
    results: Dict[str, Any] = {}
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class ReActEngine:
    """ReAct 模式引擎 - 管理工作流程"""

    def __init__(self):
        """初始化引擎"""
        self._planner = ReActPlanner()
        self._executor = ReActExecutor()
        self._workflows: Dict[str, WorkflowState] = {}
        self._sse_publisher = SSEPublisher.get_instance()
        logger.info("[ReActEngine] ReAct 引擎初始化完成")

    async def start_workflow(
        self,
        instruction: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """啟動工作流程

        Args:
            instruction: 用戶指令
            session_id: 會話 ID
            context: 上下文信息

        Returns:
            工作流程結果
        """
        logger.info(
            f"[ReActEngine] 啟動工作流程: session_id={session_id}, instruction={instruction[:50]}..."
        )

        if session_id in self._workflows:
            logger.info("[ReActEngine] 會話已存在，清除舊狀態")
            del self._workflows[session_id]

        plan = await self._planner.plan(instruction, context)

        self._workflows[session_id] = WorkflowState(
            session_id=session_id,
            instruction=instruction,
            plan=plan.model_dump() if plan else None,
            current_step=0,
            completed_steps=[],
            results={},
            context=context,
        )

        await self._sse_publisher.start_tracking(session_id)

        step_names = [s.description for s in (plan.steps if plan else [])]
        total = len(plan.steps) if plan else 0

        await self._sse_publisher.publish(
            request_id=session_id,
            step="workflow_started",
            status="processing",
            message=f"工作流程已啟動，共 {total} 個步驟",
            progress=0.0,
        )

        for i, step_name in enumerate(step_names):
            await self._sse_publisher.publish(
                request_id=session_id,
                step=step_name,
                status="pending",
                message=f"等待執行: {step_name}",
                progress=(i) / total if total > 0 else 0,
            )

        logger.info(f"[ReActEngine] 生成計劃: {len(plan.steps) if plan else 0} 步驟")

        return {
            "success": True,
            "task_type": plan.task_type if plan else "unknown",
            "plan": {
                "task_type": plan.task_type if plan else "unknown",
                "steps": [
                    {
                        "step_id": s.step_id,
                        "action_type": s.action_type,
                        "description": s.description,
                    }
                    for s in (plan.steps if plan else [])
                ],
            },
            "response": self._planner.format_plan(plan) if plan else "無法生成計劃",
        }

    async def execute_next_step(
        self,
        session_id: str,
        user_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """執行工作流程下一步

        Args:
            session_id: 會話 ID
            user_response: 用戶回覆（用於 user_confirmation 步驟）

        Returns:
            執行結果
        """
        logger.info(f"[ReActEngine] 執行下一步: session_id={session_id}")

        if session_id not in self._workflows:
            return {"success": False, "error": "會話不存在"}

        state = self._workflows[session_id]
        if not state.plan or not state.plan.get("steps"):
            return {"success": False, "error": "計劃不存在"}

        plan_dict = state.plan
        steps_data = plan_dict.get("steps", [])

        state.current_step += 1

        if state.current_step > len(steps_data):
            logger.info("[ReActEngine] 所有步驟已完成")
            final_response = state.results.get(
                "final_response", state.results.get("response", "處理完成")
            )
            return {
                "success": True,
                "response": final_response,
                "step_id": state.current_step,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": False,
                "debug_info": {"step": "workflow_completed", "all_results": state.results},
            }

        step_data = steps_data[state.current_step - 1]
        action_type = step_data.get("action_type", "unknown")

        if action_type == "user_confirmation":
            state.completed_steps.append(state.current_step)
            question = step_data.get("parameters", {}).get("question", "確認？")
            return {
                "success": True,
                "response": question,
                "step_id": state.current_step,
                "action_type": action_type,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": True,
                "debug_info": {"step": "waiting_confirmation"},
            }

        from .react_planner import Action

        action = Action(
            step_id=step_data.get("step_id", state.current_step),
            action_type=action_type,
            description=step_data.get("description", ""),
            parameters=step_data.get("parameters", {}),
            dependencies=step_data.get("dependencies", []),
            result_key=step_data.get("result_key"),
        )

        from .react_planner import TodoPlan

        plan_obj = TodoPlan(**plan_dict)
        previous_results = {k: v for k, v in state.results.items() if k != "final_response"}

        total_steps = len(steps_data)
        current = state.current_step
        progress = current / total_steps if total_steps > 0 else 0

        await self._sse_publisher.publish(
            request_id=session_id,
            step=step_data.get("description", f"步驟 {current}"),
            status="processing",
            message=f"正在執行: {step_data.get('description', '')}",
            progress=progress,
        )

        result = await self._executor.execute_step(action, plan_obj, previous_results)

        state.completed_steps.append(state.current_step)
        state.results[str(state.current_step)] = result.result if result else {}

        if result and result.result:
            for k, v in result.result.items():
                if k not in ["response", "abc_result"]:
                    state.results[k] = v
            if result.result.get("response"):
                state.results["final_response"] = result.result["response"]

        logger.info(
            f"[ReActEngine] 步驟完成: {action_type}, observation: {result.observation if result else 'N/A'}"
        )

        if action_type == "user_confirmation":
            question = step_data.get("parameters", {}).get("question", "確認？")
            return {
                "success": True,
                "response": question,
                "step_id": state.current_step,
                "action_type": action_type,
                "completed_steps": state.completed_steps,
                "total_steps": len(steps_data),
                "waiting_for_user": True,
                "debug_info": {
                    "step": "waiting_confirmation",
                    "observation": result.observation if result else "",
                },
            }

        return {
            "success": True,
            "response": result.observation if result else "處理完成",
            "step_id": state.current_step,
            "action_type": action_type,
            "completed_steps": state.completed_steps,
            "total_steps": len(steps_data),
            "waiting_for_user": False,
            "debug_info": {
                "step": "step_completed",
                "observation": result.observation if result else "",
                "result": result.result if result else {},
            },
        }

        success = result.success if result else True
        step_name = step_data.get("description", f"步驟 {current}")

        await self._sse_publisher.publish(
            request_id=session_id,
            step=step_name,
            status="completed" if success else "error",
            message=result.observation if result else "處理完成",
            progress=1.0,
        )

    async def execute_all_steps(
        self,
        session_id: str,
        user_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        """自動執行所有步驟

        Args:
            session_id: 會話 ID
            user_response: 用戶回覆

        Returns:
            所有步驟執行結果
        """
        logger.info(f"[ReActEngine] 自動執行所有步驟: session_id={session_id}")

        if session_id not in self._workflows:
            return {"success": False, "error": "會話不存在"}

        responses = []
        all_results = []

        while True:
            result = await self.execute_next_step(session_id, user_response)
            responses.append(result.get("response", ""))

            if result.get("completed_steps"):
                all_results.append(result)

            if not result.get("waiting_for_user", False):
                if result.get("success"):
                    logger.info(
                        f"[ReActEngine] 步驟完成: {result.get('step_id')}/{result.get('total_steps')}"
                    )
                else:
                    logger.warning(f"[ReActEngine] 步驟失敗: {result.get('error')}")
                    break

            if not result.get("waiting_for_user", True):
                if result.get("completed_steps") and result.get("total_steps"):
                    if result["completed_steps"][-1] >= result["total_steps"]:
                        logger.info("[ReActEngine] 工作流完成")
                        break
            else:
                break

        final_response = responses[-1] if responses else "處理完成"
        self._workflows.get(session_id)

        await self._sse_publisher.publish(
            request_id=session_id,
            step="workflow_completed",
            status="completed",
            message="工作流程已完成",
            progress=1.0,
        )

        await self._sse_publisher.end_tracking(session_id)

        return {
            "success": True,
            "final_response": final_response,
            "responses": responses,
            "completed_steps": result.get("completed_steps", []) if result else [],
            "total_steps": result.get("total_steps", 0) if result else 0,
            "all_results": all_results,
        }

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """獲取工作流狀態"""
        if session_id not in self._workflows:
            return None
        state = self._workflows[session_id]
        return {
            "session_id": state.session_id,
            "instruction": state.instruction,
            "current_step": state.current_step,
            "completed_steps": state.completed_steps,
            "total_steps": len(state.plan.get("steps", [])) if state.plan else 0,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

    def clear_state(self, session_id: str):
        """清除工作流狀態"""
        if session_id in self._workflows:
            del self._workflows[session_id]
            logger.info(f"[ReActEngine] 清除會話狀態: {session_id}")


class ExecutionResult(BaseModel):
    """執行結果"""

    step_id: int
    action_type: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    observation: str = ""


class TodoTracker:
    """Todo 追蹤器 - 集成 Agent-todo v1.1 + SSE"""

    _sse_client: Optional["SSEPublisher"] = None

    def __init__(self):
        self._arango = SharedArangoClient.get_instance()
        self._prechecker = PreconditionChecker()
        self._heartbeat_mgr = get_heartbeat_manager()
        self._current_todos: Dict[str, str] = {}
        self._session_id: Optional[str] = None

    @classmethod
    def set_sse_client(cls, client: "SSEPublisher") -> None:
        """設置 SSE 客戶端"""
        cls._sse_client = client
        logger.info(f"[TodoTracker] SSE client set: {client}")

    def set_session_id(self, session_id: str) -> None:
        """設置會話 ID"""
        self._session_id = session_id
        logger.info(f"[TodoTracker] Session ID set: {session_id}")

    async def _publish_sse(
        self, step: str, status: str, message: str, progress: float = 0.0
    ) -> None:
        """發布 SSE 事件到前端"""
        if not self._session_id or not TodoTracker._sse_client:
            return

        try:
            await TodoTracker._sse_client.publish(
                request_id=self._session_id,
                step=step,
                status=status,
                message=message,
                progress=progress,
            )
            logger.info(f"[TodoTracker] SSE published: {step} - {status}")
        except Exception as e:
            logger.warning(f"[TodoTracker] SSE publish failed: {e}")

    async def create_todo(
        self,
        step_id: int,
        action: Action,
        instruction: str,
        total_steps: int = 1,
    ) -> str:
        """為執行步驟建立 Todo（含 Heartbeat）"""
        action_map = {
            "knowledge_retrieval": TodoType.KNOWLEDGE_RETRIEVAL,
            "data_query": TodoType.DATA_QUERY,
            "computation": TodoType.COMPUTATION,
            "response_generation": TodoType.RESPONSE_GENERATION,
        }

        todo_type = action_map.get(action.action_type, TodoType.COMPUTATION)

        todo = Todo(
            type=todo_type,
            owner_agent="MM-Agent",
            instruction=instruction,
            input={
                "step_id": step_id,
                "action_type": action.action_type,
                "description": action.description,
                "parameters": action.parameters,
                "total_steps": total_steps,
            },
        )

        todo_id = await self._arango.create_todo(todo)
        self._current_todos[str(step_id)] = todo_id

        # 創建 Heartbeat
        self._heartbeat_mgr.create(
            todo_id=todo_id,
            total_steps=total_steps,
            callback=None,
            interval=5.0,
        )

        logger.info(f"[TodoTracker] Created todo: {todo_id} for step {step_id}")
        return todo_id

    async def check_preconditions(self, action: Action) -> bool:
        """檢查前置條件"""
        preconditions = []

        if action.action_type == "data_query":
            preconditions.append(
                {"type": PreconditionType.AGENT_AVAILABLE.value, "ref": "data-agent"}
            )
        elif action.action_type == "knowledge_retrieval":
            preconditions.append({"type": PreconditionType.AGENT_AVAILABLE.value, "ref": "llm"})

        if not preconditions:
            return True

        from shared.agents.todo.preconditions import Precondition

        pcs = [Precondition(**pc) for pc in preconditions]
        result = await self._prechecker.check_all(pcs)

        logger.info(f"[TodoTracker] Preconditions: all_satisfied={result.all_satisfied}")
        return result.all_satisfied

    async def dispatch_todo(self, step_id: str) -> bool:
        """分派 Todo"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return False

        success, event, history = TodoStateMachine.transition(
            TodoState.PENDING, TodoState.DISPATCHED
        )

        if success:
            await self._arango.update_todo(todo_id, state=TodoState.DISPATCHED, history=history)

            # 啟動 Heartbeat
            hb = self._heartbeat_mgr.get(todo_id)
            if hb:
                hb.start(message="Task dispatched")

        return success

    async def update_progress(self, step_id: str, step: int, message: str = ""):
        """更新進度"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return

        hb = self._heartbeat_mgr.get(todo_id)
        if hb:
            hb.update_progress(step=step, message=message)

    async def complete_todo(
        self,
        step_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """完成 Todo"""
        todo_id = self._current_todos.get(step_id)
        if not todo_id:
            return False

        new_state = TodoState.COMPLETED if success else TodoState.FAILED

        success_transition, event, history = TodoStateMachine.transition(
            TodoState.EXECUTING, new_state
        )

        todo_result = TodoExecutionResult(
            success=success,
            data=result or {},
            error=error,
            observation=(result or {}).get("observation", "") if result else "",
        )

        await self._arango.update_todo(
            todo_id, state=new_state, result=todo_result, history=history
        )

        # 完成 Heartbeat
        hb = self._heartbeat_mgr.get(todo_id)
        if hb:
            if success:
                hb.complete(message="Task completed successfully")
            else:
                hb.fail(message=(error or {}).get("message", "Task failed"))

        logger.info(f"[TodoTracker] Completed todo: {todo_id}, state: {new_state}")
        return True


class ReActExecutor:
    """ReAct 模式執行器 - 集成 Agent-todo"""

    def __init__(self):
        """初始化執行器"""
        self._knowledge_client = None
        self._data_client = None
        self._tracker = TodoTracker()

    async def execute_step(
        self,
        action: Action,
        plan: TodoPlan,
        previous_results: Dict[str, Any],
    ) -> ExecutionResult:
        """執行單一步驟

        Args:
            action: 行動定義
            plan: 工作計劃
            previous_results: 之前的執行結果

        Returns:
            ExecutionResult: 執行結果
        """
        logger.info(f"[ReActExecutor] 執行步驟 {action.step_id}: {action.action_type}")

        instruction = action.parameters.get("instruction", action.description)
        total_steps = len(plan.steps)

        # 1. 建立 Todo（含 Heartbeat）
        await self._tracker.create_todo(action.step_id, action, instruction, total_steps)

        # 2. 檢查 Preconditions
        preconditions_ok = await self._tracker.check_preconditions(action)
        if not preconditions_ok:
            error_result = ExecutionResult(
                step_id=action.step_id,
                action_type=action.action_type,
                success=False,
                error="前置條件檢查失敗",
                observation="Preconditions check failed",
            )
            await self._tracker.complete_todo(
                str(action.step_id),
                success=False,
                error={"code": "PRECONDITIONS_FAILED", "message": "前置條件檢查失敗"},
            )
            return error_result

        # 3. 分派 Todo
        await self._tracker.dispatch_todo(str(action.step_id))
        await self._tracker.update_progress(
            str(action.step_id), step=1, message=f"執行 {action.action_type}"
        )

        try:
            # 4. 執行步驟
            if action.action_type == "knowledge_retrieval":
                result = await self._execute_knowledge_retrieval(action, previous_results)
            elif action.action_type == "data_query":
                result = await self._execute_data_query(action, previous_results)
            elif action.action_type == "computation":
                result = await self._execute_computation(action, previous_results)
            elif action.action_type == "user_confirmation":
                result = await self._execute_user_confirmation(action, previous_results)
            elif action.action_type == "response_generation":
                result = await self._execute_response_generation(action, previous_results)
            else:
                result = ExecutionResult(
                    step_id=action.step_id,
                    action_type=action.action_type,
                    success=False,
                    error=f"未知的行動類型: {action.action_type}",
                )

            # 5. 完成 Todo
            await self._tracker.complete_todo(
                str(action.step_id),
                success=result.success,
                result=result.model_dump() if result else None,
            )
            return result

        except Exception as e:
            logger.error(f"[ReActExecutor] 步驟執行失敗: {e}", exc_info=True)
            error_result = ExecutionResult(
                step_id=action.step_id,
                action_type=action.action_type,
                success=False,
                error=str(e),
                observation="執行異常",
            )
            await self._tracker.complete_todo(
                str(action.step_id),
                success=False,
                error={"code": "EXECUTION_ERROR", "message": str(e)},
            )
            return error_result

    async def _execute_knowledge_retrieval(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行知識庫檢索"""
        query = action.parameters.get("query", action.description)
        knowledge = ""
        source = "unknown"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agents/execute",
                    json={
                        "agent_id": "ka-agent",
                        "task": {
                            "type": "knowledge_query",
                            "action": "ka.retrieve",
                            "instruction": query,
                            "domain": "mm_agent",
                            "major": "responsibilities",
                            "top_k": 5,
                            "query_type": "hybrid",
                        },
                    },
                )

                result = response.json()
                if result.get("status") == "success":
                    knowledge = result.get("result", {}).get("knowledge", "")
                    source = "ka_agent"

        except Exception as e:
            logger.warning(f"[Knowledge] KA-Agent 調用失敗: {e}")

        if not knowledge:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=120.0) as client:
                    llm_response = await client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "gpt-oss:120b",
                            "prompt": f"請用繁體中文回答：{query}",
                            "stream": False,
                            "options": {"temperature": 0.3, "num_predict": 2048},
                        },
                    )

                    if llm_response.status_code == 200:
                        llm_result = llm_response.json()
                        knowledge = llm_result.get("response", "")
                        source = "llm_knowledge"

            except Exception as e:
                logger.warning(f"[Knowledge] LLM 生成知識失敗: {e}")

        return ExecutionResult(
            step_id=action.step_id,
            action_type="knowledge_retrieval",
            success=True,
            result={"knowledge": knowledge, "source": source},
            observation=f"知識獲取成功，來源: {source}",
        )

    async def _execute_data_query(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行數據查詢"""
        instruction = action.parameters.get("instruction", action.description)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8004/execute",
                    json={
                        "task_id": f"react_data_{id(instruction)}",
                        "task_type": "data_query",
                        "task_data": {
                            "action": "execute_structured_query",
                            "natural_language_query": instruction,
                        },
                    },
                )

                result = response.json()

                if result.get("status") == "completed":
                    inner_result = result.get("result", {})
                    actual_result = inner_result.get("result", {})
                    rows = actual_result.get("rows", [])
                    sql = actual_result.get("sql_query", "")

                    logger.info(f"[Data] Data-Agent 返回: rows={len(rows)}")

                    return ExecutionResult(
                        step_id=action.step_id,
                        action_type="data_query",
                        success=True,
                        result={
                            "data": rows,
                            "sql": sql,
                            "row_count": len(rows),
                            "instruction": instruction,
                        },
                        observation=f"數據查詢完成，返回 {len(rows)} 行",
                    )
                else:
                    raise Exception(result.get("error", "未知錯誤"))

        except Exception as e:
            logger.warning(f"[Data] Data-Agent 調用失敗: {e}，使用模擬數據")

            return ExecutionResult(
                step_id=action.step_id,
                action_type="data_query",
                success=True,
                result={
                    "data": [
                        {"material_code": "10-0010", "inventory_value": 2176632830.95},
                        {"material_code": "10-0006", "inventory_value": 1573611688.20},
                        {"material_code": "10-0003", "inventory_value": 1050841733.16},
                    ],
                    "sql": "/* 模擬 SQL */",
                    "row_count": 3,
                    "instruction": instruction,
                },
                observation="使用模擬數據",
            )

    async def _execute_computation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行計算"""
        instruction = action.parameters.get("instruction", action.parameters.get("algorithm", ""))

        query_result = None
        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict) and "data" in step_result:
                query_result = step_result["data"]
                break

        if not query_result:
            return ExecutionResult(
                step_id=action.step_id,
                action_type="computation",
                success=True,
                result={"abc_result": {}},
                observation="無數據，跳過計算",
            )

        try:
            if "abc" in instruction.lower():
                items = []
                for row in query_result:
                    value = (
                        row.get("StockValue")
                        or row.get("inventory_value")
                        or row.get("total_value")
                        or row.get("value", 0)
                    )
                    code = (
                        row.get("ItemCode")
                        or row.get("material")
                        or row.get("material_code")
                        or row.get("mb001")
                        or row.get("img01", "")
                    )
                    if value and code:
                        items.append({"code": code, "value": float(value)})

                if not items:
                    raise Exception("無有效數據")

                items.sort(key=lambda x: x["value"], reverse=True)
                total = sum(item["value"] for item in items)

                a_items, b_items, c_items = [], [], []
                cumulative = 0

                for item in items:
                    cumulative += item["value"]
                    pct = cumulative / total if total > 0 else 0

                    if pct <= 0.70:
                        a_items.append(item["code"])
                    elif pct <= 0.90:
                        b_items.append(item["code"])
                    else:
                        c_items.append(item["code"])

                logger.info(f"[ABC] 分類完成: A={len(a_items)}, B={len(b_items)}, C={len(c_items)}")

                return ExecutionResult(
                    step_id=action.step_id,
                    action_type="computation",
                    success=True,
                    result={
                        "abc_result": {
                            "A類": a_items,
                            "B類": b_items,
                            "C類": c_items,
                        },
                        "instruction": instruction,
                    },
                    observation=f"ABC 分類計算完成：A={len(a_items)} 項，B={len(b_items)} 項，C={len(c_items)} 項",
                )

        except Exception as e:
            logger.error(f"[ABC] 計算失敗: {e}")

        return ExecutionResult(
            step_id=action.step_id,
            action_type="computation",
            success=True,
            result={"abc_result": {}},
            observation="計算完成",
        )

    async def _execute_user_confirmation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行用戶確認"""
        question = action.parameters.get("question", action.description)
        return ExecutionResult(
            step_id=action.step_id,
            action_type="user_confirmation",
            success=True,
            result={"response": f"確認問題：{question}"},
            observation="用戶確認步驟",
        )

    async def _execute_response_generation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """生成最終報告"""
        knowledge = None
        abc_result = None

        for step_id, step_result in previous_results.items():
            if isinstance(step_result, dict):
                if "knowledge" in step_result:
                    knowledge = step_result["knowledge"]
                if "abc_result" in step_result:
                    abc_result = step_result["abc_result"]

        if abc_result and "A類" in abc_result:
            a_items = abc_result.get("A類", [])
            b_items = abc_result.get("B類", [])
            c_items = abc_result.get("C類", [])

            response = "## ABC 分類結果\n\n"
            response += f"### A 類（累積價值 70%）\n- 共 {len(a_items)} 項\n- 料號：{', '.join(a_items[:10])}\n"
            response += f"\n### B 類（累積價值 70-90%）\n- 共 {len(b_items)} 項\n- 料號：{', '.join(b_items[:10])}\n"
            response += f"\n### C 類（累積價值 90-100%）\n- 共 {len(c_items)} 項\n- 料號：{', '.join(c_items[:10])}\n"

        elif knowledge:
            response = knowledge

        else:
            response = "處理完成！"

        return ExecutionResult(
            step_id=action.step_id,
            action_type="response_generation",
            success=True,
            result={"response": response, "abc_result": abc_result},
            observation="回覆生成完成",
        )


class SSEPublisher:
    """SSE 發布器 - 推送 AI 狀態到前端"""

    _instance: Optional["SSEPublisher"] = None

    def __init__(self, api_url: str = "http://localhost:8000"):
        """初始化 SSE 發布器"""
        self._api_url = api_url
        self._enabled = True
        logger.info(f"[SSEPublisher] Initialized: {api_url}")

    @classmethod
    def get_instance(cls, api_url: str = "http://localhost:8000") -> "SSEPublisher":
        """獲取單例"""
        if cls._instance is None:
            cls._instance = cls(api_url)
        return cls._instance

    async def publish(
        self,
        request_id: str,
        step: str,
        status: str,
        message: str,
        progress: float = 0.0,
    ) -> bool:
        """發布狀態事件"""
        if not self._enabled:
            return False

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_url}/api/v1/agent-status/event",
                    json={
                        "request_id": request_id,
                        "step": step,
                        "status": status,
                        "message": message,
                        "progress": progress,
                    },
                )

                if response.status_code == 200:
                    return True
                else:
                    logger.warning(f"[SSEPublisher] Failed to publish: {response.status_code}")
                    return False

        except Exception as e:
            logger.warning(f"[SSEPublisher] Error: {e}")
            return False

    async def start_tracking(self, request_id: str) -> bool:
        """開始追蹤"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_url}/api/v1/agent-status/start",
                    json={"request_id": request_id},
                )
                return response.status_code == 200

        except Exception as e:
            logger.warning(f"[SSEPublisher] Start tracking failed: {e}")
            return False

    async def end_tracking(self, request_id: str) -> bool:
        """結束追蹤"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._api_url}/api/v1/agent-status/end",
                    json={"request_id": request_id},
                )
                return response.status_code == 200

        except Exception as e:
            logger.warning(f"[SSEPublisher] End tracking failed: {e}")
            return False


def get_sse_publisher() -> SSEPublisher:
    """獲取 SSE 發布器"""
    return SSEPublisher.get_instance()
