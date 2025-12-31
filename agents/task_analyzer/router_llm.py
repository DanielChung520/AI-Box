# 代碼功能說明: Router LLM 工程級實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Router LLM 工程級實現 - 固定 System Prompt、完整 Schema 驗證、失敗保護機制"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import RouterDecision, RouterInput
from llm.clients.factory import LLMClientFactory

logger = logging.getLogger(__name__)

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

Examples that NEED tools:
- "告訴我此刻時間" / "what time is it" → needs_tools=true (requires time tool)
- "幫我查台積電股價" / "check TSMC stock price" → needs_tools=true (requires stock API)
- "今天天氣如何" / "what's the weather today" → needs_tools=true (requires weather API)
- "搜尋AI相關資訊" / "search for AI information" → needs_tools=true (requires web search)

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

        prompt = f"""Analyze the following input and classify it according to the schema.

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

2. complexity:
   - low: single-step, obvious, straightforward (e.g., "what time is it")
   - mid: structured reasoning, requires some logic (e.g., "compare X and Y")
   - high: multi-step, orchestration, planning required (e.g., "analyze last month's sales and create a report")

3. needs_agent:
   - true ONLY if task requires multi-step planning, coordination, or complex workflow
   - false for simple queries that can be answered directly or with a single tool

4. needs_tools (CRITICAL):
   - true if query requires external data, real-time information, or system operations:
     * Current time/date queries (e.g., "告訴我此刻時間", "what time is it")
     * Stock prices, exchange rates, financial data
     * Weather information
     * Web search
     * Location/maps
     * File operations
     * Database queries
   - false if query only needs knowledge/explanation (LLM can answer from training data)
   - Examples:
     * "告訴我此刻時間" → needs_tools=true (requires time tool)
     * "幫我看台積電股價" → needs_tools=true (requires stock API)
     * "什麼是DevSecOps" → needs_tools=false (knowledge question)

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
                router_input.session_context["similar_decisions"] = similar_decisions[
                    :3
                ]  # 最多 3 個
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
            response = await client.chat(messages=messages, model=None)  # 使用默認模型
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
