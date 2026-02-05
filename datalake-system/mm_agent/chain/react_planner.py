# 代碼功能說明: ReAct 模式工作排程器 - LLM 思考 → 行動 → 觀察 循環
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""ReAct 模式工作排程器 - 支持複雜任務分解與逐步執行"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Action(BaseModel):
    """行動定義"""

    step_id: int = Field(..., description="步驟 ID")
    action_type: str = Field(..., description="行動類型")
    description: str = Field(..., description="步驟描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="行動參數")
    dependencies: List[int] = Field(default_factory=list, description="依賴的步驟")
    result_key: Optional[str] = Field(None, description="結果存儲鍵")


class TodoPlan(BaseModel):
    """工作計劃"""

    task_type: str = Field(..., description="任務類型")
    original_instruction: str = Field(..., description="原始指令")
    steps: List[Action] = Field(default_factory=list, description="行動步驟")
    current_step: int = Field(default=0, description="當前步驟")
    completed_steps: List[int] = Field(default_factory=list, description="已完成的步驟")


class ThoughtRecord(BaseModel):
    """思考記錄"""

    step: int = Field(..., description="思考步驟")
    thought: str = Field(..., description="思考內容")
    action: Optional[str] = Field(None, description="採取的行動")
    observation: Optional[str] = Field(None, description="觀察結果")
    reflection: Optional[str] = Field(None, description="反思與調整")


class ReActPlanner:
    """ReAct 模式工作排程器"""

    def __init__(self, llm_model: str = "gpt-oss:120b", llm_url: str = "http://localhost:11434"):
        """初始化 ReAct 排程器

        Args:
            llm_model: LLM 模型名稱（使用 gpt-oss:120b）
            llm_url: LLM API URL
        """
        self._llm_model = llm_model
        self._llm_url = llm_url
        self._llm_available = self._check_llm_available()
        if self._llm_available:
            logger.info(f"[ReActPlanner] 使用 LLM 模型: {self._llm_model}")
        else:
            logger.warning(f"[ReActPlanner] LLM 不可用，回退到規則引擎")

    def _check_llm_available(self) -> bool:
        """檢查 LLM 是否可用"""
        try:
            import requests

            response = requests.get(f"{self._llm_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                logger.info(f"[ReActPlanner] 可用的 Ollama 模型: {model_names}")
                return True
            return False
        except Exception as e:
            logger.warning(f"[ReActPlanner] LLM 不可用: {e}")
            return False

    async def plan(self, instruction: str, context: Optional[Dict[str, Any]] = None) -> TodoPlan:
        """生成工作計劃（ReAct 思考）

        Args:
            instruction: 用戶指令
            context: 上下文信息

        Returns:
            TodoPlan: 工作計劃
        """
        # 構建 prompt
        user_prompt = f"""用戶指令：{instruction}

上下文：{json.dumps(context or {}, ensure_ascii=False)}

請分析這個任務，生成工作計劃。

規則：
1. 如果是簡單的數據查詢，使用 single_query
2. 如果是操作指引類（如何、怎麼、步驟），使用 guidance
3. 如果需要多步驟執行，使用 compound_workflow
4. 如果指令包含模糊的時間（如「最近」），在步驟中加入用戶確認

請僅返回 JSON，不要有其他文字。"""

        # 嘗試使用 LLM
        if self._llm_available:
            try:
                plan_json = await self._call_llm(user_prompt)
                return self._parse_plan(instruction, plan_json)
            except Exception as e:
                logger.warning(f"[ReActPlanner] LLM 調用失敗，回退到規則引擎: {e}")

        # 回退到規則引擎
        return self._rule_based_plan(instruction)

    async def _call_llm(self, user_prompt: str) -> str:
        """調用 LLM"""
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._llm_url}/api/generate",
                json={
                    "model": self._llm_model,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )

            if response.status_code != 200:
                raise RuntimeError(f"LLM 調用失敗: {response.status_code}")

            result = response.json()
            return result.get("response", "")

    def _parse_plan(self, instruction: str, plan_json: str) -> TodoPlan:
        """解析 LLM 返回的計劃"""
        try:
            # 清理 JSON（去除 markdown 代碼塊）
            plan_json = plan_json.strip()
            if plan_json.startswith("```json"):
                plan_json = plan_json[7:]
            if plan_json.startswith("```"):
                plan_json = plan_json[3:]
            if plan_json.endswith("```"):
                plan_json = plan_json[:-3]
            plan_json = plan_json.strip()

            data = json.loads(plan_json)

            steps = []
            for i, step_data in enumerate(data.get("steps", [])):
                action = Action(
                    step_id=i + 1,  # 確保從 1 開始的順序編號
                    action_type=step_data.get("action_type", "unknown"),
                    description=step_data.get("description", ""),
                    parameters=step_data.get("parameters", {}),
                    dependencies=step_data.get("dependencies", []),
                    result_key=step_data.get("result_key"),
                )
                steps.append(action)

            return TodoPlan(
                task_type=data.get("task_type", "single_query"),
                original_instruction=instruction,
                steps=steps,
                current_step=1,
                completed_steps=[],
            )
        except json.JSONDecodeError as e:
            logger.warning(f"[ReActPlanner] 解析計劃失敗: {e}，回退到規則引擎")
            return self._rule_based_plan(instruction)

    def _rule_based_plan(self, instruction: str) -> TodoPlan:
        """基於規則的計劃生成（回退方案）"""
        instruction_lower = instruction.lower()

        # 檢測是否為操作指引類
        guidance_keywords = ["如何", "怎麼", "步驟", "設置", "設定", "建立", "操作", "方法"]
        is_guidance = any(kw in instruction for kw in guidance_keywords)

        # 檢測是否為複合工作
        compound_keywords = ["然後", "接著", "完成後", "最後", "並且", "以及"]
        is_compound = any(kw in instruction_lower for kw in compound_keywords)

        # 檢測是否為單一查詢
        query_keywords = ["多少", "有多少", "庫存", "採購", "銷售", "進貨"]
        is_query = any(kw in instruction for kw in query_keywords)

        if is_guidance or is_compound:
            # 操作指引或複合工作
            steps = [
                Action(
                    step_id=1,
                    action_type="knowledge_retrieval",
                    description="檢索相關知識",
                    parameters={"query": instruction},
                    dependencies=[],
                    result_key="knowledge",
                ),
                Action(
                    step_id=2,
                    action_type="response_generation",
                    description="生成操作指引",
                    parameters={},
                    dependencies=[1],
                    result_key=None,
                ),
            ]

            # 如果需要數據，加入數據查詢步驟
            if "abc" in instruction_lower:
                steps.insert(
                    1,
                    Action(
                        step_id=1,
                        action_type="user_confirmation",
                        description="確認是否有數據",
                        parameters={"question": "您有物料使用數據嗎？"},
                        dependencies=[],
                        result_key="data_confirmed",
                    ),
                )
                # 重新編號
                for i, step in enumerate(steps):
                    step.step_id = i + 1

            return TodoPlan(
                task_type="guidance",
                original_instruction=instruction,
                steps=steps,
                current_step=1,
                completed_steps=[],
            )
        elif is_query:
            # 單一查詢
            steps = [
                Action(
                    step_id=1,
                    action_type="data_query",
                    description="執行數據查詢",
                    parameters={"instruction": instruction},
                    dependencies=[],
                    result_key="query_result",
                ),
                Action(
                    step_id=2,
                    action_type="response_generation",
                    description="生成回覆",
                    parameters={},
                    dependencies=[1],
                    result_key=None,
                ),
            ]

            return TodoPlan(
                task_type="single_query",
                original_instruction=instruction,
                steps=steps,
                current_step=1,
                completed_steps=[],
            )
        else:
            # 默認：簡單處理
            steps = [
                Action(
                    step_id=1,
                    action_type="response_generation",
                    description="生成回覆",
                    parameters={"message": f"已收到指令：{instruction}"},
                    dependencies=[],
                    result_key=None,
                ),
            ]

            return TodoPlan(
                task_type="single_query",
                original_instruction=instruction,
                steps=steps,
                current_step=1,
                completed_steps=[],
            )

    def get_current_step(self, plan: TodoPlan) -> Optional[Action]:
        """獲取當前待執行的步驟"""
        if plan.current_step <= len(plan.steps):
            return plan.steps[plan.current_step - 1]
        return None

    def format_plan(self, plan: TodoPlan) -> str:
        """格式化計劃為可讀字符串"""
        if plan.task_type == "single_query":
            lines = ["這是一個簡單查詢，我來為您執行。"]
        elif plan.task_type == "guidance":
            lines = ["這是一個操作指引，讓我為您分解步驟：", ""]
        else:
            lines = [f"任務類型：{plan.task_type}", ""]

        for step in plan.steps:
            lines.append(f"Step {step.step_id}: {step.description}")
            lines.append(f"  └─ 類型：{step.action_type}")

        lines.append("")
        lines.append("【請問您想從哪一步開始？】")

        return "\n".join(lines)

    def format_step(self, step: Action, previous_results: Dict[str, Any] = None) -> str:
        """格式化單一步驟為可讀字符串"""
        previous_results = previous_results or {}
        lines = [f"Step {step.step_id}: {step.description}", ""]

        if step.action_type == "knowledge_retrieval":
            lines.append("正在從知識庫檢索相關資訊...")
        elif step.action_type == "data_query":
            lines.append("正在查詢數據...")
        elif step.action_type == "computation":
            lines.append("正在執行計算...")
        elif step.action_type == "user_confirmation":
            if step.parameters.get("question"):
                lines.append(step.parameters["question"])
        elif step.action_type == "response_generation":
            lines.append("處理完成！")

        return "\n".join(lines)
