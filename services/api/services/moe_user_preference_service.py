# 代碼功能說明: MoE 用戶偏好服務
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE 用戶偏好服務 - 管理用戶在各場景的模型偏好設定"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "user_model_preferences"

# 全局客戶端實例
_arangodb_client: Optional[ArangoDBClient] = None

# 內存回退存儲
_fallback_storage: Dict[str, Dict[str, Any]] = {}


def get_arangodb_client() -> ArangoDBClient:
    """獲取 ArangoDB 客戶端實例"""
    global _arangodb_client
    if _arangodb_client is None:
        _arangodb_client = ArangoDBClient()
    return _arangodb_client


def _use_fallback() -> bool:
    """檢查是否應該使用回退存儲"""
    return os.getenv("MOE_USE_FALLBACK_STORAGE", "false").lower() == "true"


class MoEUserPreferenceService:
    """MoE 用戶偏好服務 - 存取用戶在各場景的模型偏好"""

    def __init__(self):
        self._client = None
        self._db = None
        self._collection = None
        self._init_collection()

    def _init_collection(self):
        """初始化 ArangoDB collection"""
        try:
            self._client = get_arangodb_client()
            self._db = self._client.db
            self._collection = self._db.collection(COLLECTION_NAME)
            logger.info("moe_user_preference_collection_initialized", collection=COLLECTION_NAME)
        except Exception as e:
            logger.warning(
                "failed_to_init_moe_user_preference_collection",
                error=str(e),
                message="ArangoDB 不可用，將使用內存回退",
            )
            self._collection = None
            if _use_fallback():
                logger.info("using_fallback_storage_for_user_preferences")

    def _ensure_collection(self):
        """確保 collection 存在"""
        if self._collection is None and not _use_fallback():
            self._init_collection()
        if self._collection is None and not _use_fallback():
            raise RuntimeError(f"Collection '{COLLECTION_NAME}' is not available")

    def _make_doc_key(self, user_id: str, scene: str) -> str:
        return f"{user_id}_{scene}"

    def get_preference(self, user_id: str, scene: str) -> Optional[Dict[str, Any]]:
        """
        獲取用戶在特定場景的模型偏好

        Args:
            user_id: 用戶 ID
            scene: 場景名稱

        Returns:
            偏好配置，如果不存在則返回 None
        """
        # 先嘗試使用回退存儲
        if _use_fallback():
            doc_key = self._make_doc_key(user_id, scene)
            if doc_key in _fallback_storage:
                doc = _fallback_storage[doc_key]
                return {
                    "user_id": doc.get("user_id"),
                    "scene": doc.get("scene"),
                    "model": doc.get("model"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                }
            return None

        try:
            self._ensure_collection()
            doc = self._collection.get(self._make_doc_key(user_id, scene))
            if doc:
                return {
                    "user_id": doc.get("user_id"),
                    "scene": doc.get("scene"),
                    "model": doc.get("model"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at"),
                }
        except Exception as e:
            logger.debug(
                "get_user_preference_failed",
                user_id=user_id,
                scene=scene,
                error=str(e),
            )
        return None

    def set_preference(
        self,
        user_id: str,
        scene: str,
        model: str,
    ) -> Dict[str, Any]:
        """
        設置用戶在特定場景的模型偏好

        Args:
            user_id: 用戶 ID
            scene: 場景名稱
            model: 偏好的模型名稱

        Returns:
            設置的偏好配置
        """
        now = datetime.utcnow().isoformat()
        doc_key = self._make_doc_key(user_id, scene)
        doc = {
            "_key": doc_key,
            "user_id": user_id,
            "scene": scene,
            "model": model,
            "created_at": now,
            "updated_at": now,
        }

        # 使用回退存儲
        if _use_fallback():
            _fallback_storage[doc_key] = doc
            logger.info(
                "user_preference_set_fallback",
                user_id=user_id,
                scene=scene,
                model=model,
            )
            return {
                "user_id": user_id,
                "scene": scene,
                "model": model,
                "created_at": now,
                "updated_at": now,
            }

        try:
            self._ensure_collection()
            self._collection.insert(doc, overwrite=True)
            logger.info(
                "user_preference_set",
                user_id=user_id,
                scene=scene,
                model=model,
            )
            return {
                "user_id": user_id,
                "scene": scene,
                "model": model,
                "created_at": now,
                "updated_at": now,
            }
        except Exception as e:
            logger.error(
                "set_user_preference_failed",
                user_id=user_id,
                scene=scene,
                model=model,
                error=str(e),
            )
            raise

    def delete_preference(self, user_id: str, scene: str) -> bool:
        """
        刪除用戶在特定場景的模型偏好

        Args:
            user_id: 用戶 ID
            scene: 場景名稱

        Returns:
            是否成功刪除
        """
        doc_key = self._make_doc_key(user_id, scene)

        # 使用回退存儲
        if _use_fallback():
            if doc_key in _fallback_storage:
                del _fallback_storage[doc_key]
                logger.info(
                    "user_preference_deleted_fallback",
                    user_id=user_id,
                    scene=scene,
                )
                return True
            return False

        try:
            self._ensure_collection()
            self._collection.delete(doc_key)
            logger.info(
                "user_preference_deleted",
                user_id=user_id,
                scene=scene,
            )
            return True
        except Exception as e:
            logger.debug(
                "delete_user_preference_failed",
                user_id=user_id,
                scene=scene,
                error=str(e),
            )
            return False

    def get_all_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取用戶所有場景的模型偏好

        Args:
            user_id: 用戶 ID

        Returns:
            偏好配置列表
        """
        # 使用回退存儲
        if _use_fallback():
            result = []
            for doc in _fallback_storage.values():
                if doc.get("user_id") == user_id:
                    result.append(
                        {
                            "user_id": doc.get("user_id"),
                            "scene": doc.get("scene"),
                            "model": doc.get("model"),
                            "created_at": doc.get("created_at"),
                            "updated_at": doc.get("updated_at"),
                        }
                    )
            return result

        try:
            self._ensure_collection()
            query = """
            FOR doc IN @@collection
                FILTER doc.user_id == @user_id
                RETURN {
                    "user_id": doc.user_id,
                    "scene": doc.scene,
                    "model": doc.model,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at
                }
            """
            cursor = self._db.aql.execute(
                query,
                bind_vars={"@collection": COLLECTION_NAME, "user_id": user_id},
            )
            return list(cursor)
        except Exception as e:
            logger.error(
                "get_all_user_preferences_failed",
                user_id=user_id,
                error=str(e),
            )
            return []

    def get_user_preference_for_scene(self, user_id: str, scene: str) -> Optional[str]:
        """
        獲取用戶在特定場景的偏好模型名稱（簡化接口）

        Args:
            user_id: 用戶 ID
            scene: 場景名稱

        Returns:
            偏好的模型名稱，如果不存在則返回 None
        """
        preference = self.get_preference(user_id, scene)
        if preference:
            return preference.get("model")
        return None


_service: Optional[MoEUserPreferenceService] = None


def get_moe_user_preference_service() -> MoEUserPreferenceService:
    """獲取 MoE 用戶偏好服務實例（單例）"""
    global _service
    if _service is None:
        _service = MoEUserPreferenceService()
    return _service
