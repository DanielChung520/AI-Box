# 代碼功能說明: Router LLM 工程級實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""Router LLM 工程級實現 - 固定 System Prompt、完整 Schema 驗證、失敗保護機制"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import RouterDecision, RouterInput
from llm.clients.factory import LLMClientFactory

logger = logging.getLogger(__name__)

# 意圖分析默認模型（根據測試結果選擇最優模型）
# 測試結果（2026-01-09）：gpt-oss:120b-cloud 表現最優（100% 正確率，2.56s 平均耗時）
ROUTER_LLM_DEFAULT_MODEL = "gpt-oss:120b-cloud"

# 固定 System Prompt（不可動）
ROUTER_SYSTEM_PROMPT = """You are a routing and classification engine inside an enterprise GenAI system.

Your ONLY responsibility is to classify the user's query and system context into a routing decision object.

STRICT RULES:
- You must NOT answer the user's question.
- You must NOT perform reasoning, planning, or step-by-step thinking.
- You must NOT select specific tools, agents, or models.
- You must NOT include explanations, markdown, or extra text.

TOOL REQUIREMENT DETECTION (needs_tools):
Set needs_tools=true if the query requires:
1. Real-time data (current time, stock prices, weather, exchange rates)
2. External API calls (web search, location services, maps)
3. System operations (file I/O, database queries, system info)
4. Deterministic calculations (unit conversions, currency exchange)
5. Document creation or editing (creating files, generating documents, editing files)

AGENT REQUIREMENT DETECTION (needs_agent):
Set needs_agent=true if the query requires:
1. Multi-step planning, coordination, or complex workflow
2. File/document operations (creating, editing, generating documents) - ALWAYS requires document-editing-agent
3. Agent-specific capabilities that cannot be handled by simple tools

CRITICAL RULE: File editing tasks MUST have:
- intent_type=execution
- needs_tools=true
- needs_agent=true

Examples that NEED tools:
- "告訴我此刻時間" / "what time is it" → needs_tools=true (requires time tool)
- "幫我查台積電股價" / "check TSMC stock price" → needs_tools=true (requires stock API)
- "今天天氣如何" / "what's the weather today" → needs_tools=true (requires weather API)
- "搜尋AI相關資訊" / "search for AI information" → needs_tools=true (requires web search)
- "幫我產生Data Agent文件" / "generate Data Agent document" → needs_tools=true (requires document editing tool)
- "幫我產生文件" / "generate a file" → needs_tools=true (requires document editing tool)
- "生成文件" / "create a file" → needs_tools=true (requires document editing tool)
- "幫我將Data Agent的說明做成一份文件" / "create a document about Data Agent" → needs_tools=true (requires document editing tool)
- "生成一份報告" / "generate a report" → needs_tools=true (requires document editing tool)
- "編輯README.md文件" / "edit README.md file" → needs_tools=true (requires document editing tool)

Examples that DON'T need tools:
- "什麼是DevSecOps" / "what is DevSecOps" → needs_tools=false (knowledge question)
- "解釋一下微服務架構" / "explain microservices" → needs_tools=false (explanation)
- "你好" / "hello" → needs_tools=false (conversation)

You must ALWAYS return a valid JSON object that strictly follows the given JSON Schema.
If the query is ambiguous, unsafe, or unclear, choose the SAFEST and LOWEST-COST routing option.
If you are unsure, reduce complexity, avoid agents, and avoid tools."""

# Safe Fallback（失敗保護）
SAFE_FALLBACK = RouterDecision(
    intent_type="conversation",
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

    def _build_user_prompt(self, router_input: RouterInput) -> str:
        """
        構建 User Prompt

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

        prompt = f"""Analyze the following input and classify it according to the schema.
{agents_info}

User Query:
{router_input.user_query}

Session Context:
{session_context_str}

System Constraints:
{system_constraints_str}

Classification Guidelines:

1. intent_type:
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
       - Technical operation keywords: "插入", "設置", "填充", "重命名", "合併", "凍結", "複製", "刪除", "更新", "創建"
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
       - Rule: If the query contains technical operation keywords (插入, 設置, 填充, 重命名, 合併, 凍結, 複製, 刪除, 更新, 創建) AND refers to a file/spreadsheet, it MUST be execution (NOT query)

2. complexity:
   - low: single-step, obvious, straightforward (e.g., "what time is it")
   - mid: structured reasoning, requires some logic (e.g., "compare X and Y")
   - high: multi-step, orchestration, planning required (e.g., "analyze last month's sales and create a report")

3. needs_agent:
   - true if task requires:
     * Multi-step planning, coordination, or complex workflow
     * File/document operations (creating, editing, generating documents) - REQUIRES document-editing-agent
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
     * "編輯README.md文件" → needs_tools=true, needs_agent=true (user wants to EDIT a document - requires document-editing-agent)
     * "幫我產生文件" → needs_tools=true, needs_agent=true (user wants to CREATE a document - requires document-editing-agent)
     * "生成報告" → needs_tools=true, needs_agent=true (user wants to GENERATE a document - requires document-editing-agent)
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
