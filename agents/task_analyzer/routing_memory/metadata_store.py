# 代碼功能說明: 元數據存儲服務（ArangoDB）
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""元數據存儲服務 - 使用 ArangoDB 存儲決策事實"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.arangodb.client import ArangoDBClient

logger = logging.getLogger(__name__)

# Collection 名稱
ROUTING_DECISIONS_COLLECTION = "routing_decisions"


class RoutingMetadataStore:
    """Routing Memory 元數據存儲類"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化元數據存儲

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保 Collection 存在並創建索引"""
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        try:
            if not self._client.db.has_collection(ROUTING_DECISIONS_COLLECTION):
                self._client.db.create_collection(ROUTING_DECISIONS_COLLECTION)

                # 創建索引
                collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)
                collection.add_index({"type": "persistent", "fields": ["intent_type"]})
                collection.add_index({"type": "persistent", "fields": ["complexity"]})
                collection.add_index({"type": "persistent", "fields": ["risk_level"]})
                collection.add_index({"type": "persistent", "fields": ["chosen_agent"]})
                collection.add_index({"type": "persistent", "fields": ["chosen_model"]})
                collection.add_index({"type": "persistent", "fields": ["success"]})
                collection.add_index({"type": "persistent", "fields": ["created_at"]})
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["intent_type", "complexity", "risk_level"],
                    }
                )

                logger.info(f"Created collection: {ROUTING_DECISIONS_COLLECTION}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}", exc_info=True)
            raise

    def save(self, decision_log: Any) -> bool:
        """
        保存決策日誌到 ArangoDB

        Args:
            decision_log: 決策日誌對象

        Returns:
            是否成功
        """
        if self._client.db is None:
            logger.error("ArangoDB client is not connected")
            return False

        try:
            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 構建文檔
            doc = {
                "_key": decision_log.decision_id,
                "intent_type": decision_log.router_output.intent_type,
                "complexity": decision_log.router_output.complexity,
                "risk_level": decision_log.router_output.risk_level,
                "chosen_agent": decision_log.decision_engine.chosen_agent,
                "chosen_model": decision_log.decision_engine.chosen_model,
                "chosen_tools": decision_log.decision_engine.chosen_tools,
                "fallback_used": decision_log.decision_engine.fallback_used,
                "success": decision_log.execution_result.get("success", False)
                if decision_log.execution_result
                else False,
                "latency_ms": decision_log.execution_result.get("latency_ms")
                if decision_log.execution_result
                else None,
                "cost": decision_log.execution_result.get("cost")
                if decision_log.execution_result
                else None,
                "created_at": decision_log.timestamp.isoformat()
                if isinstance(decision_log.timestamp, datetime)
                else decision_log.timestamp,
            }

            # 保存文檔（如果已存在則更新）
            collection.insert(doc, overwrite=True)

            logger.info(f"Saved routing decision: {decision_log.decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save routing decision: {e}", exc_info=True)
            return False

    def get(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取決策日誌

        Args:
            decision_id: 決策 ID

        Returns:
            決策日誌文檔，如果不存在返回 None
        """
        if self._client.db is None:
            logger.error("ArangoDB client is not connected")
            return None

        try:
            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)
            doc = collection.get(decision_id)
            return doc

        except Exception as e:
            logger.error(f"Failed to get routing decision: {e}", exc_info=True)
            return None

    def query(
        self,
        intent_type: Optional[str] = None,
        complexity: Optional[str] = None,
        risk_level: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢決策日誌

        Args:
            intent_type: 意圖類型過濾
            complexity: 複雜度過濾
            risk_level: 風險等級過濾
            success: 成功狀態過濾
            limit: 返回數量限制

        Returns:
            決策日誌列表
        """
        if self._client.db is None:
            logger.error("ArangoDB client is not connected")
            return []

        try:
            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 構建過濾條件
            filters: Dict[str, Any] = {}
            if intent_type:
                filters["intent_type"] = intent_type
            if complexity:
                filters["complexity"] = complexity
            if risk_level:
                filters["risk_level"] = risk_level
            if success is not None:
                filters["success"] = success

            # 查詢
            cursor = collection.find(filters, limit=limit)
            results = list(cursor)

            return results

        except Exception as e:
            logger.error(f"Failed to query routing decisions: {e}", exc_info=True)
            return []
