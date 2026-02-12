# 代碼功能說明: ReAct 模式工作排程器 - LLM 思考 → 行動 → 觀察 循環
# 創建日期: 2026-02-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-07

"""ReAct 模式工作排程器 - 支持複雜任務分解與逐步執行"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("mm_agent")

# 計劃生成專用 System Prompt（勿與 MM-Agent 對話用 system prompt 混用）
# 用途：讓 LLM 明確角色為「工作流規劃器」，只輸出 JSON 陣列，以產出可解析的 Todo 步驟
PLANNER_SYSTEM_PROMPT = """你是工作流規劃器（Workflow Planner）。你的唯一任務是根據用戶指令，輸出一個 JSON 陣列。

【輸出格式】
- 只輸出一個 JSON 陣列，不要輸出 markdown 代碼塊（不要 ```json 或 ```）
- 不要輸出任何說明、前言或結尾文字
- 陣列中每個元素必須包含：step_id（數字）、action_type（字串）、description（字串）、instruction（字串）

【action_type 僅限以下之一】
knowledge_retrieval, data_query, data_cleaning, computation, visualization, response_generation

【範例開頭】
[{"step_id": 1, "action_type": "knowledge_retrieval", "description": "...", "instruction": "..."}, ...]"""


class Action(BaseModel):
    """行動定義"""

    step_id: int = Field(..., description="步驟 ID")
    action_type: str = Field(..., description="行動類型")
    description: str = Field(..., description="步驟描述")
    instruction: str = Field(default="", description="詳細執行指令")
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
    thought_process: str = Field(default="", description="LLM 思考過程")


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
            logger.warning("[ReActPlanner] LLM 不可用，回退到規則引擎")

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
            logger.warning("[ReActPlanner] LLM 不可用，回退到規則引擎")
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
            user_prompt = f"""你是一位專業的庫存管理 AI Agent。用戶指令是：{instruction}

你的工作是：
1. 理解用戶的具體需求
2. 動態生成一個靈活的工作流程來完成這個任務
3. 每個步驟都要有明確的 instruction，告訴下一個 Agent 具體要做什麼

【重要原則】
- 不要預設固定的步驟數量！根據任務複雜度決定步驟
- 例如簡單查詢可能只需 2-3 步，複雜分析可能需要 5-7 步
- 每個步驟的 instruction 必須非常具體，告訴接收者：
  * 要做什麼
  * 需要什麼數據
  * 輸出什麼格式
  * 有什麼特殊要求

【action_type 類型】
- knowledge_retrieval: 搜尋相關知識/理論
- data_query: 向 Data-Agent 查詢數據
- data_cleaning: 數據清洗/處理
- computation: 數學計算/分析
- visualization: 生成圖表
- response_generation: 生成最終報告

【工作流格式要求】
[
  {{
    "step_id": 1,
    "action_type": "action_type 名稱",
    "description": "簡短描述這步要做什麼（10字以內）",
    "instruction": "詳細指令，必須具體說明這步的目標、輸入、輸出、要求（50-200字）"
  }},
  ...
]

【範例靈活工作流】
用戶：「請幫我做庫存ABC分類表」

AI 動態生成：
[
  {{
    "step_id": 1,
    "action_type": "knowledge_retrieval",
    "description": "理解ABC分類理論",
    "instruction": "請搜尋並彙整 ABC 分類（Pareto 分析）的完整方法論，包括：A 類＝累積價值前 70% 的物料、B 類＝累積價值 70%~90% 的物料、C 類＝累積價值 90%~100% 的物料。說明分類目的（庫存重點管理）、常見分類比例、以及這個方法在供應鏈管理中的實際應用場景。"
  }},
  {{
    "step_id": 2,
    "action_type": "data_query",
    "description": "查詢庫存價值資料",
    "instruction": "Data-Agent你好，我需要進行 ABC 分類分析，請從庫存系統查詢以下資料：\n1. 所有有料號的庫存數量（imgl04 欄位）\n2. 最近交易單價（pmn09 欄位）\n3. 料號（imgl01）\n4. 倉庫代碼（imgl02）\n\n請計算每個料號的庫存價值 = 數量 × 單價，然後按料號彙總，按總價值降序排列，取前 100 筆。產出欄位：料號、總數量、單價、總價值。"
  }},
  {{
    "step_id": 3,
    "action_type": "computation",
    "description": "執行ABC分類計算",
    "instruction": "根據上一步取得的庫存價值資料，請執行以下計算：\n1. 計算每個料號的累積價值和累積百分比\n2. 套用 ABC 分類規則：\n   - A 類：累積百分比 ≤ 70%\n   - B 類：累積百分比 70% ~ 90%\n   - C 類：累積百分比 > 90%\n3. 產出：A 類料號清單、B 類料號清單、C 類料號清單，以及各類的數量統計和價值統計。"
  }},
  {{
    "step_id": 4,
    "action_type": "response_generation",
    "description": "生成ABC分類報告",
    "instruction": "根據 ABC 分類結果，請生成一份管理報告，包含：\n1. 三類物料的清單（料號、價值、佔比）\n2. 各類統計摘要：A/B/C 類的數量、總價值、各自佔比\n3. 管理建議：\n   - A 類：重點控管、安全庫存策略\n   - B 類：適度關注、週期性盤點\n   - C 類：簡化管理、減少庫存"
  }}
]

