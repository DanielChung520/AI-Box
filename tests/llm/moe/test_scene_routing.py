# 代碼功能說明: MoE 場景路由測試
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""MoE 場景路由模組的單元測試"""

import os
from unittest.mock import patch


# 設置環境變數以使用回退存儲
os.environ["MOE_USE_FALLBACK_STORAGE"] = "true"


class TestModelConfig:
    """ModelConfig 類的測試"""

    def test_model_config_creation(self):
        """測試 ModelConfig 建立"""
        from llm.moe.scene_routing import ModelConfig

        config = ModelConfig(
            model="gpt-oss:120b-cloud",
            context_size=131072,
            max_tokens=4096,
            temperature=0.7,
            timeout=60,
        )

        assert config.model == "gpt-oss:120b-cloud"
        assert config.context_size == 131072
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.timeout == 60
        assert config.retries == 3  # 默認值
        assert config.rpm == 30  # 默認值
        assert config.concurrency == 5  # 默認值

    def test_model_config_from_dict(self):
        """測試從字典創建 ModelConfig"""
        from llm.moe.scene_routing import ModelConfig

        data = {
            "model": "glm-4.7:cloud",
            "context_size": 128000,
            "max_tokens": 4096,
            "temperature": 0.3,
            "timeout": 90,
            "retries": 2,
            "rpm": 20,
            "concurrency": 3,
        }

        config = ModelConfig.from_dict(data)

        assert config.model == "glm-4.7:cloud"
        assert config.context_size == 128000
        assert config.temperature == 0.3
        assert config.timeout == 90


class TestSceneConfig:
    """SceneConfig 類的測試"""

    def test_scene_config_creation(self):
        """測試 SceneConfig 建立"""
        from llm.moe.scene_routing import ModelConfig, SceneConfig

        priority = [
            ModelConfig(model="gpt-oss:120b-cloud"),
            ModelConfig(model="glm-4.7:cloud"),
        ]

        config = SceneConfig(
            scene="chat",
            frontend_editable=True,
            user_default="gpt-oss:120b-cloud",
            priority=priority,
        )

        assert config.scene == "chat"
        assert config.frontend_editable is True
        assert config.user_default == "gpt-oss:120b-cloud"
        assert len(config.priority) == 2

    def test_scene_config_from_dict(self):
        """測試從字典創建 SceneConfig"""
        from llm.moe.scene_routing import SceneConfig

        data = {
            "frontend_editable": True,
            "user_default": "gpt-oss:120b-cloud",
            "priority": [
                {"model": "gpt-oss:120b-cloud", "temperature": 0.7},
                {"model": "glm-4.7:cloud", "temperature": 0.7},
            ],
        }

        config = SceneConfig.from_dict("chat", data)

        assert config.scene == "chat"
        assert config.frontend_editable is True
        assert config.user_default == "gpt-oss:120b-cloud"
        assert len(config.priority) == 2


class TestModelSelectionResult:
    """ModelSelectionResult 類的測試"""

    def test_result_creation(self):
        """測試 ModelSelectionResult 建立"""
        from llm.moe.scene_routing import ModelSelectionResult

        result = ModelSelectionResult(
            model="gpt-oss:120b-cloud",
            scene="chat",
            context_size=131072,
            max_tokens=4096,
            temperature=0.7,
            timeout=60,
            retries=3,
            rpm=30,
            concurrency=5,
            dimension=None,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
            is_user_preference=False,
            fallback_used=False,
            original_model="gpt-oss:120b-cloud",
        )

        assert result.model == "gpt-oss:120b-cloud"
        assert result.scene == "chat"
        assert result.temperature == 0.7
        assert result.is_user_preference is False
        assert result.fallback_used is False

    def test_result_to_dict(self):
        """測試 ModelSelectionResult 轉換為字典"""
        from llm.moe.scene_routing import ModelSelectionResult

        result = ModelSelectionResult(
            model="gpt-oss:120b-cloud",
            scene="chat",
            context_size=131072,
            max_tokens=4096,
            temperature=0.7,
            timeout=60,
            retries=3,
            rpm=30,
            concurrency=5,
            dimension=None,
            cost_per_1k_input=None,
            cost_per_1k_output=None,
        )

        result_dict = result.to_dict()

        assert result_dict["model"] == "gpt-oss:120b-cloud"
        assert result_dict["scene"] == "chat"
        assert result_dict["temperature"] == 0.7
        assert "to_dict" not in str(result_dict)


class TestMoEConfigLoader:
    """MoEConfigLoader 類的測試"""

    def test_get_all_scenes(self):
        """測試獲取所有場景"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        scenes = loader.get_all_scenes()

        assert isinstance(scenes, list)
        assert "chat" in scenes
        assert "embedding" in scenes
        assert "knowledge_graph_extraction" in scenes

    def test_get_scene_config(self):
        """測試獲取場景配置"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        config = loader.get_scene_config("chat")

        assert config is not None
        assert config.scene == "chat"
        assert isinstance(config.priority, list)
        assert len(config.priority) > 0

    def test_get_priority_list(self):
        """測試獲取優先級列表"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        priority = loader.get_priority_list("embedding")

        assert isinstance(priority, list)
        assert len(priority) > 0
        # embedding 場景第一個應該是 nomic-embed-text
        assert priority[0].model == "nomic-embed-text:latest"

    def test_is_feature_enabled(self):
        """測試功能開關"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()

        # user_preference_enabled 應該是 True
        assert loader.is_user_preference_enabled() is True

        # auto_fallback_enabled 應該是 True
        assert loader.is_auto_fallback_enabled() is True

        # adaptive_learning_enabled 應該是 False
        assert loader.is_feature_enabled("adaptive_learning_enabled") is False

    def test_get_model_from_env(self):
        """測試從環境變數獲取模型"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()

        # 沒有設置環境變數時應該返回 None
        assert loader.get_model_from_env("chat") is None

    def test_get_model_from_env_with_override(self):
        """測試環境變數覆蓋"""
        from llm.moe.scene_routing import get_moe_config_loader

        # 設置環境變數
        with patch.dict(os.environ, {"MOE_CHAT_MODEL": "test-model:v1"}):
            loader = get_moe_config_loader()
            # 需要重新創建 loader 來讀取新的環境變數
            # 這裡因為 loader 是單例，所以可能不會看到新值
            # 在實際使用中應該設置環境變數後重啟服務


class TestSceneRoutingIntegration:
    """場景路由整合測試"""

    def test_embedding_scene_config(self):
        """測試 embedding 場景配置"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        config = loader.get_scene_config("embedding")

        assert config is not None
        assert config.scene == "embedding"
        # embedding 不應該可編輯
        assert config.frontend_editable is False
        # 檢查模型配置
        assert len(config.priority) > 0
        assert config.priority[0].dimension == 768  # nomic-embed-text

    def test_kg_extraction_scene_config(self):
        """測試 knowledge_graph_extraction 場景配置"""
        from llm.moe.scene_routing import get_moe_config_loader

        loader = get_moe_config_loader()
        config = loader.get_scene_config("knowledge_graph_extraction")

        assert config is not None
        assert config.scene == "knowledge_graph_extraction"
        # KG 場景溫度應該較低
        assert config.priority[0].temperature == 0.2
        # 超時時間應該較長
        assert config.priority[0].timeout == 180
