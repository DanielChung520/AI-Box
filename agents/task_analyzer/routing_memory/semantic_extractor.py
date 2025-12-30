# 代碼功能說明: 決策語義提取器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""決策語義提取器 - 從決策日誌中提取可泛化的決策語義"""

from agents.task_analyzer.models import DecisionLog


def build_routing_semantic(decision_log: DecisionLog) -> str:
    """
    構建路由語義文本

    從決策日誌中提取可泛化的決策語義，用於向量化存儲。

    Args:
        decision_log: 決策日誌

    Returns:
        路由語義文本
    """
    router_output = decision_log.router_output
    decision_engine = decision_log.decision_engine

    # 構建語義文本（不是語言語義，而是決策語義）
    chosen_path = decision_engine.chosen_agent or decision_engine.chosen_model or "unknown"
    if decision_engine.chosen_tools:
        chosen_path += f"+tools({','.join(decision_engine.chosen_tools)})"

    semantic = f"""Intent:{router_output.intent_type}
Complexity:{router_output.complexity}
Risk:{router_output.risk_level}
NeedsAgent:{router_output.needs_agent}
NeedsTools:{router_output.needs_tools}
ChosenPath:{chosen_path}
"""

    return semantic.strip()
