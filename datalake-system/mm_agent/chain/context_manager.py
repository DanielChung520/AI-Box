# 代碼功能說明: 對話上下文管理器
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""對話上下文管理器 - 管理多輪對話歷史和狀態"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    """對話消息"""

    role: str  # 'user' 或 'assistant'
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationContext(BaseModel):
    """對話上下文"""

    session_id: str
    user_id: Optional[str] = None
    messages: List[Message] = []
    extracted_entities: Dict[str, Any] = {}  # 提取的實體（料號、時間等）
    last_intent: Optional[str] = None  # 上次意圖
    last_table: Optional[str] = None  # 上次查詢的表
    created_at: str = ""
    updated_at: str = ""


class ContextManager:
    """對話上下文管理器"""

    def __init__(self, storage_backend: str = "memory"):
        """初始化上下文管理器

        Args:
            storage_backend: 存儲後端（'memory' 或 'redis'）
        """
        self._storage_backend = storage_backend
        self._memory_storage: Dict[str, ConversationContext] = {}
        self._redis_client = None

        if storage_backend == "redis":
            try:
                import redis

                self._redis_client = redis.Redis(
                    host="localhost", port=6379, db=0, decode_responses=True
                )
            except Exception as e:
                print(f"警告：Redis 連接失敗，使用内存存儲: {e}")
                self._storage_backend = "memory"

    def _generate_session_id(self, user_id: Optional[str] = None) -> str:
        """生成會話 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if user_id:
            return f"{user_id}_{timestamp}"
        return f"session_{timestamp}_{id(self)}"

    def create_session(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """創建新的對話會話

        Args:
            user_id: 用戶 ID
            session_id: 可選的會話 ID（如果不提供則自動生成）

        Returns:
            會話 ID
        """
        if not session_id:
            session_id = self._generate_session_id(user_id)

        now = datetime.now().isoformat()
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            extracted_entities={},
            last_intent=None,
            last_table=None,
            created_at=now,
            updated_at=now,
        )

        self._save_context(session_id, context)
        return session_id

    def _save_context(self, session_id: str, context: ConversationContext):
        """保存上下文"""
        if self._storage_backend == "redis" and self._redis_client:
            # Redis 存儲（24 小時過期）
            self._redis_client.setex(
                f"mm_agent:context:{session_id}",
                86400,  # 24 小時
                context.model_dump_json(),
            )
        else:
            # 内存存儲
            self._memory_storage[session_id] = context

    def _load_context(self, session_id: str) -> Optional[ConversationContext]:
        """加載上下文"""
        if self._storage_backend == "redis" and self._redis_client:
            data = self._redis_client.get(f"mm_agent:context:{session_id}")
            if data:
                return ConversationContext(**json.loads(data))
            return None
        else:
            return self._memory_storage.get(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """添加消息到對話歷史

        Args:
            session_id: 會話 ID
            role: 角色（'user' 或 'assistant'）
            content: 消息內容
            metadata: 可選的元數據

        Returns:
            是否成功
        """
        context = self._load_context(session_id)
        if not context:
            return False

        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
        )

        context.messages.append(message)
        context.updated_at = datetime.now().isoformat()

        # 更新實體信息（如果 metadata 中有）
        if metadata:
            if "part_number" in metadata and metadata["part_number"]:
                context.extracted_entities["part_number"] = metadata["part_number"]
            if "tlf19" in metadata and metadata["tlf19"]:
                context.extracted_entities["tlf19"] = metadata["tlf19"]
            if "table_name" in metadata and metadata["table_name"]:
                context.last_table = metadata["table_name"]
            if "intent" in metadata and metadata["intent"]:
                context.last_intent = metadata["intent"]

        self._save_context(session_id, context)
        return True

    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """獲取對話上下文"""
        return self._load_context(session_id)

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 5,
    ) -> List[Message]:
        """獲取最近的對話消息

        Args:
            session_id: 會話 ID
            limit: 返回的消息數量（默認最近 5 條）

        Returns:
            消息列表
        """
        context = self._load_context(session_id)
        if not context:
            return []

        return context.messages[-limit:] if len(context.messages) > limit else context.messages

    def get_extracted_entities(self, session_id: str) -> Dict[str, Any]:
        """獲取已提取的實體"""
        context = self._load_context(session_id)
        if not context:
            return {}

        return context.extracted_entities

    def clear_context(self, session_id: str) -> bool:
        """清除對話上下文"""
        if self._storage_backend == "redis" and self._redis_client:
            self._redis_client.delete(f"mm_agent:context:{session_id}")
        else:
            if session_id in self._memory_storage:
                del self._memory_storage[session_id]
                return True
        return False

    def resolve_references(
        self,
        session_id: str,
        current_query: str,
    ) -> Dict[str, Any]:
        """解析指代引用（指代消解）

        從當前查詢中識別指代詞（如"這個"、"那個"、"它"等），
        並從上下文中提取相關實體。

        Args:
            session_id: 會話 ID
            current_query: 當前查詢

        Returns:
            解析後的實體信息
        """
        context = self._load_context(session_id)
        if not context:
            return {"resolved": False, "entities": {}}

        resolved_entities = {}
        needs_resolution = False

        # 指代詞列表
        pronouns = ["這個", "那個", "它", "這", "那", "他", "她"]

        # 檢查是否需要指代消解
        for pronoun in pronouns:
            if pronoun in current_query:
                needs_resolution = True
                break

        if not needs_resolution:
            return {"resolved": False, "entities": {}}

        # 從上下文提取實體
        entities = context.extracted_entities

        # 優先級：最近的消息 > 歷史累積
        if entities.get("part_number"):
            resolved_entities["part_number"] = entities["part_number"]

        if entities.get("tlf19"):
            resolved_entities["tlf19"] = entities["tlf19"]

        if context.last_table:
            resolved_entities["table_name"] = context.last_table

        if context.last_intent:
            resolved_entities["intent"] = context.last_intent

        return {
            "resolved": len(resolved_entities) > 0,
            "entities": resolved_entities,
            "original_query": current_query,
        }


