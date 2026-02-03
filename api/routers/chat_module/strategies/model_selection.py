# 代碼功能說明: Chat 模型選擇策略（調用 MoE select_model）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""select_model：根據 model_selector 與 user_id 返回選中的模型信息。"""

from typing import Any, Optional

from services.api.models.chat import ModelSelector


def select_model(
    model_selector: ModelSelector,
    user_id: Optional[str] = None,
) -> Any:
    """
    根據 model_selector 與 user_id 選擇模型；內部調用 MoE select_model("chat", user_id)。

    Args:
        model_selector: 模型選擇器（auto/manual/favorite）
        user_id: 用戶 ID（用於用戶偏好）

    Returns:
        ModelSelectionResult（或等效結構）：含 model、scene、temperature 等
    """
    from api.routers.chat_module.dependencies import get_moe_manager

    moe = get_moe_manager()
    result = moe.select_model(
        scene="chat",
        user_id=user_id,
        context=None,
    )
    return result
