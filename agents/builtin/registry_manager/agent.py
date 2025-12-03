# 代碼功能說明: Registry Manager Agent 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Registry Manager Agent 實現

AI 驱动的 Agent 注册管理服务，提供智能匹配、发现和推荐功能。
"""

import logging
import json
from typing import Dict, Any, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.discovery import AgentDiscovery
from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

from .models import RegistryManagerRequest, RegistryManagerResponse

logger = logging.getLogger(__name__)


class RegistryManagerAgent(AgentServiceProtocol):
    """Registry Manager Agent - 注册管理员

    AI 驱动的 Agent 注册管理服务，提供：
    - 智能 Agent 匹配
    - Agent 发现和推荐
    - 注册分析和优化建议
    """

    def __init__(self):
        """初始化 Registry Manager Agent"""
        self._registry = get_agent_registry()
        self._discovery = AgentDiscovery(self._registry)
        self._llm_client = None  # 延迟初始化
        self._logger = logger

    def _get_llm_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self._llm_client is None:
            try:
                # 优先使用 Ollama（本地）
                self._llm_client = get_client(LLMProvider.OLLAMA)
            except Exception as e:
                self._logger.warning(f"Failed to initialize Ollama client: {e}")
                # 如果 Ollama 不可用，尝试其他 Provider
                try:
                    self._llm_client = get_client(LLMProvider.QWEN)
                except Exception:
                    self._logger.error("No LLM client available")
        return self._llm_client

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        执行注册管理任务

        Args:
            request: Agent 服务请求

        Returns:
            Agent 服务响应
        """
        try:
            # 解析请求数据
            task_data = request.task_data
            action = task_data.get("action", "discover")
            registry_request = RegistryManagerRequest(**task_data)

            # 根据操作类型执行相应功能
            if action == "match":
                result = await self._match_agents(registry_request)
            elif action == "discover":
                result = await self._discover_agents(registry_request)
            elif action == "recommend":
                result = await self._recommend_agents(registry_request)
            elif action == "analyze":
                result = await self._analyze_registry(registry_request)
            else:
                result = RegistryManagerResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                )

            # 构建响应
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result={
                    "success": result.success,
                    "action": result.action,
                    "agents": (
                        [agent.model_dump() for agent in result.agents]
                        if result.agents
                        else None
                    ),
                    "recommendations": result.recommendations,
                    "analysis": result.analysis,
                    "message": result.message,
                    "error": result.error,
                },
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Registry Manager execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=str(e),
                metadata=request.metadata,
            )

    async def _match_agents(
        self, request: RegistryManagerRequest
    ) -> RegistryManagerResponse:
        """
        AI 驱动的 Agent 匹配

        Args:
            request: 注册管理请求

        Returns:
            注册管理响应
        """
        try:
            # 基础发现
            agents = self._discovery.discover_agents(
                required_capabilities=request.required_capabilities,
                agent_type=request.agent_type,
                category=request.category,
            )

            # 如果有任务描述，使用 AI 进行智能匹配
            if request.task_description and self._get_llm_client():
                agents = await self._ai_match_agents(
                    request.task_description, agents, request.context
                )

            return RegistryManagerResponse(
                success=True,
                action="match",
                agents=agents,
                message=f"Found {len(agents)} matching agents",
            )

        except Exception as e:
            self._logger.error(f"Agent matching failed: {e}")
            return RegistryManagerResponse(
                success=False,
                action="match",
                error=str(e),
            )

    async def _discover_agents(
        self, request: RegistryManagerRequest
    ) -> RegistryManagerResponse:
        """
        发现可用的 Agent

        Args:
            request: 注册管理请求

        Returns:
            注册管理响应
        """
        try:
            agents = self._discovery.discover_agents(
                required_capabilities=request.required_capabilities,
                agent_type=request.agent_type,
                category=request.category,
            )

            return RegistryManagerResponse(
                success=True,
                action="discover",
                agents=agents,
                message=f"Discovered {len(agents)} agents",
            )

        except Exception as e:
            self._logger.error(f"Agent discovery failed: {e}")
            return RegistryManagerResponse(
                success=False,
                action="discover",
                error=str(e),
            )

    async def _recommend_agents(
        self, request: RegistryManagerRequest
    ) -> RegistryManagerResponse:
        """
        AI 驱动的 Agent 推荐

        Args:
            request: 注册管理请求

        Returns:
            注册管理响应
        """
        try:
            # 基础发现
            agents = self._discovery.discover_agents(
                required_capabilities=request.required_capabilities,
                agent_type=request.agent_type,
                category=request.category,
            )

            # 使用 AI 进行推荐
            recommendations = []
            if request.task_description and self._get_llm_client():
                recommendations = await self._ai_recommend_agents(
                    request.task_description, agents, request.context
                )
            else:
                # 如果没有 LLM，返回基础推荐（按注册时间排序）
                recommendations = [
                    {
                        "agent_id": agent.agent_id,
                        "name": agent.name,
                        "reason": "Recently registered",
                        "score": 0.5,
                    }
                    for agent in agents[:5]
                ]

            return RegistryManagerResponse(
                success=True,
                action="recommend",
                agents=agents,
                recommendations=recommendations,
                message=f"Generated {len(recommendations)} recommendations",
            )

        except Exception as e:
            self._logger.error(f"Agent recommendation failed: {e}")
            return RegistryManagerResponse(
                success=False,
                action="recommend",
                error=str(e),
            )

    async def _analyze_registry(
        self, request: RegistryManagerRequest
    ) -> RegistryManagerResponse:
        """
        分析注册表状态

        Args:
            request: 注册管理请求

        Returns:
            注册管理响应
        """
        try:
            all_agents = self._registry.list_agents()

            # 基础统计
            analysis: Dict[str, Any] = {
                "total_agents": len(all_agents),
                "by_type": {},
                "by_status": {},
                "internal_count": 0,
                "external_count": 0,
            }

            for agent in all_agents:
                # 按类型统计
                agent_type = agent.agent_type
                analysis["by_type"][agent_type] = (
                    analysis["by_type"].get(agent_type, 0) + 1
                )

                # 按状态统计
                status = agent.status.value
                analysis["by_status"][status] = analysis["by_status"].get(status, 0) + 1

                # 内部/外部统计
                if agent.endpoints.is_internal:
                    analysis["internal_count"] += 1
                else:
                    analysis["external_count"] += 1

            # 如果有 LLM，进行 AI 分析
            if self._get_llm_client():
                ai_analysis = await self._ai_analyze_registry(all_agents, analysis)
                analysis.update(ai_analysis)

            return RegistryManagerResponse(
                success=True,
                action="analyze",
                analysis=analysis,
                message="Registry analysis completed",
            )

        except Exception as e:
            self._logger.error(f"Registry analysis failed: {e}")
            return RegistryManagerResponse(
                success=False,
                action="analyze",
                error=str(e),
            )

    async def _ai_match_agents(
        self, task_description: str, agents: list, context: Optional[Dict[str, Any]]
    ) -> list:
        """
        使用 AI 进行智能 Agent 匹配

        Args:
            task_description: 任务描述
            agents: Agent 列表
            context: 上下文信息

        Returns:
            匹配的 Agent 列表
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return agents

            # 构建提示词
            agent_summaries = [
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "type": agent.agent_type,
                    "capabilities": agent.capabilities,
                    "description": agent.metadata.description or "",
                }
                for agent in agents
            ]

            prompt = f"""你是一个 Agent 匹配专家。根据任务描述，从以下 Agent 列表中选择最匹配的 Agent。

