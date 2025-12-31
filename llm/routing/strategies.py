# 代碼功能說明: LLM 路由策略實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""實現多種路由策略：任務類型、複雜度、成本、延遲等。"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from agents.task_analyzer.models import LLMProvider, TaskClassificationResult, TaskType

from .base import BaseRoutingStrategy, RoutingResult, RoutingStrategyRegistry

logger = logging.getLogger(__name__)


class TaskTypeBasedStrategy(BaseRoutingStrategy):
    """基於任務類型的路由策略。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # 定義任務類型到 LLM 提供商的映射規則
        self.provider_rules: Dict[TaskType, Dict[LLMProvider, float]] = {
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

        # 從配置加載規則（如果提供）
        if config and "rules" in config:
            self._load_rules_from_config(config["rules"])

    def _load_rules_from_config(self, rules_config: Dict[str, Any]) -> None:
        """從配置加載路由規則。"""
        for task_type_str, provider_scores in rules_config.items():
            try:
                task_type = TaskType(task_type_str)
                provider_dict: Dict[LLMProvider, float] = {}
                for provider_str, score in provider_scores.items():
                    provider_dict[LLMProvider(provider_str)] = float(score)
                self.provider_rules[task_type] = provider_dict
            except (ValueError, KeyError) as exc:
                logger.warning(f"忽略無效的路由規則配置: {task_type_str}, {exc}")

    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """基於任務類型選擇提供商。"""
        task_type = task_classification.task_type

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

            # 選擇得分最高的提供商
            provider = max(rules.items(), key=lambda x: x[1])[0]
            confidence = rules[provider]
            reasoning = (
                f"根據任務類型 {task_type.value}，選擇 {provider.value} 提供商，"
                f"置信度 {confidence:.2f}"
            )

        return RoutingResult(
            provider=provider,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"task_type": task_type.value},
        )

    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """評估提供商對任務類型的適合度。"""
        try:
            task_type_enum = TaskType(task_type)
            if task_type_enum in self.provider_rules:
                return self.provider_rules[task_type_enum].get(provider, 0.0)
        except ValueError:
            pass
        return 0.0

    @property
    def strategy_name(self) -> str:
        return "task_type"


class TaskComplexityEvaluator:
    """任務複雜度評估器。"""

    # 複雜任務關鍵詞
    COMPLEX_KEYWORDS = [
        "分析",
        "比較",
        "評估",
        "設計",
        "規劃",
        "優化",
        "解決",
        "實現",
        "開發",
        "創建",
    ]

    # 簡單任務關鍵詞
    SIMPLE_KEYWORDS = [
        "查詢",
        "查找",
        "獲取",
        "顯示",
        "列出",
        "說明",
        "解釋",
    ]

    @classmethod
    def evaluate(cls, task: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        評估任務複雜度。

        Args:
            task: 任務描述
            context: 上下文信息

        Returns:
            複雜度分數（0.0-1.0），越高越複雜
        """
        complexity = 0.0

        # 基於任務長度
        task_length = len(task)
        if task_length > 500:
            complexity += 0.3
        elif task_length > 200:
            complexity += 0.2
        elif task_length > 100:
            complexity += 0.1

        # 基於關鍵詞
        task_lower = task.lower()
        complex_count = sum(1 for kw in cls.COMPLEX_KEYWORDS if kw in task_lower)
        simple_count = sum(1 for kw in cls.SIMPLE_KEYWORDS if kw in task_lower)

        if complex_count > 0:
            complexity += min(0.4, complex_count * 0.1)
        if simple_count > 0:
            complexity -= min(0.2, simple_count * 0.05)

        # 基於上下文複雜度
        if context:
            if context.get("requires_multiple_steps", False):
                complexity += 0.2
            if context.get("requires_external_data", False):
                complexity += 0.1

        # 正則表達式：檢查是否包含多個問題或步驟
        question_marks = len(re.findall(r"[？?]", task))
        if question_marks > 1:
            complexity += min(0.2, question_marks * 0.05)

        return max(0.0, min(1.0, complexity))


