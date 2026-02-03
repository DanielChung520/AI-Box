# 代碼功能說明: Chat 響應格式化策略（佔位）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""響應格式化策略；佔位，後續可統一包裝 routing/observability。"""

from typing import Any, Dict, Optional


def format_chat_response(
    content: str,
    routing: Dict[str, Any],
    observability: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    佔位：將 content、routing、observability 組裝為統一響應結構。

    Args:
        content: 模型回覆內容
        routing: 路由結果
        observability: 觀測欄位（可選）

    Returns:
        響應字典
    """
    return {
        "content": content,
        "routing": routing,
        "observability": observability or {},
    }
