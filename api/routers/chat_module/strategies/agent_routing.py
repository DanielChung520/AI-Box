# 代碼功能說明: Chat Agent 路由策略（佔位）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""Agent 路由策略；佔位，後續可接 Task Analyzer / Agent Registry。"""

from typing import Any, Dict, Optional


def route_agent(
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    佔位：根據用戶消息與上下文決定是否路由到外部 Agent。

    Args:
        user_message: 用戶消息內容
        context: 可選上下文

    Returns:
        None 或 Agent 路由結果字典
    """
    return None
