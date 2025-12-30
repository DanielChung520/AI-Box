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
                from agents.task_analyzer.models import (
                    LLMProvider,
                    TaskClassificationResult,
                    TaskType,
                )

                # 創建臨時分類結果（用於路由選擇）
                temp_classification = TaskClassificationResult(
                    task_type=TaskType.QUERY,
                    confidence=0.5,
                    reasoning="Router LLM initialization",
                )

                # 使用 LLM Router 選擇低成本模型
                llm_router = LLMRouter()
                routing_result = llm_router.route(temp_classification, "", {})

                # 優先使用本地模型（低成本）
                if routing_result.provider == LLMProvider.OLLAMA:
                    self._llm_client = LLMClientFactory.create_client(
                        routing_result.provider, use_cache=True
                    )
                else:
                    # 如果沒有本地模型，嘗試使用首選提供商
                    try:
                        provider_enum = LLMProvider(self.preferred_provider)
                        self._llm_client = LLMClientFactory.create_client(
                            provider_enum, use_cache=True
                        )
                    except (ValueError, Exception):
                        # 最後回退到 ChatGPT
                        self._llm_client = LLMClientFactory.create_client(
                            LLMProvider.CHATGPT, use_cache=True
                        )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client, will use fallback: {e}")
                # 如果初始化失敗，使用 ChatGPT 作為最後選擇
                from agents.task_analyzer.models import LLMProvider

                self._llm_client = LLMClientFactory.create_client(
                    LLMProvider.CHATGPT, use_cache=True
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
- intent_type:
  - conversation: casual, explanation, discussion
  - retrieval: lookup, fetch, search
  - analysis: reasoning, comparison, evaluation
  - execution: actions, commands, operations
- complexity:
  - low: single-step, obvious
  - mid: structured reasoning
  - high: multi-step or orchestration
- needs_agent:
  - true only if task requires multi-step planning or coordination
- needs_tools:
  - true if deterministic or structured external operations are required
- determinism_required:
  - true if output must be reproducible or exact
- risk_level:
  - high if involving finance, legal, production systems, or irreversible actions
- confidence:
  - your confidence in this classification (0.0 to 1.0)

Return ONLY valid JSON."""
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
            client = self._get_llm_client()
            response = await client.chat(messages=messages, model=None)  # 使用默認模型

            # 提取響應內容
            content = response.get("content") or response.get("text", "")
            if not content:
                logger.warning("LLM returned empty response, using fallback")
                return SAFE_FALLBACK

            # 提取 JSON
            json_data = self._extract_json_from_response(content)
            if json_data is None:
                logger.warning("Failed to extract JSON from LLM response, using fallback")
                return SAFE_FALLBACK

            # 驗證 Schema
            try:
                decision = RouterDecision(**json_data)
            except Exception as e:
                logger.warning(f"Schema validation failed: {e}, using fallback")
                return SAFE_FALLBACK

            # Confidence 門檻檢查
            if decision.confidence < MIN_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Confidence {decision.confidence} below threshold {MIN_CONFIDENCE_THRESHOLD}, using fallback"
                )
                return SAFE_FALLBACK

            logger.info(
                f"Router decision: intent={decision.intent_type}, "
                f"complexity={decision.complexity}, confidence={decision.confidence:.2f}"
            )

            return decision

        except Exception as e:
            logger.error(f"Router LLM failed: {e}", exc_info=True)
            # 失敗時使用 Safe Fallback（不重試）
            return SAFE_FALLBACK
