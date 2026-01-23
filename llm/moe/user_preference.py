# 代碼功能說明: MoE 用戶偏好讀取模組
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE 用戶偏好讀取介面"""

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.api.services.moe_user_preference_service import MoEUserPreferenceService


_service: Optional["MoEUserPreferenceService"] = None


def _use_fallback() -> bool:
    """檢查是否應該使用回退存儲"""
    return os.getenv("MOE_USE_FALLBACK_STORAGE", "false").lower() == "true"


def get_moe_user_preference_service() -> Optional["MoEUserPreferenceService"]:
    """獲取 MoE 用戶偏好服務實例（單例）"""
    global _service
    if _service is None:
        if _use_fallback():
            try:
                from services.api.services.moe_user_preference_service import (
                    MoEUserPreferenceService,
                )

                _service = MoEUserPreferenceService()
            except Exception:
                pass
        else:
            try:
                from services.api.services.moe_user_preference_service import (
                    MoEUserPreferenceService,
                )

                _service = MoEUserPreferenceService()
            except Exception:
                pass
    return _service


def get_user_preference(user_id: str, scene: str) -> Optional[str]:
    """
    獲取用戶在特定場景的偏好模型

    Args:
        user_id: 用戶 ID
        scene: 場景名稱

    Returns:
        偏好的模型名稱，如果不存在則返回 None
    """
    service = get_moe_user_preference_service()
    if service is None:
        return None

    try:
        return service.get_user_preference_for_scene(user_id, scene)
    except Exception:
        return None
