# 代碼功能說明: MoE 用戶偏好服務測試
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE 用戶偏好服務的單元測試"""

import os
from unittest.mock import patch

import pytest

# 設置環境變數以使用回退存儲
os.environ["MOE_USE_FALLBACK_STORAGE"] = "true"


class TestMoEUserPreferenceService:
    """MoEUserPreferenceService 的測試"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每個測試前設置"""
        from services.api.services.moe_user_preference_service import (
            _fallback_storage,
            get_moe_user_preference_service,
        )

        self.service = get_moe_user_preference_service()
        self.test_user = "test_user_moe_001"
        self.test_scene = "chat"
        self.test_model = "glm-4.7:cloud"

        # 清理測試數據
        self.service.delete_preference(self.test_user, self.test_scene)
        _fallback_storage.clear()

    def test_set_preference(self):
        """測試設置用戶偏好"""
        result = self.service.set_preference(self.test_user, self.test_scene, self.test_model)

        assert result is not None
        assert result["user_id"] == self.test_user
        assert result["scene"] == self.test_scene
        assert result["model"] == self.test_model
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_preference(self):
        """測試獲取用戶偏好"""
        # 先設置
        self.service.set_preference(self.test_user, self.test_scene, self.test_model)

        # 後獲取
        result = self.service.get_preference(self.test_user, self.test_scene)

        assert result is not None
        assert result["user_id"] == self.test_user
        assert result["scene"] == self.test_scene
        assert result["model"] == self.test_model

    def test_get_preference_not_found(self):
        """測試獲取不存在的用戶偏好"""
        result = self.service.get_preference("nonexistent_user", "chat")

        assert result is None

    def test_delete_preference(self):
        """測試刪除用戶偏好"""
        # 先設置
        self.service.set_preference(self.test_user, self.test_scene, self.test_model)

        # 後刪除
        result = self.service.delete_preference(self.test_user, self.test_scene)

        assert result is True

        # 確認已刪除
        fetch_result = self.service.get_preference(self.test_user, self.test_scene)
        assert fetch_result is None

    def test_delete_nonexistent_preference(self):
        """測試刪除不存在的用戶偏好"""
        result = self.service.delete_preference("nonexistent_user", "chat")

        assert result is False

    def test_get_all_preferences(self):
        """測試獲取用戶所有偏好"""
        # 設置多個場景的偏好
        self.service.set_preference(self.test_user, "chat", "glm-4.7:cloud")
        self.service.set_preference(self.test_user, "embedding", "bge-large:latest")

        result = self.service.get_all_preferences(self.test_user)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_user_preference_for_scene(self):
        """測試簡化接口"""
        self.service.set_preference(self.test_user, self.test_scene, self.test_model)

        result = self.service.get_user_preference_for_scene(self.test_user, self.test_scene)

        assert result == self.test_model

    def test_overwrite_preference(self):
        """測試覆蓋用戶偏好"""
        # 第一次設置
        self.service.set_preference(self.test_user, self.test_scene, "model_v1")

        # 第二次設置（覆蓋）
        result = self.service.set_preference(self.test_user, self.test_scene, "model_v2")

        assert result["model"] == "model_v2"

        # 確認已更新
        fetch_result = self.service.get_preference(self.test_user, self.test_scene)
        assert fetch_result["model"] == "model_v2"


class TestUserPreferenceModule:
    """user_preference 模組的測試"""

    def test_get_user_preference(self):
        """測試 get_user_preference 函數"""
        from llm.moe.user_preference import get_moe_user_preference_service, get_user_preference

        service = get_moe_user_preference_service()
        service.set_preference("test_user", "chat", "qwen3-next:latest")

        try:
            result = get_user_preference("test_user", "chat")

            assert result == "qwen3-next:latest"
        finally:
            service.delete_preference("test_user", "chat")

    def test_get_user_preference_not_found(self):
        """測試 get_user_preference 返回 None"""
        from llm.moe.user_preference import get_user_preference

        result = get_user_preference("nonexistent_user", "chat")

        assert result is None

    def test_use_fallback_env_var(self):
        """測試環境變數控制回退存儲"""
        from llm.moe.user_preference import _use_fallback

        # 設置了 MOE_USE_FALLBACK_STORAGE=true
        assert _use_fallback() is True

        # 測試不同值
        with patch.dict(os.environ, {"MOE_USE_FALLBACK_STORAGE": "false"}):
            # 需要重新加載模組來測試
            import importlib

            from llm.moe import user_preference as up_module

            importlib.reload(up_module)
            assert up_module._use_fallback() is False

        # 恢復設置
        importlib.reload(up_module)
