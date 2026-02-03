# 代碼功能說明: 簡化模型列表服務
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 00:06 UTC+8

"""簡化模型列表服務 - 實現 SmartQ 品牌策略的前端模型簡化"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from services.api.models.llm_model import LLMModel, LLMProvider, ModelCapability, ModelStatus

logger = logging.getLogger(__name__)


class SimplifiedModelService:
    """簡化模型列表服務"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化簡化模型服務

        Args:
            config_path: 簡化模型配置文件路徑
        """
        self.config_path = (
            config_path
            or Path(__file__).parent.parent.parent.parent
            / "config"
            / "simplified_model_config.json"
        )
        self.logger = logger
        self._config = None
        self._load_config()

    def _load_config(self) -> None:
        """載入簡化模型配置""",
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                self.logger.info(f"simplified_model_config_loaded: path={self.config_path}"),
            else:
                self.logger.warning(f"simplified_model_config_not_found: path={self.config_path}")
                self._config = self._get_default_config()
        except Exception as e:
            self.logger.error(
                f"simplified_model_config_load_error: path={self.config_path}, error={str(e)}"
            )
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認簡化模型配置"""
        return {
            "frontend_model_simplification": {
                "enabled": True,
                "model_mapping": {
                    "gpt": {
                        "id": "gpt-latest",
                        "name": "GPT",
                        "provider": "openai",
                        "icon": "fa-robot",
                        "color": "text-green-400",
                        "description": "OpenAI 最新 GPT 模型",
                        "backend_model": "gpt-oss:120b-cloud",
                    },
                    "gemini": {
                        "id": "gemini-latest",
                        "name": "Gemini",
                        "provider": "google",
                        "icon": "fa-gem",
                        "color": "text-blue-400",
                        "description": "Google 最新 Gemini 模型",
                        "backend_model": "gemini-2.0-flash",
                    },
                    "ollama": {
                        "id": "ollama-local",
                        "name": "Ollama",
                        "provider": "ollama",
                        "icon": "fa-server",
                        "color": "text-purple-400",
                        "description": "本地部署模型",
                        # gpt-oss:120b-cloud 若不存在，Ollama 會 404；改為 gpt-oss:120b（常見本地版）
                        # 可透過 config/simplified_model_config.json 覆寫
                        "backend_model": "gpt-oss:120b",
                    },
                    "smartq-hci": {
                        "id": "smartq-hci",
                        "name": "SmartQ-HCI",
                        "provider": "smartq",
                        "icon": "fa-microchip",
                        "color": "text-orange-400",
                        "description": "智能融合模型 (Human-Computer Interface)",
                        "backend_model": "auto",
                    },
                },
                "auto_model": {
                    "id": "auto",
                    "name": "Auto",
                    "provider": "auto",
                    "icon": "fa-magic",
                    "color": "text-purple-400",
                    "description": "自動選擇最佳模型",
                },
            },
            "backend_routing": {
                "smartq-hci_config": {
                    "primary_models": ["gpt-oss:120b-cloud", "glm-4.7:cloud", "qwen3-next:latest"],
                    "fallback_models": ["llama3.2:latest", "glm-4.6:cloud"],
                    "selection_criteria": {
                        "performance_weight": 0.4,
                        "cost_weight": 0.3,
                        "availability_weight": 0.3,
                    },
                }
            },
        }

    def is_enabled(self) -> bool:
        """檢查簡化模型功能是否啟用"""
        return self._config.get("frontend_model_simplification", {}).get("enabled", False)

    def get_simplified_models(self) -> List[Dict[str, Any]]:
        """
        獲取簡化的前端模型列表

        Returns:
            簡化的模型列表
        """
        if not self.is_enabled():
            return []

        config = self._config["frontend_model_simplification"]
        models = []

        # 添加 Auto 模型
        auto_model = config.get("auto_model", {})
        if auto_model:
            models.append(auto_model)

        # 添加映射的模型
        for model_key, model_config in config.get("model_mapping", {}).items():
            models.append(model_config)

        return models

    def map_frontend_to_backend(self, frontend_model_id: str) -> str:
        """
        將前端模型 ID 映射到後端實際模型

        Args:
            frontend_model_id: 前端模型 ID

        Returns:
            後端實際模型 ID
        """
        if not self.is_enabled():
            return frontend_model_id

        config = self._config["frontend_model_simplification"]

        # Auto 模型直接返回
        if frontend_model_id == "auto":
            return "auto"

        # 查找映射
        model_mapping = config.get("model_mapping", {})
        for model_key, model_config in model_mapping.items():
            if model_config.get("id") == frontend_model_id:
                backend_model = model_config.get("backend_model", frontend_model_id)
                self.logger.debug(
                    f"model_mapped: frontend={frontend_model_id}, backend={backend_model}"
                )
                return backend_model

        # 如果沒有找到映射，返回原始 ID
        self.logger.warning(f"model_mapping_not_found: frontend={frontend_model_id}")
        return frontend_model_id

    def get_backend_routing_config(self, frontend_model_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取後端路由配置

        Args:
            frontend_model_id: 前端模型 ID

        Returns:
            後端路由配置
        """
        if not self.is_enabled():
            return None

        config = self._config.get("backend_routing", {})

        # SmartQ-HCI 的路由配置
        if frontend_model_id == "smartq-hci":
            return config.get("smartq-hci_config", {})

        return None

    def convert_to_llm_model_format(
        self, simplified_models: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        將簡化模型轉換為 LLMModel API 格式

        Args:
            simplified_models: 簡化模型列表

        Returns:
            LLMModel API 格式的模型列表
        """
        result = []

        for model in simplified_models:
            # 轉換為 LLMModel API 格式
            llm_model = {
                "model_id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
                "description": model.get("description", ""),
                "status": "active",
                "capabilities": ["chat", "text_generation"],
                "icon": model.get("icon"),
                "color": model.get("color"),
                "order": 0,
                "is_default": False,
                "metadata": {
                    "simplified_model": True,
                    "backend_model": model.get("backend_model"),
                    "is_smartq": model["provider"] == "smartq",
                },
            }
            result.append(llm_model)

        return result


# 全局實例
_simplified_model_service: Optional[SimplifiedModelService] = None


def get_simplified_model_service() -> SimplifiedModelService:
    """
    獲取簡化模型服務實例

    Returns:
        SimplifiedModelService 實例
    """
    global _simplified_model_service
    if _simplified_model_service is None:
        _simplified_model_service = SimplifiedModelService()
    return _simplified_model_service
