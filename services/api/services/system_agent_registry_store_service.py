# 代碼功能說明: System Agent Registry 存儲服務
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""System Agent Registry 存儲服務

提供 System Agent（內建 Agent）的註冊和存儲服務，存儲在 ArangoDB 中。
System Agent 是系統內部的支援層 Agent，不會在前端註冊表中顯示。

支持的 System Agents:
1. 安全審計 Agent (security-audit-agent)
2. Report Agent (report-agent)
3. 文件編輯 Agent (document-editing-agent)
4. 其他陸續定義中...
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient

logger = structlog.get_logger(__name__)

SYSTEM_AGENT_REGISTRY_COLLECTION = "system_agent_registry"


class SystemAgentRegistryModel:
    """System Agent Registry 數據模型"""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        name: str,
        description: str,
        capabilities: List[str],
        version: str = "1.0.0",
        status: str = "online",
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        """
        初始化 System Agent Registry Model

        Args:
            agent_id: Agent ID（如 "document-editing-agent"）
            agent_type: Agent 類型（如 "document_editing", "security_audit", "report"）
            name: Agent 名稱（如 "Document Editing Agent"）
            description: Agent 描述
            capabilities: Agent 能力列表
            version: Agent 版本（默認 "1.0.0"）
            status: Agent 狀態（"online", "offline", "maintenance"，默認 "online"）
            is_active: 是否啟用（默認 True）
            metadata: 額外元數據（可選）
            created_at: 創建時間（ISO 8601 格式，可選）
            updated_at: 更新時間（ISO 8601 格式，可選）
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.version = version
        self.status = status
        self.is_active = is_active
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "_key": self.agent_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "version": self.version,
            "status": self.status,
            "is_active": self.is_active,
            "is_system_agent": True,  # System Agent 標記
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, doc: Dict[str, Any]) -> SystemAgentRegistryModel:
        """從字典創建模型"""
        return cls(
            agent_id=doc.get("agent_id") or doc.get("_key"),
            agent_type=doc.get("agent_type"),
            name=doc.get("name"),
            description=doc.get("description"),
            capabilities=doc.get("capabilities", []),
            version=doc.get("version", "1.0.0"),
            status=doc.get("status", "online"),
            is_active=doc.get("is_active", True),
            metadata=doc.get("metadata", {}),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )


def _document_to_model(doc: Dict[str, Any]) -> SystemAgentRegistryModel:
    """將 ArangoDB document 轉換為 SystemAgentRegistryModel"""
    return SystemAgentRegistryModel.from_dict(doc)


class SystemAgentRegistryStoreService:
    """System Agent Registry 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 System Agent Registry Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(SYSTEM_AGENT_REGISTRY_COLLECTION)
        self._collection = ArangoCollection(collection)
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """確保索引存在"""
        if self._client.db is None:
            return

        collection = self._client.db.collection(SYSTEM_AGENT_REGISTRY_COLLECTION)

        # 創建索引
        indexes = collection.indexes()
        # 使用 tuple 而不是 list，因為列表不可哈希
        existing_index_fields = {
            (
                tuple(idx.get("fields", []))
                if isinstance(idx.get("fields"), list)
                else idx.get("fields")
            )
            for idx in indexes
        }

        # agent_type 索引
        agent_type_fields = ("agent_type",)
        if agent_type_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["agent_type"]})

        # is_system_agent 索引（用於過濾 System Agent）
        is_system_agent_fields = ("is_system_agent",)
        if is_system_agent_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["is_system_agent"]})

        # status 索引
        status_fields = ("status",)
        if status_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["status"]})

        # is_active 索引
        is_active_fields = ("is_active",)
        if is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["is_active"]})

        # 複合索引：agent_type + is_active
        agent_type_is_active_fields = ("agent_type", "is_active")
        if agent_type_is_active_fields not in existing_index_fields:
            collection.add_index({"type": "persistent", "fields": ["agent_type", "is_active"]})

        # 複合索引：is_system_agent + is_active + status
        system_agent_composite_fields = ("is_system_agent", "is_active", "status")
        if system_agent_composite_fields not in existing_index_fields:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": ["is_system_agent", "is_active", "status"],
                }
            )

    def register_system_agent(
        self,
        agent_id: str,
        agent_type: str,
        name: str,
        description: str,
        capabilities: List[str],
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SystemAgentRegistryModel:
        """
        註冊 System Agent

        Args:
            agent_id: Agent ID（如 "document-editing-agent"）
            agent_type: Agent 類型（如 "document_editing"）
            name: Agent 名稱
            description: Agent 描述
            capabilities: Agent 能力列表
            version: Agent 版本（默認 "1.0.0"）
            metadata: 額外元數據（可選）

        Returns:
            註冊的 System Agent 記錄

        Raises:
            ValueError: 如果 Agent ID 已存在
        """
        # 檢查 Agent 是否已存在
        existing = self._collection.get(agent_id)
        if existing is not None:
            # 更新現有 Agent（如果 existing 是字符串，說明可能是 _key，需要轉換為字典）
            if isinstance(existing, str):
                # 如果返回的是字符串（_key），重新獲取完整文檔
                existing = self._collection.get(agent_id)
            if existing is not None and isinstance(existing, dict):
                # 更新現有 Agent
                self._logger.info(
                    "system_agent_already_exists",
                    agent_id=agent_id,
                    message="Updating existing system agent",
                )
                return self.update_system_agent(
                    agent_id=agent_id,
                    name=name,
                    description=description,
                    capabilities=capabilities,
                    version=version,
                    metadata=metadata,
                    status="online",
                )

        now = datetime.utcnow().isoformat()
        agent_model = SystemAgentRegistryModel(
            agent_id=agent_id,
            agent_type=agent_type,
            name=name,
            description=description,
            capabilities=capabilities,
            version=version,
            status="online",
            is_active=True,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        doc = agent_model.to_dict()

        try:
            self._collection.insert(doc)
            self._logger.info(
                "system_agent_registered",
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
            )
            return agent_model
        except Exception as exc:
            self._logger.error(
                "system_agent_register_failed",
                agent_id=agent_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def get_system_agent(self, agent_id: str) -> Optional[SystemAgentRegistryModel]:
        """
        獲取 System Agent 記錄

        Args:
            agent_id: Agent ID

        Returns:
            System Agent 記錄，如果不存在返回 None
        """
        doc = self._collection.get(agent_id)
        if doc is None:
            return None

        # 確保是 System Agent
        if not doc.get("is_system_agent", False):
            self._logger.warning(
                "agent_not_system_agent",
                agent_id=agent_id,
                message="Agent exists but is not marked as system agent",
            )
            return None

        return _document_to_model(doc)

    def update_system_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        version: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SystemAgentRegistryModel:
        """
        更新 System Agent 記錄

        Args:
            agent_id: Agent ID
            name: Agent 名稱（可選）
            description: Agent 描述（可選）
            capabilities: Agent 能力列表（可選）
            version: Agent 版本（可選）
            status: Agent 狀態（可選）
            is_active: 是否啟用（可選）
            metadata: 額外元數據（可選）

        Returns:
            更新後的 System Agent 記錄

        Raises:
            ValueError: 如果 Agent 不存在
        """
        doc = self._collection.get(agent_id)
        if doc is None:
            raise ValueError(f"System Agent '{agent_id}' not found")

        # 確保是 System Agent
        if not doc.get("is_system_agent", False):
            raise ValueError(f"Agent '{agent_id}' is not a system agent")

        # 更新字段
        if name is not None:
            doc["name"] = name
        if description is not None:
            doc["description"] = description
        if capabilities is not None:
            doc["capabilities"] = capabilities
        if version is not None:
            doc["version"] = version
        if status is not None:
            doc["status"] = status
        if is_active is not None:
            doc["is_active"] = is_active
        if metadata is not None:
            doc["metadata"] = {**doc.get("metadata", {}), **metadata}

        doc["updated_at"] = datetime.utcnow().isoformat()
        doc["is_system_agent"] = True  # 確保標記為 System Agent

        try:
            # ArangoDB update 方法需要傳入文檔的 _key 或 _id，而不是字符串
            # 使用 {"_key": agent_id} 作為文檔標識
            self._collection.update({"_key": agent_id}, doc)
            self._logger.info("system_agent_updated", agent_id=agent_id)
            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error(
                "system_agent_update_failed",
                agent_id=agent_id,
                error=str(exc),
                exc_info=True,
            )
            raise

    def list_system_agents(
        self,
        agent_type: Optional[str] = None,
        is_active: Optional[bool] = True,
        status: Optional[str] = None,
    ) -> List[SystemAgentRegistryModel]:
        """
        列出 System Agent 記錄

        Args:
            agent_type: Agent 類型過濾（可選）
            is_active: 是否啟用过濾（可選，默認 True）
            status: Agent 狀態過濾（可選）

        Returns:
            System Agent 記錄列表
        """
        filters: Dict[str, Any] = {"is_system_agent": True}

        if agent_type is not None:
            filters["agent_type"] = agent_type
        if is_active is not None:
            filters["is_active"] = is_active
        if status is not None:
            filters["status"] = status

        try:
            aql = f"""
            FOR doc IN {SYSTEM_AGENT_REGISTRY_COLLECTION}
            FILTER doc.is_system_agent == true
            """
            bind_vars: Dict[str, Any] = {}

            if agent_type is not None:
                aql += " AND doc.agent_type == @agent_type"
                bind_vars["agent_type"] = agent_type
            if is_active is not None:
                aql += " AND doc.is_active == @is_active"
                bind_vars["is_active"] = is_active
            if status is not None:
                aql += " AND doc.status == @status"
                bind_vars["status"] = status

            aql += " SORT doc.agent_id RETURN doc"

            if self._client.db is None or self._client.db.aql is None:
                raise RuntimeError("AQL is not available")

            cursor = self._client.db.aql.execute(aql, bind_vars=bind_vars)
            docs = list(cursor)

            agents = [_document_to_model(doc) for doc in docs]
            self._logger.info(
                "system_agents_listed",
                count=len(agents),
                agent_type=agent_type,
                is_active=is_active,
                status=status,
            )
            return agents
        except Exception as exc:
            self._logger.error(
                "system_agents_list_failed",
                error=str(exc),
                exc_info=True,
            )
            raise

    def unregister_system_agent(self, agent_id: str) -> bool:
        """
        取消註冊 System Agent（標記為非活躍狀態）

        Args:
            agent_id: Agent ID

        Returns:
            是否成功取消註冊

        Raises:
            ValueError: 如果 Agent 不存在
        """
        doc = self._collection.get(agent_id)
        if doc is None:
            raise ValueError(f"System Agent '{agent_id}' not found")

        # 確保是 System Agent
        if not doc.get("is_system_agent", False):
            raise ValueError(f"Agent '{agent_id}' is not a system agent")

        # 標記為非活躍狀態（不刪除）
        doc["is_active"] = False
        doc["status"] = "offline"
        doc["updated_at"] = datetime.utcnow().isoformat()

        try:
            # ArangoDB update 方法需要傳入文檔的 _key 或 _id，而不是字符串
            self._collection.update({"_key": agent_id}, doc)
            self._logger.info("system_agent_unregistered", agent_id=agent_id)
            return True
        except Exception as exc:
            self._logger.error(
                "system_agent_unregister_failed",
                agent_id=agent_id,
                error=str(exc),
                exc_info=True,
            )
            raise


# 全局單例
_system_agent_registry_store_service: Optional[SystemAgentRegistryStoreService] = None


def get_system_agent_registry_store_service() -> SystemAgentRegistryStoreService:
    """
    獲取 System Agent Registry Store Service 單例

    Returns:
        SystemAgentRegistryStoreService 實例
    """
    global _system_agent_registry_store_service
    if _system_agent_registry_store_service is None:
        _system_agent_registry_store_service = SystemAgentRegistryStoreService()
    return _system_agent_registry_store_service
