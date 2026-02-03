# 代碼功能說明: SmartQ 模型路由處理
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""SmartQ 模型路由處理 - 實現 SmartQ-HCI 的智能路由策略"""

import logging
from typing import Any, Dict, Optional

from services.api.services.simplified_model_service import get_simplified_model_service

logger = logging.getLogger(__name__)


class SmartQRouting:
    """SmartQ 模型路由處理器"""

    def __init__(self):
        """初始化 SmartQ 路由器"""
        self.logger = logger
        self.simplified_service = get_simplified_model_service()

    def map_frontend_model(self, frontend_model_id: str, scene: str = "chat") -> str:
        """
        將前端模型 ID 映射到後端實際模型

        Args:
            frontend_model_id: 前端模型 ID
            scene: 使用場景

        Returns:
            後端實際模型 ID
        """
        # 使用簡化模型服務進行映射
        backend_model = self.simplified_service.map_frontend_to_backend(frontend_model_id)

        # 如果是 SmartQ-HCI，需要根據場景選擇最佳模型
        if frontend_model_id == "smartq-hci":
            return self._select_smartq_model(scene)

        self.logger.debug(
            f"smartq_routing: frontend={frontend_model_id}, backend={backend_model}, scene={scene}"
        )
        return backend_model

    def _select_smartq_model(self, scene: str) -> str:
        """
        為 SmartQ-HCI 選擇最佳後端模型

        Args:
            scene: 使用場景

        Returns:
            選擇的模型 ID
        """,
        try:
            # 獲取 SmartQ-HCI 的路由配置
            routing_config = self.simplified_service.get_backend_routing_config("smartq-hci")

            if not routing_config:
                # 如果沒有配置，使用默認模型
                self.logger.warning("smartq_hci_no_routing_config, using_default")
                return "gpt-oss:120b-cloud"

            # 根據場景選擇模型
            scene_mapping = routing_config.get("scene_mapping", {})
            if scene in scene_mapping:
                scene_models = scene_mapping[scene]
                # 簡單策略：選擇第一個可用的模型
                for model in scene_models:
                    if self._is_model_available(model):
                        self.logger.info(f"smartq_hci_scene_selected: scene={scene}, model={model}")
                        return model

                # 如果場景專用模型不可用，使用主要模型
                primary_models = routing_config.get("primary_models", [])
                for model in primary_models:
                    if self._is_model_available(model):
                        self.logger.info(
                            f"smartq_hci_primary_fallback: scene={scene}, model={model}"
                        )
                        return model

                # 最後使用備用模型
                fallback_models = routing_config.get("fallback_models", [])
                for model in fallback_models:
                    if self._is_model_available(model):
                        self.logger.info(f"smartq_hci_fallback: scene={scene}, model={model}")
                        return model

            # 如果沒有場景映射，使用主要模型
            primary_models = routing_config.get("primary_models", ["gpt-oss:120b-cloud"])
            for model in primary_models:
                if self._is_model_available(model):
                    self.logger.info(f"smartq_hci_default: model={model}")
                    return model

            # 最終備選
            return "gpt-oss:120b-cloud"

        except Exception as e:
            self.logger.error(f"smartq_hci_routing_error: scene={scene}, error={str(e)}")
            return "gpt-oss:120b-cloud"

    def _is_model_available(self, model_id: str) -> bool:
        """
        檢查模型是否可用

        Args:
            model_id: 模型 ID

        Returns:
            是否可用
        """
        # 簡化檢查：實際應該檢查模型服務狀態
        # 這裡可以集成模型健康檢查
        try:
            from llm.moe.moe_manager import LLMMoEManager

            moe_manager = LLMMoEManager()
            # 嘗試獲取模型狀態
            model_status = moe_manager.get_model_status(model_id)
            return model_status.get("available", True)
        except Exception as e:
            self.logger.debug(f"model_availability_check_failed: model={model_id}, error={str(e)}")
            # 假設模型可用
            return True

    def get_model_info(self, frontend_model_id: str) -> Dict[str, Any]:
        """
        獲取模型信息

        Args:
            frontend_model_id: 前端模型 ID

        Returns:
            模型信息
        """
        simplified_models = self.simplified_service.get_simplified_models()

        for model in simplified_models:
            if model.get("id") == frontend_model_id:
                return model

        return {}


# 全局實例
_smartq_routing: Optional[SmartQRouting] = None


def get_smartq_routing() -> SmartQRouting:
    """
    獲取 SmartQ 路由實例

    Returns:
        SmartQRouting 實例
    """
    global _smartq_routing
    if _smartq_routing is None:
        _smartq_routing = SmartQRouting()
    return _smartq_routing
