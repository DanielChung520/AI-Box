# 代碼功能說明: ReAct 模式執行器 - 執行 TODO 步驟
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""ReAct 模式執行器 - 執行 TODO 步驟"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel

from .react_planner import Action, TodoPlan, ReActPlanner

logger = logging.getLogger(__name__)


class ExecutionResult(BaseModel):
    """執行結果"""

    step_id: int
    action_type: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    observation: str = ""


class ReActExecutor:
    """ReAct 模式執行器"""

    def __init__(self):
        """初始化執行器"""
        self._knowledge_client = None
        self._data_client = None

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

        try:
            if action.action_type == "knowledge_retrieval":
                return await self._execute_knowledge_retrieval(action, previous_results)
            elif action.action_type == "data_query":
                return await self._execute_data_query(action, previous_results)
            elif action.action_type == "computation":
                return await self._execute_computation(action, previous_results)
            elif action.action_type == "user_confirmation":
                return await self._execute_user_confirmation(action, previous_results)
            elif action.action_type == "response_generation":
                return await self._execute_response_generation(action, previous_results)
            else:
                return ExecutionResult(
                    step_id=action.step_id,
                    action_type=action.action_type,
                    success=False,
                    error=f"未知的行動類型: {action.action_type}",
                )
        except Exception as e:
            logger.error(f"[ReActExecutor] 步驟執行失敗: {e}", exc_info=True)
            return ExecutionResult(
                step_id=action.step_id,
                action_type=action.action_type,
                success=False,
                error=str(e),
            )

    async def _execute_knowledge_retrieval(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行知識庫檢索"""
        query = action.parameters.get("query", action.description)

        # 這裡應該調用 KA-Agent 或本地知識庫
        # 目前返回模擬結果
        knowledge_content = f"""【ABC 分類法說明】

ABC 分類法是庫存管理中常用的分類方法，基於帕累托原則（80/20 規則）：

## 分類標準

| 類別 | 佔品項比例 | 佔價值比例 | 管理策略 |
|------|-----------|-----------|----------|
| A 類 | 5-10% | 70-80% | 嚴格控制、高頻盤點 |
| B 類 | 15-20% | 15-25% | 例行管理 |
| C 類 | 70-80% | 5-10% | 簡化管理、批量採購 |

## 設置步驟

1. 收集數據：料號、單價、年度使用量
2. 計算年度使用金額
3. 按金額排序，計算累積百分比
4. 劃分 A/B/C 類
5. 制定各類管理策略"""

        return ExecutionResult(
            step_id=action.step_id,
            action_type="knowledge_retrieval",
            success=True,
            result={"knowledge": knowledge_content},
            observation=f"知識庫檢索成功，內容長度: {len(knowledge_content)}",
        )

    async def _execute_data_query(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行數據查詢"""
        # 這裡應該調用 Data-Agent
        # 目前返回模擬結果
        return ExecutionResult(
            step_id=action.step_id,
            action_type="data_query",
            success=True,
            result={"data": "數據查詢結果"},
            observation="數據查詢完成",
        )

    async def _execute_computation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行計算"""
        algorithm = action.parameters.get("algorithm", "")

        if algorithm == "abc_classification":
            # ABC 分類計算
            return ExecutionResult(
                step_id=action.step_id,
                action_type="computation",
                success=True,
                result={
                    "abc_result": {
                        "A類": ["RM01-009", "RM02-010"],
                        "B類": ["RM03-011", "RM04-012"],
                        "C類": ["RM05-013", "RM06-014", "RM07-015"],
                    }
                },
                observation="ABC 分類計算完成",
            )

        return ExecutionResult(
            step_id=action.step_id,
            action_type="computation",
            success=True,
            result={},
            observation="計算完成",
        )

    async def _execute_user_confirmation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """執行用戶確認"""
        question = action.parameters.get("question", "請確認")

        return ExecutionResult(
            step_id=action.step_id,
            action_type="user_confirmation",
            success=True,
            result={"question": question, "waiting_for_user": True},
            observation="等待用戶回應",
        )

    async def _execute_response_generation(
        self, action: Action, previous_results: Dict[str, Any]
    ) -> ExecutionResult:
        """生成回覆"""
        # 根據 previous_results 生成最終回覆
        response = "處理完成！"

        # 如果有知識內容，加入回覆
        if "knowledge" in previous_results:
            response = previous_results["knowledge"]

        # 如果有計算結果，加入回覆
        if "abc_result" in previous_results:
            abc = previous_results["abc_result"]
            response += f"\n\n【ABC 分類結果】\nA 類: {', '.join(abc.get('A類', []))}\nB 類: {', '.join(abc.get('B類', []))}\nC 類: {', '.join(abc.get('C類', []))}"

        return ExecutionResult(
            step_id=action.step_id,
            action_type="response_generation",
            success=True,
            result={"response": response},
            observation="回覆生成完成",
        )


class ReActEngine:
    """ReAct 引擎 - 整合排程與執行"""

    def __init__(self, planner: Optional[ReActPlanner] = None):
        """初始化引擎

        Args:
            planner: ReAct 排程器（可選，預設使用 gpt-oss:120b）
        """
        self._planner = planner if planner is not None else ReActPlanner(llm_model="gpt-oss:120b")
        self._executor = ReActExecutor()

        # 會話狀態存儲
        self._session_states: Dict[str, Dict[str, Any]] = {}

    def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """獲取會話狀態"""
        if session_id not in self._session_states:
            self._session_states[session_id] = {
                "plan": None,
                "current_step": 0,
                "completed_steps": [],
                "step_results": {},
                "waiting_for_user": False,
            }
        return self._session_states[session_id]

    async def start_workflow(
        self, instruction: str, session_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """啟動工作流程

        Args:
            instruction: 用戶指令
            session_id: 會話 ID
            context: 上下文

        Returns:
            初始回覆和計劃
        """
        state = self._get_session_state(session_id)

        # 生成計劃（使用 gpt-oss:120b）
        plan = await self._planner.plan(instruction, context)

        # 保存計劃
        state["plan"] = plan.model_dump()
        state["current_step"] = 0
        state["completed_steps"] = []
        state["step_results"] = {}
        state["waiting_for_user"] = True

        # 格式化計劃
        plan_text = self._planner.format_plan(plan)

        return {
            "success": True,
            "response": plan_text,
            "plan": plan.model_dump(),
            "task_type": plan.task_type,
            "waiting_for_user": True,
            "debug_info": {
                "step": "workflow_started",
                "total_steps": len(plan.steps),
            },
        }

    async def execute_next_step(
        self, session_id: str, user_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """執行下一步

        Args:
            session_id: 會話 ID
            user_response: 用戶回應（用於 user_confirmation 步驟）

        Returns:
            執行結果
        """
        state = self._get_session_state(session_id)

        if state["plan"] is None:
            return {"success": False, "error": "沒有進行中的工作流程"}

        plan = TodoPlan(**state["plan"])

        # 找到下一個可執行的步驟
        next_step = None
        for step in plan.steps:
            if step.step_id not in state["completed_steps"]:
                # 檢查依賴是否滿足
                dependencies_met = all(dep in state["completed_steps"] for dep in step.dependencies)
                if dependencies_met:
                    next_step = step
                    break

        if next_step is None:
            return {"success": False, "error": "所有步驟已完成"}

        # 執行步驟
        result = await self._executor.execute_step(next_step, plan, state["step_results"])

        # 更新狀態
        state["current_step"] = next_step.step_id
        state["completed_steps"].append(next_step.step_id)
        state["step_results"][next_step.step_id] = result.result or {}

        # 生成回覆
        response = ""
        if result.action_type == "user_confirmation":
            result_data = result.result or {}
            response = result_data.get("question", "請確認")
            state["waiting_for_user"] = True
        elif result.action_type == "response_generation":
            result_data = result.result or {}
            response = result_data.get("response", "處理完成")
            state["waiting_for_user"] = False
        else:
            response = f"Step {next_step.step_id} 完成：{result.observation}"
            state["waiting_for_user"] = True

        return {
            "success": result.success,
            "response": response,
            "step_id": next_step.step_id,
            "action_type": next_step.action_type,
            "completed_steps": state["completed_steps"],
            "total_steps": len(plan.steps),
            "waiting_for_user": state["waiting_for_user"],
            "debug_info": {
                "step": "step_executed",
                "observation": result.observation,
                "error": result.error,
            },
        }


# 全局 ReActEngine 單例
_react_engine_instance: Optional[ReActEngine] = None


def get_react_engine() -> ReActEngine:
    """獲取 ReActEngine 單例"""
    global _react_engine_instance
    if _react_engine_instance is None:
        _react_engine_instance = ReActEngine(ReActPlanner(llm_model="gpt-oss:120b"))
    return _react_engine_instance
