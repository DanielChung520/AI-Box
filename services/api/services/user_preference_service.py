"""
代碼功能說明: 用戶偏好（收藏模型）服務（Redis 優先、fallback memory）
創建日期: 2025-12-13 17:28:02 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 17:42:45 (UTC+8)
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence

import structlog

from database.redis.client import get_redis_client

logger = structlog.get_logger(__name__)


class UserPreferenceService:
    """用戶偏好服務（MVP：收藏模型）。"""

    def __init__(self) -> None:
        self._fallback_favorite_models: Dict[str, List[str]] = {}
        self._redis = None
        try:
            self._redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("user_preference_redis_unavailable", error=str(exc))

    @staticmethod
    def _favorite_models_key(user_id: str) -> str:
        return f"user:{user_id}:favorite_models"

    def get_favorite_models(self, *, user_id: str) -> List[str]:
        """取得收藏模型列表（保序、去重後）。"""
        key = self._favorite_models_key(user_id)

        if self._redis is not None:
            try:
                raw = self._redis.get(key)  # type: ignore[union-attr]
                if raw is not None:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="ignore")
                    if not isinstance(raw, str):
                        raw = str(raw)
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return self._normalize_model_ids(parsed)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "get_favorite_models_redis_failed", user_id=user_id, error=str(exc)
                )

        return self._fallback_favorite_models.get(user_id, [])

    def set_favorite_models(self, *, user_id: str, model_ids: List[str]) -> List[str]:
        """更新收藏模型列表（回傳實際保存的清單）。"""
        normalized = self._normalize_model_ids(model_ids)
        key = self._favorite_models_key(user_id)

        if self._redis is not None:
            try:
                self._redis.set(key, json.dumps(normalized, ensure_ascii=False))
                return normalized
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "set_favorite_models_redis_failed", user_id=user_id, error=str(exc)
                )

        self._fallback_favorite_models[user_id] = normalized
        return normalized

    @staticmethod
    def _normalize_model_ids(model_ids: Sequence[object]) -> List[str]:
        seen: set[str] = set()
        normalized: List[str] = []
        for mid in model_ids:
            value = str(mid).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized


_service: Optional[UserPreferenceService] = None


def get_user_preference_service() -> UserPreferenceService:
    global _service
    if _service is None:
        _service = UserPreferenceService()
    return _service
