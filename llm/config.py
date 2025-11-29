# 代碼功能說明: LLM 負載均衡配置載入工具
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""載入 LLM 負載均衡配置並提供配置結構。"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.task_analyzer.models import LLMProvider
from core.config import get_config_section


def load_load_balancer_config() -> Dict[str, Any]:
    """
    從配置文件載入負載均衡配置。

    Returns:
        負載均衡配置字典
    """
    config = get_config_section("llm", "load_balancer", default={})
    return config or {}


def get_load_balancer_strategy() -> str:
    """
    獲取負載均衡策略。

    Returns:
        策略名稱（round_robin, weighted, least_connections, latency_based, response_time_based）
    """
    config = load_load_balancer_config()
    return config.get("strategy", "round_robin")


def get_load_balancer_weights() -> Dict[LLMProvider, int]:
    """
    獲取提供商權重配置。

    Returns:
        提供商權重字典
    """
    config = load_load_balancer_config()
    weights_config = config.get("weights", {})
    weights: Dict[LLMProvider, int] = {}
    for provider_str, weight in weights_config.items():
        try:
            provider = LLMProvider(provider_str)
            weights[provider] = int(weight)
        except (ValueError, KeyError):
            continue
    return weights


def get_load_balancer_cooldown() -> int:
    """
    獲取故障冷卻時間（秒）。

    Returns:
        冷卻時間（秒）
    """
    config = load_load_balancer_config()
    return config.get("cooldown_seconds", 30)


def get_load_balancer_providers() -> List[LLMProvider]:
    """
    獲取要使用的 LLM 提供商列表。

    Returns:
        提供商列表
    """
    config = load_load_balancer_config()
    providers_config = config.get("providers", [])
    if not providers_config:
        # 默認使用所有提供商
        return list(LLMProvider)

    providers: List[LLMProvider] = []
    for provider_str in providers_config:
        try:
            provider = LLMProvider(provider_str)
            providers.append(provider)
        except (ValueError, KeyError):
            continue
    return providers


def load_health_check_config() -> Dict[str, Any]:
    """
    從配置文件載入健康檢查配置。

    Returns:
        健康檢查配置字典
    """
    config = get_config_section("llm", "health_check", default={})
    return config or {}


def get_health_check_interval() -> float:
    """
    獲取健康檢查間隔（秒）。

    Returns:
        健康檢查間隔（秒）
    """
    config = load_health_check_config()
    return float(config.get("interval", 60.0))


def get_health_check_timeout() -> float:
    """
    獲取健康檢查超時（秒）。

    Returns:
        健康檢查超時（秒）
    """
    config = load_health_check_config()
    return float(config.get("timeout", 5.0))


def get_health_check_failure_threshold() -> int:
    """
    獲取失敗閾值（連續失敗次數）。

    Returns:
        失敗閾值
    """
    config = load_health_check_config()
    return int(config.get("failure_threshold", 3))
