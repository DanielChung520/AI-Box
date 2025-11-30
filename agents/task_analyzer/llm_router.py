# 代碼功能說明: LLM 路由選擇器實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""LLM 路由選擇器 - 實現 LLM 路由選擇邏輯，集成新的路由策略架構。"""

import logging
from typing import Dict, Any, Optional, List

from system.infra.config.config import get_config_section
from llm.router import LLMNodeConfig, LLMNodeRouter
from llm.routing.dynamic import DynamicRouter
from llm.routing.evaluator import RoutingEvaluator
from llm.routing.ab_testing import ABTestManager, ABTestGroup, TrafficAllocationMethod

from agents.task_analyzer.models import (
    TaskType,
    LLMProvider,
    LLMRoutingResult,
    TaskClassificationResult,
)

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由選擇器"""

    def __init__(self, use_new_strategy: bool = True):
        """
        初始化 LLM 路由選擇器。

        Args:
            use_new_strategy: 是否使用新的路由策略架構（默認 True）
        """
        self.local_router: Optional[LLMNodeRouter] = None
        self.use_new_strategy = use_new_strategy

        # 定義模型映射
        self.model_mapping = {
            LLMProvider.CHATGPT: "gpt-4-turbo-preview",
            LLMProvider.GEMINI: "gemini-pro",
            LLMProvider.GROK: "grok-beta",
            LLMProvider.QWEN: "qwen-turbo",
            LLMProvider.OLLAMA: "llama2",
        }

        # 定義備用提供商
        self.fallback_mapping = {
            LLMProvider.CHATGPT: [LLMProvider.GEMINI, LLMProvider.QWEN],
            LLMProvider.GEMINI: [LLMProvider.CHATGPT, LLMProvider.QWEN],
            LLMProvider.GROK: [LLMProvider.CHATGPT, LLMProvider.GEMINI],
            LLMProvider.QWEN: [LLMProvider.CHATGPT, LLMProvider.GEMINI],
            LLMProvider.OLLAMA: [LLMProvider.QWEN, LLMProvider.CHATGPT],
        }

        # 舊版路由規則（向後兼容）
        self.provider_rules = {
            TaskType.QUERY: {
                LLMProvider.CHATGPT: 0.8,
                LLMProvider.GEMINI: 0.7,
                LLMProvider.QWEN: 0.6,
                LLMProvider.OLLAMA: 0.5,
            },
            TaskType.EXECUTION: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.OLLAMA: 0.6,
            },
            TaskType.REVIEW: {
                LLMProvider.GEMINI: 0.8,
                LLMProvider.CHATGPT: 0.7,
                LLMProvider.QWEN: 0.6,
                LLMProvider.OLLAMA: 0.5,
            },
            TaskType.PLANNING: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.GROK: 0.6,
            },
            TaskType.COMPLEX: {
                LLMProvider.CHATGPT: 0.9,
                LLMProvider.GEMINI: 0.8,
                LLMProvider.QWEN: 0.7,
                LLMProvider.OLLAMA: 0.5,
            },
        }

        # 初始化新架構組件
        if self.use_new_strategy:
            self._init_new_strategy_architecture()
        else:
            self.dynamic_router: Optional[DynamicRouter] = None
            self.evaluator: Optional[RoutingEvaluator] = None
            self.ab_test_manager: Optional[ABTestManager] = None

        self._init_local_llm_settings()

    def _init_new_strategy_architecture(self) -> None:
        """初始化新的路由策略架構。"""
        # 從配置加載路由策略設置
        routing_cfg = get_config_section("llm", "routing", default={}) or {}
        default_strategy = routing_cfg.get("default_strategy", "hybrid")

        # 初始化動態路由器
        self.dynamic_router = DynamicRouter(default_strategy=default_strategy)

        # 初始化評估器
        self.evaluator = RoutingEvaluator()

        # 初始化 A/B 測試管理器（如果配置了）
        self.ab_test_manager = None
        if routing_cfg.get("ab_testing", {}).get("enabled", False):
            ab_test_cfg = routing_cfg["ab_testing"]
            groups = [
                ABTestGroup(
                    name=g["name"],
                    strategy=g["strategy"],
                    traffic_percentage=g["traffic_percentage"],
                    config=g.get("config", {}),
                )
                for g in ab_test_cfg.get("groups", [])
            ]
            allocation_method = TrafficAllocationMethod(
                ab_test_cfg.get("allocation_method", "random")
            )
            self.ab_test_manager = ABTestManager(
                test_name=ab_test_cfg.get("test_name", "default"),
                groups=groups,
                allocation_method=allocation_method,
            )

    def _init_local_llm_settings(self) -> None:
        """依 config/services/ollama 設定本地模型與節點資訊。"""
        ollama_cfg = get_config_section("services", "ollama", default={}) or {}
        default_model = ollama_cfg.get("default_model")
        if default_model:
            self.model_mapping[LLMProvider.OLLAMA] = default_model

        nodes_cfg: List[LLMNodeConfig] = []
        for idx, node in enumerate(ollama_cfg.get("nodes", [])):
            try:
                nodes_cfg.append(
                    LLMNodeConfig(
                        name=node.get("name", f"ollama-node-{idx+1}"),
                        host=node["host"],
                        port=int(node.get("port", 11434)),
                        weight=int(node.get("weight", 1)),
                    )
                )
            except KeyError as exc:
                logger.warning("忽略不完整的 Ollama 節點設定（index=%s）: %s", idx, exc)

        if nodes_cfg:
            router_cfg = ollama_cfg.get("router", {}) or {}
            self.local_router = LLMNodeRouter(
                nodes=nodes_cfg,
                strategy=router_cfg.get("strategy", "round_robin"),
                cooldown_seconds=int(router_cfg.get("cooldown_seconds", 30)),
            )

    def route(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LLMRoutingResult:
        """
        選擇合適的 LLM 提供商。

        Args:
            task_classification: 任務分類結果
            task: 任務描述
            context: 上下文信息

        Returns:
            LLM 路由選擇結果
        """
        logger.info(f"Routing LLM for task type: {task_classification.task_type.value}")

        # 使用新架構或舊架構
        if self.use_new_strategy and self.dynamic_router is not None:
            return self._route_with_new_strategy(task_classification, task, context)
        else:
            return self._route_with_legacy_strategy(task_classification, task, context)

    def _route_with_new_strategy(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LLMRoutingResult:
        """使用新路由策略架構進行路由。"""
        # 確保 dynamic_router 不為 None
        if self.dynamic_router is None:
            raise RuntimeError("DynamicRouter is not initialized")

        # 檢查是否有 A/B 測試
        ab_test_group: Optional[ABTestGroup] = None
        if self.ab_test_manager is not None and self.ab_test_manager.active:
            user_id = context.get("user_id") if context else None
            session_id = context.get("session_id") if context else None
            task_type = task_classification.task_type.value
            ab_test_group = self.ab_test_manager.assign_group(
                user_id=user_id, session_id=session_id, task_type=task_type
            )

        # 獲取路由策略
        if ab_test_group:
            strategy_name = ab_test_group.strategy
            strategy_config = ab_test_group.config
        else:
            strategy_name = None
            strategy_config = None

        strategy = self.dynamic_router.get_strategy(strategy_name)
        if strategy_config:
            # 如果 A/B 測試提供了配置，臨時更新策略
            strategy.config.update(strategy_config)

        # 執行路由選擇
        routing_result = strategy.select_provider(task_classification, task, context)

        provider = routing_result.provider
        confidence = routing_result.confidence
        reasoning = routing_result.reasoning

        # 獲取模型名稱
        model = self.model_mapping.get(provider, "default")

        # 獲取備用提供商列表
        fallback_providers = self.fallback_mapping.get(provider, [])

        # 處理本地 LLM 節點選擇
        target_node: Optional[str] = None
        if provider == LLMProvider.OLLAMA and self.local_router:
            node = self.local_router.select_node()
            target_node = node.name
            reasoning += f"，指派節點 {target_node}"

        # 構建路由元數據
        routing_metadata = routing_result.metadata.copy()
        routing_metadata["strategy"] = strategy.strategy_name
        if ab_test_group:
            routing_metadata["ab_test_group"] = ab_test_group.name

        # 估算延遲和成本（從元數據或使用默認值）
        estimated_latency = routing_metadata.get("latency_score")
        estimated_cost = routing_metadata.get("cost_score")
        quality_score = routing_metadata.get("quality_score")

        logger.info(
            f"Routed to {provider.value} ({model}) with confidence {confidence:.2f}"
        )

        return LLMRoutingResult(
            provider=provider,
            model=model,
            confidence=confidence,
            reasoning=reasoning,
            fallback_providers=fallback_providers,
            target_node=target_node,
            routing_strategy=strategy.strategy_name,
            estimated_latency=estimated_latency,
            estimated_cost=estimated_cost,
            quality_score=quality_score,
            routing_metadata=routing_metadata,
        )

    def _route_with_legacy_strategy(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> LLMRoutingResult:
        """使用舊版路由策略（向後兼容）。"""
        task_type = task_classification.task_type

        # 獲取該任務類型的提供商規則
        target_node: Optional[str] = None

        if task_type not in self.provider_rules:
            # 默認使用 ChatGPT
            provider = LLMProvider.CHATGPT
            confidence = 0.5
            reasoning = f"未知任務類型 {task_type.value}，默認使用 ChatGPT"
        else:
            rules = self.provider_rules[task_type].copy()

            # 考慮上下文中的提供商偏好
            if context:
                if "preferred_provider" in context:
                    preferred = context["preferred_provider"]
                    try:
                        preferred_provider = LLMProvider(preferred)
                        if preferred_provider in rules:
                            rules[preferred_provider] += 0.2
                    except ValueError:
                        logger.warning(f"無效的提供商偏好: {preferred}")

                # 考慮成本因素
                if context.get("cost_sensitive", False):
                    # 成本敏感時優先使用本地或便宜的提供商
                    if LLMProvider.OLLAMA in rules:
                        rules[LLMProvider.OLLAMA] += 0.3
                    if LLMProvider.QWEN in rules:
                        rules[LLMProvider.QWEN] += 0.2

                # 考慮延遲要求
                if context.get("low_latency", False):
                    # 低延遲要求時優先使用本地提供商
                    if LLMProvider.OLLAMA in rules:
                        rules[LLMProvider.OLLAMA] += 0.3

            # 選擇得分最高的提供商
            provider = max(rules.items(), key=lambda x: x[1])[0]
            confidence = rules[provider]
            reasoning = (
                f"根據任務類型 {task_type.value}，選擇 {provider.value} 提供商，"
                f"置信度 {confidence:.2f}"
            )

        # 獲取模型名稱
        model = self.model_mapping.get(provider, "default")

        # 獲取備用提供商列表
        fallback_providers = self.fallback_mapping.get(provider, [])

        if provider == LLMProvider.OLLAMA and self.local_router:
            node = self.local_router.select_node()
            target_node = node.name
            reasoning += f"，指派節點 {target_node}"

        logger.info(
            f"Routed to {provider.value} ({model}) with confidence {confidence:.2f}"
        )

        return LLMRoutingResult(
            provider=provider,
            model=model,
            confidence=confidence,
            reasoning=reasoning,
            fallback_providers=fallback_providers,
            target_node=target_node,
            routing_strategy="legacy",
            estimated_latency=None,
            estimated_cost=None,
            quality_score=None,
            routing_metadata={},
        )

    def record_routing_result(
        self,
        provider: LLMProvider,
        success: bool,
        latency: Optional[float] = None,
        cost: Optional[float] = None,
        quality_score: Optional[float] = None,
        strategy_name: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> None:
        """
        記錄路由結果（用於評估和優化）。

        Args:
            provider: LLM 提供商
            success: 是否成功
            latency: 延遲時間（秒）
            cost: 成本
            quality_score: 質量評分（0.0-1.0）
            strategy_name: 使用的策略名稱
            task_type: 任務類型
        """
        if self.evaluator is not None:
            self.evaluator.record_decision(
                provider=provider,
                strategy=strategy_name or "unknown",
                task_type=task_type or "unknown",
                success=success,
                latency=latency,
                cost=cost,
                quality_score=quality_score,
            )

        if self.dynamic_router is not None and strategy_name:
            self.dynamic_router.record_request(strategy_name, success)

        if self.ab_test_manager is not None:
            # A/B 測試結果記錄需要組名，這裡簡化處理
            pass
