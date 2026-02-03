# 代碼功能說明: AAM 存儲適配器
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 20:06:02 (UTC+8)

"""AAM 存儲適配器 - 提供 Redis、ChromaDB、ArangoDB 適配器"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional

import structlog

from agents.infra.memory.aam.models import Memory, MemoryType

logger = structlog.get_logger(__name__)


class BaseStorageAdapter(ABC):
    """存儲適配器抽象基類"""

    @abstractmethod
    def store(self, memory: Memory) -> bool:
        """存儲記憶"""
        pass

    @abstractmethod
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """檢索記憶"""
        pass

    @abstractmethod
    def update(self, memory: Memory) -> bool:
        """更新記憶"""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """刪除記憶"""
        pass

    @abstractmethod
    def search(
        self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 10
    ) -> List[Memory]:
        """搜索記憶"""
        pass


class RedisAdapter(BaseStorageAdapter):
    """Redis 存儲適配器（用於短期記憶）"""

    def __init__(self, redis_client: Any, ttl: int = 3600, key_prefix: str = "aam:memory:"):
        """
        初始化 Redis 適配器

        Args:
            redis_client: Redis 客戶端
            ttl: 默認過期時間（秒）
            key_prefix: 鍵前綴
        """
        if redis_client is None:
            raise ValueError("Redis client is required")
        self.redis_client = redis_client
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.logger = logger.bind(adapter="redis")

    def store(self, memory: Memory) -> bool:
        """存儲記憶到 Redis"""
        try:
            key = f"{self.key_prefix}{memory.memory_id}"
            value = json.dumps(memory.to_dict())
            self.redis_client.setex(key, self.ttl, value)
            self.logger.debug("Stored memory to Redis", memory_id=memory.memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to store memory to Redis", error=str(e))
            return False

    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """從 Redis 檢索記憶"""
        try:
            key = f"{self.key_prefix}{memory_id}"
            value = self.redis_client.get(key)
            if value is None:
                return None
            data = json.loads(value)
            return Memory.from_dict(data)
        except Exception as e:
            self.logger.error("Failed to retrieve memory from Redis", error=str(e))
            return None

    def update(self, memory: Memory) -> bool:
        """更新 Redis 中的記憶"""
        return self.store(memory)

    def delete(self, memory_id: str) -> bool:
        """從 Redis 刪除記憶"""
        try:
            key = f"{self.key_prefix}{memory_id}"
            result = self.redis_client.delete(key)
            self.logger.debug("Deleted memory from Redis", memory_id=memory_id)
            return result > 0
        except Exception as e:
            self.logger.error("Failed to delete memory from Redis", error=str(e))
            return False

    def search(
        self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 10
    ) -> List[Memory]:
        """搜索 Redis 中的記憶（簡單實現，僅支持鍵匹配）"""
        # Redis 不適合複雜搜索，這裡返回空列表
        # 實際應用中應該使用 Redis 的 SCAN 命令或外部索引
        self.logger.warning("Redis search is not fully supported")
        return []


class ChromaDBAdapter(BaseStorageAdapter):
    """
    ⚠️ DEPRECATED 棄用警告 ⚠️
    此適配器已棄用，請使用 QdrantAdapter 替代。
    原因: 系統已遷移到 Qdrant 作為主要向量資料庫。
    遷移日期: 2026-02-02
    替代方案: 請使用 agents.infra.memory.aam.qdrant_adapter.QdrantAdapter

    ChromaDB 存儲適配器（用於長期記憶向量存儲）
    """

    def __init__(
        self,
        chromadb_client: Any,
        collection_name: str = "aam_memories",
    ):
        """
        初始化 ChromaDB 適配器

        Args:
            chromadb_client: ChromaDB 客戶端
            collection_name: 集合名稱
        """
        if chromadb_client is None:
            raise ValueError("ChromaDB client is required")
        self.chromadb_client = chromadb_client
        self.collection_name = collection_name
        self.logger = logger.bind(adapter="chromadb", collection=collection_name)

    def _get_collection(self) -> Any:
        """獲取或創建集合"""
        try:
            return self.chromadb_client.get_or_create_collection(name=self.collection_name)
        except Exception as e:
            self.logger.error("Failed to get collection", error=str(e))
            raise

    def store(self, memory: Memory) -> bool:
        """存儲記憶到 ChromaDB"""
        try:
            collection = self._get_collection()
            metadata = memory.to_dict()
            # 移除不需要的字段
            metadata.pop("memory_id", None)
            metadata.pop("content", None)

            # ChromaDB metadata 不支援巢狀 dict/list：將 metadata 轉為可存儲格式
            raw_user_metadata = (
                metadata.pop("metadata", {}) if isinstance(metadata.get("metadata"), dict) else {}
            )
            metadata["metadata_json"] = json.dumps(
                raw_user_metadata, ensure_ascii=False, default=str
            )
            for k in ("user_id", "session_id", "task_id"):
                v = raw_user_metadata.get(k)
                if v is not None and isinstance(v, (str, int, float, bool)):
                    metadata[k] = v

            for k, v in list(metadata.items()):
                if isinstance(v, (dict, list)):
                    metadata[k] = json.dumps(v, ensure_ascii=False, default=str)

            collection.add(
                ids=[memory.memory_id],
                documents=[memory.content],
                metadatas=[metadata],
            )
            self.logger.debug("Stored memory to ChromaDB", memory_id=memory.memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to store memory to ChromaDB", error=str(e))
            return False

    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """從 ChromaDB 檢索記憶"""
        try:
            collection = self._get_collection()
            results = collection.get(ids=[memory_id])
            if not results["ids"]:
                return None

            metadata = results["metadatas"][0] if results["metadatas"] else {}
            content = results["documents"][0] if results["documents"] else ""

            user_metadata: dict = {}
            try:
                raw = metadata.get("metadata_json")
                if isinstance(raw, str) and raw:
                    user_metadata = json.loads(raw)
            except Exception:  # noqa: BLE001
                user_metadata = {}
            for k in ("user_id", "session_id", "task_id"):
                if k in metadata and k not in user_metadata and metadata.get(k) is not None:
                    user_metadata[k] = metadata.get(k)

            cleaned_metadata = {
                k: v
                for k, v in metadata.items()
                if k not in {"metadata_json", "user_id", "session_id", "task_id"}
            }
            memory_dict = {
                "memory_id": memory_id,
                "content": content,
                "metadata": user_metadata,
                **cleaned_metadata,
            }
            return Memory.from_dict(memory_dict)
        except Exception as e:
            self.logger.error("Failed to retrieve memory from ChromaDB", error=str(e))
            return None

    def update(self, memory: Memory) -> bool:
        """更新 ChromaDB 中的記憶"""
        try:
            collection = self._get_collection()
            metadata = memory.to_dict()
            metadata.pop("memory_id", None)
            metadata.pop("content", None)

            raw_user_metadata = (
                metadata.pop("metadata", {}) if isinstance(metadata.get("metadata"), dict) else {}
            )
            metadata["metadata_json"] = json.dumps(
                raw_user_metadata, ensure_ascii=False, default=str
            )
            for k in ("user_id", "session_id", "task_id"):
                v = raw_user_metadata.get(k)
                if v is not None and isinstance(v, (str, int, float, bool)):
                    metadata[k] = v

            for k, v in list(metadata.items()):
                if isinstance(v, (dict, list)):
                    metadata[k] = json.dumps(v, ensure_ascii=False, default=str)

            collection.update(
                ids=[memory.memory_id],
                documents=[memory.content],
                metadatas=[metadata],
            )
            self.logger.debug("Updated memory in ChromaDB", memory_id=memory.memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to update memory in ChromaDB", error=str(e))
            return False

    def delete(self, memory_id: str) -> bool:
        """從 ChromaDB 刪除記憶"""
        try:
            collection = self._get_collection()
            collection.delete(ids=[memory_id])
            self.logger.debug("Deleted memory from ChromaDB", memory_id=memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to delete memory from ChromaDB", error=str(e))
            return False

    def search(
        self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 10
    ) -> List[Memory]:
        """搜索 ChromaDB 中的記憶（向量相似度搜索）"""
        try:
            collection = self._get_collection()
            where = {}
            if memory_type:
                where["memory_type"] = memory_type.value

            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where if where else None,
            )

            memories: List[Memory] = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, memory_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    content = results["documents"][0][i] if results["documents"] else ""
                    distance = results["distances"][0][i] if results["distances"] else 1.0

                    user_metadata: dict = {}
                    try:
                        raw = metadata.get("metadata_json")
                        if isinstance(raw, str) and raw:
                            user_metadata = json.loads(raw)
                    except Exception:  # noqa: BLE001
                        user_metadata = {}
                    for k in ("user_id", "session_id", "task_id"):
                        if k in metadata and k not in user_metadata and metadata.get(k) is not None:
                            user_metadata[k] = metadata.get(k)

                    cleaned_metadata = {
                        k: v
                        for k, v in metadata.items()
                        if k not in {"metadata_json", "user_id", "session_id", "task_id"}
                    }
                    memory_dict = {
                        "memory_id": memory_id,
                        "content": content,
                        "relevance_score": 1.0 - distance,  # 距離轉換為相關度
                        "metadata": user_metadata,
                        **cleaned_metadata,
                    }
                    memories.append(Memory.from_dict(memory_dict))

            return memories
        except Exception as e:
            self.logger.error("Failed to search memories in ChromaDB", error=str(e))
            return []


class ArangoDBAdapter(BaseStorageAdapter):
    """ArangoDB 存儲適配器（用於記憶關係圖）"""

    def __init__(
        self,
        arangodb_client: Any,
        collection_name: str = "aam_memories",
        graph_name: str = "memory_graph",
    ):
        """
        初始化 ArangoDB 適配器

        Args:
            arangodb_client: ArangoDB 客戶端
            collection_name: 集合名稱
            graph_name: 圖名稱
        """
        if arangodb_client is None or arangodb_client.db is None:
            raise ValueError("ArangoDB client with database connection is required")
        self.client = arangodb_client
        self.collection_name = collection_name
        self.graph_name = graph_name
        self.logger = logger.bind(adapter="arangodb", collection=collection_name)

    def _get_collection(self) -> Any:
        """獲取或創建集合"""
        try:
            if self.client.db is None:
                raise RuntimeError("ArangoDB database is not connected")
            if not self.client.db.has_collection(self.collection_name):
                self.client.db.create_collection(self.collection_name)
            return self.client.db.collection(self.collection_name)
        except Exception as e:
            self.logger.error("Failed to get collection", error=str(e))
            raise

    def store(self, memory: Memory) -> bool:
        """存儲記憶到 ArangoDB"""
        try:
            collection = self._get_collection()
            document = memory.to_dict()
            document["_key"] = memory.memory_id
            collection.insert(document, overwrite=True)
            self.logger.debug("Stored memory to ArangoDB", memory_id=memory.memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to store memory to ArangoDB", error=str(e))
            return False

    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """從 ArangoDB 檢索記憶"""
        try:
            collection = self._get_collection()
            document = collection.get(memory_id)
            if document is None:
                return None
            return Memory.from_dict(document)
        except Exception as e:
            self.logger.error("Failed to retrieve memory from ArangoDB", error=str(e))
            return None

    def update(self, memory: Memory) -> bool:
        """更新 ArangoDB 中的記憶"""
        try:
            collection = self._get_collection()
            document = memory.to_dict()
            collection.update({"_key": memory.memory_id}, document)
            self.logger.debug("Updated memory in ArangoDB", memory_id=memory.memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to update memory in ArangoDB", error=str(e))
            return False

    def delete(self, memory_id: str) -> bool:
        """從 ArangoDB 刪除記憶"""
        try:
            collection = self._get_collection()
            collection.delete(memory_id)
            self.logger.debug("Deleted memory from ArangoDB", memory_id=memory_id)
            return True
        except Exception as e:
            self.logger.error("Failed to delete memory from ArangoDB", error=str(e))
            return False

    def search(
        self, query: str, memory_type: Optional[MemoryType] = None, limit: int = 10
    ) -> List[Memory]:
        """搜索 ArangoDB 中的記憶（AQL 查詢）"""
        try:
            if self.client.db is None or self.client.db.aql is None:
                raise RuntimeError("AQL is not available")
            aql = """
            FOR doc IN @@collection
                FILTER doc.content LIKE @query
                LIMIT @limit
                RETURN doc
            """
            bind_vars = {
                "@collection": self.collection_name,
                "query": f"%{query}%",
                "limit": limit,
            }
            if memory_type:
                aql = """
                FOR doc IN @@collection
                    FILTER doc.content LIKE @query
                    FILTER doc.memory_type == @memory_type
                    LIMIT @limit
                    RETURN doc
                """
                bind_vars["memory_type"] = memory_type.value

            cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
            results = [doc for doc in cursor]
            return [Memory.from_dict(doc) for doc in results]
        except Exception as e:
            self.logger.error("Failed to search memories in ArangoDB", error=str(e))
            return []
