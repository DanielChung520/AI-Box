# 代碼功能說明: Agent Registry 核心服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Agent Registry 核心服務實現"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.services.protocol.base import AgentServiceProtocol, AgentServiceProtocolType
from agents.services.protocol.factory import AgentServiceClientFactory
from agents.services.registry.models import (
    AgentMetadata,
    AgentPermissionConfig,
    AgentRegistrationRequest,
    AgentRegistryInfo,
    AgentStatus,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent Registry 核心服務"""

    def __init__(self, storage: Optional[Any] = None):
        """
        初始化 Agent Registry

        Args:
            storage: 持久化存儲接口（可選，暫時使用內存存儲）
        """
        self._agents: Dict[str, AgentRegistryInfo] = {}
        self._agent_instances: Dict[str, AgentServiceProtocol] = {}
        self._storage = storage
        self._logger = logger

    def register_agent(
        self,
        request: AgentRegistrationRequest,
        instance: Optional[AgentServiceProtocol] = None,
    ) -> bool:
        """
        註冊 Agent

        Args:
            request: Agent 註冊請求
            instance: Agent 服務實例（可選，僅用於內部 Agent）

        Returns:
            是否成功註冊
        """
        try:
            # 檢查 Agent ID 是否已存在
            if request.agent_id in self._agents:
                self._logger.warning(f"Agent '{request.agent_id}' already exists, updating...")
                # 更新現有 Agent
                existing = self._agents[request.agent_id]
                existing.status = AgentStatus.ONLINE
                existing.capabilities = request.capabilities
                if request.metadata:
                    existing.metadata = request.metadata
                existing.endpoints = request.endpoints
                if request.permissions:
                    existing.permissions = request.permissions
                # last_updated 是只讀屬性，通過更新 last_heartbeat 來間接更新
                existing.last_heartbeat = datetime.now()  # type: ignore[assignment]  # 更新心跳時間以反映更新

                # 如果是內部 Agent 且提供了新實例，更新實例
                if request.endpoints.is_internal and instance:
                    self._agent_instances[request.agent_id] = instance
                    self._logger.debug(
                        f"Updated agent instance for internal agent '{request.agent_id}'"
                    )

                return True

            # 驗證外部 Agent 認證配置
            if not request.endpoints.is_internal:
                if request.permissions:
                    # 延遲導入以避免循環導入
                    from agents.services.auth.external_auth import validate_external_agent_config
                    from agents.services.auth.models import ExternalAuthConfig

                    auth_config = ExternalAuthConfig(
                        api_key=request.permissions.api_key,
                        server_certificate=request.permissions.server_certificate,
                        ip_whitelist=request.permissions.ip_whitelist,
                        server_fingerprint=request.permissions.server_fingerprint,
                    )  # type: ignore[call-arg]  # 所有參數都有默認值
                    if not validate_external_agent_config(auth_config):
                        self._logger.error(
                            f"Invalid authentication config for external agent '{request.agent_id}'"
                        )
                        return False

            # 如果是內部 Agent 但未提供實例，記錄警告
            if request.endpoints.is_internal and not instance:
                self._logger.warning(
                    f"Internal agent '{request.agent_id}' registered without instance. "
                    f"Instance should be provided for direct access."
                )

            # 檢查是否為 System Agent（從 System Agent Registry 查詢）
            is_system_agent = False
            try:
                from services.api.services.system_agent_registry_store_service import (
                    get_system_agent_registry_store_service,
                )

                system_agent_store = get_system_agent_registry_store_service()
                system_agent = system_agent_store.get_system_agent(request.agent_id)
                if system_agent:
                    is_system_agent = True
            except Exception as e:
                # 如果查詢失敗，默認為非 System Agent
                self._logger.debug(
                    f"Failed to check system agent status for {request.agent_id}: {e}"
                )

            # 創建新的 Agent 註冊信息
            agent_info = AgentRegistryInfo(
                agent_id=request.agent_id,
                agent_type=request.agent_type,
                name=request.name,
                status=AgentStatus.REGISTERING,  # 默認為註冊中狀態，等待管理單位核准
                capabilities=request.capabilities,
                metadata=request.metadata or AgentMetadata(),  # type: ignore[call-arg]
                endpoints=request.endpoints,
                permissions=request.permissions or AgentPermissionConfig(),  # type: ignore[call-arg]
                registered_at=datetime.now(),
                last_heartbeat=None,  # 初始註冊時沒有心跳
                load=0,  # 初始負載為 0
                is_system_agent=is_system_agent,  # 標記是否為 System Agent
            )

            self._agents[request.agent_id] = agent_info

            # 如果是內部 Agent 且提供了實例，存儲實例
            if request.endpoints.is_internal and instance:
                self._agent_instances[request.agent_id] = instance
                self._logger.debug(f"Stored agent instance for internal agent '{request.agent_id}'")

            # 持久化存儲（如果有）
            if self._storage:
                try:
                    self._storage.save_agent(agent_info)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent: {e}")

            self._logger.info(
                f"Registered agent: {request.agent_id} "
                f"(type: {request.agent_type}, name: {request.name}, "
                f"internal: {request.endpoints.is_internal})"
            )
            return True

        except Exception as e:
            self._logger.error(f"Failed to register agent '{request.agent_id}': {e}")
            return False

    def unregister_agent(self, agent_id: str) -> bool:
        """
        取消註冊 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否成功取消註冊
        """
        try:
            if agent_id in self._agents:
                # 標記為已作廢狀態而非刪除
                self._agents[agent_id].status = AgentStatus.DEPRECATED
                # last_updated 是只讀屬性，通過更新 last_heartbeat 來間接更新
                self._agents[agent_id].last_heartbeat = datetime.now()  # type: ignore[assignment]  # 更新心跳時間以反映更新

                # 清理實例存儲（如果存在）
                if agent_id in self._agent_instances:
                    instance = self._agent_instances[agent_id]
                    try:
                        # 如果實例支持 close() 方法，調用它
                        if hasattr(instance, "close"):
                            if callable(instance.close):
                                # 檢查是否是異步方法
                                import inspect

                                if inspect.iscoroutinefunction(instance.close):
                                    # 注意：這裡不能直接 await，因為這是同步方法
                                    # 實際的清理應該在調用方進行
                                    self._logger.debug(
                                        f"Agent instance '{agent_id}' has async close method"
                                    )
                                else:
                                    instance.close()
                    except Exception as e:
                        self._logger.warning(f"Failed to close agent instance '{agent_id}': {e}")

                    # 從實例字典中刪除
                    del self._agent_instances[agent_id]
                    self._logger.debug(f"Removed agent instance for '{agent_id}'")

                if self._storage:
                    try:
                        self._storage.update_agent(self._agents[agent_id])
                    except Exception as e:
                        self._logger.error(f"Failed to persist agent update: {e}")

                self._logger.info(f"Unregistered agent: {agent_id}")
                return True
            else:
                self._logger.warning(f"Agent '{agent_id}' not found")
                return False

        except Exception as e:
            self._logger.error(f"Failed to unregister agent '{agent_id}': {e}")
            return False

    def get_agent_info(self, agent_id: str) -> Optional[AgentRegistryInfo]:
        """
        獲取 Agent 註冊信息

        Args:
            agent_id: Agent ID

        Returns:
            Agent 註冊信息，如果不存在則返回 None
        """
        return self._agents.get(agent_id)

    def get_agent(self, agent_id: str) -> Optional[AgentServiceProtocol]:
        """
        獲取 Agent 服務實例或 Client（智能路由）

        根據 Agent 的 `is_internal` 標誌智能返回：
        - 內部 Agent：返回實例（從 `_agent_instances`）
        - 外部 Agent：返回 Client（通過 `get_agent_client()`）

        Args:
            agent_id: Agent ID

        Returns:
            Agent 服務實例或 Client，如果不存在則返回 None

        示例：
            # 內部 Agent：返回實例（直接調用）
            agent = registry.get_agent("planning-agent-1")
            result = await agent.execute(request)

            # 外部 Agent：返回 Client（Protocol 調用）
            client = registry.get_agent("partner-agent-1")
            result = await client.execute(request)
        """
        agent_info = self.get_agent_info(agent_id)
        if not agent_info:
            return None

        # 內部 Agent：返回實例
        if agent_info.endpoints.is_internal:
            instance = self._agent_instances.get(agent_id)
            if instance:
                return instance
            else:
                self._logger.warning(
                    f"Internal agent '{agent_id}' instance not found. "
                    f"Agent may not have been registered with an instance."
                )
                return None

        # 外部 Agent：返回 Client
        return self.get_agent_client(agent_id)

    def get_agent_client(self, agent_id: str) -> Optional[AgentServiceProtocol]:
        """
        獲取 Agent Service Client（僅用於外部 Agent）

        Args:
            agent_id: Agent ID

        Returns:
            Agent Service Client 實例，如果不存在返回 None

        注意：此方法僅用於外部 Agent。內部 Agent 應該使用 `get_agent()` 獲取實例。
        """
        agent_info = self.get_agent_info(agent_id)
        if not agent_info:
            return None

        # 檢查是否為外部 Agent
        if agent_info.endpoints.is_internal:
            self._logger.warning(
                f"Attempted to get client for internal agent '{agent_id}'. "
                f"Use get_agent() instead to get the instance."
            )
            return None

        # 根據協議類型創建對應的 Client
        protocol = agent_info.endpoints.protocol
        endpoint = (
            agent_info.endpoints.http
            if protocol == AgentServiceProtocolType.HTTP
            else agent_info.endpoints.mcp
        )

        if not endpoint:
            self._logger.error(f"Agent {agent_id} endpoint not configured for protocol {protocol}")
            return None

        # 從權限配置獲取認證信息
        permissions = agent_info.permissions

        # 驗證外部 Agent 認證配置（可選，用於檢查配置完整性）
        # 注意：實際的認證驗證在服務器端進行（當外部 Agent 調用我們的服務時）
        # 這裡僅驗證配置是否完整
        from agents.services.auth.external_auth import validate_external_agent_config
        from agents.services.auth.models import ExternalAuthConfig

        auth_config = ExternalAuthConfig(
            api_key=permissions.api_key,
            server_certificate=permissions.server_certificate,
            ip_whitelist=permissions.ip_whitelist,
            server_fingerprint=permissions.server_fingerprint,
            require_mtls=bool(permissions.server_certificate),
            require_signature=bool(permissions.api_key),
            require_ip_check=bool(permissions.ip_whitelist),
        )

        if not validate_external_agent_config(auth_config):
            self._logger.warning(
                f"External agent '{agent_id}' authentication config validation failed. "
                f"Client will be created but authentication may fail."
            )

        return AgentServiceClientFactory.create(
            protocol=protocol,
            endpoint=endpoint,
            api_key=permissions.api_key,
            server_certificate=permissions.server_certificate,
            ip_whitelist=permissions.ip_whitelist,
            server_fingerprint=permissions.server_fingerprint,
        )

    def list_agents(
        self,
        agent_type: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        include_system_agents: bool = False,  # 默認不包括 System Agents
    ) -> List[AgentRegistryInfo]:
        """
        列出 Agent

        Args:
            agent_type: Agent 類型過濾器
            status: Agent 狀態過濾器
            include_system_agents: 是否包括 System Agents（默認 False，僅系統內部調用時為 True）

        Returns:
            Agent 列表（默認過濾 System Agents）
        """
        agents = list(self._agents.values())

        # 如果包括 System Agents，從 System Agent Registry Store 加載
        if include_system_agents:
            try:
                from services.api.services.system_agent_registry_store_service import (
                    get_system_agent_registry_store_service,
                )

                system_agent_store = get_system_agent_registry_store_service()

                # 構建查詢參數
                system_agent_type = agent_type if agent_type else None
                system_agent_status = status.value if status else None

                # 從 System Agent Registry Store 加載 System Agents
                system_agents = system_agent_store.list_system_agents(
                    agent_type=system_agent_type,
                    status=system_agent_status,
                    is_active=True,
                )

                # 將 System Agents 轉換為 AgentRegistryInfo
                from agents.services.protocol.base import AgentServiceProtocolType
                from agents.services.registry.models import (
                    AgentEndpoints,
                    AgentMetadata,
                    AgentPermissionConfig,
                )

                for sys_agent in system_agents:
                    # 檢查是否已經在內存中
                    if sys_agent.agent_id in self._agents:
                        # 如果已經在內存中，使用內存中的版本（可能已註冊實例）
                        continue

                    # 轉換為 AgentRegistryInfo
                    # 將 System Agent 狀態轉換為 AgentStatus
                    agent_status = AgentStatus.ONLINE
                    if sys_agent.status == "offline":
                        agent_status = AgentStatus.OFFLINE
                    elif sys_agent.status == "maintenance":
                        agent_status = AgentStatus.MAINTENANCE

                    agent_info = AgentRegistryInfo(
                        agent_id=sys_agent.agent_id,
                        agent_type=sys_agent.agent_type,
                        name=sys_agent.name,
                        description=sys_agent.description,
                        capabilities=sys_agent.capabilities,
                        status=agent_status,
                        endpoints=AgentEndpoints(
                            http=None,
                            mcp=None,
                            protocol=AgentServiceProtocolType.HTTP,
                            is_internal=True,
                        ),
                        metadata=AgentMetadata(
                            version=sys_agent.version,
                            description=sys_agent.description,
                            author="AI-Box Team",
                            tags=[sys_agent.agent_type, "system", "builtin"],
                        ),
                        permissions=AgentPermissionConfig(),
                        is_system_agent=True,
                    )
                    agents.append(agent_info)
                    self._logger.debug(
                        f"Loaded system agent from store: {sys_agent.agent_id} "
                        f"(type: {sys_agent.agent_type}, status: {sys_agent.status})"
                    )
            except Exception as e:
                self._logger.warning(f"Failed to load system agents from store: {e}", exc_info=True)
        else:
            # 默認過濾 System Agents（僅系統內部調用時才包括）
            agents = [a for a in agents if not a.is_system_agent]

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        if status:
            agents = [a for a in agents if a.status == status]

        return agents

    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """
        更新 Agent 狀態

        Args:
            agent_id: Agent ID
            status: 新狀態

        Returns:
            是否成功更新
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status
            # last_updated 是只讀屬性，通過更新 last_heartbeat 來間接更新
            agent.last_heartbeat = datetime.now()  # type: ignore[assignment]  # 更新心跳時間以反映更新

            if self._storage:
                try:
                    self._storage.update_agent(agent)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent update: {e}")

            self._logger.debug(f"Updated agent {agent_id} status to {status.value}")
            return True
        return False

    def update_heartbeat(self, agent_id: str) -> bool:
        """
        更新 Agent 心跳

        Args:
            agent_id: Agent ID

        Returns:
            是否成功更新
        """
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = datetime.now()
            # 如果之前是維修中狀態，自動恢復為在線狀態
            if agent.status == AgentStatus.MAINTENANCE:
                agent.status = AgentStatus.ONLINE

            if self._storage:
                try:
                    self._storage.update_agent(agent)
                except Exception as e:
                    self._logger.error(f"Failed to persist agent update: {e}")

            return True
        return False

    def get_all_agents(self) -> List[AgentRegistryInfo]:
        """
        獲取所有 Agent（包括離線的）

        Returns:
            所有 Agent 列表
        """
        return list(self._agents.values())


# 全局 Agent Registry 實例
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    獲取全局 Agent Registry 實例

    Returns:
        Agent Registry 實例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
