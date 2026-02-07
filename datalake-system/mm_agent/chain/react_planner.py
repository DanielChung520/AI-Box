# 代碼功能說明: ReAct 模式工作排程器 - LLM 思考 → 行動 → 觀察 循環
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-04

"""ReAct 模式工作排程器 - 支持複雜任務分解與逐步執行"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("mm_agent")


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

            response = requests.get(f"{self._llm_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                logger.info(f"[ReActPlanner] 可用的 Ollama 模型: {model_names}")
                # 檢查配置的模型是否存在
                logger.info(
                    f"[ReActPlanner] 檢查模型: {self._llm_model} (in list: {self._llm_model in model_names})"
                )
                if self._llm_model in model_names:
                    logger.info(f"[ReActPlanner] LLM 模型 {self._llm_model} 可用")
                    return True
                else:
                    logger.warning(
                        f"[ReActPlanner] 模型 {self._llm_model} 不在可用列表中，使用 mistral-nemo:12b"
                    )
                    self._llm_model = "mistral-nemo:12b"
                    return True
            logger.warning(f"[ReActPlanner] LLM API 返回非 200 狀態: {response.status_code}")
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
        # 每次都檢查 LLM 可用性
        if not self._check_llm_available():
            logger.warning(f"[ReActPlanner] LLM 不可用，回退到規則引擎")
            return self._rule_based_plan(instruction)

        instruction_lower = instruction.lower()

        is_data_task = any(
            kw in instruction_lower
            for kw in [
                "執行",
                "分析",
                "分類",
                "計算",
                "統計",
                "查詢",
                "abc",
                "庫存",
                "使用量",
                "金額",
            ]
        )

        if is_data_task:
            user_prompt = f"""用戶指令：{instruction}

這是一個數據分析任務，請生成工作計劃。

【原則】
- MM-Agent 不涉及 schema，由 Data-Agent 處理 schema
- 指令必須包含：需要什麼數據、做什麼計算、用途是什麼
- 讓 Data-Agent 推斷如何查詢

【工作流格式】
[
  {{
    "action_type": "knowledge_retrieval",
    "description": "檢索ABC分類知識",
    "instruction": "請提供ABC分類的方法論，包括A類(70%)/B類(20%)/C類(10%)的定義"
  }},
  {{
    "action_type": "data_query",
    "description": "查詢庫存價值",
    "instruction": "查詢每個料號的庫存數量和單價，我需要計算庫存價值=數量×單價，按價值降序排列，用於ABC分類"
  }},
  {{
    "action_type": "computation",
    "description": "執行ABC分類",
    "instruction": "根據以下庫存價值列表，執行ABC分類：A類=累積價值前70%，B類=累積價值70-90%，C類=累積價值90-100%"
  }},
  {{
    "action_type": "response_generation",
    "description": "生成ABC分類報告",
    "instruction": "根據ABC分類結果，生成包含A/B/C三類清單、統計摘要和管理建議的報告"
  }}
]

只返回 JSON 陣列，確保指令具體且包含用途。"""
        else:
            user_prompt = f"""用戶指令：{instruction}

這是一個知識問答任務，請生成工作計劃。

只返回 JSON：
{{"task_type": "guidance", "steps": [
  {{"action_type": "knowledge_retrieval", "description": "檢索相關知識", "parameters": {{"query": "知識查詢"}}}},
  {{"action_type": "response_generation", "description": "生成回覆", "parameters": {{}}}}
]}}"""

        try:
            logger.info(f"[ReActPlanner] 調用 LLM: model={self._llm_model}")
            plan_json = await self._call_llm(user_prompt)
            logger.info(f"[ReActPlanner] LLM 返回: {plan_json[:200]}...")
            return self._parse_plan(instruction, plan_json)
        except Exception as e:
            logger.warning(f"[ReActPlanner] LLM 調用失敗: {e}，回退到規則引擎")
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

            # 嘗試解析為陣列
            try:
                steps_data = json.loads(plan_json)
                if isinstance(steps_data, list):
                    # 新格式：直接是步驟陣列
                    steps = []
                    for i, step_data in enumerate(steps_data):
                        action = Action(
                            step_id=i + 1,
                            action_type=step_data.get("action_type", "unknown"),
                            description=step_data.get("description", ""),
                            parameters={"instruction": step_data.get("instruction", "")},
                            dependencies=[],
                            result_key=None,
                        )
                        steps.append(action)
                    return TodoPlan(
                        task_type="data_analysis",
                        original_instruction=instruction,
                        steps=steps,
                        current_step=1,
                        completed_steps=[],
                    )
                else:
                    # 舊格式：包含 steps 欄位
                    steps_data = steps_data.get("steps", [])
            except json.JSONDecodeError:
                pass

            # 舊格式解析
            data = json.loads(plan_json)
            steps_data = data.get("steps", [])

            steps = []
            for i, step_data in enumerate(steps_data):
                action = Action(
                    step_id=i + 1,
                    action_type=step_data.get("action_type", "unknown"),
                    description=step_data.get("description", ""),
                    parameters={"instruction": step_data.get("parameters", {}).get("query", "")},
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

        # 檢測是否為數據分析任務（需要編排）
        data_analysis_keywords = ["執行", "分析", "分類", "計算", "統計", "abc分類"]
        is_data_analysis = any(kw in instruction_lower for kw in data_analysis_keywords)

        # 檢測是否為操作指引類
        guidance_keywords = ["如何", "怎麼", "步驟", "設置", "設定", "建立", "操作", "方法"]
        is_guidance = any(kw in instruction for kw in guidance_keywords)

        # 檢測是否為複合工作
        compound_keywords = ["然後", "接著", "完成後", "最後", "並且", "以及"]
        is_compound = any(kw in instruction_lower for kw in compound_keywords)

        # 檢測是否為單一查詢
        query_keywords = ["多少", "有多少", "庫存", "採購", "銷售", "進貨"]
        is_query = any(kw in instruction for kw in query_keywords)

        if is_data_analysis:
            # === 數據分析任務：完整的 4 步編排 ===
            steps = [
                Action(
                    step_id=1,
                    action_type="knowledge_retrieval",
                    description="檢索相關領域知識",
                    parameters={"query": instruction},
                    dependencies=[],
                    result_key="knowledge",
                ),
                Action(
                    step_id=2,
                    action_type="data_query",
                    description="查詢所需數據",
                    parameters={"instruction": instruction},
                    dependencies=[1],
                    result_key="query_result",
                ),
                Action(
                    step_id=3,
                    action_type="computation",
                    description="執行計算分析",
                    parameters={"instruction": instruction},
                    dependencies=[2],
                    result_key="analysis_result",
                ),
                Action(
                    step_id=4,
                    action_type="response_generation",
                    description="生成最終報告",
                    parameters={},
                    dependencies=[3],
                    result_key="final_response",
                ),
            ]

            logger.info(f"[ReActPlanner] 生成數據分析工作流: {len(steps)} 步驟")
            return TodoPlan(
                task_type="data_analysis",
                original_instruction=instruction,
                steps=steps,
                current_step=1,
                completed_steps=[],
            )

        elif is_guidance or is_compound:
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
            lines = ["這是一個簡單查詢，我來為您處理。"]
        elif plan.task_type == "guidance":
            lines = ["這是一個操作指引，讓我為您分解步驟：", ""]
        else:
            lines = [f"任務類型：{plan.task_type}", ""]

        for step in plan.steps:
            lines.append(f"Step {step.step_id}: {step.description}")
            lines.append(f"  └─ 類型：{step.action_type}")

        lines.append("")
        lines.append("【自動執行中...】")

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