class ComplexityBasedStrategy(BaseRoutingStrategy):
    """基於任務複雜度的路由策略。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.evaluator = TaskComplexityEvaluator()

        # 複雜度到提供商的映射
        self.complexity_thresholds = {
            "high": 0.7,  # 高複雜度使用 ChatGPT/Gemini
            "medium": 0.4,  # 中等複雜度使用 Qwen/Gemini
            "low": 0.0,  # 低複雜度使用 Ollama/Qwen
        }

        # 從配置加載（如果提供）
        if config and "thresholds" in config:
            self.complexity_thresholds.update(config["thresholds"])

    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """基於任務複雜度選擇提供商。"""
        complexity = self.evaluator.evaluate(task, context)

        if complexity >= self.complexity_thresholds["high"]:
            provider = LLMProvider.CHATGPT
            confidence = 0.9
            reasoning = f"高複雜度任務（{complexity:.2f}），選擇 ChatGPT"
        elif complexity >= self.complexity_thresholds["medium"]:
            provider = LLMProvider.GEMINI
            confidence = 0.8
            reasoning = f"中等複雜度任務（{complexity:.2f}），選擇 Gemini"
        else:
            provider = LLMProvider.QWEN
            confidence = 0.7
            reasoning = f"低複雜度任務（{complexity:.2f}），選擇 Qwen"

        return RoutingResult(
            provider=provider,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"complexity": complexity},
        )

    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """評估提供商對複雜度的適合度。"""
        # 簡化評估：ChatGPT 和 Gemini 適合高複雜度，Qwen 和 Ollama 適合低複雜度
        if provider in [LLMProvider.CHATGPT, LLMProvider.GEMINI]:
            return 0.8
        elif provider in [LLMProvider.QWEN, LLMProvider.OLLAMA]:
            return 0.6
        return 0.5

    @property
    def strategy_name(self) -> str:
        return "complexity"


class CostBasedStrategy(BaseRoutingStrategy):
    """基於成本的路由策略。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 提供商成本評分（越低越便宜）
        self.cost_scores: Dict[LLMProvider, float] = {
            LLMProvider.OLLAMA: 0.1,  # 本地，成本最低
            LLMProvider.QWEN: 0.3,  # 相對便宜
            LLMProvider.GEMINI: 0.5,  # 中等
            LLMProvider.GROK: 0.6,  # 中等偏高
            LLMProvider.CHATGPT: 0.9,  # 最貴
        }

        if config and "cost_scores" in config:
            for provider_str, score in config["cost_scores"].items():
                try:
                    self.cost_scores[LLMProvider(provider_str)] = float(score)
                except (ValueError, KeyError):
                    pass

    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """基於成本選擇提供商。"""
        # 檢查是否成本敏感
        cost_sensitive = context.get("cost_sensitive", False) if context else False

        if cost_sensitive:
            # 選擇成本最低的提供商
            provider = min(self.cost_scores.items(), key=lambda x: x[1])[0]
            confidence = 0.8
            reasoning = (
                f"成本敏感任務，選擇 {provider.value}（成本評分：{self.cost_scores[provider]:.2f}）"
            )
        else:
            # 平衡成本和質量，選擇中等成本的提供商
            sorted_providers = sorted(self.cost_scores.items(), key=lambda x: x[1])
            provider = sorted_providers[len(sorted_providers) // 2][0]
            confidence = 0.7
            reasoning = f"平衡成本和質量，選擇 {provider.value}"

        return RoutingResult(
            provider=provider,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"cost_score": self.cost_scores[provider]},
        )

    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """評估提供商成本。"""
        cost_score = self.cost_scores.get(provider, 0.5)
        # 成本越低，適合度越高（反轉）
        return 1.0 - cost_score

    @property
    def strategy_name(self) -> str:
        return "cost"


