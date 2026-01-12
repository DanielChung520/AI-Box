# 代碼功能說明: 元數據存儲服務（ArangoDB）
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""元數據存儲服務 - 使用 ArangoDB 存儲決策事實（符合 GRO 規範）"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from agents.task_analyzer.models import DecisionLog, GroDecisionLog
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
        """確保 Collection 存在並創建索引（符合 GRO 規範）"""
        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        try:
            collection_created = False
            if not self._client.db.has_collection(ROUTING_DECISIONS_COLLECTION):
                self._client.db.create_collection(ROUTING_DECISIONS_COLLECTION)
                collection_created = True
                logger.info(f"Created collection: {ROUTING_DECISIONS_COLLECTION}")

            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)
            indexes = collection.indexes()
            index_names = [idx.get("name", "") for idx in indexes]

            # GRO 規範索引
            if "idx_react_id" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["react_id"], "name": "idx_react_id"}
                )
            if "idx_iteration" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["iteration"], "name": "idx_iteration"}
                )
            if "idx_state" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["state"], "name": "idx_state"}
                )
            if "idx_outcome" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["outcome"], "name": "idx_outcome"}
                )
            # 複合索引：react_id + iteration（用於查詢特定 ReAct session）
            if "idx_react_iteration" not in index_names:
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": ["react_id", "iteration"],
                        "unique": False,
                        "name": "idx_react_iteration",
                    }
                )

            # 向後兼容索引（舊版 DecisionLog 字段）
            if "idx_intent_type" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["intent_type"], "name": "idx_intent_type"}
                )
            if "idx_complexity" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["complexity"], "name": "idx_complexity"}
                )
            if "idx_risk_level" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["risk_level"], "name": "idx_risk_level"}
                )
            if "idx_created_at" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["created_at"], "name": "idx_created_at"}
                )
            if "idx_timestamp" not in index_names:
                collection.add_index(
                    {"type": "persistent", "fields": ["timestamp"], "name": "idx_timestamp"}
                )

            if collection_created:
                logger.info(f"Created indexes for collection: {ROUTING_DECISIONS_COLLECTION}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}", exc_info=True)
            raise

    def save(self, decision_log: Union[DecisionLog, GroDecisionLog]) -> bool:
        """
        保存決策日誌到 ArangoDB（支持 GRO 規範和舊版格式）

        Args:
            decision_log: 決策日誌對象（GroDecisionLog 或 DecisionLog）

        Returns:
            是否成功
        """
        if self._client.db is None:
            logger.error("ArangoDB client is not connected")
            return False

        try:
            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)

            if isinstance(decision_log, GroDecisionLog):
                # GRO 規範格式
                # 使用 react_id + iteration 作為 _key（確保唯一性）
                doc_key = f"{decision_log.react_id}_{decision_log.iteration}"
                doc = {
                    "_key": doc_key,
                    "react_id": decision_log.react_id,
                    "iteration": decision_log.iteration,
                    "state": decision_log.state.value,
                    "input_signature": decision_log.input_signature,
                    "observations": decision_log.observations,
                    "decision": {
                        "action": decision_log.decision.action.value,
                        "reason": decision_log.decision.reason,
                        "next_state": decision_log.decision.next_state.value,
                    },
                    "outcome": decision_log.outcome.value,
                    "timestamp": (
                        decision_log.timestamp.isoformat()
                        if isinstance(decision_log.timestamp, datetime)
                        else decision_log.timestamp
                    ),
                    "correlation_id": decision_log.correlation_id,
                    "metadata": decision_log.metadata,
                }

                # 向後兼容字段（從 input_signature 和 metadata 提取）
                input_sig = decision_log.input_signature
                doc["intent_type"] = input_sig.get("intent_type")
                doc["complexity"] = input_sig.get("complexity")
                doc["risk_level"] = input_sig.get("risk_level")
                doc["chosen_agent"] = decision_log.metadata.get("chosen_agent")
                doc["chosen_model"] = decision_log.metadata.get("chosen_model")
                doc["chosen_tools"] = decision_log.metadata.get("chosen_tools", [])
                doc["success"] = decision_log.outcome.value == "success"
                doc["created_at"] = doc["timestamp"]
            else:
                # 舊版 DecisionLog 格式（向後兼容）
                doc_key = decision_log.decision_id
                doc = {
                    "_key": doc_key,
                    "intent_type": decision_log.router_output.intent_type,
                    "complexity": decision_log.router_output.complexity,
                    "risk_level": decision_log.router_output.risk_level,
                    "chosen_agent": decision_log.decision_engine.chosen_agent,
                    "chosen_model": decision_log.decision_engine.chosen_model,
                    "chosen_tools": decision_log.decision_engine.chosen_tools,
                    "fallback_used": decision_log.decision_engine.fallback_used,
                    "success": (
                        decision_log.execution_result.get("success", False)
                        if decision_log.execution_result
                        else False
                    ),
                    "latency_ms": (
                        decision_log.execution_result.get("latency_ms")
                        if decision_log.execution_result
                        else None
                    ),
                    "cost": (
                        decision_log.execution_result.get("cost")
                        if decision_log.execution_result
                        else None
                    ),
                    "created_at": (
                        decision_log.timestamp.isoformat()
                        if isinstance(decision_log.timestamp, datetime)
                        else decision_log.timestamp
                    ),
                    "timestamp": (
                        decision_log.timestamp.isoformat()
                        if isinstance(decision_log.timestamp, datetime)
                        else decision_log.timestamp
                    ),
                }

            # 保存文檔（如果已存在則更新）
            collection.insert(doc, overwrite=True)

            if isinstance(decision_log, GroDecisionLog):
                logger.info(
                    f"Saved routing decision: react_id={decision_log.react_id}, "
                    f"iteration={decision_log.iteration}, state={decision_log.state.value}"
                )
            else:
                logger.info(f"Saved routing decision: {decision_log.decision_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save routing decision: {e}", exc_info=True)
            return False

    def get(
        self,
        decision_id: Optional[str] = None,
        react_id: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        獲取決策日誌

        支持通過 decision_id（舊版）或 react_id + iteration（GRO 規範）查詢。

        Args:
            decision_id: 決策 ID（舊版格式）
            react_id: ReAct session ID（GRO 規範）
            iteration: 迭代次數（GRO 規範）

        Returns:
            決策日誌文檔，如果不存在返回 None
        """
        if self._client.db is None:
            logger.error("ArangoDB client is not connected")
            return None

        try:
            collection = self._client.db.collection(ROUTING_DECISIONS_COLLECTION)

            if react_id is not None and iteration is not None:
                # GRO 規範查詢
                doc_key = f"{react_id}_{iteration}"
                doc = collection.get(doc_key)
            elif decision_id:
                # 舊版格式查詢
                doc = collection.get(decision_id)
            else:
                logger.warning("Either decision_id or (react_id, iteration) must be provided")
                return None

            return doc

        except Exception as e:
            logger.error(f"Failed to get routing decision: {e}", exc_info=True)
            return None

    def query(
        self,
        react_id: Optional[str] = None,
        state: Optional[str] = None,
        outcome: Optional[str] = None,
        intent_type: Optional[str] = None,
        complexity: Optional[str] = None,
        risk_level: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查詢決策日誌（支持 GRO 規範和舊版格式）

        Args:
            react_id: ReAct session ID（GRO 規範）
            state: 狀態過濾（GRO 規範）
            outcome: 結果過濾（GRO 規範）
            intent_type: 意圖類型過濾（向後兼容）
            complexity: 複雜度過濾（向後兼容）
            risk_level: 風險等級過濾（向後兼容）
            success: 成功狀態過濾（向後兼容）
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
            if react_id:
                filters["react_id"] = react_id
            if state:
                filters["state"] = state
            if outcome:
                filters["outcome"] = outcome
            # 向後兼容字段
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