【你的任務】
用戶指令：{instruction}

請根據這個具體需求，動態生成合適的工作流程。記住：
- 步驟數量由任務決定，不要硬編碼
- 每個 instruction 都要具體到執行者可以直接執行
- 考慮數據流向：誰提供輸入、誰處理、誰產出

只返回 JSON 陣列，不要返回 markdown 代碼塊。"""
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
            plan = self._parse_plan(instruction, plan_json)

            # 添加思考過程到計劃中
            thought_process = f"""我理解用戶想要：{instruction}

經過分析，這是一個「{plan.task_type}」類型的任務。

我的思考過程：
1. 首先理解用戶的需求
2. 判斷任務類型：這是一個需要多步驟處理的複合任務
3. 制定執行計劃：
   - Step 1: {plan.steps[0].description if len(plan.steps) > 0 else "起始步驟"}
   - Step 2: {plan.steps[1].description if len(plan.steps) > 1 else "後續步驟"}
   - Step 3: {plan.steps[2].description if len(plan.steps) > 2 else "數據處理"}
   - Step 4: {plan.steps[3].description if len(plan.steps) > 3 else "結果生成"}
4. 準備按順序執行每個步驟

讓我按照這個計劃來執行。"""

            plan.thought_process = thought_process
            return plan
        except Exception as e:
            logger.warning(f"[ReActPlanner] LLM 調用失敗: {e}，回退到規則引擎")
            return self._rule_based_plan(instruction)

    async def _call_llm(self, user_prompt: str) -> str:
        """調用 LLM（傳入計劃專用 system prompt，確保產出可解析的 JSON 工作流）"""
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            payload: Dict[str, Any] = {
                "model": self._llm_model,
                "prompt": user_prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            }
            # Ollama /api/generate 支援 system：約束模型只輸出 JSON，避免與對話用 prompt 混淆
            payload["system"] = PLANNER_SYSTEM_PROMPT
            response = await client.post(
                f"{self._llm_url}/api/generate",
                json=payload,
            )

            if response.status_code != 200:
                raise RuntimeError(f"LLM 調用失敗: {response.status_code}")

            result = response.json()
            return result.get("response", "")

    def _extract_json_array(self, raw: str) -> Optional[str]:
        """從回傳中抽取 JSON 陣列（容錯：模型可能包在 markdown 或前後有說明文字）"""
        raw = raw.strip()
        # 先去掉 markdown 代碼塊
        if "```json" in raw:
            start = raw.find("```json") + 7
            end = raw.find("```", start)
            if end != -1:
                raw = raw[start:end]
        elif "```" in raw:
            start = raw.find("```") + 3
            end = raw.find("```", start)
            if end != -1:
                raw = raw[start:end]
        # 若仍無陣列，嘗試找第一個 [ ... ] 區間
        if "[" not in raw and "{" in raw:
            return None
        start_idx = raw.find("[")
        if start_idx == -1:
            return None
        depth = 0
        for i in range(start_idx, len(raw)):
            if raw[i] == "[":
                depth += 1
            elif raw[i] == "]":
                depth -= 1
                if depth == 0:
                    return raw[start_idx : i + 1]
        return raw[start_idx:].strip() or None

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

            # 若仍無法直接解析，嘗試抽取陣列
            if not plan_json.startswith("[") and not plan_json.startswith("{"):
                extracted = self._extract_json_array(plan_json)
                if extracted:
                    plan_json = extracted

            # 嘗試解析為陣列
            try:
                steps_data = json.loads(plan_json)
                if isinstance(steps_data, list):
                    # 新格式：直接是步驟陣列（包含 step_id）
                    steps = []
                    for step_data in steps_data:
                        action = Action(
                            step_id=step_data.get("step_id", len(steps) + 1),
                            action_type=step_data.get("action_type", "unknown"),
                            description=step_data.get("description", ""),
                            instruction=step_data.get("instruction", ""),
                            parameters=step_data.get("parameters", {}) or {},
                            dependencies=step_data.get("dependencies", []) or [],
                            result_key=step_data.get("result_key"),
                        )
                        logger.info(
                            f"[ReActPlanner] Parsed step {action.step_id}: description={action.description[:30]}, instruction={action.instruction[:50] if action.instruction else 'EMPTY'}..."
                        )
                        steps.append(action)

                    task_type = "data_analysis"
                    if len(steps) > 0:
                        first_action = steps[0].action_type
                        if first_action == "knowledge_retrieval":
                            task_type = "guidance"

                    return TodoPlan(
                        task_type=task_type,
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
                params = step_data.get("parameters")
                action = Action(
                    step_id=i + 1,
                    action_type=step_data.get("action_type", "unknown"),
                    description=step_data.get("description", ""),
                    instruction=step_data.get("instruction", ""),
                    parameters={}
                    if params is None
                    else (params if isinstance(params, dict) else {}),
                    dependencies=step_data.get("dependencies", []) or [],
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
