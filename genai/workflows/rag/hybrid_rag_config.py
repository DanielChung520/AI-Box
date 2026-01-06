# 代碼功能說明: HybridRAG 權重配置服務
# 創建日期: 2026-01-05
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-05

"""HybridRAG 權重配置服務 - 提供權重配置的 CRUD 操作"""

from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from services.api.models.config import ConfigCreate, ConfigModel
from services.api.services.config_store_service import ConfigStoreService

logger = structlog.get_logger(__name__)

# 配置 Scope
HYBRID_RAG_CONFIG_SCOPE = "rag.hybrid_weights"

# 默認權重配置
DEFAULT_WEIGHTS = {
    "default": {"vector_weight": 0.6, "graph_weight": 0.4},
    "structure_query": {
        "vector_weight": 0.4,
        "graph_weight": 0.6,
    },  # 結構化查詢（框架、步驟、流程）
    "semantic_query": {"vector_weight": 0.7, "graph_weight": 0.3},  # 語義查詢（解釋、說明）
    "entity_query": {"vector_weight": 0.3, "graph_weight": 0.7},  # 實體查詢（具體名稱、關係）
}

# 結構化查詢關鍵詞
STRUCTURE_KEYWORDS = ["框架", "步驟", "流程", "階段", "順序", "架構", "設計"]

# 實體查詢關鍵詞
ENTITY_KEYWORDS = ["是什麼", "關係", "連接", "包含", "屬於"]


