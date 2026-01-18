# 代碼功能說明: Router LLM 工程級實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Router LLM 工程級實現 - 固定 System Prompt、完整 Schema 驗證、失敗保護機制"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import RouterDecision, RouterInput, SemanticUnderstandingOutput
from llm.clients.factory import LLMClientFactory

logger = logging.getLogger(__name__)

# 意圖分析默認模型（根據測試結果選擇最優模型）
# 測試結果（2026-01-09）：gpt-oss:120b-cloud 表現最優（100% 正確率，2.56s 平均耗時）
#
# 【重要架構說明】
# 任務分析和語義理解（L1-L2層級）始終使用本地模型（Ollama），不受前端選擇的模型影響。
# 前端聊天框選擇的模型只用於：
# 1. 交付任務（任務描述的最終補全）
# 2. 上網和內部信息無關的模型調用（需要外部API的模型）
# 3. 最終輸出生成
#
# 這是多模型架構的核心設計：不同的工作使用不同的模型。
ROUTER_LLM_DEFAULT_MODEL = "gpt-oss:120b-cloud"

# 固定 System Prompt（v4 更新：純語義理解，不產生 intent）
ROUTER_SYSTEM_PROMPT = """You are a semantic understanding engine inside an enterprise GenAI system.

Your ONLY responsibility is to understand the semantic meaning of the user's query and extract structured semantic information.

STRICT RULES:
- You must NOT answer the user's question.
- You must NOT perform reasoning, planning, or step-by-step thinking.
- You must NOT select specific tools, agents, or models.
- You must NOT include explanations, markdown, or extra text.
- You must NOT generate intent types (intent matching happens at L2 layer).
- You must NOT specify which agent to use (agent selection happens at L3 layer).
- You must ONLY output semantic understanding: topics, entities, action_signals, modality, and certainty.

You must ALWAYS return a valid JSON object that strictly follows the SemanticUnderstandingOutput schema.
The output must ONLY contain: topics, entities, action_signals, modality, and certainty.
Do NOT include any intent classification, agent selection, or tool requirements (these are handled at later layers)."""

# Safe Fallback（失敗保護，v4 更新：純語義理解輸出）
SAFE_FALLBACK_SEMANTIC = SemanticUnderstandingOutput(
    topics=[],
    entities=[],
    action_signals=[],
    modality="conversation",
    certainty=0.0,
)

# Legacy Safe Fallback（過渡期兼容，保留用於向後兼容）
SAFE_FALLBACK = RouterDecision(
    topics=[],
    entities=[],
    action_signals=[],
    modality="conversation",
    intent_type="conversation",  # 過渡期兼容
    complexity="low",
    needs_agent=False,
    needs_tools=False,
    determinism_required=False,
    risk_level="low",
    confidence=0.0,
)

# Confidence 門檻
MIN_CONFIDENCE_THRESHOLD = 0.6