class LatencyBasedStrategy(BaseRoutingStrategy):
    """基於延遲的路由策略。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 提供商延遲評分（越低延遲越低）
        self.latency_scores: Dict[LLMProvider, float] = {
            LLMProvider.OLLAMA: 0.2,  # 本地，延遲最低
            LLMProvider.QWEN: 0.4,  # 相對低延遲
            LLMProvider.GEMINI: 0.6,  # 中等
            LLMProvider.CHATGPT: 0.7,  # 中等偏高
            LLMProvider.GROK: 0.8,  # 延遲較高
        }

        if config and "latency_scores" in config:
            for provider_str, score in config["latency_scores"].items():
                try:
                    self.latency_scores[LLMProvider(provider_str)] = float(score)
                except (ValueError, KeyError):
                    pass

    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """基於延遲選擇提供商。"""
        # 檢查是否低延遲要求
        low_latency = context.get("low_latency", False) if context else False

        if low_latency:
            # 選擇延遲最低的提供商
            provider = min(self.latency_scores.items(), key=lambda x: x[1])[0]
            confidence = 0.8
            reasoning = f"低延遲要求，選擇 {provider.value}（延遲評分：{self.latency_scores[provider]:.2f}）"
        else:
            # 平衡延遲和質量
            sorted_providers = sorted(self.latency_scores.items(), key=lambda x: x[1])
            provider = sorted_providers[len(sorted_providers) // 2][0]
            confidence = 0.7
            reasoning = f"平衡延遲和質量，選擇 {provider.value}"

        return RoutingResult(
            provider=provider,
            confidence=confidence,
            reasoning=reasoning,
            metadata={"latency_score": self.latency_scores[provider]},
        )

    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """評估提供商延遲。"""
        latency_score = self.latency_scores.get(provider, 0.5)
        # 延遲越低，適合度越高（反轉）
        return 1.0 - latency_score

    @property
    def strategy_name(self) -> str:
        return "latency"


class HybridRoutingStrategy(BaseRoutingStrategy):
    """混合路由策略：組合多種策略。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 默認策略和權重
        self.strategy_weights: Dict[str, float] = {
            "task_type": 0.4,
            "complexity": 0.3,
            "cost": 0.2,
            "latency": 0.1,
        }

        # 創建子策略
        self.strategies: Dict[str, BaseRoutingStrategy] = {
            "task_type": TaskTypeBasedStrategy(),
            "complexity": ComplexityBasedStrategy(),
            "cost": CostBasedStrategy(),
            "latency": LatencyBasedStrategy(),
        }

        # 從配置加載
        if config:
            if "weights" in config:
                self.strategy_weights.update(config["weights"])

            # 為子策略傳遞配置
            for strategy_name, strategy in self.strategies.items():
                if strategy_name in config:
                    # 重新創建策略實例以應用配置
                    strategy_class = type(strategy)
                    self.strategies[strategy_name] = strategy_class(config[strategy_name])

    def select_provider(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingResult:
        """使用混合策略選擇提供商。"""
        # 收集各策略的選擇結果
        strategy_results: Dict[str, RoutingResult] = {}
        provider_scores: Dict[LLMProvider, float] = {}

        for strategy_name, strategy in self.strategies.items():
            if strategy_name not in self.strategy_weights:
                continue

            weight = self.strategy_weights[strategy_name]
            result = strategy.select_provider(task_classification, task, context)

            strategy_results[strategy_name] = result

            # 加權累計分數
            provider = result.provider
            score = result.confidence * weight
            provider_scores[provider] = provider_scores.get(provider, 0.0) + score

        # 選擇得分最高的提供商
        if not provider_scores:
            # 如果沒有結果，使用默認
            provider = LLMProvider.CHATGPT
            confidence = 0.5
        else:
            provider = max(provider_scores.items(), key=lambda x: x[1])[0]
            confidence = min(1.0, provider_scores[provider])

        # 構建推理說明
        reasoning_parts = [f"混合策略選擇 {provider.value}（置信度：{confidence:.2f}）"]
        for strategy_name, result in strategy_results.items():
            reasoning_parts.append(
                f"{strategy_name}: {result.provider.value} ({result.confidence:.2f})"
            )
        reasoning = "；".join(reasoning_parts)

        return RoutingResult(
            provider=provider,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "strategy_results": {
                    name: {
                        "provider": result.provider.value,
                        "confidence": result.confidence,
                    }
                    for name, result in strategy_results.items()
                },
                "final_scores": {p.value: s for p, s in provider_scores.items()},
            },
        )

    def evaluate(
        self,
        provider: LLMProvider,
        task_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """使用混合策略評估。"""
        total_score = 0.0
        total_weight = 0.0

        for strategy_name, strategy in self.strategies.items():
            if strategy_name not in self.strategy_weights:
                continue

            weight = self.strategy_weights[strategy_name]
            score = strategy.evaluate(provider, task_type, context)

            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    @property
    def strategy_name(self) -> str:
        return "hybrid"


# 註冊所有策略
RoutingStrategyRegistry.register("task_type", TaskTypeBasedStrategy)
RoutingStrategyRegistry.register("complexity", ComplexityBasedStrategy)
RoutingStrategyRegistry.register("cost", CostBasedStrategy)
RoutingStrategyRegistry.register("latency", LatencyBasedStrategy)
RoutingStrategyRegistry.register("hybrid", HybridRoutingStrategy)
