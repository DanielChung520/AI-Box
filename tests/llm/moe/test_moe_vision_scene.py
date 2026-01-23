# 代碼功能說明: MoE Vision 場景配置測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""MoE Vision 場景配置測試 - 驗證 vision 場景的模型選擇邏輯

測試場景：
1. Vision 場景配置載入
2. Vision 模型優先級選擇
3. Vision 環境變數覆蓋
4. Vision 與其他場景的區別
"""

import os
from unittest.mock import patch

import pytest


class TestVisionSceneConfig:
    """測試 Vision 場景配置"""

    def test_vision_scene_exists(self):
        """測試 Vision 場景存在於配置中"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        scenes = loader.get_all_scenes()

        assert "vision" in scenes, "Vision 場景應該存在於配置中"

    def test_vision_scene_config(self):
        """測試 Vision 場景配置結構"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        scene_config = loader.get_scene_config("vision")

        assert scene_config is not None, "Vision 場景配置不應為 None"
        assert scene_config.scene == "vision"
        assert scene_config.frontend_editable is False, "Vision 場景不應允許前端編輯"

    def test_vision_model_priority(self):
        """測試 Vision 場景模型優先級"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        priority_list = loader.get_priority_list("vision")

        assert len(priority_list) > 0, "Vision 場景應該有模型優先級列表"

        first_model = priority_list[0]
        assert "qwen3-vl" in first_model.model, "首選模型應該是 qwen3-vl 系列"

    def test_vision_model_config_details(self):
        """測試 Vision 場景模型配置詳情"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        priority_list = loader.get_priority_list("vision")

        if len(priority_list) > 0:
            first_model = priority_list[0]
            assert first_model.context_size >= 16384, "Vision 模型上下文窗口應該足夠大"
            assert first_model.temperature == 0.3, "Vision 模型溫度應為 0.3"
            assert first_model.timeout >= 90, "Vision 模型超時應該足夠長"


class TestVisionEnvOverride:
    """測試 Vision 環境變數覆蓋"""

    def test_vision_env_variable_exists(self):
        """測試 Vision 環境變數映射存在"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        env_model = loader.get_model_from_env("vision")

        assert env_model is None or isinstance(env_model, str), "環境變數返回值應該是字串或 None"

    def test_vision_env_override(self):
        """測試 Vision 環境變數覆蓋配置"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()

        with patch.dict(os.environ, {"MOE_VISION_MODEL": "custom-vision-model"}):
            env_model = loader.get_model_from_env("vision")
            assert env_model == "custom-vision-model", "環境變數應該覆蓋模型選擇"


class TestVisionSceneIntegration:
    """測試 Vision 場景集成"""

    def test_vision_scene_selection(self):
        """測試 Vision 場景選擇邏輯"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        scene_config = loader.get_scene_config("vision")

        assert scene_config is not None
        assert len(scene_config.priority) >= 1

        first_model = scene_config.priority[0]
        assert "qwen3-vl" in first_model.model

    def test_vision_fallback_mechanism(self):
        """測試 Vision 場景回退機制"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        priority_list = loader.get_priority_list("vision")

        if len(priority_list) >= 2:
            first_model = priority_list[0]
            second_model = priority_list[1]

            assert first_model.model != second_model.model, "回退模型應該不同"
            assert first_model.timeout >= second_model.timeout, "首選模型超時應該更長"


class TestVisionVsOtherScenes:
    """測試 Vision 場景與其他場景的區別"""

    def test_vision_not_editable(self):
        """測試 Vision 場景不可編輯"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        vision_config = loader.get_scene_config("vision")
        chat_config = loader.get_scene_config("chat")

        assert vision_config is not None
        assert chat_config is not None

        assert vision_config.frontend_editable is False, "Vision 不應允許前端編輯"
        assert chat_config.frontend_editable is True, "Chat 應該允許前端編輯"

    def test_vision_model_type(self):
        """測試 Vision 場景使用 VLM 模型"""
        from llm.moe.scene_routing import MoEConfigLoader

        loader = MoEConfigLoader()
        vision_priority = loader.get_priority_list("vision")
        embedding_priority = loader.get_priority_list("embedding")

        vision_models = [m.model for m in vision_priority]
        embedding_models = [m.model for m in embedding_priority]

        assert any("qwen3-vl" in m for m in vision_models), "Vision 應該使用 VL 模型"
        assert not any("qwen3-vl" in m for m in embedding_models), "Embedding 不應使用 VL 模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