# 全局上下文管理器實例
_context_manager: Optional[ContextManager] = None


def get_context_manager(storage_backend: str = "memory") -> ContextManager:
    """獲取全局上下文管理器實例（單例模式）"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(storage_backend)
    return _context_manager


if __name__ == "__main__":
    # 測試上下文管理器
    print("=" * 60)
    print("對話上下文管理器測試")
    print("=" * 60)

    # 創建管理器
    manager = ContextManager(storage_backend="memory")

    # 創建會話
    session_id = manager.create_session(user_id="user_001")
    print(f"\n1. 創建會話: {session_id}")

    # 添加對話消息
    print("\n2. 模擬多輪對話:")

    # 第一輪
    manager.add_message(
        session_id,
        "user",
        "RM05-008 上月買進多少",
        metadata={
            "part_number": "RM05-008",
            "tlf19": "101",
            "intent": "purchase",
            "table_name": "tlf_file",
        },
    )
    print("   用戶: RM05-008 上月買進多少")

    manager.add_message(
        session_id, "assistant", "RM05-008 採購進貨共 5,000 KG", metadata={"has_data": True}
    )
    print("   助手: RM05-008 採購進貨共 5,000 KG")

    # 第二輪（指代消解測試）
    print("\n3. 指代消解測試:")
    current_query = "這個料號庫存還有多少"
    print(f"   用戶: {current_query}")

    resolution = manager.resolve_references(session_id, current_query)
    print(f"   指代解析結果:")
    print(f"   - 需要消解: {resolution['resolved']}")
    print(f"   - 解析出的實體: {resolution['entities']}")

    if resolution["resolved"]:
        # 添加上下文信息後的完整查詢
        entities = resolution["entities"]
        resolved_query = current_query
        if "這個" in resolved_query and entities.get("part_number"):
            resolved_query = resolved_query.replace("這個", entities["part_number"])
        print(f"   - 消解後查詢: {resolved_query}")

    # 顯示對話歷史
    print("\n4. 對話歷史:")
    messages = manager.get_recent_messages(session_id)
    for i, msg in enumerate(messages, 1):
        print(f"   {i}. [{msg.role}] {msg.content}")

    # 顯示提取的實體
    print("\n5. 提取的實體:")
    entities = manager.get_extracted_entities(session_id)
    for key, value in entities.items():
        print(f"   - {key}: {value}")

    print("\n" + "=" * 60)
    print("測試完成")
