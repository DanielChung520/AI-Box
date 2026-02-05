from __future__ import annotations
# 代碼功能說明: LangGraph條件邊緣邏輯
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""LangGraph條件邊緣邏輯 - 實現狀態機的條件分支"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class ConditionResult:
    """條件評估結果"""
    condition_name: str
    result: bool
    confidence: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseCondition(ABC):
    """基礎條件抽象類"""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def evaluate(self, state: AIBoxState) -> ConditionResult:
        """
        評估條件

        Args:
            state: 當前狀態
        Returns:
            ConditionResult: 評估結果
        """
        pass


class ConditionCache:
    """條件評估快取"""
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, ConditionResult] = {}
        self.max_size = max_size
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[ConditionResult]:
        """獲取快取結果"""
        return self.cache.get(key)

    def set(self, key: str, result: ConditionResult) -> None:
        """設置快取結果"""
        if len(self.cache) >= self.max_size:
            # 簡單的LRU: 移除第一個
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[key] = result

    def clear(self) -> None:
        """清空快取"""
        self.cache.clear()
        self.logger.info("Condition cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": 0.0,  # 可以後續實現命中率統計
        }


class RouteDecision:
    """路由決策"""
    def __init__(
        self,
        target_node: str,
        confidence: float = 1.0,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.target_node = target_node
        self.confidence = confidence
        self.reason = reason
        self.metadata = metadata or {}


class RouteRule:
    """路由規則"""
    def __init__(
        self, name: str, conditions: List[BaseCondition], target_node: str, priority: int = 0,
    ):
        self.name = name
        self.conditions = conditions
        self.target_node = target_node
        self.priority = priority

    def evaluate(
        self, state: AIBoxState, cache: Optional[ConditionCache] = None,
    ) -> Optional[RouteDecision]:
        """
        評估路由規則

        Args:
            state: 當前狀態
            cache: 條件快取
        Returns:
            RouteDecision or None: 如果條件滿足則返回決策
        """
        try:
            all_true = True
            total_confidence = 1.0
            reasons = []

            for condition in self.conditions:
                # 檢查快取
                cache_key = f"{condition.name}:{state.session_id}:{hash(str(state.updated_at))}"
                cached_result = cache.get(cache_key) if cache else None

                if cached_result:
                    result = cached_result
                else:
                    result = condition.evaluate(state)
                    if cache:
                        cache.set(cache_key, result)

                if not result.result:
                    all_true = False
                    break

                total_confidence *= result.confidence
                reasons.append(f"{condition.name}: {result.metadata}")

            if all_true:
                return RouteDecision(
                    target_node=self.target_node,
                    confidence=total_confidence,
                    reason=f"Rule {self.name} matched: {'; '.join(reasons)}",
                    metadata={"rule_name": self.name, "conditions": len(self.conditions)},
                )

            return None

        except Exception as e:
            logger.error(f"Error evaluating route rule {self.name}: {e}")
            return None


class ConditionalRouter:
    """條件路由器"""
    def __init__(self):
        self.rules: List[RouteRule] = []
        self.cache = ConditionCache()
        self.logger = logging.getLogger(__name__)

    def add_rule(self, rule: RouteRule) -> None:
        """添加路由規則"""
        self.rules.append(rule)
        # 按優先級排序（高優先級在前）
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.logger.info(f"Added route rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> None:
        """移除路由規則"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        self.logger.info(f"Removed route rule: {rule_name}")

    def route(self, state: AIBoxState) -> Optional[RouteDecision]:
        """
        基於狀態進行路由決策

        Args:
            state: 當前狀態
        Returns:
            RouteDecision or None: 路由決策
        """
        try:
            for rule in self.rules:
                decision = rule.evaluate(state, self.cache)
                if decision:
                    self.logger.info(f"Route decision: {decision.target_node} (rule: {rule.name})")
                    return decision

            self.logger.warning("No route rule matched for current state")
            return None

        except Exception as e:
            self.logger.error(f"Error in routing: {e}")
            return None

    def clear_cache(self) -> None:
        """清空條件快取""",
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """獲取路由器統計""",
        return {"rules_count": len(self.rules), "cache_stats": self.cache.get_stats()}


# 預定義條件類
class InputTypeCondition(BaseCondition):
    """輸入類型條件""",
    def __init__(self, target_type: str):
        super().__init__(f"input_type_{target_type}", f"檢查輸入類型是否為 {target_type}")
        self.target_type = target_type

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        result = state.input_type == self.target_type
        return ConditionResult(
            condition_name=self.name,
            result=result,
            metadata={"actual_type": state.input_type, "expected_type": self.target_type},
        )


class ComplexityCondition(BaseCondition):
    """複雜度條件""",
    def __init__(self, min_complexity: str = "simple"):
        super().__init__(f"complexity_{min_complexity}", f"檢查複雜度是否 >= {min_complexity}")
        self.complexity_levels = {"simple": 1, "medium": 2, "complex": 3}
        self.min_level = self.complexity_levels.get(min_complexity, 1)

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        if not state.semantic_analysis:
            return ConditionResult(
                condition_name=self.name, result=False, metadata={"reason": "no_semantic_analysis"}
            )

        actual_level = self.complexity_levels.get(state.semantic_analysis.complexity, 1)
        result = actual_level >= self.min_level

        return ConditionResult(
            condition_name=self.name,
            result=result,
            metadata={
                "actual_complexity": state.semantic_analysis.complexity,
                "min_complexity": list(self.complexity_levels.keys())[self.min_level - 1],
            },
        )


class ResourceCondition(BaseCondition):
    """資源條件""",
    def __init__(self, require_available: bool = True):
        super().__init__(
            f"resources_{'available' if require_available else 'unavailable'}",
            f"檢查資源{'可用' if require_available else '不可用'}",
        )
        self.require_available = require_available

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        result = state.resources_available == self.require_available,
        return ConditionResult(
            condition_name=self.name,
            result=result,
            metadata={"resources_available": state.resources_available}
        )


class PolicyCondition(BaseCondition):
    """策略條件""",
    def __init__(self, require_passed: bool = True):
        super().__init__(
            f"policy_{'passed' if require_passed else 'failed'}",
            f"檢查策略{'通過' if require_passed else '失敗'}",
        )
        self.require_passed = require_passed

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        result = state.policy_passed == self.require_passed,
        return ConditionResult(
            condition_name=self.name, result=result, metadata={"policy_passed": state.policy_passed}
        )


class CapabilityCondition(BaseCondition):
    """能力條件""",
    def __init__(self, required_capability: str, min_count: int = 1):
        super().__init__(
            f"capability_{required_capability}_{min_count}",
            f"檢查是否有至少{min_count}個{required_capability}能力",
        )
        self.required_capability = required_capability,
        self.min_count = min_count

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        matching_caps = [
            cap
            for cap in state.capability_match
            if cap.name == self.required_capability and cap.available
        ]

        result = len(matching_caps) >= self.min_count
        return ConditionResult(
            condition_name=self.name,
            result=result,
            metadata={
                "required_capability": self.required_capability,
                "available_count": len(matching_caps),
                "min_required": self.min_count,
            },
        )


class MessageCountCondition(BaseCondition):
    """消息數量條件""",
    def __init__(self, min_count: int = 1):
        super().__init__(f"message_count_{min_count}", f"檢查消息數量是否 >= {min_count}")
        self.min_count = min_count

    def evaluate(self, state: AIBoxState) -> ConditionResult:
        message_count = len(state.messages)
        result = message_count >= self.min_count,
        return ConditionResult(
            condition_name=self.name,
            result=result,
            metadata={"actual_count": message_count, "min_required": self.min_count},
        )


# 路由規則工廠
class RouteRuleFactory:
    """路由規則工廠"""
    @staticmethod
    def create_free_chat_rule() -> RouteRule:
        """創建自由對話路由規則"""
        return RouteRule(
            name="free_chat",
            conditions=[InputTypeCondition("free")],
            target_node="SimpleLLMNode",
            priority=10,
        )

    @staticmethod
    def create_assistant_rule() -> RouteRule:
        """創建助理路由規則"""
        return RouteRule(
            name="assistant_mode",
            conditions=[
                InputTypeCondition("assistant"),
                ResourceCondition(require_available=True),
                PolicyCondition(require_passed=True),
            ],
            target_node="LangGraphStateMachine",
            priority=9,
        )

    @staticmethod
    def create_agent_rule() -> RouteRule:
        """創建代理路由規則"""
        return RouteRule(
            name="agent_mode",
            conditions=[
                InputTypeCondition("agent"),
                ResourceCondition(require_available=True),
                PolicyCondition(require_passed=True),
                MessageCountCondition(min_count=1),
            ],
            target_node="LangGraphStateMachine",
            priority=8,
        )

    @staticmethod
    def create_complex_task_rule() -> RouteRule:
        """創建複雜任務路由規則"""
        return RouteRule(
            name="complex_task",
            conditions=[
                ComplexityCondition(min_complexity="medium"),
                CapabilityCondition("task_planning", min_count=1),
                ResourceCondition(require_available=True),
            ],
            target_node="TaskPlannerNode",
            priority=7,
        )


# 全局路由器實例
_conditional_router = None


def get_conditional_router() -> ConditionalRouter:
    """獲取條件路由器實例"""
    global _conditional_router
    if _conditional_router is None:
        _conditional_router = ConditionalRouter()

        # 註冊默認規則
        factory = RouteRuleFactory()
        _conditional_router.add_rule(factory.create_free_chat_rule())
        _conditional_router.add_rule(factory.create_assistant_rule())
        _conditional_router.add_rule(factory.create_agent_rule())
        _conditional_router.add_rule(factory.create_complex_task_rule())

    return _conditional_router