任务描述：{task_description}

可用 Agent：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请返回匹配的 Agent ID 列表（JSON 格式），按匹配度排序：
{{"matched_agent_ids": ["agent_id1", "agent_id2", ...]}}"""

            # 调用 LLM
            response = await llm_client.generate(prompt, max_tokens=500)
            result_text = response.get("text", "") or response.get("content", "")

            # 解析结果
            try:
                result = json.loads(result_text)
                matched_ids = result.get("matched_agent_ids", [])
                # 按匹配顺序排序
                agent_dict = {agent.agent_id: agent for agent in agents}
                matched_agents = [
                    agent_dict[agent_id]
                    for agent_id in matched_ids
                    if agent_id in agent_dict
                ]
                # 添加未匹配的 Agent
                matched_agents.extend(
                    [agent for agent in agents if agent.agent_id not in matched_ids]
                )
                return matched_agents
            except json.JSONDecodeError:
                self._logger.warning(
                    "Failed to parse LLM response, returning original list"
                )
                return agents

        except Exception as e:
            self._logger.error(f"AI matching failed: {e}")
            return agents

    async def _ai_recommend_agents(
        self, task_description: str, agents: list, context: Optional[Dict[str, Any]]
    ) -> list:
        """
        使用 AI 进行 Agent 推荐

        Args:
            task_description: 任务描述
            agents: Agent 列表
            context: 上下文信息

        Returns:
            推荐结果列表
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return []

            # 构建提示词
            agent_summaries = [
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "type": agent.agent_type,
                    "capabilities": agent.capabilities,
                    "description": agent.metadata.description or "",
                }
                for agent in agents
            ]

            prompt = f"""你是一个 Agent 推荐专家。根据任务描述，从以下 Agent 列表中选择最合适的 Agent 并给出推荐理由。

任务描述：{task_description}

可用 Agent：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请返回推荐结果（JSON 格式），包含 agent_id、reason（推荐理由）、score（推荐分数 0-1）：
{{"recommendations": [{{"agent_id": "...", "reason": "...", "score": 0.9}}, ...]}}"""

            # 调用 LLM
            response = await llm_client.generate(prompt, max_tokens=1000)
            result_text = response.get("text", "") or response.get("content", "")

            # 解析结果
            try:
                result = json.loads(result_text)
                return result.get("recommendations", [])
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return []

        except Exception as e:
            self._logger.error(f"AI recommendation failed: {e}")
            return []

    async def _ai_analyze_registry(
        self, agents: list, base_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 AI 分析注册表

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

            prompt = f"""你是一个系统架构专家。分析以下 Agent 注册表的状态，提供优化建议。

注册表统计：
{json.dumps(base_analysis, ensure_ascii=False, indent=2)}

请返回分析结果（JSON 格式），包含：
- insights: 洞察和建议
- recommendations: 优化建议列表
- warnings: 警告信息列表

{{"insights": "...", "recommendations": [...], "warnings": [...]}}"""

            # 调用 LLM
            response = await llm_client.generate(prompt, max_tokens=1000)
            result_text = response.get("text", "") or response.get("content", "")

            # 解析结果
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
            # 检查 Registry 是否可用
            agents = self._registry.list_agents()
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
            "name": "Registry Manager Agent",
            "description": "AI 驱动的 Agent 注册管理服务",
            "capabilities": [
                "agent_matching",  # Agent 匹配
                "agent_discovery",  # Agent 发现
                "agent_recommendation",  # Agent 推荐
                "registry_analysis",  # 注册表分析
            ],
            "ai_enabled": True,
            "version": "1.0.0",
        }
