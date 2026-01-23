# 代碼功能說明: MoE Manager 測試
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE Manager 的單元測試"""

import os

import pytest

# 設置環境變數以使用回退存儲
os.environ["MOE_USE_FALLBACK_STORAGE"] = "true"


class TestLLMMoEManagerSelectModel:
    """LLMMoEManager.select_model() 的測試"""

    def test_select_chat_model(self):
        """測試選擇 chat 場景模型"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = moe.select_model("chat")

        assert result is not None
        assert result.model == "gpt-oss:120b-cloud"
        assert result.scene == "chat"
        assert result.temperature == 0.7

    def test_select_embedding_model(self):
        """測試選擇 embedding 場景模型"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = moe.select_model("embedding")

        assert result is not None
        assert result.model == "nomic-embed-text:latest"
        assert result.scene == "embedding"
        assert result.timeout == 120

    def test_select_kg_extraction_model(self):
        """測試選擇 knowledge_graph_extraction 場景模型"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = moe.select_model("knowledge_graph_extraction")

        assert result is not None
        assert result.model == "gpt-oss:120b-cloud"
        assert result.scene == "knowledge_graph_extraction"
        assert result.temperature == 0.2  # KG 場景使用較低溫度
        assert result.timeout == 180  # KG 場景使用較長超時

    def test_select_unknown_scene_raises_error(self):
        """測試選擇未知場景拋出錯誤"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()

        with pytest.raises(ValueError, match="Scene config not found"):
            moe.select_model("unknown_scene")

    def test_select_model_with_user_preference(self):
        """測試選擇模型時使用用戶偏好"""
        from llm.moe.moe_manager import LLMMoEManager
        from llm.moe.user_preference import get_moe_user_preference_service

        # 設置用戶偏好
        service = get_moe_user_preference_service()
        service.set_preference("test_user_001", "chat", "glm-4.7:cloud")

        try:
            moe = LLMMoEManager()
            result = moe.select_model("chat", user_id="test_user_001")

            assert result is not None
            assert result.model == "glm-4.7:cloud"
            assert result.is_user_preference is True
        finally:
            # 清理
            service.delete_preference("test_user_001", "chat")

    def test_select_model_without_user_preference(self):
        """測試選擇模型時沒有用戶偏好"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = moe.select_model("chat", user_id="nonexistent_user")

        assert result is not None
        assert result.model == "gpt-oss:120b-cloud"  # 默認模型
        assert result.is_user_preference is False

    def test_select_model_returns_full_config(self):
        """測試選擇模型返回完整配置"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = moe.select_model("chat")

        assert result is not None
        # 檢查所有必要欄位
        assert result.model is not None
        assert result.scene is not None
        assert result.context_size is not None
        assert result.max_tokens is not None
        assert result.temperature is not None
        assert result.timeout is not None
        assert result.retries is not None
        assert result.rpm is not None
        assert result.concurrency is not None

        # 檢查 to_dict 方法
        result_dict = result.to_dict()
        assert "model" in result_dict
        assert "scene" in result_dict
        assert "temperature" in result_dict
        assert "timeout" in result_dict


class TestLLMMoEManagerGetScenes:
    """LLMMoEManager.get_available_scenes() 的測試"""

    def test_get_available_scenes(self):
        """測試獲取可用場景列表"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        scenes = moe.get_available_scenes()

        assert isinstance(scenes, list)
        assert len(scenes) == 6
        assert "chat" in scenes
        assert "semantic_understanding" in scenes
        assert "task_analysis" in scenes
        assert "orchestrator" in scenes
        assert "embedding" in scenes
        assert "knowledge_graph_extraction" in scenes


class TestLLMMoEManagerGetSceneConfig:
    """LLMMoEManager.get_scene_config() 的測試"""

    def test_get_chat_scene_config(self):
        """測試獲取 chat 場景配置"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        config = moe.get_scene_config("chat")

        assert config is not None
        assert config.scene == "chat"
        assert config.frontend_editable is True  # chat 場景可編輯

    def test_get_kg_scene_config(self):
        """測試獲取 knowledge_graph_extraction 場景配置"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        config = moe.get_scene_config("knowledge_graph_extraction")

        assert config is not None
        assert config.scene == "knowledge_graph_extraction"
        assert config.frontend_editable is False  # KG 場景不可編輯
        assert len(config.priority) > 0

    def test_get_unknown_scene_config(self):
        """測試獲取未知場景配置返回 None"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        config = moe.get_scene_config("unknown_scene")

        assert config is None


class TestLLMMoEManagerUserPreference:
    """LLMMoEManager 用戶偏好相關測試"""

    def test_get_user_preference_when_enabled(self):
        """測試獲取用戶偏好（當功能開啟時）"""
        from llm.moe.moe_manager import LLMMoEManager
        from llm.moe.user_preference import get_moe_user_preference_service

        # 設置用戶偏好
        service = get_moe_user_preference_service()
        service.set_preference("test_user", "chat", "qwen3-next:latest")

        try:
            moe = LLMMoEManager()
            preference = moe._get_user_preference("test_user", "chat")

            assert preference == "qwen3-next:latest"
        finally:
            service.delete_preference("test_user", "chat")

    def test_get_user_preference_when_disabled(self):
        """測試獲取用戶偏好（當功能關閉時）"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()

        # 沒有設置偏好時應該返回 None
        preference = moe._get_user_preference("nonexistent_user", "chat")

        assert preference is None


class TestLLMMoEManagerIntegration:
    """LLM MoE Manager 整合測試"""

    def test_all_scenes_return_valid_models(self):
        """測試所有場景都返回有效模型"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        scenes = moe.get_available_scenes()

        for scene in scenes:
            result = moe.select_model(scene)
            assert result is not None, f"Scene {scene} returned None"
            assert result.model is not None, f"Scene {scene} has no model"
            assert result.scene == scene, f"Scene {scene} has wrong scene name"

    def test_fallback_scenario(self):
        """測試備用模型場景"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()

        # 選擇一個有多個備用模型的場景
        result = moe.select_model("chat")

        assert result is not None
        assert result.fallback_used is False  # 第一個模型可用
        # 如果需要測試 fallback，需要模擬第一個模型不可用

    def test_model_config_from_different_scenes(self):
        """測試不同場景的模型配置差異"""
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()

        chat_result = moe.select_model("chat")
        kg_result = moe.select_model("knowledge_graph_extraction")

        # Chat 場景溫度較高
        assert chat_result.temperature == 0.7
        # KG 場景溫度較低
        assert kg_result.temperature == 0.2

        # Chat 超時較短
        assert chat_result.timeout == 60
        # KG 超時較長
        assert kg_result.timeout == 180
