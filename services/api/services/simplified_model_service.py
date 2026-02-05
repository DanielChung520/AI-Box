# 代碼功能說明: 簡化模型列表服務
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03 UTC+8

"""簡化模型列表服務 - 實現 SmartQ 品牌策略的前端模型簡化"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path


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
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self) -> None:
        """載入簡化模型配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                self.logger.info(f"simplified_model_config_loaded: path={self.config_path}")
            else:
                self.logger.warning(f"simplified_model_config_not_found: path={self.config_path}")
                self._config = self._get_default_config()
        except Exception as e:
            self.logger.error(
                f"simplified_model_config_load_error: path={self.config_path}, error={str(e)}"
            )
            self._config = self._get_default_config()

    def _save_config(self) -> bool:
        """保存簡化模型配置到文件

        Returns:
            是否保存成功
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"simplified_model_config_saved: path={self.config_path}")
            return True
        except Exception as e:
            self.logger.error(
                f"simplified_model_config_save_error: path={self.config_path}, error={str(e)}"
            )
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認簡化模型配置"""
        return {
            "frontend_model_simplification": {
                "enabled": True,
                "model_mapping": {
                    "auto": {
                        "id": "auto",
                        "name": "1. 自動",
                        "provider": "auto",
                        "icon": "fa-magic",
                        "color": "text-purple-400",
                        "description": "自動選擇最佳模型（依據 config 中的 model_priority）",
                        "status": "active",
                    },
                    "chatgpt": {
                        "id": "chatgpt",
                        "name": "2. ChatGPT",
                        "provider": "openai",
                        "icon": "fa-robot",
                        "color": "text-green-400",
                        "description": "OpenAI ChatGPT 模型",
                        "backend_model": "gpt-oss:120b-cloud",
                        "status": "inactive",
                        "inactive_reason": "尚未設定 API Key",
                    },
                    "gemini": {
                        "id": "gemini",
                        "name": "3. Gemini",
                        "provider": "google",
                        "icon": "fa-gem",
                        "color": "text-blue-400",
                        "description": "Google Gemini 模型",
                        "backend_model": "gemini-2.0-flash",
                        "status": "inactive",
                        "inactive_reason": "尚未設定 API Key",
                    },
                    "claude": {
                        "id": "claude",
                        "name": "4. Claude",
                        "provider": "anthropic",
                        "icon": "fa-brain",
                        "color": "text-orange-400",
                        "description": "Anthropic Claude 模型",
                        "backend_model": "claude-3-5-sonnet",
                        "status": "inactive",
                        "inactive_reason": "尚未設定 API Key",
                    },
                    "grok": {
                        "id": "grok",
                        "name": "5. Grok",
                        "provider": "xai",
                        "icon": "fa-bolt",
                        "color": "text-yellow-400",
                        "description": "xAI Grok 模型",
                        "backend_model": "grok-2",
                        "status": "inactive",
                        "inactive_reason": "尚未設定 API Key",
                    },
                    "ollama": {
                        "id": "ollama-local",
                        "name": "6. Ollama-Local",
                        "provider": "ollama",
                        "icon": "fa-server",
                        "color": "text-purple-400",
                        "description": "本地部署模型",
                        "backend_model_priority": [
                            "gpt-oss:120b",
                            "llama3.2-vision:90b",
                            "qwen3:32b",
                        ],
                        "status": "active",
                    },
                    "smartq-hci": {
                        "id": "smartq-hci",
                        "name": "7. SmartQ",
                        "provider": "smartq",
                        "icon": "fa-microchip",
                        "color": "text-orange-400",
                        "description": "SmartQ-HCI 智能融合模型",
                        "backend_model": "auto",
                        "moe_routing": {
                            "enabled": True,
                            "scene": "chat",
                            "fallback_strategy": "cost_performance_balance",
                        },
                        "status": "active",
                    },
                },
            },
        }

    def is_enabled(self) -> bool:
        """檢查簡化模型功能是否啟用"""
        return self._config.get("frontend_model_simplification", {}).get("enabled", False)

    def get_simplified_models(self) -> List[Dict[str, Any]]:
        """
        獲取簡化的前端模型列表

        Returns:
            簡化的模型列表（頂級選項，不包含 sub_models）
        """
        if not self.is_enabled():
            return []

        config = self._config.get("frontend_model_simplification", {})
        if not config:
            return []

        model_mapping = config.get("model_mapping", {})
        models = []

        for key, model_config in model_mapping.items():
            # 創建頂級模型項目（不包含 sub_models 和 backend_model_priority）
            top_level_model = {
                "id": model_config.get("id", key),
                "name": model_config.get("name", key),
                "provider": model_config.get("provider", "unknown"),
                "icon": model_config.get("icon", "fa-question"),
                "color": model_config.get("color", "text-gray-400"),
                "description": model_config.get("description", ""),
                "type": key,
                "status": model_config.get("status", "active"),
            }

            # 添加 inactive_reason
            if "inactive_reason" in model_config:
                top_level_model["inactive_reason"] = model_config["inactive_reason"]

            # 如果有子模型，添加標記
            if "sub_models" in model_config:
                top_level_model["has_sub_models"] = True
                top_level_model["sub_models"] = model_config["sub_models"]

            # 如果有優先級列表，添加標記
            if "backend_model_priority" in model_config:
                top_level_model["has_priority_list"] = True
                top_level_model["backend_model_priority"] = model_config["backend_model_priority"]

            # 對於 SmartQ-HCI，標記為智能路由
            if model_config.get("provider") == "smartq":
                top_level_model["is_smartq_hci"] = True
                top_level_model["moe_routing"] = model_config.get("moe_routing", {})

            models.append(top_level_model)

        return models

    def get_all_sub_models(self) -> List[Dict[str, Any]]:
        """
        獲取所有子模型（用於展開顯示）

        Returns:
            所有子模型的列表
        """
        if not self.is_enabled():
            return []

        config = self._config.get("frontend_model_simplification", {})
        if not config:
            return []

        model_mapping = config.get("model_mapping", {})
        sub_models = []

        for key, model_config in model_mapping.items():
            if "sub_models" in model_config:
                for sub_model in model_config["sub_models"]:
                    sub_model["parent_type"] = key
                    sub_models.append(sub_model)

        return sub_models

    def update_model_status_from_health_check(
        self,
        provider_health: Dict[str, Any],
    ) -> bool:
        """
        根據 health check 結果更新模型狀態

        Args:
            provider_health: provider 健康狀態字典，格式為:
                {
                    "chatgpt": {"healthy": True, "latency": 1.5, "error": None},
                    "gemini": {"healthy": False, "latency": 0, "error": "API key not configured"},
                    ...
                }

        Returns:
            是否有任何狀態改變並保存成功
        """
        if not self.is_enabled():
            return False

        # Provider 到模型 ID 的映射
        provider_to_model_ids = {
            "chatgpt": "chatgpt",
            "gemini": "gemini",
            "anthropic": "claude",
            "xai": "grok",
            "ollama": "ollama-local",
        }

        config = self._config.get("frontend_model_simplification", {})
        if not config:
            return False

        model_mapping = config.get("model_mapping", {})
        has_changes = False

        for provider_key, health_result in provider_health.items():
            # 查找對應的模型 ID
            model_id = provider_to_model_ids.get(provider_key)
            if not model_id:
                continue

            # 查找模型配置
            model_config = None
            for key, config_data in model_mapping.items():
                if config_data.get("id") == model_id:
                    model_config = config_data
                    break

            if not model_config:
                continue

            # 計算新狀態
            is_healthy = health_result.get("healthy", False)
            new_status = "active" if is_healthy else "inactive"

            # 獲取當前狀態
            current_status = model_config.get("status", "active")

            # 如果狀態改變
            if current_status != new_status:
                error_message = health_result.get("error", "")
                new_inactive_reason = None

                if not is_healthy:
                    if error_message:
                        new_inactive_reason = error_message
                    elif health_result.get("latency", 0) > 30:
                        new_inactive_reason = "回應時間過長"
                    else:
                        new_inactive_reason = "連線失敗或未設定 API Key"
                else:
                    # 恢復活躍狀態，清除 inactive_reason
                    model_config.pop("inactive_reason", None)

                # 更新狀態
                model_config["status"] = new_status

                if new_inactive_reason:
                    model_config["inactive_reason"] = new_inactive_reason

                has_changes = True
                self.logger.info(
                    f"model_status_updated: model_id={model_id}, "
                    f"old_status={current_status}, new_status={new_status}, "
                    f"reason={new_inactive_reason}"
                )

        # 如果有改變，保存配置
        if has_changes:
            return self._save_config()

        return False

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

        config = self._config.get("frontend_model_simplification", {})
        if not config:
            return frontend_model_id

        model_mapping = config.get("model_mapping", {})

        # Auto 模型直接返回
        if frontend_model_id == "auto":
            return "auto"

        # 首先檢查是否為子模型
        for key, model_config in model_mapping.items():
            if "sub_models" in model_config:
                for sub_model in model_config["sub_models"]:
                    if sub_model.get("id") == frontend_model_id:
                        backend_model = sub_model.get("backend_model", frontend_model_id)
                        self.logger.debug(
                            f"sub_model_mapped: frontend={frontend_model_id}, backend={backend_model}"
                        )
                        return backend_model

        # 查找映射
        for key, model_config in model_mapping.items():
            if model_config.get("id") == frontend_model_id:
                # SmartQ-HCI 使用 auto
                if model_config.get("provider") == "smartq":
                    return "auto"

                # Ollama 使用優先級列表的第一個可用模型
                if "backend_model_priority" in model_config:
                    priority_list = model_config["backend_model_priority"]
                    if priority_list:
                        self.logger.debug(
                            f"ollama_model_priority: frontend={frontend_model_id}, first={priority_list[0]}"
                        )
                        return priority_list[0]

                backend_model = model_config.get("backend_model", frontend_model_id)
                self.logger.debug(
                    f"model_mapped: frontend={frontend_model_id}, backend={backend_model}"
                )
                return backend_model

        # 如果沒有找到映射，返回原始 ID
        self.logger.warning(f"model_mapping_not_found: frontend={frontend_model_id}")
        return frontend_model_id

    def get_ollama_priority_list(self) -> List[str]:
        """
        獲取 Ollama 的模型優先級列表

        Returns:
            優先級模型列表
        """
        if not self.is_enabled():
            return []

        config = self._config.get("frontend_model_simplification", {})
        if not config:
            return []

        model_mapping = config.get("model_mapping", {})

        ollama_config = model_mapping.get("ollama", {})
        return ollama_config.get("backend_model_priority", [])

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
            llm_model = {
                "model_id": model["id"],
                "name": model["name"],
                "provider": model["provider"],
                "description": model.get("description", ""),
                "status": model.get("status", "active"),
                "capabilities": ["chat", "text_generation"],
                "icon": model.get("icon"),
                "color": model.get("color"),
                "order": 0,
                "is_default": False,
                "metadata": {
                    "simplified_model": True,
                    "model_type": model.get("type", "unknown"),
                    "is_smartq": model.get("provider") == "smartq",
                },
            }

            # 添加 inactive_reason
            if "inactive_reason" in model:
                llm_model["inactive_reason"] = model["inactive_reason"]
                llm_model["metadata"]["inactive_reason"] = model["inactive_reason"]

            # 添加子模型信息
            if "has_sub_models" in model:
                llm_model["metadata"]["has_sub_models"] = True
                llm_model["metadata"]["sub_models"] = model.get("sub_models", [])

            # 添加優先級列表信息
            if "has_priority_list" in model:
                llm_model["metadata"]["has_priority_list"] = True
                llm_model["metadata"]["backend_model_priority"] = model.get(
                    "backend_model_priority", []
                )

            result.append(llm_model)

        return result


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
