# 代碼功能說明: 能力匹配器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""能力匹配器 - 匹配 Agent、Tool、Model 的能力"""

import logging
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import CapabilityMatch, RouterDecision
from services.api.models.llm_model import LLMProvider, ModelCapability, ModelStatus

logger = logging.getLogger(__name__)


class CapabilityMatcher:
    """能力匹配器類"""

    def __init__(self):
        """初始化能力匹配器"""
        self._agent_registry = None
        self._tool_registry = None

    def _get_agent_registry(self):
        """獲取 Agent Registry（懶加載）"""
        if self._agent_registry is None:
            try:
                from agents.services.registry.registry import AgentRegistry

                self._agent_registry = AgentRegistry()
            except Exception as e:
                logger.warning(f"Failed to initialize Agent Registry: {e}")
                self._agent_registry = None
        return self._agent_registry

    def _get_tool_registry(self):
        """獲取 Tool Registry（懶加載）"""
        if self._tool_registry is None:
            try:
                from tools.registry_loader import get_tools_for_task_analysis

                self._tool_registry = get_tools_for_task_analysis()
            except Exception as e:
                logger.warning(f"Failed to initialize Tool Registry: {e}")
                self._tool_registry = None
        return self._tool_registry

    def _extract_required_capabilities(self, router_decision: RouterDecision) -> List[str]:
        """
        從 Router 決策中提取所需能力

        Args:
            router_decision: Router 決策

        Returns:
            所需能力列表
        """
        capabilities = []

        # 根據 intent_type 添加能力
        if router_decision.intent_type == "analysis":
            capabilities.append("analysis")
            capabilities.append("reasoning")
        elif router_decision.intent_type == "retrieval":
            capabilities.append("retrieval")
            capabilities.append("search")
        elif router_decision.intent_type == "execution":
            capabilities.append("execution")
            capabilities.append("action")

        # 根據 complexity 添加能力
        if router_decision.complexity == "high":
            capabilities.append("complex_reasoning")
            capabilities.append("multi_step")

        # 根據 determinism_required 添加能力
        if router_decision.determinism_required:
            capabilities.append("deterministic")

        return capabilities

    def _extract_required_model_capabilities(
        self, router_decision: RouterDecision
    ) -> List[ModelCapability]:
        """
        從 Router 決策中提取所需的模型能力

        Args:
            router_decision: Router 決策

        Returns:
            所需的 ModelCapability 列表
        """
        capabilities = []

        # 根據 intent_type 映射能力
        if router_decision.intent_type == "conversation":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.STREAMING)
        elif router_decision.intent_type == "retrieval":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.COMPLETION)
        elif router_decision.intent_type == "analysis":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.REASONING)
        elif router_decision.intent_type == "execution":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.FUNCTION_CALLING)

        # 根據複雜度添加能力
        if router_decision.complexity == "high":
            capabilities.append(ModelCapability.REASONING)

        # 確保 CHAT 能力始終存在（所有任務都需要對話能力）
        if ModelCapability.CHAT not in capabilities:
            capabilities.append(ModelCapability.CHAT)

        return capabilities

    def _calculate_model_scores(
        self,
        model: Any,
        router_decision: RouterDecision,
        required_capabilities: List[ModelCapability],
    ) -> Dict[str, float]:
        """
        計算模型的各項評分

        Args:
            model: LLM 模型對象
            router_decision: Router 決策
            required_capabilities: 所需能力列表

        Returns:
            包含各項評分的字典
        """

        scores: Dict[str, float] = {}

        # 1. 能力匹配度
        model_capabilities = set(model.capabilities)
        required_set = set(required_capabilities)
        if required_set:
            capability_match = len(required_set.intersection(model_capabilities)) / len(
                required_set
            )
        else:
            capability_match = 0.5  # 如果沒有明確要求，給中等匹配度
        scores["capability_match"] = capability_match

        # 2. 成本評分（基於 provider 和 context_window）
        # 本地模型（OLLAMA）成本最低，大模型（context_window 大）成本較高
        if model.provider == LLMProvider.OLLAMA:
            cost_score = 0.95  # 本地模型成本最低
        elif model.context_window and model.context_window > 100000:
            cost_score = 0.5  # 大上下文窗口模型成本較高
        elif model.context_window and model.context_window > 32000:
            cost_score = 0.7
        else:
            cost_score = 0.8
        scores["cost_score"] = cost_score

        # 3. 延遲評分（基於 provider）
        # 本地模型延遲最低，雲服務延遲中等
        if model.provider == LLMProvider.OLLAMA:
            latency_score = 0.9  # 本地模型延遲最低
        else:
            latency_score = 0.7  # 雲服務延遲中等
        scores["latency_score"] = latency_score

        # 4. 歷史成功率（默認值，後續可從 Routing Memory 獲取）
        success_history = 0.8
        scores["success_history"] = success_history

        # 5. 穩定度（基於 status 和 provider）
        if model.status == ModelStatus.ACTIVE:
            if model.provider in [LLMProvider.OLLAMA, LLMProvider.OPENAI, LLMProvider.GOOGLE]:
                stability = 0.9  # 穩定提供商
            else:
                stability = 0.8
        else:
            stability = 0.5  # 非活躍狀態穩定性較低
        scores["stability"] = stability

        # 根據複雜度調整評分
        if router_decision.complexity == "high":
            # 複雜任務需要更強的能力匹配度
            scores["capability_match"] = min(scores["capability_match"] * 1.1, 1.0)
        elif router_decision.complexity == "low":
            # 簡單任務可以優先考慮成本
            scores["cost_score"] = min(scores["cost_score"] * 1.1, 1.0)

        return scores

    async def match_agents(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配 Agent 能力

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的 Agent 列表（按匹配度排序）
        """
        if not router_decision.needs_agent:
            return []

        registry = self._get_agent_registry()
        if registry is None:
            logger.warning("Agent Registry not available, returning empty list")
            return []

        try:
            from agents.services.registry.discovery import AgentDiscovery

            # 提取所需能力
            required_capabilities = self._extract_required_capabilities(router_decision)

            # 發現可用 Agent
            discovery = AgentDiscovery(registry)
            agents = discovery.discover_agents(
                required_capabilities=required_capabilities if required_capabilities else None,
                user_id=context.get("user_id") if context else None,
                user_roles=context.get("user_roles") if context else None,
            )

            # 計算匹配度
            matches = []
            for agent in agents:
                agent_capabilities = set(agent.capabilities)
                required_set = set(required_capabilities)

                # 計算能力匹配度
                if required_set:
                    capability_match = len(required_set.intersection(agent_capabilities)) / len(
                        required_set
                    )
                else:
                    capability_match = 0.5  # 如果沒有明確要求，給中等匹配度

                # 簡化的評分（實際應該從歷史數據獲取）
                cost_score = 0.7  # 默認值
                latency_score = 0.7  # 默認值
                success_history = 0.8  # 默認值
                stability = 0.8  # 默認值

                # 計算總評分
                total_score = (
                    0.35 * capability_match
                    + 0.20 * cost_score
                    + 0.15 * latency_score
                    + 0.20 * success_history
                    + 0.10 * stability
                )

                matches.append(
                    CapabilityMatch(
                        candidate_id=agent.agent_id,
                        candidate_type="agent",
                        capability_match=capability_match,
                        cost_score=cost_score,
                        latency_score=latency_score,
                        success_history=success_history,
                        stability=stability,
                        total_score=total_score,
                        metadata={
                            "agent_type": agent.agent_type,
                            "capabilities": agent.capabilities,
                            "load": agent.load,
                        },
                    )
                )

            # 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            logger.info(f"Matched {len(matches)} agents for router decision")
            return matches

        except Exception as e:
            logger.error(f"Failed to match agents: {e}", exc_info=True)
            return []

    async def match_tools(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配工具能力

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的工具列表（按匹配度排序）
        """
        if not router_decision.needs_tools:
            return []

        registry = self._get_tool_registry()
        if registry is None:
            logger.warning("Tool Registry not available, returning empty list")
            return []

        try:
            tools = registry.get("tools", [])

            # 提取所需能力
            required_capabilities = self._extract_required_capabilities(router_decision)

            # 從 context 中獲取用戶查詢（用於基於查詢文本的匹配）
            user_query = ""
            if context:
                user_query = context.get("task", "") or context.get("query", "") or ""
            user_query_lower = user_query.lower() if user_query else ""

            matches = []
            for tool in tools:
                tool_name = tool.get("name", "")
                tool_category = tool.get("category", "")
                tool_purpose = tool.get("purpose", "")
                tool_use_cases = tool.get("use_cases", [])

                # 基於工具名稱和類別的匹配（優先級最高）
                name_category_match = 0.0
                if tool_name == "datetime" and any(
                    keyword in user_query_lower
                    for keyword in [
                        "時間",
                        "時間",
                        "time",
                        "現在",
                        "此刻",
                        "當前",
                        "當前時間",
                        "現在幾點",
                    ]
                ):
                    # datetime 工具 + 時間查詢 = 完美匹配
                    name_category_match = 1.0
                elif tool_category == "時間與日期" and any(
                    keyword in user_query_lower
                    for keyword in ["時間", "時間", "time", "現在", "此刻", "當前", "日期", "date"]
                ):
                    # 時間類別工具 + 時間查詢 = 高匹配度
                    name_category_match = 0.9
                elif tool_name == "weather" and any(
                    keyword in user_query_lower
                    for keyword in ["天氣", "weather", "氣象", "溫度", "temperature"]
                ):
                    # weather 工具 + 天氣查詢 = 完美匹配
                    name_category_match = 1.0
                elif tool_category == "天氣" and any(
                    keyword in user_query_lower
                    for keyword in ["天氣", "weather", "氣象", "溫度", "temperature"]
                ):
                    # 天氣類別工具 + 天氣查詢 = 高匹配度
                    name_category_match = 0.9

                # 簡單的匹配邏輯：檢查工具用途和使用場景
                tool_capabilities = []
                if "搜索" in tool_purpose or "search" in tool_purpose.lower():
                    tool_capabilities.append("search")
                    tool_capabilities.append("retrieval")
                if "計算" in tool_purpose or "calculate" in tool_purpose.lower():
                    tool_capabilities.append("calculation")
                if "查詢" in tool_purpose or "query" in tool_purpose.lower():
                    tool_capabilities.append("query")
                    tool_capabilities.append("retrieval")
                if (
                    "時間" in tool_purpose
                    or "時間" in tool_purpose
                    or "time" in tool_purpose.lower()
                ):
                    tool_capabilities.append("time")
                    tool_capabilities.append("retrieval")
                if "天氣" in tool_purpose or "weather" in tool_purpose.lower():
                    tool_capabilities.append("weather")
                    tool_capabilities.append("retrieval")

                # 根據 intent_type 匹配
                if router_decision.intent_type == "retrieval" and "search" in tool_capabilities:
                    tool_capabilities.append("retrieval")
                if router_decision.intent_type == "analysis" and "calculation" in tool_capabilities:
                    tool_capabilities.append("analysis")

                # 計算能力匹配度
                if name_category_match > 0.0:
                    # 如果有名稱/類別匹配，優先使用（最高優先級）
                    capability_match = name_category_match
                elif required_capabilities:
                    tool_cap_set = set(tool_capabilities)
                    required_set = set(required_capabilities)
                    capability_match = len(required_set.intersection(tool_cap_set)) / len(
                        required_set
                    )
                else:
                    # 如果沒有明確要求，根據 determinism_required 判斷
                    if router_decision.determinism_required:
                        # 確定性工具通常有明確的輸入輸出
                        capability_match = 0.6
                    else:
                        capability_match = 0.4

                # 簡化的評分
                cost_score = 0.9  # 工具通常成本較低
                latency_score = 0.8  # 工具通常延遲較低
                success_history = 0.85  # 默認值
                stability = 0.9  # 工具通常較穩定

                # 計算總評分
                total_score = (
                    0.35 * capability_match
                    + 0.20 * cost_score
                    + 0.15 * latency_score
                    + 0.20 * success_history
                    + 0.10 * stability
                )

                matches.append(
                    CapabilityMatch(
                        candidate_id=tool_name,
                        candidate_type="tool",
                        capability_match=capability_match,
                        cost_score=cost_score,
                        latency_score=latency_score,
                        success_history=success_history,
                        stability=stability,
                        total_score=total_score,
                        metadata={
                            "category": tool.get("category"),
                            "purpose": tool_purpose,
                            "use_cases": tool_use_cases,
                        },
                    )
                )

            # 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            logger.info(f"Matched {len(matches)} tools for router decision")
            return matches

        except Exception as e:
            logger.error(f"Failed to match tools: {e}", exc_info=True)
            return []

    async def match_models(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配模型能力 - 改進版本

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的模型列表（按匹配度排序）
        """
        try:
            from services.api.models.llm_model import LLMModelQuery
            from services.api.services.llm_model_service import LLMModelService

            # 1. 從 ArangoDB 獲取所有可用模型
            model_service = LLMModelService()
            query = LLMModelQuery(
                status=ModelStatus.ACTIVE,
                limit=1000,  # 獲取所有可用模型
            )
            all_models = model_service.get_all(query)

            if not all_models:
                logger.warning("No active models found in database")
                return []

            # 2. 提取所需能力
            required_capabilities = self._extract_required_model_capabilities(router_decision)

            # 3. 計算每個模型的匹配度和評分
            matches = []
            for model in all_models:
                # 計算各項評分
                scores = self._calculate_model_scores(model, router_decision, required_capabilities)

                # 計算總評分（使用與 Agent/Tool 相同的權重）
                total_score = (
                    0.35 * scores["capability_match"]
                    + 0.20 * scores["cost_score"]
                    + 0.15 * scores["latency_score"]
                    + 0.20 * scores["success_history"]
                    + 0.10 * scores["stability"]
                )

                # 構建候選 ID（格式：provider:model_id）
                candidate_id = f"{model.provider.value}:{model.model_id}"

                matches.append(
                    CapabilityMatch(
                        candidate_id=candidate_id,
                        candidate_type="model",
                        capability_match=scores["capability_match"],
                        cost_score=scores["cost_score"],
                        latency_score=scores["latency_score"],
                        success_history=scores["success_history"],
                        stability=scores["stability"],
                        total_score=total_score,
                        metadata={
                            "provider": model.provider.value,
                            "model_id": model.model_id,
                            "model_name": model.name,
                            "capabilities": [cap.value for cap in model.capabilities],
                            "context_window": model.context_window,
                            "status": model.status.value,
                            "is_default": model.is_default,
                        },
                    )
                )

            # 4. 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            logger.info(
                f"Matched {len(matches)} models for router decision "
                f"(intent={router_decision.intent_type}, complexity={router_decision.complexity})"
            )

            return matches

        except Exception as e:
            logger.error(f"Failed to match models: {e}", exc_info=True)
            # 失敗時返回空列表，而不是使用舊的 LLMRouter 邏輯
            return []