class RouterLLM:
    """Router LLM 工程級實現"""

    def __init__(self, preferred_provider: Optional[str] = None):
        """
        初始化 Router LLM

        Args:
            preferred_provider: 首選 LLM 提供商（優先使用低成本模型，如 ollama）

        【重要】任務分析和語義理解始終使用本地模型（Ollama），不受前端選擇的模型影響。
        這是多模型架構的核心設計：不同的工作使用不同的模型。
        """
        self.preferred_provider = preferred_provider or "ollama"
        self._llm_client: Optional[Any] = None

    def _get_llm_client(self):
        """獲取 LLM 客戶端（懶加載）"""
        if self._llm_client is None:
            try:
                from agents.task_analyzer.llm_router import LLMRouter
                from agents.task_analyzer.models import TaskClassificationResult, TaskType
                from services.api.models.llm_model import LLMProvider as APILLMProvider

                # 創建臨時分類結果（用於路由選擇）
                temp_classification = TaskClassificationResult(
                    task_type=TaskType.QUERY,
                    confidence=0.5,
                    reasoning="Router LLM initialization",
                )

                # 使用 LLM Router 選擇低成本模型
                llm_router = LLMRouter()
                routing_result = llm_router.route(temp_classification, "", {})

                # 將 routing_result.provider 轉換為 APILLMProvider
                # routing_result.provider 是 agents.task_analyzer.models.LLMProvider
                # 需要轉換為 services.api.models.llm_model.LLMProvider
                provider_value = routing_result.provider.value

                # 優先使用本地模型（低成本）
                if provider_value == "ollama":
                    provider_enum = APILLMProvider.OLLAMA
                    self._llm_client = LLMClientFactory.create_client(provider_enum, use_cache=True)
                else:
                    # 如果沒有本地模型，嘗試使用首選提供商
                    try:
                        # 將字符串轉換為 APILLMProvider
                        provider_enum = APILLMProvider(self.preferred_provider)
                        self._llm_client = LLMClientFactory.create_client(
                            provider_enum, use_cache=True
                        )
                    except (ValueError, Exception):
                        # 最後回退到 OpenAI (ChatGPT)
                        provider_enum = APILLMProvider.OPENAI
                        self._llm_client = LLMClientFactory.create_client(
                            provider_enum, use_cache=True
                        )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client, will use fallback: {e}")
                # 如果初始化失敗，使用 OpenAI (ChatGPT) 作為最後選擇
                from services.api.models.llm_model import LLMProvider as APILLMProvider

                self._llm_client = LLMClientFactory.create_client(
                    APILLMProvider.OPENAI, use_cache=True
                )

        return self._llm_client

    def _get_available_agents_info(self) -> str:
        """
        獲取可用 Agent 列表信息（用於構建 Prompt）

        Returns:
            Agent 列表字符串
        """
        try:
            from agents.task_analyzer.agent_capability_retriever import AgentCapabilityRetriever

            retriever = AgentCapabilityRetriever()
            agent_descriptions = retriever.get_agent_descriptions()

            if not agent_descriptions:
                return ""

            # 構建 Agent 列表字符串
            agent_list = "\n".join([f"- {desc['description']}" for desc in agent_descriptions])

            # 添加 Agent 選擇示例
            examples = """
Agent Selection Examples:
- "編輯文件 README.md" → md-editor (編輯 Markdown 文件)
- "編輯文件 data.xlsx" → xls-editor (編輯 Excel 文件)
- "將 README.md 轉換為 PDF" → md-to-pdf (Markdown 轉 PDF)
- "將 data.xlsx 轉換為 PDF" → xls-to-pdf (Excel 轉 PDF)
- "將 document.pdf 轉換為 Markdown" → pdf-to-md (PDF 轉 Markdown)
"""

            return f"""
Available Agents:
{agent_list}

{examples}
"""

        except Exception as e:
            logger.warning(f"Failed to get available agents info: {e}")
            return ""

    def _build_user_prompt_v4(self, router_input: RouterInput) -> str:
        """
        構建 User Prompt（v4.0 純語義理解版本）

        Args:
            router_input: Router 輸入

        Returns:
            User Prompt 字符串
        """
        session_context_str = json.dumps(router_input.session_context, ensure_ascii=False, indent=2)
        system_constraints_str = json.dumps(
            router_input.system_constraints, ensure_ascii=False, indent=2
        )

        prompt = f"""Analyze the following input and extract ONLY semantic understanding information.

User Query:
{router_input.user_query}

Session Context:
{session_context_str}

System Constraints:
{system_constraints_str}

Semantic Understanding Guidelines (v4.0 - L1 Layer):

Your task is to extract semantic information from the user's query. You must NOT:
- Generate intent types (intent matching happens at L2 layer)
- Select agents (agent selection happens at L3 layer)
- Determine tool requirements (tool selection happens at L3 layer)
- Classify complexity or risk levels (these are handled at later layers)

You must ONLY extract:

1. topics (List[str]): Extract key topics/themes from the query
   - Examples:
     * "幫我產生Data Agent文件" → topics: ["document", "agent_design"]
     * "編輯README.md文件" → topics: ["document", "file_editing"]
     * "什麼是DevSecOps" → topics: ["devops", "security"]
     * "解釋一下微服務架構" → topics: ["architecture", "microservices"]

2. entities (List[str]): Extract mentioned entities (agents, systems, documents, etc.)
   - Examples:
     * "幫我產生Data Agent文件" → entities: ["Data Agent"]
     * "編輯README.md文件" → entities: ["README.md"]
     * "查詢系統配置" → entities: ["System Config", "Config Service"]

3. action_signals (List[str]): Extract action verbs/signals indicating user intent
   - Examples:
     * "幫我產生Data Agent文件" → action_signals: ["generate", "create", "design"]
     * "編輯README.md文件" → action_signals: ["edit", "modify", "update"]
     * "整理一下這個文件" → action_signals: ["organize", "structure", "refine"]
     * "什麼是DevSecOps" → action_signals: ["explain", "query"]

4. modality (Literal["instruction", "question", "conversation", "command"]): Determine the communication mode
   - instruction: User is giving instructions (e.g., "幫我產生文件", "編輯README.md")
   - question: User is asking a question (e.g., "什麼是DevSecOps", "如何實現")
   - conversation: Casual chat (e.g., "你好", "謝謝")
   - command: Direct command (e.g., "執行這個任務", "運行測試")

5. certainty (float, 0.0-1.0): Your confidence in the semantic understanding
   - 0.9-1.0: Very clear semantic meaning
   - 0.7-0.9: Clear semantic meaning with some ambiguity
   - 0.6-0.7: Ambiguous semantic meaning
   - <0.6: Very uncertain (will use fallback)

Return ONLY valid JSON following the SemanticUnderstandingOutput schema:
{{
  "topics": ["topic1", "topic2"],
  "entities": ["entity1", "entity2"],
  "action_signals": ["action1", "action2"],
  "modality": "instruction|question|conversation|command",
  "certainty": 0.95
}}"""
        return prompt

    def _build_user_prompt(self, router_input: RouterInput) -> str:
        """
        構建 User Prompt（Legacy 版本，過渡期兼容）

        Args:
            router_input: Router 輸入

        Returns:
            User Prompt 字符串
        """
        session_context_str = json.dumps(router_input.session_context, ensure_ascii=False, indent=2)
        system_constraints_str = json.dumps(
            router_input.system_constraints, ensure_ascii=False, indent=2
        )

        # 獲取可用 Agent 信息
        agents_info = self._get_available_agents_info()

        prompt = f"""Analyze the following input and extract semantic understanding according to the schema.
{agents_info}

User Query:
{router_input.user_query}

Session Context:
{session_context_str}

System Constraints:
{system_constraints_str}

Semantic Understanding Guidelines (v4 - Primary Output):

1. topics (List[str]): Extract key topics/themes from the query
   - Examples:
     * "幫我產生Data Agent文件" → topics: ["document", "agent_design"]
     * "編輯README.md文件" → topics: ["document", "file_editing"]
     * "什麼是DevSecOps" → topics: ["devops", "security"]
     * "解釋一下微服務架構" → topics: ["architecture", "microservices"]

2. entities (List[str]): Extract mentioned entities (agents, systems, documents, etc.)
   - Examples:
     * "幫我產生Data Agent文件" → entities: ["Data Agent", "Document Editing Agent"]
     * "編輯README.md文件" → entities: ["README.md", "Document Editing Agent"]
     * "查詢系統配置" → entities: ["System Config", "Config Service"]

3. action_signals (List[str]): Extract action verbs/signals indicating user intent
   - Examples:
     * "幫我產生Data Agent文件" → action_signals: ["generate", "create", "design"]
     * "編輯README.md文件" → action_signals: ["edit", "modify", "update"]
     * "整理一下這個文件" → action_signals: ["organize", "structure", "refine"]
     * "什麼是DevSecOps" → action_signals: ["explain", "query"]

4. modality (Literal["instruction", "question", "conversation", "command"]): Determine the communication mode
   - instruction: User is giving instructions (e.g., "幫我產生文件", "編輯README.md")
   - question: User is asking a question (e.g., "什麼是DevSecOps", "如何實現")
   - conversation: Casual chat (e.g., "你好", "謝謝")
   - command: Direct command (e.g., "執行這個任務", "運行測試")

Legacy Classification Guidelines (Transition Period - Keep for compatibility):

1. intent_type (DEPRECATED - kept for backward compatibility):
   - conversation: casual chat, greetings, explanations, discussions (no action needed)
   - retrieval: lookup, fetch, search, query existing data
   - analysis: reasoning, comparison, evaluation, inference
   - execution: actions, commands, operations, system changes
   - CRITICAL: File editing tasks (creating, editing, generating documents) MUST be classified as execution
     * Explicit examples: "編輯文件", "產生文件", "生成報告", "創建文檔" → intent_type=execution
     * Implicit examples (MUST also be execution):
       - "幫我在文件中加入..." → intent_type=execution (adding content to file)
       - "在文件裡添加..." → intent_type=execution (adding content to file)
       - "把這個改成..." → intent_type=execution (modifying file content)
       - "整理一下這個文件" → intent_type=execution (organizing file)
       - "優化這個代碼文件" → intent_type=execution (optimizing file)
       - "格式化整個文件" → intent_type=execution (formatting file)
       - "在文件中添加註釋" → intent_type=execution (adding comments to file)
       - "幫我整理一下這個文件" → intent_type=execution (organizing file)
     * CRITICAL: Technical operation descriptions (MUST be execution):
       - ANY task containing specific operation instructions MUST be classified as execution
       - Technical operation keywords: "插入", "設置", "填充", "重命名", "合併", "凍結", "複製", "刪除", "更新", "創建", "輸入", "添加", "修改", "編輯"
       - Excel/spreadsheet operation examples (ALL must be execution):
         * "在 data.xlsx 中插入一列" → intent_type=execution (inserting column)
         * "將 A1 單元格設置為粗體" → intent_type=execution (setting format)
         * "填充 A1 到 A10 的序號" → intent_type=execution (filling sequence)
         * "將 Sheet1 重命名為 '數據'" → intent_type=execution (renaming sheet)
         * "合併 A1 到 C1 的單元格" → intent_type=execution (merging cells)
         * "設置 A 列的寬度為 20" → intent_type=execution (setting column width)
         * "凍結第一行" → intent_type=execution (freezing row)
         * "複製 Sheet1 並命名為 '備份'" → intent_type=execution (copying sheet)
         * "刪除第 5 行" → intent_type=execution (deleting row)
         * "更新 B10 單元格的公式" → intent_type=execution (updating formula)
         * "在 data.xlsx 的 Sheet1 中 A1 單元格輸入數據" → intent_type=execution (inputting data into cell)
         * "在 Sheet1 中添加一行數據" → intent_type=execution (adding row data)
       - Rule: If the query contains technical operation keywords (插入, 設置, 填充, 重命名, 合併, 凍結, 複製, 刪除, 更新, 創建, 輸入, 添加, 修改, 編輯) AND refers to a file/spreadsheet, it MUST be execution (NOT query)

2. complexity:
   - low: single-step, obvious, straightforward (e.g., "what time is it")
   - mid: structured reasoning, requires some logic (e.g., "compare X and Y")
   - high: multi-step, orchestration, planning required (e.g., "analyze last month's sales and create a report")

3. needs_agent:
   - true if task requires:
     * Multi-step planning, coordination, or complex workflow
     * File/document operations (creating, editing, generating documents) - requires appropriate file editing agents (md-editor, xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md)
     * Agent-specific capabilities that cannot be handled by simple tools
   - false for simple queries that can be answered directly or with a single tool
   - CRITICAL: File editing tasks (creating, editing, generating documents) ALWAYS require needs_agent=true
     * Explicit examples: "編輯文件", "產生文件", "生成報告", "創建文檔" → needs_agent=true
     * Implicit examples (MUST also have needs_agent=true):
       - "幫我在文件中加入..." → needs_agent=true (adding content to file)
       - "在文件裡添加..." → needs_agent=true (adding content to file)
       - "把這個改成..." → needs_agent=true (modifying file content)
       - "整理一下這個文件" → needs_agent=true (organizing file)
       - "優化這個代碼文件" → needs_agent=true (optimizing file)
       - "格式化整個文件" → needs_agent=true (formatting file)
     * CRITICAL: Technical operation tasks (Excel/spreadsheet operations) ALWAYS require needs_agent=true
       - ANY task containing technical operation keywords (插入, 設置, 填充, 重命名, 合併, 凍結, 複製, 刪除, 更新, 創建) with file references MUST have needs_agent=true
       - Examples: "插入一列", "設置格式", "填充序號", "重命名工作表", "合併單元格", "凍結行", "複製工作表" → ALL need needs_agent=true

4. needs_tools (CRITICAL):
   - true if query requires external data, real-time information, or system operations:
     * Current time/date queries (e.g., "告訴我此刻時間", "what time is it")
     * Stock prices, exchange rates, financial data
     * Weather information
     * Web search
     * Location/maps
     * File operations (creating, editing, generating documents - when user explicitly requests document creation/editing)
     * Database queries
   - false if query only needs knowledge/explanation (LLM can answer from training data)
   - Examples:
     * "告訴我此刻時間" → needs_tools=true (requires time tool)
     * "幫我看台積電股價" → needs_tools=true (requires stock API)
     * "幫我產生Data Agent文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "幫我產生文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "生成文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "幫我將Data Agent的說明做成一份文件" → needs_tools=true (user wants to CREATE a document - requires document editing tool)
     * "生成一份報告" → needs_tools=true (user wants to GENERATE a document - requires document editing tool)
     * "編輯README.md文件" → needs_tools=true, needs_agent=true (user wants to EDIT a document - requires md-editor)
     * "幫我產生文件" → needs_tools=true, needs_agent=true (user wants to CREATE a document - requires appropriate file editing agent)
     * "生成報告" → needs_tools=true, needs_agent=true (user wants to GENERATE a document - requires appropriate file editing agent)
     * "什麼是DevSecOps" → needs_tools=false, needs_agent=false (knowledge question - user only wants explanation, not document creation)

5. determinism_required:
   - true if output must be exact, reproducible, or from authoritative source
   - Examples: time (must be exact), stock price (must be real-time), calculations (must be accurate)

6. risk_level:
   - low: information queries, casual conversation
   - mid: data retrieval, analysis
   - high: financial operations, legal matters, production systems, irreversible actions

7. confidence:
   - 0.9-1.0: very clear intent (e.g., "what time is it" → needs_tools=true, intent_type=retrieval)
   - 0.7-0.9: clear intent with some ambiguity
   - 0.6-0.7: ambiguous, use safest option
   - <0.6: very uncertain, use safe fallback (will be rejected)

Return ONLY valid JSON following the RouterDecision schema."""
        return prompt

    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        從 LLM 響應中提取 JSON

        Args:
            content: LLM 響應內容

        Returns:
            JSON 字典，如果解析失敗返回 None
        """
        if not content:
            return None

        # 移除可能的 markdown 代碼塊
        json_str = content.strip()
        if json_str.startswith("```"):
            # 移除 markdown 代碼塊標記
            json_str = re.sub(r"```(?:json)?\s*\n?", "", json_str)
            json_str = re.sub(r"\n?```\s*$", "", json_str).strip()

        # 嘗試解析 JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            # 嘗試提取 JSON 對象（如果響應包含其他文本）
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", json_str, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            return None

    async def route(
        self, router_input: RouterInput, similar_decisions: Optional[List[Dict[str, Any]]] = None
    ) -> RouterDecision:
        """
        執行路由決策

        Args:
            router_input: Router 輸入
            similar_decisions: 相似決策列表（可選，用於 Context Bias）

        Returns:
            Router 決策結果
        """
        logger.info(f"Routing query: {router_input.user_query[:100]}...")

        try:
            # 如果有相似決策，添加到 context 中作為 bias
            if similar_decisions:
                # 確保 session_context 不是 None
                if router_input.session_context is None:
                    router_input.session_context = {}
                router_input.session_context["similar_decisions"] = similar_decisions[:3]  # 最多 3 個
            # 構建 Prompt
            user_prompt = self._build_user_prompt(router_input)

            # 如果有相似決策，添加到 prompt 中
            if similar_decisions:
                similar_context = "\n\nSimilar previous decisions:\n"
                for i, decision in enumerate(similar_decisions[:3], 1):
                    similar_context += f"{i}. Intent: {decision.get('intent_type', 'unknown')}, "
                    similar_context += f"Complexity: {decision.get('complexity', 'unknown')}, "
                    similar_context += f"Success: {decision.get('success', False)}\n"
                user_prompt = similar_context + "\n" + user_prompt

            # 構建消息列表
            messages = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            # 調用 LLM
            logger.info("Router LLM: Calling LLM for intent classification")
            client = self._get_llm_client()
            # 模型選擇：優先使用環境變量（用於測試），否則使用默認最優模型
            import os

            model_name = os.getenv("ROUTER_LLM_MODEL", ROUTER_LLM_DEFAULT_MODEL)
            logger.debug(f"Router LLM: Using model: {model_name}")
            response = await client.chat(messages=messages, model=model_name)
            logger.debug("Router LLM: LLM response received")

            # 提取響應內容
            content = response.get("content") or response.get("text", "")
            if not content:
                logger.warning("Router LLM: LLM returned empty response, using fallback")
                return SAFE_FALLBACK

            logger.debug(f"Router LLM: LLM response content length: {len(content)}")

            # 提取 JSON
            json_data = self._extract_json_from_response(content)
            if json_data is None:
                logger.warning(
                    "Router LLM: Failed to extract JSON from LLM response, using fallback"
                )
                logger.debug(f"Router LLM: Raw response content (first 500 chars): {content[:500]}")
                return SAFE_FALLBACK

            logger.debug(f"Router LLM: Extracted JSON data: {json_data}")

            # 驗證 Schema
            try:
                decision = RouterDecision(**json_data)
            except Exception as e:
                logger.warning(f"Router LLM: Schema validation failed: {e}, using fallback")
                logger.debug(f"Router LLM: JSON data that failed validation: {json_data}")
                return SAFE_FALLBACK

            # Confidence 門檻檢查
            if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Router LLM: Confidence {decision.confidence} below threshold {MIN_CONFIDENCE_THRESHOLD}, using fallback"
                )
                return SAFE_FALLBACK

            logger.info(
                f"Router LLM: Router decision - intent={decision.intent_type}, "
                f"complexity={decision.complexity}, needs_tools={decision.needs_tools}, "
                f"needs_agent={decision.needs_agent}, confidence={decision.confidence:.2f}"
            )

            return decision

        except Exception as e:
            logger.error(f"Router LLM failed: {e}", exc_info=True)
            # 失敗時使用 Safe Fallback（不重試）
            return SAFE_FALLBACK

    async def route_v4(
        self, router_input: RouterInput, similar_decisions: Optional[List[Dict[str, Any]]] = None
    ) -> SemanticUnderstandingOutput:
        """
        執行語義理解（v4.0 L1 層級純語義理解輸出）

        Args:
            router_input: Router 輸入
            similar_decisions: 相似決策列表（可選，用於 Context Bias，v4 中不使用）

        Returns:
            語義理解結果（SemanticUnderstandingOutput）
        """
        logger.info(f"L1 Semantic Understanding: {router_input.user_query[:100]}...")

        try:
            # 構建 v4 Prompt（純語義理解）
            user_prompt = self._build_user_prompt_v4(router_input)

            # 構建消息列表
            messages = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            # 調用 LLM
            logger.info("Router LLM v4: Calling LLM for semantic understanding")
            client = self._get_llm_client()
            # 模型選擇：優先使用環境變量（用於測試），否則使用默認最優模型
            import os

            model_name = os.getenv("ROUTER_LLM_MODEL", ROUTER_LLM_DEFAULT_MODEL)
            logger.debug(f"Router LLM v4: Using model: {model_name}")
            response = await client.chat(messages=messages, model=model_name)
            logger.debug("Router LLM v4: LLM response received")

            # 提取響應內容
            content = response.get("content") or response.get("text", "")
            if not content:
                logger.warning("Router LLM v4: LLM returned empty response, using fallback")
                return SAFE_FALLBACK_SEMANTIC

            logger.debug(f"Router LLM v4: LLM response content length: {len(content)}")

            # 提取 JSON
            json_data = self._extract_json_from_response(content)
            if json_data is None:
                logger.warning(
                    "Router LLM v4: Failed to extract JSON from LLM response, using fallback"
                )
                logger.debug(
                    f"Router LLM v4: Raw response content (first 500 chars): {content[:500]}"
                )
                return SAFE_FALLBACK_SEMANTIC

            logger.debug(f"Router LLM v4: Extracted JSON data: {json_data}")

            # 驗證 Schema
            try:
                semantic_output = SemanticUnderstandingOutput(**json_data)
            except Exception as e:
                logger.warning(f"Router LLM v4: Schema validation failed: {e}, using fallback")
                logger.debug(f"Router LLM v4: JSON data that failed validation: {json_data}")
                return SAFE_FALLBACK_SEMANTIC

            # Certainty 門檻檢查
            if semantic_output.certainty < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Router LLM v4: Certainty {semantic_output.certainty} below threshold {MIN_CONFIDENCE_THRESHOLD}, using fallback"
                )
                return SAFE_FALLBACK_SEMANTIC

            logger.info(
                f"Router LLM v4: Semantic understanding - topics={semantic_output.topics}, "
                f"entities={semantic_output.entities}, action_signals={semantic_output.action_signals}, "
                f"modality={semantic_output.modality}, certainty={semantic_output.certainty:.2f}"
            )

            return semantic_output

        except Exception as e:
            logger.error(f"Router LLM v4 failed: {e}", exc_info=True)
            # 失敗時使用 Safe Fallback（不重試）
            return SAFE_FALLBACK_SEMANTIC
