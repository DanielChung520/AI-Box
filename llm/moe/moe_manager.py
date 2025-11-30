# 代碼功能說明: LLM MoE 管理器實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""LLM MoE（Mixture of Experts）管理器，整合所有 LLM 客戶端和路由策略系統。"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider, TaskClassificationResult

from ..clients.factory import LLMClientFactory
from ..clients.base import BaseLLMClient
from ..routing.dynamic import DynamicRouter
from ..routing.evaluator import RoutingEvaluator
from ..load_balancer import MultiLLMLoadBalancer
from ..failover import LLMFailoverManager
from ..config import (
    get_load_balancer_strategy,
    get_load_balancer_weights,
    get_load_balancer_cooldown,
    get_load_balancer_providers,
    get_health_check_interval,
    get_health_check_timeout,
    get_health_check_failure_threshold,
)

logger = logging.getLogger(__name__)


class LLMMoEManager:
    """LLM MoE 管理器，提供統一的 LLM 調用接口。"""

    def __init__(
        self,
        dynamic_router: Optional[DynamicRouter] = None,
        evaluator: Optional[RoutingEvaluator] = None,
        enable_failover: bool = True,
        load_balancer: Optional[MultiLLMLoadBalancer] = None,
        failover_manager: Optional[LLMFailoverManager] = None,
    ):
        """
        初始化 LLM MoE 管理器。

        Args:
            dynamic_router: 動態路由器（可選，自動創建）
            evaluator: 路由評估器（可選，自動創建）
            enable_failover: 是否啟用故障轉移
            load_balancer: 負載均衡器（可選，自動創建）
            failover_manager: 故障轉移管理器（可選，自動創建）
        """
        self.dynamic_router = dynamic_router or DynamicRouter()
        self.evaluator = evaluator or RoutingEvaluator()
        self.enable_failover = enable_failover

        # 負載均衡器和故障轉移管理器
        if failover_manager is None and enable_failover:
            # 從配置文件創建故障轉移管理器
            self.failover_manager = LLMFailoverManager(
                health_check_interval=get_health_check_interval(),
                health_check_timeout=get_health_check_timeout(),
                failure_threshold=get_health_check_failure_threshold(),
            )
        else:
            self.failover_manager = failover_manager  # type: ignore[assignment]

        if load_balancer is None:
            # 從配置文件創建負載均衡器
            providers = get_load_balancer_providers()
            strategy = get_load_balancer_strategy()
            weights = get_load_balancer_weights()
            cooldown = get_load_balancer_cooldown()

            # 如果提供了故障轉移管理器，使用其健康檢查回調
            health_check_callback = None
            if self.failover_manager is not None:
                health_check_callback = self.failover_manager.is_provider_healthy

            self.load_balancer = MultiLLMLoadBalancer(
                providers=providers,
                strategy=strategy,
                weights=weights if weights else None,
                cooldown_seconds=cooldown,
                health_check_callback=health_check_callback,
            )
        else:
            self.load_balancer = load_balancer

        # 如果提供了故障轉移管理器，啟動健康檢查並整合到負載均衡器
        if self.failover_manager is not None and self.load_balancer is not None:
            # 啟動健康檢查循環
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循環正在運行，創建任務
                    asyncio.create_task(self.failover_manager.start())
                else:
                    # 否則直接啟動
                    loop.run_until_complete(self.failover_manager.start())
            except RuntimeError:
                # 沒有事件循環，稍後啟動
                pass

        # 客戶端緩存
        self._client_cache: Dict[LLMProvider, BaseLLMClient] = {}

    def get_client(self, provider: LLMProvider) -> BaseLLMClient:
        """
        獲取 LLM 客戶端實例。

        Args:
            provider: LLM 提供商

        Returns:
            LLM 客戶端實例
        """
        if provider not in self._client_cache:
            self._client_cache[provider] = LLMClientFactory.create_client(
                provider, use_cache=True
            )
        return self._client_cache[provider]

    async def generate(
        self,
        prompt: str,
        *,
        task_classification: Optional[TaskClassificationResult] = None,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成文本（統一接口）。

        Args:
            prompt: 輸入提示詞
            task_classification: 任務分類結果（用於路由選擇）
            provider: 指定的 LLM 提供商（可選，如果不指定則使用路由策略）
            model: 模型名稱（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            **kwargs: 其他參數

        Returns:
            生成結果字典
        """
        start_time = time.time()

        # 選擇 LLM 提供商
        if provider is None and task_classification is not None:
            # 優先使用負載均衡器選擇提供商（如果啟用）
            if self.load_balancer is not None:
                # 先從負載均衡器獲取候選提供商
                provider = self.load_balancer.select_provider()
                strategy_name = f"load_balancer_{self.load_balancer.strategy}"
            else:
                # 使用路由策略選擇提供商
                routing_result = self.dynamic_router.get_strategy().select_provider(
                    task_classification, prompt, context
                )
                provider = routing_result.provider
                strategy_name = routing_result.metadata.get("strategy", "unknown")
        else:
            provider = provider or LLMProvider.CHATGPT
            strategy_name = "manual"

        # 獲取客戶端
        client = self.get_client(provider)

        # 嘗試調用
        latency: Optional[float] = None

        try:
            result = await client.generate(
                prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            latency = time.time() - start_time

            # 記錄路由結果
            if task_classification is not None:
                self.evaluator.record_decision(
                    provider=provider,
                    strategy=strategy_name,
                    task_type=task_classification.task_type.value,
                    success=True,
                    latency=latency,
                )

            return result

        except Exception as exc:
            latency = time.time() - start_time
            logger.error(f"LLM generate error with {provider.value}: {exc}")

            # 標記負載均衡器失敗
            if self.load_balancer is not None:
                self.load_balancer.mark_failure(provider)

            # 記錄失敗
            if task_classification is not None:
                self.evaluator.record_decision(
                    provider=provider,
                    strategy=strategy_name,
                    task_type=task_classification.task_type.value,
                    success=False,
                    latency=latency,
                )

            # 故障轉移
            if self.enable_failover:
                return await self._failover_generate(
                    prompt,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    **kwargs,
                )

            raise

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        task_classification: Optional[TaskClassificationResult] = None,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        對話生成（統一接口）。

        Args:
            messages: 消息列表
            task_classification: 任務分類結果（用於路由選擇）
            provider: 指定的 LLM 提供商（可選）
            model: 模型名稱（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            **kwargs: 其他參數

        Returns:
            對話結果字典
        """
        start_time = time.time()

        # 選擇 LLM 提供商
        if provider is None and task_classification is not None:
            # 優先使用負載均衡器選擇提供商（如果啟用）
            if self.load_balancer is not None:
                # 先從負載均衡器獲取候選提供商
                provider = self.load_balancer.select_provider()
                strategy_name = f"load_balancer_{self.load_balancer.strategy}"
            else:
                # 使用路由策略選擇提供商
                # 從最後一條消息提取任務描述
                task_description = messages[-1].get("content", "") if messages else ""
                routing_result = self.dynamic_router.get_strategy().select_provider(
                    task_classification, task_description, context
                )
                provider = routing_result.provider
                strategy_name = routing_result.metadata.get("strategy", "unknown")
        else:
            provider = provider or LLMProvider.CHATGPT
            strategy_name = "manual"

        # 獲取客戶端
        client = self.get_client(provider)

        # 嘗試調用
        latency: Optional[float] = None

        try:
            result = await client.chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            latency = time.time() - start_time

            # 標記負載均衡器成功
            if self.load_balancer is not None:
                self.load_balancer.mark_success(provider, latency=latency)

            # 記錄路由結果
            if task_classification is not None:
                self.evaluator.record_decision(
                    provider=provider,
                    strategy=strategy_name,
                    task_type=task_classification.task_type.value,
                    success=True,
                    latency=latency,
                )

            return result

        except Exception as exc:
            latency = time.time() - start_time
            logger.error(f"LLM chat error with {provider.value}: {exc}")

            # 標記負載均衡器失敗
            if self.load_balancer is not None:
                self.load_balancer.mark_failure(provider)

            # 記錄失敗
            if task_classification is not None:
                self.evaluator.record_decision(
                    provider=provider,
                    strategy=strategy_name,
                    task_type=task_classification.task_type.value,
                    success=False,
                    latency=latency,
                )

            # 故障轉移
            if self.enable_failover:
                return await self._failover_chat(
                    messages,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    **kwargs,
                )

            raise

    async def embeddings(
        self,
        text: str,
        *,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[float]:
        """
        生成文本嵌入向量（統一接口）。

        Args:
            text: 輸入文本
            provider: 指定的 LLM 提供商（可選，默認使用 ChatGPT）
            model: 嵌入模型名稱（可選）
            **kwargs: 其他參數

        Returns:
            嵌入向量列表
        """
        provider = provider or LLMProvider.CHATGPT
        client = self.get_client(provider)

        try:
            return await client.embeddings(text, model=model, **kwargs)
        except Exception as exc:
            logger.error(f"LLM embeddings error with {provider.value}: {exc}")

            # 故障轉移到其他支持 embeddings 的提供商
            if self.enable_failover:
                fallback_providers = [
                    LLMProvider.GEMINI,
                    LLMProvider.QWEN,
                    LLMProvider.CHATGPT,
                ]
                for fallback in fallback_providers:
                    if fallback == provider:
                        continue
                    try:
                        fallback_client = self.get_client(fallback)
                        if fallback_client.is_available():
                            return await fallback_client.embeddings(
                                text, model=model, **kwargs
                            )
                    except Exception:
                        continue

            raise

    async def _failover_generate(
        self,
        prompt: str,
        failed_provider: LLMProvider,
        task_classification: Optional[TaskClassificationResult] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        故障轉移生成（嘗試備用提供商）。

        Args:
            prompt: 輸入提示詞
            failed_provider: 失敗的提供商
            task_classification: 任務分類結果
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            **kwargs: 其他參數

        Returns:
            生成結果字典

        Raises:
            Exception: 如果所有提供商都失敗
        """
        # 定義備用提供商順序（優先級從高到低）
        fallback_providers = [
            LLMProvider.GEMINI,
            LLMProvider.QWEN,
            LLMProvider.CHATGPT,
            LLMProvider.OLLAMA,
        ]

        # 移除失敗的提供商
        if failed_provider in fallback_providers:
            fallback_providers.remove(failed_provider)

        # 如果啟用了故障轉移管理器，優先選擇健康的提供商
        if self.failover_manager is not None:
            healthy_providers = self.failover_manager.get_healthy_providers(
                fallback_providers
            )
            if healthy_providers:
                # 優先使用健康的提供商
                fallback_providers = healthy_providers + [
                    p for p in fallback_providers if p not in healthy_providers
                ]

        last_exception: Optional[Exception] = None

        # 嘗試備用提供商
        for fallback in fallback_providers:
            try:
                logger.info(
                    f"Failing over from {failed_provider.value} to {fallback.value}"
                )
                client = self.get_client(fallback)

                if not client.is_available():
                    logger.debug(f"Provider {fallback.value} is not available")
                    continue

                # 檢查健康狀態（如果啟用了故障轉移管理器）
                if (
                    self.failover_manager is not None
                    and not self.failover_manager.is_provider_healthy(fallback)
                ):
                    logger.debug(f"Provider {fallback.value} is not healthy, skipping")
                    continue

                result = await client.generate(
                    prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                logger.info(
                    f"Successfully failed over from {failed_provider.value} "
                    f"to {fallback.value}"
                )

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(fallback)

                return result

            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"Fallback to {fallback.value} failed: {exc}",
                    exc_info=True,
                )

                # 標記負載均衡器失敗（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_failure(fallback)

                continue

        # 所有提供商都失敗
        error_msg = (
            f"All LLM providers failed. " f"Original provider: {failed_provider.value}"
        )
        if last_exception:
            error_msg += f". Last error: {last_exception}"
        raise Exception(error_msg)

    async def _failover_chat(
        self,
        messages: List[Dict[str, Any]],
        failed_provider: LLMProvider,
        task_classification: Optional[TaskClassificationResult] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        故障轉移對話（嘗試備用提供商）。

        Args:
            messages: 消息列表
            failed_provider: 失敗的提供商
            task_classification: 任務分類結果
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            **kwargs: 其他參數

        Returns:
            對話結果字典

        Raises:
            Exception: 如果所有提供商都失敗
        """
        # 定義備用提供商順序（優先級從高到低）
        fallback_providers = [
            LLMProvider.GEMINI,
            LLMProvider.QWEN,
            LLMProvider.CHATGPT,
            LLMProvider.OLLAMA,
        ]

        # 移除失敗的提供商
        if failed_provider in fallback_providers:
            fallback_providers.remove(failed_provider)

        # 如果啟用了故障轉移管理器，優先選擇健康的提供商
        if self.failover_manager is not None:
            healthy_providers = self.failover_manager.get_healthy_providers(
                fallback_providers
            )
            if healthy_providers:
                # 優先使用健康的提供商
                fallback_providers = healthy_providers + [
                    p for p in fallback_providers if p not in healthy_providers
                ]

        last_exception: Optional[Exception] = None

        # 嘗試備用提供商
        for fallback in fallback_providers:
            try:
                logger.info(
                    f"Failing over from {failed_provider.value} to {fallback.value}"
                )
                client = self.get_client(fallback)

                if not client.is_available():
                    logger.debug(f"Provider {fallback.value} is not available")
                    continue

                # 檢查健康狀態（如果啟用了故障轉移管理器）
                if (
                    self.failover_manager is not None
                    and not self.failover_manager.is_provider_healthy(fallback)
                ):
                    logger.debug(f"Provider {fallback.value} is not healthy, skipping")
                    continue

                result = await client.chat(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

                logger.info(
                    f"Successfully failed over from {failed_provider.value} "
                    f"to {fallback.value}"
                )

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(fallback)

                return result

            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"Fallback to {fallback.value} failed: {exc}",
                    exc_info=True,
                )

                # 標記負載均衡器失敗（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_failure(fallback)

                continue

        # 所有提供商都失敗
        error_msg = (
            f"All LLM providers failed. " f"Original provider: {failed_provider.value}"
        )
        if last_exception:
            error_msg += f". Last error: {last_exception}"
        raise Exception(error_msg)

    def get_routing_metrics(self) -> Dict[str, Any]:
        """
        獲取路由指標。

        Returns:
            路由指標字典
        """
        metrics: Dict[str, Any] = {
            "provider_metrics": self.evaluator.get_provider_metrics(),
            "strategy_metrics": self.evaluator.get_strategy_metrics(),
            "recommendations": self.evaluator.get_recommendations(),
        }

        # 添加負載均衡器統計信息
        if self.load_balancer is not None:
            metrics["load_balancer"] = {
                "provider_stats": self.load_balancer.get_provider_stats(),
                "overall_stats": self.load_balancer.get_overall_stats(),
            }

        # 添加健康檢查狀態
        if self.failover_manager is not None:
            metrics[
                "health_status"
            ] = self.failover_manager.get_provider_health_status()

        return metrics
