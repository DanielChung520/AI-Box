# 代碼功能說明: MoE 場景路由配置
# 創建日期: 2026-01-20
# 創建人: Daniel Chung

"""場景路由配置和模型選擇邏輯。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from system.infra.config.config import get_config_section


@dataclass
class ModelConfig:
    """模型配置"""

    model: str
    context_size: int = 131072
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    retries: int = 3
    rpm: int = 30
    concurrency: int = 5
    dimension: Optional[int] = None
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """從字典創建 ModelConfig"""
        return cls(
            model=data.get("model", ""),
            context_size=data.get("context_size", 131072),
            max_tokens=data.get("max_tokens", 4096),
            temperature=data.get("temperature", 0.7),
            timeout=data.get("timeout", 60),
            retries=data.get("retries", 3),
            rpm=data.get("rpm", 30),
            concurrency=data.get("concurrency", 5),
            dimension=data.get("dimension"),
            cost_per_1k_input=data.get("cost_per_1k_input"),
            cost_per_1k_output=data.get("cost_per_1k_output"),
        )


@dataclass
class SceneConfig:
    """場景配置"""

    scene: str
    frontend_editable: bool = False
    user_default: Optional[str] = None
    priority: List[ModelConfig] = None

    def __post_init__(self):
        if self.priority is None:
            self.priority = []

    @classmethod
    def from_dict(cls, scene: str, data: Dict[str, Any]) -> "SceneConfig":
        """從字典創建 SceneConfig"""
        priority = [ModelConfig.from_dict(m) for m in data.get("priority", [])]
        return cls(
            scene=scene,
            frontend_editable=data.get("frontend_editable", False),
            user_default=data.get("user_default"),
            priority=priority,
        )


@dataclass
class ModelSelectionResult:
    """模型選擇結果"""

    model: str
    scene: str
    context_size: int
    max_tokens: int
    temperature: float
    timeout: int
    retries: int
    rpm: int
    concurrency: int
    dimension: Optional[int]
    cost_per_1k_input: Optional[float]
    cost_per_1k_output: Optional[float]
    is_user_preference: bool = False
    fallback_used: bool = False
    original_model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "model": self.model,
            "scene": self.scene,
            "context_size": self.context_size,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "retries": self.retries,
            "rpm": self.rpm,
            "concurrency": self.concurrency,
            "dimension": self.dimension,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "is_user_preference": self.is_user_preference,
            "fallback_used": self.fallback_used,
            "original_model": self.original_model,
        }


class MoEConfigLoader:
    """MoE 配置載入器"""

    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
        self._features: Optional[Dict[str, bool]] = None

    def _load_config(self) -> Dict[str, Any]:
        """載入 MoE 配置"""
        if self._config is None:
            self._config = get_config_section("services", "moe", "model_priority", default={})
        return self._config

    def _load_features(self) -> Dict[str, bool]:
        """載入功能開關"""
        if self._features is None:
            moe_config = get_config_section("services", "moe", default={})
            self._features = moe_config.get(
                "features",
                {
                    "user_preference_enabled": True,
                    "adaptive_learning_enabled": False,
                    "cost_tracking_enabled": False,
                    "auto_fallback_enabled": True,
                },
            )
        return self._features

    def get_scene_config(self, scene: str) -> Optional[SceneConfig]:
        """獲取場景配置"""
        config = self._load_config()
        if scene in config:
            return SceneConfig.from_dict(scene, config[scene])
        return None

    def get_all_scenes(self) -> List[str]:
        """獲取所有場景"""
        config = self._load_config()
        return list(config.keys())

    def get_priority_list(self, scene: str) -> List[ModelConfig]:
        """獲取場景的模型優先級列表"""
        scene_config = self.get_scene_config(scene)
        if scene_config:
            return scene_config.priority
        return []

    def is_feature_enabled(self, feature: str) -> bool:
        """檢查功能是否啟用"""
        features = self._load_features()
        return features.get(feature, False)

    def is_user_preference_enabled(self) -> bool:
        """檢查用戶偏好是否啟用"""
        return self.is_feature_enabled("user_preference_enabled")

    def is_auto_fallback_enabled(self) -> bool:
        """檢查自動備用是否啟用"""
        return self.is_feature_enabled("auto_fallback_enabled")

    def get_model_from_env(self, scene: str) -> Optional[str]:
        """從環境變數獲取模型（環境變數優先）"""
        env_map = {
            "chat": "MOE_CHAT_MODEL",
            "semantic_understanding": "MOE_SEMANTIC_MODEL",
            "task_analysis": "MOE_TASK_MODEL",
            "orchestrator": "MOE_ORCHESTRATOR_MODEL",
            "embedding": "MOE_EMBEDDING_MODEL",
            "knowledge_graph_extraction": "MOE_KG_MODEL",
            "vision": "MOE_VISION_MODEL",
        }
        env_var = env_map.get(scene)
        if env_var:
            return os.getenv(env_var)
        return None


# 全局配置載入器實例
_moe_config_loader: Optional[MoEConfigLoader] = None


def get_moe_config_loader() -> MoEConfigLoader:
    """獲取 MoE 配置載入器（單例）"""
    global _moe_config_loader
    if _moe_config_loader is None:
        _moe_config_loader = MoEConfigLoader()
    return _moe_config_loader