class HybridRAGConfigService:
    """HybridRAG 權重配置服務"""

    def __init__(self, config_service: Optional[ConfigStoreService] = None):
        """
        初始化 HybridRAG 配置服務

        Args:
            config_service: ConfigStoreService 實例，如果為 None 則創建新實例（可選）
        """
        self._config_service: Optional[ConfigStoreService] = None
        self.logger = logger.bind(component="hybrid_rag_config")

        # 嘗試創建配置服務，如果失敗則使用 None（將使用默認權重）
        if config_service is not None:
            self._config_service = config_service
        else:
            try:
                self._config_service = ConfigStoreService()
            except Exception as e:
                self.logger.warning(
                    "Failed to initialize ConfigStoreService, will use default weights",
                    error=str(e),
                )
                self._config_service = None

    def get_weights(
        self,
        query: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        獲取權重配置（支持多層級：system/tenant/user）

        Args:
            query: 查詢文本（用於動態判斷查詢類型）
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）

        Returns:
            權重配置字典，格式：{"vector_weight": 0.6, "graph_weight": 0.4}
        """
        # 如果配置服務不可用，使用默認權重
        if self._config_service is None:
            return self._get_default_weights(query)

        try:
            # 獲取配置
            config = self._config_service.get_config(
                scope=HYBRID_RAG_CONFIG_SCOPE, tenant_id=tenant_id, user_id=user_id
            )

            if not config or not config.is_active:
                # 如果沒有配置或配置未啟用，使用默認配置
                return self._get_default_weights(query)

            config_data = config.config_data or {}

            # 如果有查詢文本，嘗試匹配查詢類型
            if query:
                query_type = self._detect_query_type(query)
                if query_type in config_data:
                    weights = config_data[query_type]
                    if self._validate_weights(weights):
                        self.logger.debug(
                            "Using query-type specific weights",
                            query_type=query_type,
                            weights=weights,
                        )
                        return weights

            # 使用默認權重
            default_weights = config_data.get("default", DEFAULT_WEIGHTS["default"])
            if self._validate_weights(default_weights):
                return default_weights

            # 如果配置無效，使用硬編碼默認值
            return self._get_default_weights(query)

        except Exception as e:
            self.logger.warning("Failed to get weights config, using defaults", error=str(e))
            return self._get_default_weights(query)

    def _get_default_weights(self, query: Optional[str] = None) -> Dict[str, float]:
        """獲取默認權重配置"""
        if query:
            query_type = self._detect_query_type(query)
            if query_type in DEFAULT_WEIGHTS:
                return DEFAULT_WEIGHTS[query_type].copy()
        return DEFAULT_WEIGHTS["default"].copy()

    def _detect_query_type(self, query: str) -> str:
        """
        檢測查詢類型

        Args:
            query: 查詢文本

        Returns:
            查詢類型：structure_query, entity_query, semantic_query, default
        """
        # 檢測結構化查詢
        if any(keyword in query for keyword in STRUCTURE_KEYWORDS):
            return "structure_query"

        # 檢測實體查詢
        if any(keyword in query for keyword in ENTITY_KEYWORDS):
            return "entity_query"

        # 默認為語義查詢
        return "semantic_query"

    def _validate_weights(self, weights: Dict[str, Any]) -> bool:
        """
        驗證權重配置的有效性

        Args:
            weights: 權重配置字典

        Returns:
            是否有效
        """
        if not isinstance(weights, dict):
            return False

        vector_weight = weights.get("vector_weight")
        graph_weight = weights.get("graph_weight")

        # 檢查權重是否存在且為數值
        if not isinstance(vector_weight, (int, float)) or not isinstance(
            graph_weight, (int, float)
        ):
            return False

        # 檢查權重範圍（0.0 到 1.0）
        if not (0.0 <= vector_weight <= 1.0) or not (0.0 <= graph_weight <= 1.0):
            return False

        # 檢查權重和（應該是 1.0，允許小幅誤差）
        weight_sum = vector_weight + graph_weight
        if abs(weight_sum - 1.0) > 0.01:  # 允許 1% 誤差
            return False

        return True

    def save_weights(
        self,
        weights: Dict[str, Dict[str, float]],
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> str:
        """
        保存權重配置

        Args:
            weights: 權重配置字典，格式：
                {
                    "default": {"vector_weight": 0.6, "graph_weight": 0.4},
                    "structure_query": {"vector_weight": 0.4, "graph_weight": 0.6},
                    ...
                }
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）
            changed_by: 變更者（用戶 ID）

        Returns:
            配置 ID

        Raises:
            ValueError: 如果權重配置無效
        """
        # 驗證權重配置
        for query_type, weight_config in weights.items():
            if not self._validate_weights(weight_config):
                raise ValueError(f"Invalid weights for query type '{query_type}': {weight_config}")

        # 構建配置數據
        config_data = weights.copy()
        metadata = {
            "description": "HybridRAG 檢索權重配置",
            "version": "1.0",
        }

        # 創建配置
        config_create = ConfigCreate(
            scope=HYBRID_RAG_CONFIG_SCOPE,
            config_data=config_data,
            metadata=metadata,
            tenant_id=tenant_id,
            user_id=user_id,
            data_classification="internal",
        )

        # 保存配置
        if self._config_service is None:
            raise RuntimeError("ConfigStoreService is not available, cannot save config")

        config_id = self._config_service.save_config(
            config=config_create, tenant_id=tenant_id, user_id=user_id, changed_by=changed_by
        )

        self.logger.info(
            "HybridRAG weights config saved",
            config_id=config_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return config_id

    def update_weights(
        self,
        weights: Optional[Dict[str, Dict[str, float]]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> str:
        """
        更新權重配置

        Args:
            weights: 權重配置字典（部分更新）
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）
            changed_by: 變更者（用戶 ID）

        Returns:
            配置 ID

        Raises:
            ValueError: 如果權重配置無效
        """
        # 檢查配置服務是否可用
        if self._config_service is None:
            raise RuntimeError("ConfigStoreService is not available, cannot update config")

        # 獲取現有配置
        existing_config = self._config_service.get_config(
            scope=HYBRID_RAG_CONFIG_SCOPE, tenant_id=tenant_id, user_id=user_id
        )

        if not existing_config:
            # 如果配置不存在，創建新配置
            if weights is None:
                weights = DEFAULT_WEIGHTS.copy()
            return self.save_weights(weights, tenant_id, user_id, changed_by)

        # 合併現有配置和新配置
        existing_weights = existing_config.config_data or {}
        if weights:
            # 驗證新權重配置
            for query_type, weight_config in weights.items():
                if not self._validate_weights(weight_config):
                    raise ValueError(
                        f"Invalid weights for query type '{query_type}': {weight_config}"
                    )

            # 合併配置
            updated_weights = {**existing_weights, **weights}
        else:
            updated_weights = existing_weights

        # 保存更新（使用 save_config，它會自動處理更新邏輯）
        config_create = ConfigCreate(
            scope=HYBRID_RAG_CONFIG_SCOPE,
            config_data=updated_weights,
            metadata=existing_config.metadata or {},
            tenant_id=tenant_id,
            user_id=user_id,
            data_classification=existing_config.data_classification,
        )

        config_id = self._config_service.save_config(
            config=config_create, tenant_id=tenant_id, user_id=user_id, changed_by=changed_by
        )

        self.logger.info(
            "HybridRAG weights config updated",
            config_id=config_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return config_id

    def get_config_model(
        self, tenant_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> Optional[ConfigModel]:
        """
        獲取配置模型（完整）

        Args:
            tenant_id: 租戶 ID（可選）
            user_id: 用戶 ID（可選）

        Returns:
            ConfigModel 或 None
        """
        if self._config_service is None:
            return None

        return self._config_service.get_config(
            scope=HYBRID_RAG_CONFIG_SCOPE, tenant_id=tenant_id, user_id=user_id
        )

    def initialize_default_config(self, force: bool = False, changed_by: str = "system") -> str:
        """
        初始化默認配置

        Args:
            force: 如果為 True，強制覆蓋現有配置
            changed_by: 變更者（用戶 ID）

        Returns:
            配置 ID
        """
        if self._config_service is None:
            raise RuntimeError("ConfigStoreService is not available, cannot initialize config")

        existing_config = self._config_service.get_config(scope=HYBRID_RAG_CONFIG_SCOPE)

        if existing_config and not force:
            self.logger.debug(
                "Default HybridRAG weights config already exists, skipping initialization"
            )
            return existing_config.id or HYBRID_RAG_CONFIG_SCOPE

        return self.save_weights(DEFAULT_WEIGHTS.copy(), changed_by=changed_by)
