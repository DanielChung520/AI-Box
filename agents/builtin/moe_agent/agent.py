# 代碼功能說明: MoE Agent 實現
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""MoE Agent 實現 - LLM MoE (Mixture of Experts) 專屬服務 Agent"""

import logging
from typing import Any, AsyncGenerator, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.task_analyzer.models import TaskClassificationResult
from llm.moe.moe_manager import LLMMoEManager

from .models import MoEAgentRequest, MoEAgentResponse, RoutingMetrics

logger = logging.getLogger(__name__)


class MoEAgent(AgentServiceProtocol):
    """MoE Agent - LLM MoE (Mixture of Experts) 專屬服務 Agent

    提供統一的 LLM 調用接口，封裝 MoE Manager 的功能：
    - 文本生成（generate）
    - 對話生成（chat）
    - 流式對話生成（chat_stream）
    - 嵌入向量生成（embeddings）
    - 路由指標查詢（get_metrics）
    """

    def __init__(self, moe_manager: Optional[LLMMoEManager] = None):
        """
        初始化 MoE Agent

        Args:
            moe_manager: LLM MoE Manager 實例（可選，如果不提供則自動創建）
        """
        self._moe_manager = moe_manager or LLMMoEManager()
        self._logger = logger

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行 MoE 任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 解析請求數據
            task_data = request.task_data
            moe_request = MoEAgentRequest(**task_data)
            action = moe_request.action

            # 根據操作類型執行相應功能
            if action == "generate":
                result = await self._handle_generate(moe_request)
            elif action == "chat":
                result = await self._handle_chat(moe_request)
            elif action == "chat_stream":
                # 流式對話需要特殊處理，這裡返回錯誤提示
                result = MoEAgentResponse(
                    success=False,
                    action=action,
                    error="chat_stream is not supported in synchronous execute method. Use stream_chat() instead.",
                )
            elif action == "embeddings":
                result = await self._handle_embeddings(moe_request)
            elif action == "get_metrics":
                result = await self._handle_get_metrics()
            else:
                result = MoEAgentResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                )

            # 構建響應
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result=result.model_dump(),
                error=result.error,
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"MoE Agent execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def _handle_generate(self, request: MoEAgentRequest) -> MoEAgentResponse:
        """處理文本生成請求"""
        if not request.prompt:
            return MoEAgentResponse(
                success=False,
                action="generate",
                error="prompt is required for generate action",
            )

        try:
            # 轉換 task_classification
            task_classification = None
            if request.task_classification:
                task_classification = TaskClassificationResult(**request.task_classification)

            # 轉換 provider
            provider = None
            if request.provider:
                from agents.task_analyzer.models import LLMProvider

                try:
                    provider = LLMProvider(request.provider)
                except ValueError:
                    return MoEAgentResponse(
                        success=False,
                        action="generate",
                        error=f"Invalid provider: {request.provider}",
                    )

            # 調用 MoE Manager
            result = await self._moe_manager.generate(
                prompt=request.prompt,
                task_classification=task_classification,
                provider=provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                context=request.context,
            )

            return MoEAgentResponse(
                success=True,
                action="generate",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Generate failed: {e}")
            return MoEAgentResponse(
                success=False,
                action="generate",
                error=str(e),
            )

    async def _handle_chat(self, request: MoEAgentRequest) -> MoEAgentResponse:
        """處理對話生成請求"""
        if not request.messages:
            return MoEAgentResponse(
                success=False,
                action="chat",
                error="messages is required for chat action",
            )

        try:
            # 轉換 task_classification
            task_classification = None
            if request.task_classification:
                task_classification = TaskClassificationResult(**request.task_classification)

            # 轉換 provider
            provider = None
            if request.provider:
                from agents.task_analyzer.models import LLMProvider

                try:
                    provider = LLMProvider(request.provider)
                except ValueError:
                    return MoEAgentResponse(
                        success=False,
                        action="chat",
                        error=f"Invalid provider: {request.provider}",
                    )

            # 調用 MoE Manager
            result = await self._moe_manager.chat(
                messages=request.messages,
                task_classification=task_classification,
                provider=provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                context=request.context,
            )

            return MoEAgentResponse(
                success=True,
                action="chat",
                result=result,
            )

        except Exception as e:
            self._logger.error(f"Chat failed: {e}")
            return MoEAgentResponse(
                success=False,
                action="chat",
                error=str(e),
            )

    async def _handle_embeddings(self, request: MoEAgentRequest) -> MoEAgentResponse:
        """處理嵌入向量生成請求"""
        if not request.text:
            return MoEAgentResponse(
                success=False,
                action="embeddings",
                error="text is required for embeddings action",
            )

        try:
            # 轉換 provider
            provider = None
            if request.provider:
                from agents.task_analyzer.models import LLMProvider

                try:
                    provider = LLMProvider(request.provider)
                except ValueError:
                    return MoEAgentResponse(
                        success=False,
                        action="embeddings",
                        error=f"Invalid provider: {request.provider}",
                    )

            # 調用 MoE Manager
            result = await self._moe_manager.embeddings(
                text=request.text,
                provider=provider,
                model=request.model,
                context=request.context,
            )

            return MoEAgentResponse(
                success=True,
                action="embeddings",
                result={"embeddings": result},
            )

        except Exception as e:
            self._logger.error(f"Embeddings failed: {e}")
            return MoEAgentResponse(
                success=False,
                action="embeddings",
                error=str(e),
            )

    async def _handle_get_metrics(self) -> MoEAgentResponse:
        """處理路由指標查詢請求"""
        try:
            metrics = self._moe_manager.get_routing_metrics()
            routing_metrics = RoutingMetrics(**metrics)

            return MoEAgentResponse(
                success=True,
                action="get_metrics",
                result=routing_metrics.model_dump(),
            )

        except Exception as e:
            self._logger.error(f"Get metrics failed: {e}")
            return MoEAgentResponse(
                success=False,
                action="get_metrics",
                error=str(e),
            )

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查 MoE Manager 是否可用
            if self._moe_manager is None:
                return AgentServiceStatus.UNAVAILABLE

            # 嘗試獲取路由指標（簡單的健康檢查）
            try:
                self._moe_manager.get_routing_metrics()
                return AgentServiceStatus.AVAILABLE
            except Exception:
                return AgentServiceStatus.ERROR

        except Exception:
            return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "agent_id": "moe_agent",
            "agent_type": "dedicated_service",
            "name": "MoE Agent",
            "description": "LLM MoE (Mixture of Experts) 專屬服務 Agent，提供統一的 LLM 調用接口",
            "capabilities": [
                "generate",  # 文本生成
                "chat",  # 對話生成
                "chat_stream",  # 流式對話生成（需要特殊處理）
                "embeddings",  # 嵌入向量生成
                "get_metrics",  # 路由指標查詢
            ],
            "supported_providers": [
                "chatgpt",
                "gemini",
                "qwen",
                "ollama",
            ],
            "features": [
                "動態路由",
                "負載均衡",
                "故障轉移",
                "路由指標統計",
            ],
        }

    async def stream_chat(
        self,
        messages: list[Dict[str, Any]],
        task_classification: Optional[TaskClassificationResult] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式對話生成（特殊方法，用於流式響應）

        Args:
            messages: 消息列表
            task_classification: 任務分類結果（可選）
            provider: 指定的 LLM 提供商（可選）
            model: 模型名稱（可選）
            temperature: 溫度參數（可選）
            max_tokens: 最大 token 數（可選）
            context: 上下文信息（可選）

        Yields:
            內容塊（字符串）
        """
        # 轉換 provider
        llm_provider = None
        if provider:
            from agents.task_analyzer.models import LLMProvider

            try:
                llm_provider = LLMProvider(provider)
            except ValueError:
                self._logger.error(f"Invalid provider: {provider}")
                return

        # 調用 MoE Manager 的流式方法
        async for chunk in self._moe_manager.chat_stream(
            messages=messages,
            task_classification=task_classification,
            provider=llm_provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            context=context,
        ):
            yield chunk
