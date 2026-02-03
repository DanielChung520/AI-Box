# 代碼功能說明: LLM MoE 管理器實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""LLM MoE（Mixture of Experts）管理器，整合所有 LLM 客戶端和路由策略系統。"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from agents.task_analyzer.models import LLMProvider, TaskClassificationResult

from ..clients.base import BaseLLMClient
from ..clients.factory import LLMClientFactory
from ..config import (
    get_health_check_failure_threshold,
    get_health_check_interval,
    get_health_check_timeout,
    get_load_balancer_cooldown,
    get_load_balancer_providers,
    get_load_balancer_strategy,
    get_load_balancer_weights,
)
from ..failover import LLMFailoverManager
from ..load_balancer import MultiLLMLoadBalancer
from ..routing.dynamic import DynamicRouter
from ..routing.evaluator import RoutingEvaluator
from .scene_routing import ModelSelectionResult, MoEConfigLoader, get_moe_config_loader
from .user_preference import get_user_preference

logger = structlog.get_logger(__name__)


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

    def select_model(
        self,
        scene: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ModelSelectionResult:
        """
        根據場景選擇模型

        Args:
            scene: 場景名稱（如 "chat", "knowledge_graph_extraction", "embedding" 等）
            user_id: 用戶 ID（用於用戶偏好）
            context: 上下文信息

        Returns:
            ModelSelectionResult: 模型選擇結果
        """
        loader = get_moe_config_loader()

        # 1. 嘗試從環境變量獲取模型
        env_model = loader.get_model_from_env(scene)
        if env_model:
            logger.info(f"Using model from environment for scene {scene}: {env_model}")
            return ModelSelectionResult(
                model=env_model,
                scene=scene,
                context_size=131072,
                max_tokens=4096,
                temperature=0.7,
                timeout=90,
                retries=3,
                rpm=30,
                concurrency=5,
                dimension=None,
                cost_per_1k_input=None,
                cost_per_1k_output=None,
                is_user_preference=False,
                fallback_used=False,
                original_model=env_model,
            )

        # 2. 檢查用戶偏好
        if user_id and loader.is_user_preference_enabled():
            user_pref = self._get_user_preference(user_id, scene)
            if user_pref:
                logger.info(f"Using user preference for scene {scene}, user {user_id}: {user_pref}")
                # 驗證用戶偏好的模型是否在優先級列表中
                priority_list = loader.get_priority_list(scene)
                if any(p.model == user_pref for p in priority_list):
                    # 找到用戶偏好模型的配置
                    for p in priority_list:
                        if p.model == user_pref:
                            return ModelSelectionResult(
                                model=user_pref,
                                scene=scene,
                                context_size=p.context_size,
                                max_tokens=p.max_tokens,
                                temperature=p.temperature,
                                timeout=p.timeout,
                                retries=p.retries,
                                rpm=p.rpm,
                                concurrency=p.concurrency,
                                dimension=p.dimension,
                                cost_per_1k_input=p.cost_per_1k_input,
                                cost_per_1k_output=p.cost_per_1k_output,
                                is_user_preference=True,
                                fallback_used=False,
                                original_model=user_pref,
                            )

        # 3. 從優先級列表選擇模型
        priority_list = loader.get_priority_list(scene)
        if priority_list:
            selected = priority_list[0]  # 選擇第一個（最高優先級）
            logger.info(f"Using default model for scene {scene}: {selected.model}")
            return ModelSelectionResult(
                model=selected.model,
                scene=scene,
                context_size=selected.context_size,
                max_tokens=selected.max_tokens,
                temperature=selected.temperature,
                timeout=selected.timeout,
                retries=selected.retries,
                rpm=selected.rpm,
                concurrency=selected.concurrency,
                dimension=selected.dimension,
                cost_per_1k_input=selected.cost_per_1k_input,
                cost_per_1k_output=selected.cost_per_1k_output,
                is_user_preference=False,
                fallback_used=False,
                original_model=selected.model,
            )

        # 4. 如果沒有配置，返回 None
        logger.warning(f"No model configuration found for scene {scene}")
        return None

    def _get_user_preference(self, user_id: str, scene: str) -> Optional[str]:
        """獲取用戶偏好"""
        return get_user_preference(user_id, scene)

    def get_available_scenes(self) -> List[str]:
        """獲取所有可用的場景"""
        loader = get_moe_config_loader()
        return loader.get_all_scenes()

    def get_scene_config(self, scene: str):
        """獲取場景配置"""
        loader = get_moe_config_loader()
        return loader.get_scene_config(scene)

    def get_client(self, provider: LLMProvider, *, api_key: Optional[str] = None) -> BaseLLMClient:
        """
        獲取 LLM 客戶端實例。

        Args:
            provider: LLM 提供商

        Returns:
            LLM 客戶端實例
        """
        if api_key is not None and str(api_key).strip():
            # per-request/per-user key：不可使用全域 cache
            return LLMClientFactory.create_client(
                provider, use_cache=False, api_key=str(api_key).strip()
            )

        if provider not in self._client_cache:
            self._client_cache[provider] = LLMClientFactory.create_client(provider, use_cache=True)
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
                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    allowed = [
                        p for p in self.load_balancer.get_providers() if p.value in allowed_set
                    ]
                    provider = self.load_balancer.select_provider_filtered(allowed)
                    strategy_name = f"load_balancer_{self.load_balancer.strategy}_policy"
                else:
                    provider = self.load_balancer.select_provider()
                    strategy_name = f"load_balancer_{self.load_balancer.strategy}"
            else:
                # 使用路由策略選擇提供商
                routing_result = self.dynamic_router.get_strategy().select_provider(
                    task_classification, prompt, context
                )
                provider = routing_result.provider
                strategy_name = routing_result.metadata.get("strategy", "unknown")

                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    if provider.value not in allowed_set:
                        fallback = next(
                            (p for p in LLMProvider if p.value in allowed_set),
                            None,
                        )
                        if fallback is not None:
                            provider = fallback
                            strategy_name = f"{strategy_name}_policy_fallback"
        else:
            provider = provider or LLMProvider.CHATGPT
            strategy_name = "manual"

        # 獲取客戶端
        api_key: Optional[str] = None
        if isinstance(context, dict):
            keys = context.get("llm_api_keys")
            if isinstance(keys, dict):
                api_key = keys.get(getattr(provider, "value", str(provider)))

        # 獲取客戶端（捕獲初始化異常，如缺少 SDK 或 API key）
        try:
            client = self.get_client(provider, api_key=api_key)
        except (ImportError, ValueError) as client_init_error:
            # 客戶端初始化失敗（如缺少 SDK 或 API key），直接觸發 fallback
            logger.warning(
                f"Client initialization failed for {provider.value}: {client_init_error}. "
                "Triggering failover immediately."
            )
            # 記錄失敗並觸發 fallover
            if self.enable_failover:
                return await self._failover_generate(
                    prompt,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    failed_strategy=strategy_name,
                    **kwargs,
                )
            # 如果未啟用 failover，直接拋出異常
            raise Exception(
                f"Client initialization failed for {provider.value}: {client_init_error}"
            ) from client_init_error

        # 嘗試調用
        latency: Optional[float] = None

        try:
            result = await client.generate(
                prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                # Remove internal tracking parameters that shouldn't be passed to LLM
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k
                    not in ("failed_strategy", "failed_provider", "user_id", "file_id", "purpose")
                },
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
                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    allowed = [
                        p for p in self.load_balancer.get_providers() if p.value in allowed_set
                    ]
                    provider = self.load_balancer.select_provider_filtered(allowed)
                    strategy_name = f"load_balancer_{self.load_balancer.strategy}_policy"
                else:
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

                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    if provider.value not in allowed_set:
                        fallback = next(
                            (p for p in LLMProvider if p.value in allowed_set),
                            None,
                        )
                        if fallback is not None:
                            provider = fallback
                            strategy_name = f"{strategy_name}_policy_fallback"
        else:
            provider = provider or LLMProvider.CHATGPT
            strategy_name = "manual"

        # 獲取客戶端（捕獲初始化異常，如缺少 SDK 或 API key）
        api_key = None
        if isinstance(context, dict):
            keys = context.get("llm_api_keys")
            if isinstance(keys, dict):
                api_key = keys.get(getattr(provider, "value", str(provider)))

        try:
            client = self.get_client(provider, api_key=api_key)
        except (ImportError, ValueError) as client_init_error:
            # 客戶端初始化失敗（如缺少 SDK 或 API key），直接觸發 fallback
            logger.warning(
                f"Client initialization failed for {provider.value}: {client_init_error}. "
                "Triggering failover immediately."
            )
            # 記錄失敗並觸發 fallback
            if self.enable_failover:
                return await self._failover_chat(
                    messages,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    failed_strategy=strategy_name,
                    **kwargs,
                )
            # 如果未啟用 failover，直接拋出異常
            raise Exception(
                f"Client initialization failed for {provider.value}: {client_init_error}"
            ) from client_init_error

        # 對於 Ollama provider，如果 model 包含 ollama:host:port:model_name 格式，
        # 需要提取實際的模型名稱
        normalized_model = model
        if provider == LLMProvider.OLLAMA and model and ":" in model:
            parts = model.split(":")
            if len(parts) >= 4 and parts[0] == "ollama":
                # 提取模型名稱（從第4部分開始，因為模型名稱可能包含 :）
                normalized_model = ":".join(parts[3:])
                logger.debug(
                    f"Extracted Ollama model name from model_id: {model} -> {normalized_model}"
                )
            else:
                # 簡化格式（如 gpt-oss:120b-cloud），直接使用
                # 這種格式本身就是模型名稱，可以直接傳遞給 Ollama
                normalized_model = model
                logger.debug(f"Using simplified Ollama model name: {model} (no extraction needed)")

        # 嘗試調用
        latency: Optional[float] = None

        try:
            result = await client.chat(
                messages,
                model=normalized_model,
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

            # 產品級入口需要的 routing metadata（不破壞既有返回）
            if isinstance(result, dict):
                result["_routing"] = {
                    "provider": provider.value,
                    "model": model or result.get("model"),
                    "strategy": strategy_name,
                    "latency_ms": (latency * 1000.0) if latency is not None else None,
                    "failover_used": False,
                }

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
                    failed_strategy=strategy_name,
                    **kwargs,
                )

            raise

    async def chat_stream(
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
    ) -> AsyncGenerator[str, None]:
        """
        流式對話生成（統一接口）。

        Args:
            messages: 消息列表
            task_classification: 任務分類結果（用於路由選擇）
            provider: 指定的 LLM 提供商（可選）
            model: 模型名稱（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            **kwargs: 其他參數

        Yields:
            內容塊（字符串）
        """
        start_time = time.time()

        # 選擇 LLM 提供商（與 chat 方法相同的邏輯）
        if provider is None and task_classification is not None:
            # 優先使用負載均衡器選擇提供商（如果啟用）
            if self.load_balancer is not None:
                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    allowed = [
                        p for p in self.load_balancer.get_providers() if p.value in allowed_set
                    ]
                    provider = self.load_balancer.select_provider_filtered(allowed)
                    strategy_name = f"load_balancer_{self.load_balancer.strategy}_policy"
                else:
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

                allowed_values = (
                    context.get("allowed_providers") if isinstance(context, dict) else None
                )
                if isinstance(allowed_values, list) and allowed_values:
                    allowed_set = {str(x).strip().lower() for x in allowed_values}
                    if provider.value not in allowed_set:
                        fallback = next(
                            (p for p in LLMProvider if p.value in allowed_set),
                            None,
                        )
                        if fallback is not None:
                            provider = fallback
                            strategy_name = f"{strategy_name}_policy_fallback"
        else:
            provider = provider or LLMProvider.CHATGPT
            strategy_name = "manual"

        # 獲取客戶端（捕獲初始化異常，如缺少 SDK 或 API key）
        api_key = None
        if isinstance(context, dict):
            keys = context.get("llm_api_keys")
            if isinstance(keys, dict):
                api_key = keys.get(getattr(provider, "value", str(provider)))

        try:
            client = self.get_client(provider, api_key=api_key)
        except (ImportError, ValueError) as client_init_error:
            # 客戶端初始化失敗（如缺少 SDK 或 API key），直接觸發 fallback
            logger.warning(
                f"Client initialization failed for {provider.value}: {client_init_error}. "
                "Triggering failover immediately."
            )
            # 記錄失敗並觸發 fallback
            if self.enable_failover:
                async for chunk in self._failover_chat_stream(
                    messages,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    failed_strategy=strategy_name,
                    **kwargs,
                ):
                    yield chunk
                return
            # 如果未啟用 failover，直接拋出異常
            raise Exception(
                f"Client initialization failed for {provider.value}: {client_init_error}"
            ) from client_init_error

        # 對於 Ollama provider，如果 model 包含 ollama:host:port:model_name 格式，
        # 需要提取實際的模型名稱
        normalized_model = model
        if provider == LLMProvider.OLLAMA and model and ":" in model:
            parts = model.split(":")
            if len(parts) >= 4 and parts[0] == "ollama":
                # 提取模型名稱（從第4部分開始，因為模型名稱可能包含 :）
                normalized_model = ":".join(parts[3:])
                logger.debug(
                    f"Extracted Ollama model name from model_id: {model} -> {normalized_model}"
                )
            else:
                # 簡化格式（如 gpt-oss:120b-cloud），直接使用
                # 這種格式本身就是模型名稱，可以直接傳遞給 Ollama
                normalized_model = model
                logger.debug(f"Using simplified Ollama model name: {model} (no extraction needed)")

        # 檢查客戶端是否支持 streaming
        if not hasattr(client, "chat_stream"):
            logger.error(f"Provider {provider.value} does not support streaming")
            if self.enable_failover:
                async for chunk in self._failover_chat_stream(
                    messages,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    failed_strategy=strategy_name,
                    **kwargs,
                ):
                    yield chunk
                return
            raise Exception(f"Provider {provider.value} does not support streaming")

        # 嘗試調用
        latency: Optional[float] = None
        full_content = ""

        try:
            async for chunk in client.chat_stream(
                messages,
                model=normalized_model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ):
                full_content += chunk
                yield chunk

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

        except Exception as exc:
            latency = time.time() - start_time
            logger.error(f"LLM chat_stream error with {provider.value}: {exc}")

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
                async for chunk in self._failover_chat_stream(
                    messages,
                    failed_provider=provider,
                    task_classification=task_classification,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                    failed_strategy=strategy_name,
                    **kwargs,
                ):
                    yield chunk
                return

            raise

    async def embeddings(
        self,
        text: str,
        *,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[float]:
        """
        生成文本嵌入向量（統一接口）。

        Args:
            text: 輸入文本
            provider: 指定的 LLM 提供商（可選，默認使用 ChatGPT）
            model: 嵌入模型名稱（可選）
            context: 上下文信息（可選，包含 API keys 等）
            **kwargs: 其他參數

        Returns:
            嵌入向量列表
        """
        provider = provider or LLMProvider.CHATGPT
        api_key = None
        if isinstance(context, dict):
            keys = context.get("llm_api_keys")
            if isinstance(keys, dict):
                api_key = keys.get(getattr(provider, "value", str(provider)))
        client = self.get_client(provider, api_key=api_key)

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
                        fallback_api_key = None
                        if isinstance(context, dict):
                            keys = context.get("llm_api_keys")
                            if isinstance(keys, dict):
                                fallback_api_key = keys.get(
                                    getattr(fallback, "value", str(fallback))
                                )
                        fallback_client = self.get_client(fallback, api_key=fallback_api_key)
                        if fallback_client.is_available():
                            return await fallback_client.embeddings(text, model=model, **kwargs)
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
            healthy_providers = self.failover_manager.get_healthy_providers(fallback_providers)
            if healthy_providers:
                # 優先使用健康的提供商
                fallback_providers = healthy_providers + [
                    p for p in fallback_providers if p not in healthy_providers
                ]

        last_exception: Optional[Exception] = None

        # 嘗試備用提供商
        for fallback in fallback_providers:
            try:
                logger.info(f"Failing over from {failed_provider.value} to {fallback.value}")
                fallback_api_key = None
                if isinstance(context, dict):
                    keys = context.get("llm_api_keys")
                    if isinstance(keys, dict):
                        fallback_api_key = keys.get(getattr(fallback, "value", str(fallback)))
                client = self.get_client(fallback, api_key=fallback_api_key)

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
                    # Remove internal tracking parameters that shouldn't be passed to LLM
                    **{
                        k: v
                        for k, v in kwargs.items()
                        if k
                        not in (
                            "failed_strategy",
                            "failed_provider",
                            "user_id",
                            "file_id",
                            "purpose",
                        )
                    },
                )

                logger.info(
                    f"Successfully failed over from {failed_provider.value} to {fallback.value}"
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
        error_msg = f"All LLM providers failed. Original provider: {failed_provider.value}"
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
        failed_strategy: Optional[str] = None,
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
        # 注意：OLLAMA 不在常規 fallback 列表中，作為最後的 fallback（使用 gpt-oss:20b）
        fallback_providers = [
            LLMProvider.GEMINI,
            LLMProvider.QWEN,
            LLMProvider.CHATGPT,
            # OLLAMA 不在這裡，作為最終 fallback（見最後的 fallback 邏輯）
        ]

        # 移除失敗的提供商
        if failed_provider in fallback_providers:
            fallback_providers.remove(failed_provider)

        # 如果原始 provider 是 OLLAMA，不要將它加入 fallback 列表（它會在最後作為最終 fallback 使用）

        # 如果啟用了故障轉移管理器，優先選擇健康的提供商
        if self.failover_manager is not None:
            healthy_providers = self.failover_manager.get_healthy_providers(fallback_providers)
            if healthy_providers:
                # 優先使用健康的提供商
                fallback_providers = healthy_providers + [
                    p for p in fallback_providers if p not in healthy_providers
                ]

        last_exception: Optional[Exception] = None
        skipped_providers: List[tuple[str, str]] = []  # (provider, reason)

        # 嘗試備用提供商
        for fallback in fallback_providers:
            try:
                logger.info(f"Failing over from {failed_provider.value} to {fallback.value}")

                # 對於需要 API key 的 provider，先檢查是否有 API key（除非提供了 per-request key）
                fallback_api_key = None
                if isinstance(context, dict):
                    keys = context.get("llm_api_keys")
                    if isinstance(keys, dict):
                        fallback_api_key = keys.get(getattr(fallback, "value", str(fallback)))

                # 如果沒有 per-request API key，且不是 OLLAMA（不需要 API key），
                # 先檢查 provider 是否有 API key 配置
                # 注意：LLMProvider 枚舉中沒有 AUTO，fallback 列表中也不包含 AUTO
                if not fallback_api_key and fallback != LLMProvider.OLLAMA:
                    try:
                        from services.api.services.llm_provider_config_service import (
                            get_llm_provider_config_service,
                        )

                        config_service = get_llm_provider_config_service()
                        status = config_service.get_status(fallback)
                        if not status or not status.has_api_key:
                            reason = "no API key configured"
                            logger.debug(f"Provider {fallback.value}: {reason}")
                            skipped_providers.append((fallback.value, reason))
                            continue
                    except Exception as config_check_error:
                        # 如果檢查配置時出錯，記錄但不阻止嘗試（可能是配置服務不可用）
                        logger.warning(
                            f"Failed to check API key status for {fallback.value}: {config_check_error}"
                        )

                # 嘗試創建客戶端（如果沒有 API key 會在此處失敗）
                try:
                    client = self.get_client(fallback, api_key=fallback_api_key)
                except (ValueError, ImportError) as client_init_error:
                    # 客戶端初始化失敗（如缺少 API key），跳過該 provider
                    reason = f"client initialization failed: {client_init_error}"
                    logger.debug(f"Provider {fallback.value}: {reason}")
                    skipped_providers.append((fallback.value, reason))
                    continue

                if not client.is_available():
                    logger.debug(f"Provider {fallback.value} is not available")
                    skipped_providers.append((fallback.value, "client is not available"))
                    continue

                # 檢查健康狀態（如果啟用了故障轉移管理器）
                if (
                    self.failover_manager is not None
                    and not self.failover_manager.is_provider_healthy(fallback)
                ):
                    logger.debug(f"Provider {fallback.value} is not healthy, skipping")
                    skipped_providers.append((fallback.value, "provider is not healthy"))
                    continue

                start_time = time.time()
                result = await client.chat(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                latency = time.time() - start_time

                logger.info(
                    f"Successfully failed over from {failed_provider.value} to {fallback.value}"
                )

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(fallback, latency=latency)

                # 產品級入口需要的 routing metadata（不破壞既有返回）
                if isinstance(result, dict):
                    result["_routing"] = {
                        "provider": fallback.value,
                        "model": model or result.get("model"),
                        "strategy": f"failover({failed_strategy or 'unknown'})",
                        "latency_ms": ((latency * 1000.0) if latency is not None else None),
                        "failover_used": True,
                        "failed_provider": failed_provider.value,
                    }

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

        # 所有提供商都失敗，最後嘗試本機 qwen3-next:latest（強制使用 localhost:11434）
        # 修改時間：2026-01-22 - 使用 qwen3-next:latest 作為默認 fallback 模型
        # 注意：即使原始 provider 是 OLLAMA，也嘗試最終 fallback（可能是其他節點失敗，嘗試本地節點）
        try:
            logger.info(
                f"All fallback providers failed (original: {failed_provider.value}), "
                "attempting final fallback to local qwen3-next:latest on localhost:11434"
            )
            # 為最終 fallback 創建只使用 localhost 的 Ollama 客戶端
            from llm.clients.ollama import OllamaClient
            from llm.router import LLMNodeConfig, LLMNodeRouter

            localhost_node = LLMNodeConfig(
                name="localhost-fallback",
                host="localhost",
                port=11434,
                weight=1,
            )
            localhost_router = LLMNodeRouter(
                nodes=[localhost_node],
                strategy="round_robin",
                cooldown_seconds=30,
            )
            client = OllamaClient(router=localhost_router, default_model="qwen3-next:latest")
            if client.is_available():
                start_time = time.time()
                # 對於最終 fallback，如果原始 model 是 ollama:host:port:model_name 格式，
                # 提取實際的模型名稱；否則使用 qwen3-next:latest
                fallback_model = "qwen3-next:latest"
                if model and ":" in model:
                    parts = model.split(":")
                    if len(parts) >= 4 and parts[0] == "ollama":
                        fallback_model = ":".join(parts[3:])

                result = await client.chat(
                    messages,
                    model=fallback_model,  # 使用提取的模型名稱或 qwen3-next:latest
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                latency = time.time() - start_time

                logger.info("Successfully used final fallback to local qwen3-next:latest")

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(LLMProvider.OLLAMA, latency=latency)

                # 產品級入口需要的 routing metadata
                if isinstance(result, dict):
                    result["_routing"] = {
                        "provider": LLMProvider.OLLAMA.value,
                        "model": fallback_model,
                        "strategy": f"final_fallback({failed_strategy or 'unknown'})",
                        "latency_ms": ((latency * 1000.0) if latency is not None else None),
                        "failover_used": True,
                        "failed_provider": failed_provider.value,
                        "final_fallback": True,
                    }

                return result
            else:
                logger.warning("Final fallback: localhost Ollama client is not available")
        except Exception as final_fallback_exc:
            logger.warning(
                f"Final fallback to local qwen3-next:latest also failed: {final_fallback_exc}",
                exc_info=True,
            )
            # 記錄最終 fallback 失敗的原因
            last_exception = final_fallback_exc

        # 所有提供商（包括最終 fallback）都失敗
        error_msg = f"All LLM providers failed. Original provider: {failed_provider.value}"
        if skipped_providers:
            skipped_details = ", ".join([f"{p} ({r})" for p, r in skipped_providers])
            error_msg += f". Skipped providers: {skipped_details}"
        if last_exception:
            error_msg += f". Last error: {last_exception}"
        raise Exception(error_msg)

    async def _failover_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        failed_provider: LLMProvider,
        task_classification: Optional[TaskClassificationResult] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        failed_strategy: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        故障轉移流式對話（嘗試備用提供商）。

        Args:
            messages: 消息列表
            failed_provider: 失敗的提供商
            task_classification: 任務分類結果
            model: 模型名稱
            temperature: 溫度參數
            max_tokens: 最大 token 數
            context: 上下文信息
            failed_strategy: 失敗的策略名稱
            **kwargs: 其他參數

        Yields:
            內容塊（字符串）

        Raises:
            Exception: 如果所有提供商都失敗
        """
        # 定義備用提供商順序（優先級從高到低）
        # 注意：OLLAMA 不在常規 fallback 列表中，作為最後的 fallback（使用 gpt-oss:20b）
        fallback_providers = [
            LLMProvider.GEMINI,
            LLMProvider.QWEN,
            LLMProvider.CHATGPT,
            # OLLAMA 不在這裡，作為最終 fallback（見最後的 fallback 邏輯）
        ]

        # 移除失敗的提供商
        if failed_provider in fallback_providers:
            fallback_providers.remove(failed_provider)

        # 如果啟用了故障轉移管理器，優先選擇健康的提供商
        if self.failover_manager is not None:
            healthy_providers = self.failover_manager.get_healthy_providers(fallback_providers)
            if healthy_providers:
                # 優先使用健康的提供商
                fallback_providers = healthy_providers + [
                    p for p in fallback_providers if p not in healthy_providers
                ]

        last_exception: Optional[Exception] = None
        skipped_providers: List[tuple[str, str]] = []  # (provider, reason)

        # 嘗試備用提供商
        for fallback in fallback_providers:
            try:
                logger.info(f"Failing over from {failed_provider.value} to {fallback.value}")

                # 對於需要 API key 的 provider，先檢查是否有 API key（除非提供了 per-request key）
                fallback_api_key = None
                if isinstance(context, dict):
                    keys = context.get("llm_api_keys")
                    if isinstance(keys, dict):
                        fallback_api_key = keys.get(getattr(fallback, "value", str(fallback)))

                # 如果沒有 per-request API key，且不是 OLLAMA（不需要 API key），
                # 先檢查 provider 是否有 API key 配置
                if not fallback_api_key and fallback != LLMProvider.OLLAMA:
                    try:
                        from services.api.services.llm_provider_config_service import (
                            get_llm_provider_config_service,
                        )

                        config_service = get_llm_provider_config_service()
                        status = config_service.get_status(fallback)
                        if not status or not status.has_api_key:
                            reason = "no API key configured"
                            logger.debug(f"Provider {fallback.value}: {reason}")
                            skipped_providers.append((fallback.value, reason))
                            continue
                    except Exception as config_check_error:
                        # 如果檢查配置時出錯，記錄但不阻止嘗試（可能是配置服務不可用）
                        logger.warning(
                            f"Failed to check API key status for {fallback.value}: {config_check_error}"
                        )

                # 嘗試創建客戶端（如果沒有 API key 會在此處失敗）
                try:
                    client = self.get_client(fallback, api_key=fallback_api_key)
                except (ValueError, ImportError) as client_init_error:
                    # 客戶端初始化失敗（如缺少 API key），跳過該 provider
                    reason = f"client initialization failed: {client_init_error}"
                    logger.debug(f"Provider {fallback.value}: {reason}")
                    skipped_providers.append((fallback.value, reason))
                    continue

                if not client.is_available():
                    logger.debug(f"Provider {fallback.value} is not available")
                    skipped_providers.append((fallback.value, "client is not available"))
                    continue

                # 檢查健康狀態（如果啟用了故障轉移管理器）
                if (
                    self.failover_manager is not None
                    and not self.failover_manager.is_provider_healthy(fallback)
                ):
                    logger.debug(f"Provider {fallback.value} is not healthy, skipping")
                    skipped_providers.append((fallback.value, "provider is not healthy"))
                    continue

                # 檢查客戶端是否支持 streaming
                if not hasattr(client, "chat_stream"):
                    logger.debug(f"Provider {fallback.value} does not support streaming")
                    skipped_providers.append((fallback.value, "streaming not supported"))
                    continue

                # 對於 Ollama provider，如果 model 包含 ollama:host:port:model_name 格式，
                # 需要提取實際的模型名稱
                normalized_model = model
                if fallback == LLMProvider.OLLAMA and model and ":" in model:
                    parts = model.split(":")
                    if len(parts) >= 4 and parts[0] == "ollama":
                        normalized_model = ":".join(parts[3:])
                        logger.debug(
                            f"Extracted Ollama model name from model_id: {model} -> {normalized_model}"
                        )

                start_time = time.time()
                # 流式調用
                async for chunk in client.chat_stream(
                    messages,
                    model=normalized_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ):
                    yield chunk
                latency = time.time() - start_time

                logger.info(
                    f"Successfully failed over from {failed_provider.value} to {fallback.value}"
                )

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(fallback, latency=latency)

                # 記錄路由結果
                if task_classification is not None:
                    self.evaluator.record_decision(
                        provider=fallback,
                        strategy=f"failover({failed_strategy or 'unknown'})",
                        task_type=task_classification.task_type.value,
                        success=True,
                        latency=latency,
                    )

                # 成功，返回
                return

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

        # 所有提供商都失敗，最後嘗試本機 qwen3-next:latest（強制使用 localhost:11434）
        # 修改時間：2026-01-22 - 使用 qwen3-next:latest 作為默認 fallback 模型
        # 注意：即使原始 provider 是 OLLAMA，也嘗試最終 fallback（可能是其他節點失敗，嘗試本地節點）
        try:
            logger.info(
                f"All fallback providers failed (original: {failed_provider.value}), "
                "attempting final fallback to local qwen3-next:latest on localhost:11434"
            )
            # 為最終 fallback 創建只使用 localhost 的 Ollama 客戶端
            from llm.clients.ollama import OllamaClient
            from llm.router import LLMNodeConfig, LLMNodeRouter

            localhost_node = LLMNodeConfig(
                name="localhost-fallback",
                host="localhost",
                port=11434,
                weight=1,
            )
            localhost_router = LLMNodeRouter(
                nodes=[localhost_node],
                strategy="round_robin",
                cooldown_seconds=30,
            )
            client = OllamaClient(router=localhost_router, default_model="qwen3-next:latest")
            if client.is_available() and hasattr(client, "chat_stream"):
                # 對於最終 fallback，如果原始 model 是 ollama:host:port:model_name 格式，
                # 提取實際的模型名稱；否則使用 qwen3-next:latest
                fallback_model = "qwen3-next:latest"
                if model and ":" in model:
                    parts = model.split(":")
                    if len(parts) >= 4 and parts[0] == "ollama":
                        fallback_model = ":".join(parts[3:])

                start_time = time.time()
                # 流式調用
                async for chunk in client.chat_stream(
                    messages,
                    model=fallback_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                ):
                    yield chunk
                latency = time.time() - start_time

                logger.info("Successfully used final fallback to local qwen3-next:latest")

                # 標記負載均衡器成功（如果啟用）
                if self.load_balancer is not None:
                    self.load_balancer.mark_success(LLMProvider.OLLAMA, latency=latency)

                # 記錄路由結果
                if task_classification is not None:
                    self.evaluator.record_decision(
                        provider=LLMProvider.OLLAMA,
                        strategy=f"final_fallback({failed_strategy or 'unknown'})",
                        task_type=task_classification.task_type.value,
                        success=True,
                        latency=latency,
                    )

                # 成功，返回
                return
            else:
                logger.warning(
                    "Final fallback: localhost Ollama client is not available or does not support streaming"
                )
        except Exception as final_fallback_exc:
            logger.warning(
                f"Final fallback to local qwen3-next:latest also failed: {final_fallback_exc}",
                exc_info=True,
            )
            # 記錄最終 fallback 失敗的原因
            last_exception = final_fallback_exc

        # 所有提供商（包括最終 fallback）都失敗
        error_msg = f"All LLM providers failed. Original provider: {failed_provider.value}"
        if skipped_providers:
            skipped_details = ", ".join([f"{p} ({r})" for p, r in skipped_providers])
            error_msg += f". Skipped providers: {skipped_details}"
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
            metrics["health_status"] = self.failover_manager.get_provider_health_status()

        return metrics


# ============================================================================
# 場景路由擴展 Phase 2
# ============================================================================

# 場景配置加載器實例
_moe_config_loader: Optional[MoEConfigLoader] = None
