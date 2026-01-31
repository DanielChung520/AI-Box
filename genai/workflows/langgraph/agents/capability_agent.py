from __future__ import annotations
# 代碼功能說明: CapabilityAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""CapabilityAgent實現 - 能力發現和匹配LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class CapabilityAnalysisResult:
    """能力分析結果"""
    matched_agents: List[Dict[str, Any]] 
    matched_tools: List[Dict[str, Any]] 
    matched_models: List[Dict[str, Any]] 
    primary_agent: Optional[str] = None
    primary_tool: Optional[str] = None
    primary_model: Optional[str] = None
    capability_confidence: float = 0.0
    resource_requirements: Dict[str, Any] = None
    reasoning: str = ""

    def __post_init__(self):
        # 驗證分數範圍
        if not (0.0 <= self.capability_confidence <= 1.0):
            self.capability_confidence = max(0.0, min(1.0, self.capability_confidence))

        if self.resource_requirements is None:
            self.resource_requirements = {}


class CapabilityAgent(BaseAgentNode):
    """能力匹配Agent - 負責能力發現和匹配"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化CapabilityMatcher
        self.capability_matcher = None
        self._initialize_capability_matcher()

    def _initialize_capability_matcher(self) -> None:
        """初始化CapabilityMatcher組件"""
        try:
            from agents.task_analyzer.capability_matcher import CapabilityMatcher

            self.capability_matcher = CapabilityMatcher()
            logger.info("CapabilityMatcher initialized for CapabilityAgent")
        except Exception as e:
            logger.error(f"Failed to initialize CapabilityMatcher: {e}")
            self.capability_matcher = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行能力匹配分析

        Args:
            state: 當前狀態

        Returns:
            NodeResult: 分析結果
        """
        try:
            # 檢查意圖分析結果是否存在
            if not hasattr(state, "intent_analysis") or not state.intent_analysis:
                return NodeResult.failure("No intent analysis found for capability matching")

            intent_result = state.intent_analysis

            # 執行能力匹配
            capability_result = await self._match_capabilities(intent_result, state)

            if not capability_result:
                return NodeResult.failure("Capability matching failed")

            # 更新狀態
            state.capability_analysis = capability_result

            # 記錄觀察
            state.add_observation(
                "capability_analysis_completed",
                {
                    "matched_agents_count": len(capability_result.matched_agents),
                    "matched_tools_count": len(capability_result.matched_tools),
                    "matched_models_count": len(capability_result.matched_models),
                    "primary_agent": capability_result.primary_agent,
                    "primary_tool": capability_result.primary_tool,
                    "primary_model": capability_result.primary_model,
                    "capability_confidence": capability_result.capability_confidence,
                },
                capability_result.capability_confidence,
            )

            logger.info(
                f"Capability analysis completed for user {state.user_id}: {capability_result.primary_agent}",
            )

            # 決定下一步
            next_layer = self._determine_next_layer(capability_result, state)

            return NodeResult.success(
                data={
                    "capability_analysis": {
                        "matched_agents": capability_result.matched_agents,
                        "matched_tools": capability_result.matched_tools,
                        "matched_models": capability_result.matched_models,
                        "primary_agent": capability_result.primary_agent,
                        "primary_tool": capability_result.primary_tool,
                        "primary_model": capability_result.primary_model,
                        "capability_confidence": capability_result.capability_confidence,
                        "resource_requirements": capability_result.resource_requirements,
                        "reasoning": capability_result.reasoning,
                    },
                    "capability_summary": self._create_capability_summary(capability_result),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"CapabilityAgent execution error: {e}")
            return NodeResult.failure(f"Capability analysis error: {e}")

    async def _match_capabilities(
        self, intent_result: Any, state: AIBoxState,
    ) -> Optional[CapabilityAnalysisResult]:
        """
        執行能力匹配
        """
        try:
            if not self.capability_matcher:
                return self._fallback_capability_analysis(intent_result)

            # 構建RouterDecision
            router_decision = self._build_router_decision(intent_result, state)
            if not router_decision:
                return self._fallback_capability_analysis(intent_result)

            # 構建上下文
            context = self._build_context(intent_result, state)

            # 匹配Agents
            agent_matches = await self.capability_matcher.match_agents(router_decision, context)
            agent_matches_dict = [
                {
                    "agent_id": match.candidate_id,
                    "total_score": match.total_score,
                    "capability_match": match.capability_match,
                    "cost_score": match.cost_score,
                    "latency_score": match.latency_score,
                    "success_history": match.success_history,
                    "stability": match.stability,
                    "metadata": match.metadata,
                }
                for match in agent_matches
            ]

            # 匹配Tools
            tool_matches = await self.capability_matcher.match_tools(router_decision, context)
            tool_matches_dict = [
                {
                    "tool_id": match.candidate_id,
                    "total_score": match.total_score,
                    "capability_match": match.capability_match,
                    "cost_score": match.cost_score,
                    "latency_score": match.latency_score,
                    "success_history": match.success_history,
                    "stability": match.stability,
                    "metadata": match.metadata,
                }
                for match in tool_matches
            ]

            # 匹配Models
            model_matches = await self.capability_matcher.match_models(router_decision, context)
            model_matches_dict = [
                {
                    "model_id": match.candidate_id,
                    "total_score": match.total_score,
                    "capability_match": match.capability_match,
                    "cost_score": match.cost_score,
                    "latency_score": match.latency_score,
                    "success_history": match.success_history,
                    "stability": match.stability,
                    "metadata": match.metadata,
                }
                for match in model_matches
            ]

            # 確定主要候選者
            primary_agent = agent_matches_dict[0]["agent_id"] if agent_matches_dict else None
            primary_tool = tool_matches_dict[0]["tool_id"] if tool_matches_dict else None
            primary_model = model_matches_dict[0]["model_id"] if model_matches_dict else None

            # 計算整體信心度
            confidence = self._calculate_overall_confidence(
                agent_matches_dict, tool_matches_dict, model_matches_dict, intent_result,
            )

            # 提取資源需求
            resource_requirements = self._extract_resource_requirements(
                agent_matches_dict, tool_matches_dict, model_matches_dict, intent_result,
            )

            # 生成推理說明
            reasoning = self._generate_reasoning(
                intent_result, agent_matches_dict, tool_matches_dict, model_matches_dict,
            )

            return CapabilityAnalysisResult(
                matched_agents=agent_matches_dict,
                matched_tools=tool_matches_dict,
                matched_models=model_matches_dict,
                primary_agent=primary_agent,
                primary_tool=primary_tool,
                primary_model=primary_model,
                capability_confidence=confidence,
                resource_requirements=resource_requirements,
                reasoning=reasoning,
            )

        except Exception as e:
            logger.error(f"CapabilityMatcher analysis failed: {e}")
            return self._fallback_capability_analysis(intent_result)

    def _build_router_decision(self, intent_result: Any, state: AIBoxState) -> Optional[Any]:
        """構建RouterDecision"""
        try:
            from agents.task_analyzer.models import RouterDecision

            # 從意圖結果映射到RouterDecision
            intent_name = getattr(intent_result, "intent_name", "general_query")
            domain = getattr(intent_result, "domain", "general")

            # 映射意圖類型
            intent_type_map = {
                "content_creation": "execution",
                "code_analysis": "analysis",
                "system_design": "analysis",
                "information_query": "retrieval",
                "content_modification": "execution",
                "document_analysis": "retrieval",
            }
            intent_type = intent_type_map.get(intent_name, "conversation")

            # 判斷複雜度
            complexity = (
                "high",
                if domain in ["system_architecture", "code_generation"]
                else "mid",
                if intent_name not in ["general_query"]
                else "low",
            )

            # 判斷是否需要Agent
            needs_agent = (
                intent_name not in ["general_query", "information_query"] or complexity == "high",
            )

            # 判斷是否需要工具
            needs_tools = intent_type in ["execution", "retrieval"] or complexity == "high"

            # 確定性需求
            determinism_required = intent_type == "execution" or intent_name in [
                "content_creation",
                "content_modification",
            ]

            return RouterDecision(
                intent_type=intent_type,
                complexity=complexity,
                needs_agent=needs_agent,
                needs_tools=needs_tools,
                determinism_required=determinism_required,
                user_id=state.user_id,
                session_id=state.session_id,
                risk_level="low",
                confidence=0.9,
            )

        except Exception as e:
            logger.error(f"Failed to build RouterDecision: {e}")
            return None

    def _build_context(self, intent_result: Any, state: AIBoxState) -> Dict[str, Any]:
        """構建匹配上下文"""
        context = {
            "user_id": state.user_id,
            "session_id": state.session_id,
            "task": getattr(state, "task_id", ""),
        }

        # 添加意圖信息
        if intent_result:
            context["intent_name"] = getattr(intent_result, "intent_name", "")
            context["domain"] = getattr(intent_result, "domain", "")
            context["target_agent"] = getattr(intent_result, "target_agent", "")

        # 添加最新的用戶消息
        for message in reversed(state.messages):
            if message.role == "user":
                context["user_query"] = message.content
                break

        return context

    def _calculate_overall_confidence(
        self,
        agent_matches: List[Dict[str, Any]] 
        tool_matches: List[Dict[str, Any]] 
        model_matches: List[Dict[str, Any]] 
        intent_result: Any ,
    ) -> float:
        """計算整體信心度"""
        try:
            agent_confidence = agent_matches[0]["total_score"] if agent_matches else 0.0
            tool_confidence = tool_matches[0]["total_score"] if tool_matches else 0.0
            model_confidence = model_matches[0]["total_score"] if model_matches else 0.0

            intent_name = getattr(intent_result, "intent_name", "")
            if intent_name in ["content_creation", "content_modification"]:
                confidence = 0.5 * agent_confidence + 0.3 * tool_confidence + 0.2 * model_confidence
            elif intent_name == "code_analysis":
                confidence = 0.3 * agent_confidence + 0.2 * tool_confidence + 0.5 * model_confidence
            else:
                confidence = 0.4 * agent_confidence + 0.3 * tool_confidence + 0.3 * model_confidence

            return min(confidence, 1.0)

        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5

    def _extract_resource_requirements(
        self,
        agent_matches: List[Dict[str, Any]] 
        tool_matches: List[Dict[str, Any]] 
        model_matches: List[Dict[str, Any]] 
        intent_result: Any ,
    ) -> Dict[str, Any]:
        """提取資源需求"""
        requirements = {
            "agent_required": len(agent_matches) > 0,
            "tool_required": len(tool_matches) > 0,
            "model_required": len(model_matches) > 0,
        }

        intent_name = getattr(intent_result, "intent_name", "")
        if intent_name in ["content_creation", "content_modification"]:
            requirements["file_system_access"] = True
            requirements["storage_access"] = True
        elif intent_name == "code_analysis":
            requirements["read_only_access"] = True
        elif intent_name == "system_design":
            requirements["design_tools"] = True

        return requirements

    def _generate_reasoning(
        self,
        intent_result: Any ,
        agent_matches: List[Dict[str, Any]] 
        tool_matches: List[Dict[str, Any]] 
        model_matches: List[Dict[str, Any]] 
    ) -> str:
        """生成推理說明"""
        try:
            intent_name = getattr(intent_result, "intent_name", "unknown")
            domain = getattr(intent_result, "domain", "unknown")

            reasoning_parts = [
                f"Intent '{intent_name}' in domain '{domain}' requires capability matching.",
            ]

            if agent_matches:
                top_agent = agent_matches[0]
                reasoning_parts.append(
                    f"Selected primary agent '{top_agent['agent_id']}' ",
                    f"with capability match score {top_agent['capability_match']:.2f}.",
                )

            return " ".join(reasoning_parts)

        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            return "Capability matching completed with standard reasoning."

    def _fallback_capability_analysis(self, intent_result: Any) -> CapabilityAnalysisResult:
        """後備能力分析邏輯"""
        try:
            intent_name = getattr(intent_result, "intent_name", "general_query")

            matched_agents = []
            matched_tools = []
            matched_models = []

            if intent_name == "content_creation":
                matched_agents = [
                    {"agent_id": "md-editor", "total_score": 0.7, "capability_match": 0.6}
                ]
            elif intent_name == "document_analysis":
                matched_agents = [
                    {"agent_id": "rag-agent", "total_score": 0.8, "capability_match": 0.8}
                ]

            if not matched_models:
                matched_models = [
                    {
                        "model_id": "ollama:gpt-oss-120b-cloud",
                        "total_score": 0.6,
                        "capability_match": 0.5,
                    }
                ]

            primary_agent = matched_agents[0]["agent_id"] if matched_agents else None
            primary_tool = matched_tools[0]["tool_id"] if matched_tools else None
            primary_model = (
                matched_models[0]["model_id"] if matched_models else "ollama:gpt-oss-120b-cloud",
            )

            return CapabilityAnalysisResult(
                matched_agents=matched_agents,
                matched_tools=matched_tools,
                matched_models=matched_models,
                primary_agent=primary_agent,
                primary_tool=primary_tool,
                primary_model=primary_model,
                capability_confidence=0.5,
                resource_requirements={
                    "fallback": True,
                    "agent_required": primary_agent is not None,
                },
                reasoning=f"Fallback analysis: matched capabilities for intent '{intent_name}'",
            )

        except Exception as e:
            logger.error(f"Fallback capability analysis failed: {e}")
            return CapabilityAnalysisResult(
                matched_agents=[]
                matched_tools=[]
                matched_models=[]
                capability_confidence=0.0,
                reasoning="Complete fallback failed",
            )

    def _determine_next_layer(
        self, capability_result: CapabilityAnalysisResult, state: AIBoxState,
    ) -> str:
        """決定下一步層次"""
        if capability_result.capability_confidence < 0.4 and not capability_result.matched_agents:
            return "clarification"

        return "resource_check"

    def _create_capability_summary(
        self, capability_result: CapabilityAnalysisResult,
    ) -> Dict[str, Any]:
        return {
            "primary_agent": capability_result.primary_agent,
            "confidence": capability_result.capability_confidence,
            "agent_count": len(capability_result.matched_agents),
            "complexity": "mid",
        }


def create_capability_agent_config() -> NodeConfig:
    return NodeConfig(
        name="CapabilityAgent",
        description="能力匹配Agent - 負責能力發現和匹配",
        max_retries=2,
        timeout=20.0,
        required_inputs=["user_id", "session_id", "intent_analysis"],
        optional_inputs=["task_id", "messages"],
        output_keys=["capability_analysis", "capability_summary"],
    )


def create_capability_agent() -> CapabilityAgent:
    config = create_capability_agent_config()
    return CapabilityAgent(config)