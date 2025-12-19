# 代碼功能說明: Orchestrator Manager Agent 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Orchestrator Manager Agent 實現

AI 驱动的任务协调服务，提供智能任务路由和负载均衡功能。
"""

import json
import logging
from typing import Any, Dict, Optional

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.services.registry.discovery import AgentDiscovery
from agents.services.registry.registry import get_agent_registry
from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

from .models import OrchestratorManagerRequest, OrchestratorManagerResponse, TaskRoutingDecision

logger = logging.getLogger(__name__)


class OrchestratorManagerAgent(AgentServiceProtocol):
    """Orchestrator Manager Agent - 协调管理员

    AI 驱动的任务协调服务，提供：
    - 智能任务路由
    - 负载均衡
    - 任务协调决策
    """

    def __init__(self):
        """初始化 Orchestrator Manager Agent"""
        self._registry = get_agent_registry()
        self._discovery = AgentDiscovery(self._registry)
        self._orchestrator = AgentOrchestrator()
        self._llm_client = None  # 延迟初始化
        self._logger = logger

    def _get_llm_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self._llm_client is None:
            try:
                self._llm_client = get_client(LLMProvider.OLLAMA)
            except Exception as e:
                self._logger.warning(f"Failed to initialize Ollama client: {e}")
                try:
                    self._llm_client = get_client(LLMProvider.QWEN)
                except Exception:
                    self._logger.error("No LLM client available")
        return self._llm_client

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        执行协调管理任务

        Args:
            request: Agent 服务请求

        Returns:
            Agent 服务响应
        """
        try:
            # 解析请求数据
            task_data = request.task_data
            action = task_data.get("action", "route")
            orchestrator_request = OrchestratorManagerRequest(**task_data)

            # 根据操作类型执行相应功能
            if action == "route":
                result = await self._route_task(orchestrator_request)
            elif action == "balance_load":
                result = await self._balance_load(orchestrator_request)
            elif action == "coordinate":
                result = await self._coordinate_task(orchestrator_request)
            elif action == "analyze":
                result = await self._analyze_orchestration(orchestrator_request)
            else:
                result = OrchestratorManagerResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                    routing_decision=None,  # type: ignore[call-arg]  # routing_decision 有默認值
                    load_balance_result=None,  # type: ignore[call-arg]  # load_balance_result 有默認值
                    coordination_result=None,  # type: ignore[call-arg]  # coordination_result 有默認值
                    analysis=None,  # type: ignore[call-arg]  # analysis 有默認值
                    message=None,  # type: ignore[call-arg]  # message 有默認值
                )

            # 构建响应
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result={
                    "success": result.success,
                    "action": result.action,
                    "routing_decision": (
                        result.routing_decision.model_dump() if result.routing_decision else None
                    ),
                    "load_balance_result": result.load_balance_result,
                    "coordination_result": result.coordination_result,
                    "analysis": result.analysis,
                    "message": result.message,
                    "error": result.error,
                },
                error=None,  # type: ignore[call-arg]  # error 有默認值
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Orchestrator Manager execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,  # type: ignore[call-arg]  # result 有默認值
                error=str(e),
                metadata=request.metadata,
            )

    async def _route_task(self, request: OrchestratorManagerRequest) -> OrchestratorManagerResponse:
        """
        AI 驱动的任务路由

        Args:
            request: 协调管理请求

        Returns:
            协调管理响应
        """
        try:
            # 发现可用的 Agent
            agents = self._discovery.discover_agents(
                required_capabilities=request.required_capabilities,
                agent_type=request.task_type,
            )

            if not agents:
                return OrchestratorManagerResponse(
                    success=False,
                    action="route",
                    error="No available agents found",
                )  # type: ignore[call-arg]  # 其他參數都是 Optional

            # 使用 AI 进行智能路由
            if request.task_description and self._get_llm_client():
                routing_decision = await self._ai_route_task(
                    request.task_description, agents, request.context
                )
            else:
                # 如果没有 LLM，使用简单策略（选择第一个可用 Agent）
                agent = agents[0]
                routing_decision = TaskRoutingDecision(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    confidence=0.5,
                    reasoning="First available agent",
                    alternatives=None,  # type: ignore[call-arg]  # alternatives 有默認值
                )

            return OrchestratorManagerResponse(
                success=True,
                action="route",
                routing_decision=routing_decision,
                message=f"Task routed to agent: {routing_decision.agent_id}",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Task routing failed: {e}")
            return OrchestratorManagerResponse(
                success=False,
                action="route",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _balance_load(
        self, request: OrchestratorManagerRequest
    ) -> OrchestratorManagerResponse:
        """
        负载均衡

        Args:
            request: 协调管理请求

        Returns:
            协调管理响应
        """
        try:
            # 获取所有 Agent 的负载信息
            agents = self._registry.list_agents()
            load_info = {}

            for agent in agents:
                # 这里应该从 Orchestrator 获取实际的负载信息
                # 暂时使用简单统计
                load_info[agent.agent_id] = {
                    "status": agent.status.value,
                    "capabilities": agent.capabilities,
                }

            # 使用 AI 进行负载均衡决策
            if self._get_llm_client():
                balance_result = await self._ai_balance_load(
                    request.task_description, agents, load_info, request.context
                )
            else:
                # 简单策略：选择状态为 ONLINE 的第一个 Agent
                online_agents = [agent for agent in agents if agent.status.value == "online"]
                if online_agents:
                    balance_result = {
                        "selected_agent_id": online_agents[0].agent_id,
                        "reason": "First online agent",
                    }
                else:
                    balance_result = {
                        "selected_agent_id": None,
                        "reason": "No online agents available",
                    }

            return OrchestratorManagerResponse(
                success=True,
                action="balance_load",
                load_balance_result=balance_result,
                message="Load balancing completed",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Load balancing failed: {e}")
            return OrchestratorManagerResponse(
                success=False,
                action="balance_load",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _coordinate_task(
        self, request: OrchestratorManagerRequest
    ) -> OrchestratorManagerResponse:
        """
        任务协调

        Args:
            request: 协调管理请求

        Returns:
            协调管理响应
        """
        try:
            # 使用 AI 进行任务协调决策
            if request.task_description and self._get_llm_client():
                coordination_result = await self._ai_coordinate_task(
                    request.task_description, request.context
                )
            else:
                coordination_result = {
                    "strategy": "sequential",
                    "agents": [],
                    "reason": "Default coordination strategy",
                }

            return OrchestratorManagerResponse(
                success=True,
                action="coordinate",
                coordination_result=coordination_result,
                message="Task coordination completed",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Task coordination failed: {e}")
            return OrchestratorManagerResponse(
                success=False,
                action="coordinate",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _analyze_orchestration(
        self, request: OrchestratorManagerRequest
    ) -> OrchestratorManagerResponse:
        """
        协调分析

        Args:
            request: 协调管理请求

        Returns:
            协调管理响应
        """
        try:
            # 基础分析
            agents = self._registry.list_agents()
            analysis: Dict[str, Any] = {
                "total_agents": len(agents),
                "by_status": {},
                "by_type": {},
            }

            for agent in agents:
                status = agent.status.value
                analysis["by_status"][status] = analysis["by_status"].get(status, 0) + 1
                agent_type = agent.agent_type
                analysis["by_type"][agent_type] = analysis["by_type"].get(agent_type, 0) + 1

            # 使用 AI 进行深度分析
            if self._get_llm_client():
                ai_analysis = await self._ai_analyze_orchestration(agents, analysis)
                analysis.update(ai_analysis)

            return OrchestratorManagerResponse(
                success=True,
                action="analyze",
                analysis=analysis,
                message="Orchestration analysis completed",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Orchestration analysis failed: {e}")
            return OrchestratorManagerResponse(
                success=False,
                action="analyze",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _ai_route_task(
        self, task_description: str, agents: list, context: Optional[Dict[str, Any]]
    ) -> TaskRoutingDecision:
        """
        使用 AI 进行任务路由

        Args:
            task_description: 任务描述
            agents: Agent 列表
            context: 上下文信息

        Returns:
            路由决策
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                # 回退到简单策略
                agent = agents[0]
                return TaskRoutingDecision(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    confidence=0.5,
                    reasoning="LLM unavailable, using first agent",
                    alternatives=None,  # type: ignore[call-arg]  # alternatives 有默認值
                )

            agent_summaries = [
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "type": agent.agent_type,
                    "capabilities": agent.capabilities,
                }
                for agent in agents
            ]

            prompt = f"""你是一个任务路由专家。根据任务描述，从以下 Agent 列表中选择最合适的 Agent。

任务描述：{task_description}

可用 Agent：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请返回路由决策（JSON 格式）：
{{"agent_id": "...", "reasoning": "...", "confidence": 0.0-1.0, "alternatives": [...]}}"""

            response = await llm_client.generate(prompt, max_tokens=500)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                result = json.loads(result_text)
                agent_id = result.get("agent_id")
                agent = next((a for a in agents if a.agent_id == agent_id), agents[0])

                return TaskRoutingDecision(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    confidence=result.get("confidence", 0.5),
                    reasoning=result.get("reasoning", "AI routing decision"),
                    alternatives=result.get("alternatives"),
                )
            except (json.JSONDecodeError, StopIteration):
                self._logger.warning("Failed to parse LLM response")
                agent = agents[0]
                return TaskRoutingDecision(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    confidence=0.5,
                    reasoning="LLM parsing failed, using first agent",
                    alternatives=None,  # type: ignore[call-arg]  # alternatives 有默認值
                )

        except Exception as e:
            self._logger.error(f"AI routing failed: {e}")
            agent = agents[0]
            return TaskRoutingDecision(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                confidence=0.5,
                reasoning=f"AI routing error: {e}",
                alternatives=None,  # type: ignore[call-arg]  # alternatives 有默認值
            )

    async def _ai_balance_load(
        self,
        task_description: Optional[str],
        agents: list,
        load_info: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        使用 AI 进行负载均衡

        Args:
            task_description: 任务描述
            agents: Agent 列表
            load_info: 负载信息
            context: 上下文信息

        Returns:
            负载均衡结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {"selected_agent_id": agents[0].agent_id if agents else None}

            prompt = f"""你是一个负载均衡专家。根据以下信息选择最合适的 Agent。

任务描述：{task_description or 'N/A'}

Agent 负载信息：
{json.dumps(load_info, ensure_ascii=False, indent=2)}

请返回负载均衡决策（JSON 格式）：
{{"selected_agent_id": "...", "reason": "..."}}"""

            response = await llm_client.generate(prompt, max_tokens=300)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {"selected_agent_id": agents[0].agent_id if agents else None}

        except Exception as e:
            self._logger.error(f"AI load balancing failed: {e}")
            return {"selected_agent_id": agents[0].agent_id if agents else None}

    async def _ai_coordinate_task(
        self, task_description: str, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        使用 AI 进行任务协调

        Args:
            task_description: 任务描述
            context: 上下文信息

        Returns:
            协调结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {"strategy": "sequential", "agents": []}

            prompt = f"""你是一个任务协调专家。分析以下任务，制定协调策略。

任务描述：{task_description}

请返回协调策略（JSON 格式）：
{{"strategy": "sequential|parallel|hierarchical", "agents": [...], "reason": "..."}}"""

            response = await llm_client.generate(prompt, max_tokens=500)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {"strategy": "sequential", "agents": []}

        except Exception as e:
            self._logger.error(f"AI coordination failed: {e}")
            return {"strategy": "sequential", "agents": []}

    async def _ai_analyze_orchestration(
        self, agents: list, base_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 AI 进行协调分析

        Args:
            agents: Agent 列表
            base_analysis: 基础分析结果

        Returns:
            AI 分析结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {}

            prompt = f"""你是一个系统架构专家。分析以下 Agent 协调系统的状态。

协调统计：
{json.dumps(base_analysis, ensure_ascii=False, indent=2)}

请返回分析结果（JSON 格式），包含 insights 和 recommendations。"""

            response = await llm_client.generate(prompt, max_tokens=1000)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {}

        except Exception as e:
            self._logger.error(f"AI analysis failed: {e}")
            return {}

    async def health_check(self) -> AgentServiceStatus:
        """
        健康检查

        Returns:
            服务状态
        """
        try:
            self._registry.list_agents()  # 檢查是否可用
            return AgentServiceStatus.AVAILABLE
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        获取服务能力

        Returns:
            服务能力描述
        """
        return {
            "name": "Orchestrator Manager Agent",
            "description": "AI 驱动的任务协调服务",
            "capabilities": [
                "task_routing",  # 任务路由
                "load_balancing",  # 负载均衡
                "task_coordination",  # 任务协调
                "orchestration_analysis",  # 协调分析
            ],
            "ai_enabled": True,
            "version": "1.0.0",
        }
