# 代碼功能說明: State Store 持久化邏輯
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""State Store 持久化邏輯

負責 ReAct 狀態和 Decision Log 的 ArangoDB 持久化。
"""

import logging
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from agents.services.state_store.models import DecisionLog, ReactState
from database.arangodb import ArangoDBClient

# 加載環境變數
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# ArangoDB Collection 名稱
REACT_STATES_COLLECTION_NAME = "react_states"
DECISION_LOGS_COLLECTION_NAME = "decision_logs"


class StatePersistence:
    """狀態持久化類"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化狀態持久化

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則使用默認客戶端）
        """
        self.client = client or ArangoDBClient()
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """確保 Collections 存在並創建必要的索引"""
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected")
            return

        # 創建 react_states Collection
        if not self.client.db.has_collection(REACT_STATES_COLLECTION_NAME):
            self.client.db.create_collection(REACT_STATES_COLLECTION_NAME)
            logger.info(f"Created collection: {REACT_STATES_COLLECTION_NAME}")

        react_states_collection = self.client.db.collection(REACT_STATES_COLLECTION_NAME)

        # 創建 react_states 索引
        indexes = react_states_collection.indexes()
        index_names = [idx["name"] for idx in indexes]

        # react_id 索引
        if "idx_react_id" not in index_names:
            react_states_collection.add_index(
                {"type": "persistent", "fields": ["react_id"], "name": "idx_react_id"}
            )

        # correlation_id 索引
        if "idx_correlation_id" not in index_names:
            react_states_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["correlation_id"],
                    "name": "idx_correlation_id",
                }
            )

        # timestamp 索引
        if "idx_timestamp" not in index_names:
            react_states_collection.add_index(
                {"type": "persistent", "fields": ["timestamp"], "name": "idx_timestamp"}
            )

        # 複合索引：react_id + iteration
        if "idx_react_iteration" not in index_names:
            react_states_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["react_id", "iteration"],
                    "unique": True,
                    "name": "idx_react_iteration",
                }
            )

        # 創建 decision_logs Collection
        if not self.client.db.has_collection(DECISION_LOGS_COLLECTION_NAME):
            self.client.db.create_collection(DECISION_LOGS_COLLECTION_NAME)
            logger.info(f"Created collection: {DECISION_LOGS_COLLECTION_NAME}")

        decision_logs_collection = self.client.db.collection(DECISION_LOGS_COLLECTION_NAME)

        # 創建 decision_logs 索引
        indexes = decision_logs_collection.indexes()
        index_names = [idx["name"] for idx in indexes]

        # react_id 索引
        if "idx_react_id" not in index_names:
            decision_logs_collection.add_index(
                {"type": "persistent", "fields": ["react_id"], "name": "idx_react_id"}
            )

        # correlation_id 索引
        if "idx_correlation_id" not in index_names:
            decision_logs_collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["correlation_id"],
                    "name": "idx_correlation_id",
                }
            )

        # timestamp 索引
        if "idx_timestamp" not in index_names:
            decision_logs_collection.add_index(
                {"type": "persistent", "fields": ["timestamp"], "name": "idx_timestamp"}
            )

        # state 索引
        if "idx_state" not in index_names:
            decision_logs_collection.add_index(
                {"type": "persistent", "fields": ["state"], "name": "idx_state"}
            )

        # outcome 索引
        if "idx_outcome" not in index_names:
            decision_logs_collection.add_index(
                {"type": "persistent", "fields": ["outcome"], "name": "idx_outcome"}
            )

    def save_state(self, state: ReactState) -> None:
        """
        保存 ReAct 狀態

        Args:
            state: ReAct 狀態對象
        """
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected, skipping state save")
            return

        try:
            collection = self.client.db.collection(REACT_STATES_COLLECTION_NAME)
            doc = state.to_dict()
            # 使用 react_id + iteration 作為 _key
            doc["_key"] = f"{state.react_id}_{state.iteration}"
            collection.insert(doc)
            logger.debug(f"Saved state: react_id={state.react_id}, iteration={state.iteration}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}", exc_info=True)
            raise

    def get_state(self, react_id: str, iteration: int) -> Optional[ReactState]:
        """
        獲取 ReAct 狀態

        Args:
            react_id: ReAct session ID
            iteration: 迭代次數

        Returns:
            ReAct 狀態對象，如果不存在則返回 None
        """
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected")
            return None

        try:
            collection = self.client.db.collection(REACT_STATES_COLLECTION_NAME)
            key = f"{react_id}_{iteration}"
            doc = collection.get(key)

            if not doc:
                return None

            return ReactState.from_dict(doc)
        except Exception as e:
            logger.error(f"Failed to get state: {e}", exc_info=True)
            return None

    def get_states_by_react_id(self, react_id: str) -> List[ReactState]:
        """
        獲取指定 react_id 的所有狀態

        Args:
            react_id: ReAct session ID

        Returns:
            狀態列表（按 iteration 排序）
        """
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected")
            return []

        try:
            aql = f"""
            FOR doc IN {REACT_STATES_COLLECTION_NAME}
            FILTER doc.react_id == @react_id
            SORT doc.iteration ASC
            RETURN doc
            """
            cursor = self.client.db.aql.execute(aql, bind_vars={"react_id": react_id})
            docs = list(cursor)

            return [ReactState.from_dict(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get states by react_id: {e}", exc_info=True)
            return []

    def save_decision_log(self, log: DecisionLog) -> None:
        """
        保存 Decision Log

        Args:
            log: Decision Log 對象
        """
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected, skipping decision log save")
            return

        try:
            collection = self.client.db.collection(DECISION_LOGS_COLLECTION_NAME)
            doc = log.to_dict()
            # 使用 react_id + iteration + state 作為 _key（確保唯一性）
            doc["_key"] = f"{log.react_id}_{log.iteration}_{log.state.value}"
            collection.insert(doc)
            logger.debug(
                f"Saved decision log: react_id={log.react_id}, iteration={log.iteration}, state={log.state.value}"
            )
        except Exception as e:
            logger.error(f"Failed to save decision log: {e}", exc_info=True)
            raise

    def get_decision_logs_by_react_id(self, react_id: str) -> List[DecisionLog]:
        """
        獲取指定 react_id 的所有 Decision Log

        Args:
            react_id: ReAct session ID

        Returns:
            Decision Log 列表（按 iteration 排序）
        """
        if self.client.db is None:
            logger.warning("ArangoDB client is not connected")
            return []

        try:
            aql = f"""
            FOR doc IN {DECISION_LOGS_COLLECTION_NAME}
            FILTER doc.react_id == @react_id
            SORT doc.iteration ASC
            RETURN doc
            """
            cursor = self.client.db.aql.execute(aql, bind_vars={"react_id": react_id})
            docs = list(cursor)

            return [DecisionLog.from_dict(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get decision logs by react_id: {e}", exc_info=True)
            return []
