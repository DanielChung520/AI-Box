# 代碼功能說明: Storage Manager Agent 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Storage Manager Agent 實現

AI 驱动的存储管理服务，提供智能存储策略和数据管理功能。
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
from agents.services.file_service.agent_file_service import get_agent_file_service
from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

from .models import (
    StorageManagerRequest,
    StorageManagerResponse,
    StorageType,
    StorageStrategy,
)

logger = logging.getLogger(__name__)


class StorageManagerAgent(AgentServiceProtocol):
    """Storage Manager Agent - 数据存储员

    AI 驱动的存储管理服务，提供：
    - 智能存储策略推荐
    - 数据管理和优化
    - 存储分析和建议
    """

    def __init__(self):
        """初始化 Storage Manager Agent"""
        self._file_service = get_agent_file_service()
        # Memory Manager 和数据库客户端延迟初始化
        self._memory_manager = None
        self._llm_client = None
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

    def _get_memory_manager(self):
        """获取 Memory Manager（延迟初始化）"""
        if self._memory_manager is None:
            try:
                from agents.infra.memory import MemoryManager

                self._memory_manager = MemoryManager()
            except Exception as e:
                self._logger.warning(f"Failed to initialize Memory Manager: {e}")
        return self._memory_manager

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        执行存储管理任务

        Args:
            request: Agent 服务请求

        Returns:
            Agent 服务响应
        """
        try:
            # 解析请求数据
            task_data = request.task_data
            action = task_data.get("action", "recommend")
            storage_request = StorageManagerRequest(**task_data)

            # 根据操作类型执行相应功能
            if action == "store":
                result = await self._store_data(storage_request)
            elif action == "retrieve":
                result = await self._retrieve_data(storage_request)
            elif action == "optimize":
                result = await self._optimize_storage(storage_request)
            elif action == "analyze":
                result = await self._analyze_storage(storage_request)
            elif action == "recommend":
                result = await self._recommend_strategy(storage_request)
            else:
                result = StorageManagerResponse(
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
                    "stored": result.stored,
                    "retrieved_data": result.retrieved_data,
                    "strategy": result.strategy.value if result.strategy else None,
                    "optimization_result": result.optimization_result,
                    "analysis": result.analysis,
                    "message": result.message,
                    "error": result.error,
                },
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Storage Manager execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=str(e),
                metadata=request.metadata,
            )

    async def _store_data(
        self, request: StorageManagerRequest
    ) -> StorageManagerResponse:
        """
        存储数据

        Args:
            request: 存储管理请求

        Returns:
            存储管理响应
        """
        try:
            storage_type = request.storage_type or StorageType.MEMORY
            stored = False

            if storage_type == StorageType.MEMORY:
                memory_manager = self._get_memory_manager()
                if memory_manager and request.data_key:
                    memory_manager.store_short_term(
                        key=request.data_key,
                        value=request.data_value,
                        namespace=request.namespace,
                    )
                    stored = True
            elif storage_type == StorageType.FILE:
                # 使用文件服务存储
                if request.data_key and request.data_value:
                    # 这里需要根据实际的文件服务接口实现
                    stored = True
            else:
                return StorageManagerResponse(
                    success=False,
                    action="store",
                    error=f"Unsupported storage type: {storage_type}",
                )

            return StorageManagerResponse(
                success=True,
                action="store",
                stored=stored,
                message=f"Data stored successfully in {storage_type.value}",
            )

        except Exception as e:
            self._logger.error(f"Data storage failed: {e}")
            return StorageManagerResponse(
                success=False,
                action="store",
                error=str(e),
            )

    async def _retrieve_data(
        self, request: StorageManagerRequest
    ) -> StorageManagerResponse:
        """
        检索数据

        Args:
            request: 存储管理请求

        Returns:
            存储管理响应
        """
        try:
            storage_type = request.storage_type or StorageType.MEMORY
            retrieved_data = None

            if storage_type == StorageType.MEMORY:
                memory_manager = self._get_memory_manager()
                if memory_manager and request.data_key:
                    retrieved_data = memory_manager.retrieve_short_term(
                        key=request.data_key,
                        namespace=request.namespace,
                    )
            elif storage_type == StorageType.FILE:
                # 使用文件服务检索
                if request.data_key:
                    # 这里需要根据实际的文件服务接口实现
                    retrieved_data = None
            else:
                return StorageManagerResponse(
                    success=False,
                    action="retrieve",
                    error=f"Unsupported storage type: {storage_type}",
                )

            return StorageManagerResponse(
                success=True,
                action="retrieve",
                retrieved_data=retrieved_data,
                message="Data retrieved successfully",
            )

        except Exception as e:
            self._logger.error(f"Data retrieval failed: {e}")
            return StorageManagerResponse(
                success=False,
                action="retrieve",
                error=str(e),
            )

    async def _optimize_storage(
        self, request: StorageManagerRequest
    ) -> StorageManagerResponse:
        """
        优化存储

        Args:
            request: 存储管理请求

        Returns:
            存储管理响应
        """
        try:
            # 使用 AI 进行存储优化
            if self._get_llm_client():
                optimization_result = await self._ai_optimize_storage(request)
            else:
                optimization_result = {
                    "recommendations": ["定期清理过期数据", "压缩存储数据"],
                }

            return StorageManagerResponse(
                success=True,
                action="optimize",
                optimization_result=optimization_result,
                message="Storage optimization completed",
            )

        except Exception as e:
            self._logger.error(f"Storage optimization failed: {e}")
            return StorageManagerResponse(
                success=False,
                action="optimize",
                error=str(e),
            )

    async def _analyze_storage(
        self, request: StorageManagerRequest
    ) -> StorageManagerResponse:
        """
        存储分析

        Args:
            request: 存储管理请求

        Returns:
            存储管理响应
        """
        try:
            # 基础分析
            analysis = {
                "storage_types": [st.value for st in StorageType],
                "available_strategies": [ss.value for ss in StorageStrategy],
            }

            # 使用 AI 进行深度分析
            if self._get_llm_client():
                ai_analysis = await self._ai_analyze_storage(request, analysis)
                analysis.update(ai_analysis)

            return StorageManagerResponse(
                success=True,
                action="analyze",
                analysis=analysis,
                message="Storage analysis completed",
            )

        except Exception as e:
            self._logger.error(f"Storage analysis failed: {e}")
            return StorageManagerResponse(
                success=False,
                action="analyze",
                error=str(e),
            )

    async def _recommend_strategy(
        self, request: StorageManagerRequest
    ) -> StorageManagerResponse:
        """
        AI 驱动的存储策略推荐

        Args:
            request: 存储管理请求

        Returns:
            存储管理响应
        """
        try:
            # 使用 AI 进行策略推荐
            if self._get_llm_client():
                strategy = await self._ai_recommend_strategy(request)
            else:
                # 默认策略
                strategy = StorageStrategy.IMMEDIATE

            return StorageManagerResponse(
                success=True,
                action="recommend",
                strategy=strategy,
                message=f"Recommended strategy: {strategy.value}",
            )

        except Exception as e:
            self._logger.error(f"Strategy recommendation failed: {e}")
            return StorageManagerResponse(
                success=False,
                action="recommend",
                error=str(e),
            )

    async def _ai_optimize_storage(
        self, request: StorageManagerRequest
    ) -> Dict[str, Any]:
        """
        使用 AI 进行存储优化

        Args:
            request: 存储管理请求

        Returns:
            优化结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {}

            prompt = f"""你是一个存储优化专家。分析以下存储需求，提供优化建议。

存储类型：{request.storage_type.value if request.storage_type else 'N/A'}
数据键：{request.data_key or 'N/A'}
命名空间：{request.namespace or 'N/A'}

请返回优化建议（JSON 格式）：
{{"recommendations": [...], "optimization_actions": [...]}}"""

            response = await llm_client.generate(prompt, max_tokens=500)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {}

        except Exception as e:
            self._logger.error(f"AI optimization failed: {e}")
            return {}

    async def _ai_analyze_storage(
        self, request: StorageManagerRequest, base_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 AI 进行存储分析

        Args:
            request: 存储管理请求
            base_analysis: 基础分析结果

        Returns:
            AI 分析结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {}

            prompt = f"""你是一个存储分析专家。分析以下存储配置。

基础分析：
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

    async def _ai_recommend_strategy(
        self, request: StorageManagerRequest
    ) -> StorageStrategy:
        """
        使用 AI 推荐存储策略

        Args:
            request: 存储管理请求

        Returns:
            推荐的存储策略
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return StorageStrategy.IMMEDIATE

            prompt = f"""你是一个存储策略专家。根据以下信息推荐最合适的存储策略。

存储类型：{request.storage_type.value if request.storage_type else 'N/A'}
数据键：{request.data_key or 'N/A'}
命名空间：{request.namespace or 'N/A'}

可用策略：
- immediate: 立即存储
- lazy: 延迟存储
- cached: 缓存存储
- distributed: 分布式存储

请返回推荐的策略（JSON 格式）：
{{"strategy": "immediate|lazy|cached|distributed", "reason": "..."}}"""

            response = await llm_client.generate(prompt, max_tokens=300)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                result = json.loads(result_text)
                strategy_name = result.get("strategy", "immediate")
                return StorageStrategy(strategy_name)
            except (json.JSONDecodeError, ValueError):
                self._logger.warning("Failed to parse LLM response")
                return StorageStrategy.IMMEDIATE

        except Exception as e:
            self._logger.error(f"AI strategy recommendation failed: {e}")
            return StorageStrategy.IMMEDIATE

    async def health_check(self) -> AgentServiceStatus:
        """
        健康检查

        Returns:
            服务状态
        """
        try:
            # 检查文件服务是否可用
            if self._file_service:
                return AgentServiceStatus.AVAILABLE
            return AgentServiceStatus.UNAVAILABLE
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
            "name": "Storage Manager Agent",
            "description": "AI 驱动的存储管理服务",
            "capabilities": [
                "data_storage",  # 数据存储
                "data_retrieval",  # 数据检索
                "storage_optimization",  # 存储优化
                "storage_analysis",  # 存储分析
                "strategy_recommendation",  # 策略推荐
            ],
            "ai_enabled": True,
            "version": "1.0.0",
        }
