# 代碼功能說明: 決策語義提取器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""決策語義提取器 - 從決策日誌中提取可泛化的決策語義"""

from typing import Union

from agents.task_analyzer.models import DecisionLog, GroDecisionLog


def build_routing_semantic(decision_log: Union[DecisionLog, GroDecisionLog]) -> str:
    """
    構建路由語義文本

    從決策日誌中提取可泛化的決策語義，用於向量化存儲。
    支持 GRO 規範的 GroDecisionLog 和舊版 DecisionLog（向後兼容）。

    Args:
        decision_log: 決策日誌（GroDecisionLog 或 DecisionLog）

    Returns:
        路由語義文本
    """
    if isinstance(decision_log, GroDecisionLog):
        # GRO 規範的 DecisionLog
        input_sig = decision_log.input_signature
        decision = decision_log.decision

        # 從 input_signature 提取信息
        intent_type = input_sig.get("intent_type", "unknown")
        complexity = input_sig.get("complexity", "unknown")
        risk_level = input_sig.get("risk_level", "unknown")

        # 從 decision 和 metadata 提取 chosen_path
        chosen_path = "unknown"
        if decision_log.metadata:
            chosen_agent = decision_log.metadata.get("chosen_agent")
            chosen_model = decision_log.metadata.get("chosen_model")
            chosen_tools = decision_log.metadata.get("chosen_tools", [])
            if chosen_agent:
                chosen_path = chosen_agent
            elif chosen_model:
                chosen_path = chosen_model
            if chosen_tools:
                chosen_path += f"+tools({','.join(chosen_tools)})"

        semantic = f"""Intent:{intent_type}
Complexity:{complexity}
Risk:{risk_level}
State:{decision_log.state.value}
Action:{decision.action.value}
Outcome:{decision_log.outcome.value}
ChosenPath:{chosen_path}
"""
    else:
        # 舊版 DecisionLog（向後兼容）
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
