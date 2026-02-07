# 代碼功能說明: AI-Box 共享 ArangoDB 客戶端
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""AI-Box 共享 ArangoDB 客戶端 - Agent Todo 存儲"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from arango import ArangoClient
from arango.exceptions import CollectionCreateError, DocumentInsertError

from shared.agents.todo.schema import (
    Todo,
    TodoState,
    ExecutionResult,
    TodoList,
)

logger = logging.getLogger(__name__)


def _load_env():
    """從 .env 載入環境變數"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def _serialize_todo(todo: Todo) -> Dict[str, Any]:
    """序列化 Todo 物件（處理 datetime）"""
    doc = todo.model_dump()
    doc["_key"] = todo.todo_id

    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, datetime):
                    value[k] = v.isoformat()
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        if isinstance(vv, datetime):
                            v[kk] = vv.isoformat()

    return doc


class SharedArangoClient:
    """AI-Box 共享 ArangoDB 客戶端"""

    _instance: Optional["SharedArangoClient"] = None

    def __init__(
        self,
        host: str = None,
        db_name: str = None,
        username: str = None,
        password: str = None,
    ):
        """初始化 ArangoDB 客戶端"""
        _load_env()

        self._available = False
        self._collection_prefix = "s_"

        host = host or os.environ.get("ARANGODB_HOST", "localhost")
        port = os.environ.get("ARANGODB_PORT", "8529")
        protocol = os.environ.get("ARANGODB_PROTOCOL", "http")
        db_name = db_name or os.environ.get("ARANGODB_DATABASE", "ai_box_kg")
        username = username or os.environ.get("ARANGODB_USERNAME", "root")
        password = password or os.environ.get("ARANGODB_PASSWORD", "")

        try:
            self.client = ArangoClient(hosts=f"{protocol}://{host}:{port}")
            self.db = self.db = self.client.db(db_name, username=username, password=password)
            self._ensure_collections()
            self._available = True
            logger.info(f"ArangoDB connected successfully: {host}:{port}/{db_name}")
        except Exception as e:
            logger.warning(f"ArangoDB not available: {e}")
            self.client = None
            self.db = None

    @classmethod
    def get_instance(
        cls, host: str = None, db_name: str = None, username: str = None, password: str = None
    ) -> "SharedArangoClient":
        """取得單例"""
        if cls._instance is None:
            cls._instance = cls(host=host, db_name=db_name, username=username, password=password)
        return cls._instance

    def _collection(self, name: str):
        """取得 Collection（自動添加前綴）"""
        return self.db.collection(f"{self._collection_prefix}{name}")

    def _ensure_collections(self):
        """確保 Collection 存在"""
        collections = ["todos", "todo_history"]
        for coll_name in collections:
            full_name = f"{self._collection_prefix}{coll_name}"
            try:
                if not self.db.has_collection(full_name):
                    self.db.create_collection(full_name)
                    logger.info(f"Created collection: {full_name}")
            except CollectionCreateError:
                pass

    async def create_todo(self, todo: Todo) -> str:
        """建立 Todo（已存在則更新）"""
        doc = _serialize_todo(todo)

        try:
            self._collection("todos").insert(doc, overwrite=True)
            logger.info(f"Created/Updated todo: {todo.todo_id}")
            return todo.todo_id
        except DocumentInsertError as e:
            logger.error(f"Failed to create todo: {e}")
            raise

    async def get_todo(self, todo_id: str) -> Optional[Todo]:
        """查詢 Todo"""
        doc = self._collection("todos").get(todo_id)
        if doc:
            return Todo(**doc)
        return None

    async def update_todo(
        self,
        todo_id: str,
        state: TodoState = None,
        result: ExecutionResult = None,
        history: Dict[str, Any] = None,
    ) -> bool:
        """更新 Todo"""
        update = {"updated_at": datetime.utcnow().isoformat()}

        if state:
            update["state"] = state.value if hasattr(state, "value") else state

        if result:
            update["result"] = result.model_dump()

        if state and state == TodoState.COMPLETED:
            update["completed_at"] = datetime.utcnow().isoformat()

        try:
            self._collection("todos").update({"_key": todo_id}, update)
            logger.info(f"Updated todo: {todo_id}, state: {state}")

            if history:
                import uuid

                history_doc = {
                    "_key": f"{todo_id}_{uuid.uuid4().hex[:8]}",
                    "todo_id": todo_id,
                    **history,
                }
                self._collection("todo_history").insert(history_doc, overwrite=True)

            return True
        except Exception as e:
            logger.error(f"Failed to update todo: {e}")
            return False

    async def delete_todo(self, todo_id: str) -> bool:
        """刪除 Todo"""
        try:
            self._collection("todos").delete(todo_id)
            logger.info(f"Deleted todo: {todo_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete todo: {e}")
            return False

    async def list_todos(
        self, state: TodoState = None, owner_agent: str = None, page: int = 1, page_size: int = 20
    ) -> TodoList:
        """列出 Todos"""
        aql_parts = []
        bind_vars = {}

        if state:
            aql_parts.append("FILTER t.state == @state")
            bind_vars["state"] = state.value if hasattr(state, "value") else state

        if owner_agent:
            if aql_parts:
                aql_parts.append("FILTER t.owner_agent == @owner_agent")
            else:
                aql_parts.append("FILTER t.owner_agent == @owner_agent")
            bind_vars["owner_agent"] = owner_agent

        where_clause = " WHERE ".join(aql_parts) if aql_parts else ""

        count_aql = f"""
            FOR t IN {self._collection_prefix}todos
            {where_clause}
            RETURN t
        """

        cursor = self.db.aql.execute(count_aql, bind_vars=bind_vars)
        total = len(list(cursor))

        offset = (page - 1) * page_size
        paginated_aql = f"""
            FOR t IN {self._collection_prefix}todos
            {where_clause}
            LIMIT {offset}, {page_size}
            RETURN t
        """

        cursor = self.db.aql.execute(paginated_aql, bind_vars=bind_vars)
        todos = [Todo(**doc) for doc in cursor]

        return TodoList(todos=todos, total=total, page=page, page_size=page_size)

    async def get_todo_history(self, todo_id: str) -> List[Dict[str, Any]]:
        """取得 Todo 歷史"""
        aql = f"""
            FOR h IN {self._collection_prefix}todo_history
            FILTER h.todo_id == @todo_id
            SORT h.timestamp DESC
            RETURN h
        """
        cursor = self.db.aql.execute(aql, bind_vars={"todo_id": todo_id})
        return list(cursor)

    async def get_stats(self) -> Dict[str, Any]:
        """取得統計"""
        stats = {
            "total": 0,
            "by_state": {},
            "by_agent": {},
        }

        aql = "FOR t IN {0}todos RETURN t".format(self._collection_prefix)
        cursor = self.db.aql.execute(aql)

        for doc in cursor:
            stats["total"] += 1
            state = doc.get("state", "UNKNOWN")
            stats["by_state"][state] = stats["by_state"].get(state, 0) + 1

            agent = doc.get("owner_agent", "UNKNOWN")
            stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1

        return stats
