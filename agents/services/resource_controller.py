# 代碼功能說明: Agent 資源訪問控制器
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent 資源訪問控制器

實現 Agent 資源訪問權限控制：
- 內部 Agent：完整權限（允許訪問所有資源）
- 外部 Agent：受限權限（僅可訪問分配的資源）
"""

import logging
from enum import Enum
from typing import Optional

from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import AgentRegistryInfo

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """資源類型"""

    MEMORY = "memory"
    TOOL = "tool"
    LLM = "llm"
    DATABASE = "database"
    FILE = "file"


class ResourceAccessController:
    """資源訪問控制器

    檢查 Agent 是否有權限訪問特定資源。
    """

    def __init__(self, registry=None):
        """
        初始化資源訪問控制器

        Args:
            registry: Agent Registry 實例（可選，默認使用全局實例）
        """
        self._registry = registry or get_agent_registry()
        self._logger = logger

    def check_access(
        self, agent_id: str, resource_type: ResourceType, resource_name: str
    ) -> bool:
        """
        檢查 Agent 是否有權限訪問特定資源

        Args:
            agent_id: Agent ID
            resource_type: 資源類型（MEMORY, TOOL, LLM, DATABASE, FILE）
            resource_name: 資源名稱（命名空間、工具名、Provider 名等）

        Returns:
            是否有權限訪問
        """
        try:
            agent_info = self._registry.get_agent_info(agent_id)

            if not agent_info:
                self._logger.warning(f"Agent '{agent_id}' not found")
                return False

            # 內部 Agent：完整權限
            if agent_info.endpoints.is_internal:
                self._logger.debug(
                    f"Internal agent '{agent_id}' granted full access to {resource_type.value}:{resource_name}"
                )
                return True

            # 外部 Agent：檢查權限配置
            permissions = agent_info.permissions
            return self._check_external_agent_access(
                permissions, resource_type, resource_name
            )

        except Exception as e:
            self._logger.error(f"Resource access check error for '{agent_id}': {e}")
            return False

    def _check_external_agent_access(
        self,
        permissions,
        resource_type: ResourceType,
        resource_name: str,
    ) -> bool:
        """
        檢查外部 Agent 的資源訪問權限

        Args:
            permissions: Agent 權限配置
            resource_type: 資源類型
            resource_name: 資源名稱

        Returns:
            是否有權限訪問
        """
        if resource_type == ResourceType.MEMORY:
            # 檢查 Memory 命名空間
            if not permissions.allowed_memory_namespaces:
                # 如果未配置，則不允許訪問
                self._logger.debug(
                    f"Memory namespace '{resource_name}' not in allowed list"
                )
                return False
            return resource_name in permissions.allowed_memory_namespaces

        elif resource_type == ResourceType.TOOL:
            # 檢查工具
            if not permissions.allowed_tools:
                # 如果未配置，則不允許訪問
                self._logger.debug(f"Tool '{resource_name}' not in allowed list")
                return False
            return resource_name in permissions.allowed_tools

        elif resource_type == ResourceType.LLM:
            # 檢查 LLM Provider
            if not permissions.allowed_llm_providers:
                # 如果未配置，則不允許訪問
                self._logger.debug(
                    f"LLM provider '{resource_name}' not in allowed list"
                )
                return False
            return resource_name in permissions.allowed_llm_providers

        elif resource_type == ResourceType.DATABASE:
            # 檢查數據庫
            if not permissions.allowed_databases:
                # 如果未配置，則不允許訪問
                self._logger.debug(f"Database '{resource_name}' not in allowed list")
                return False
            return resource_name in permissions.allowed_databases

        elif resource_type == ResourceType.FILE:
            # 檢查文件路徑
            if not permissions.allowed_file_paths:
                # 如果未配置，則不允許訪問
                self._logger.debug(f"File path '{resource_name}' not in allowed list")
                return False
            # 檢查文件路徑是否在允許的路徑列表中（支持前綴匹配）
            for allowed_path in permissions.allowed_file_paths:
                if resource_name.startswith(allowed_path):
                    return True
            return False

        else:
            self._logger.warning(f"Unknown resource type: {resource_type}")
            return False

    def check_memory_access(self, agent_id: str, namespace: str) -> bool:
        """
        檢查 Memory 命名空間訪問權限

        Args:
            agent_id: Agent ID
            namespace: Memory 命名空間

        Returns:
            是否有權限訪問
        """
        return self.check_access(agent_id, ResourceType.MEMORY, namespace)

    def check_tool_access(self, agent_id: str, tool_name: str) -> bool:
        """
        檢查工具訪問權限

        Args:
            agent_id: Agent ID
            tool_name: 工具名稱

        Returns:
            是否有權限訪問
        """
        return self.check_access(agent_id, ResourceType.TOOL, tool_name)

    def check_llm_access(self, agent_id: str, provider_name: str) -> bool:
        """
        檢查 LLM Provider 訪問權限

        Args:
            agent_id: Agent ID
            provider_name: LLM Provider 名稱

        Returns:
            是否有權限訪問
        """
        return self.check_access(agent_id, ResourceType.LLM, provider_name)

    def check_database_access(self, agent_id: str, database_name: str) -> bool:
        """
        檢查數據庫訪問權限

        Args:
            agent_id: Agent ID
            database_name: 數據庫名稱

        Returns:
            是否有權限訪問
        """
        return self.check_access(agent_id, ResourceType.DATABASE, database_name)

    def check_file_access(self, agent_id: str, file_path: str) -> bool:
        """
        檢查文件訪問權限

        Args:
            agent_id: Agent ID
            file_path: 文件路徑

        Returns:
            是否有權限訪問
        """
        return self.check_access(agent_id, ResourceType.FILE, file_path)


# 全局資源訪問控制器實例
_global_resource_controller: Optional[ResourceAccessController] = None


def get_resource_controller() -> ResourceAccessController:
    """
    獲取全局資源訪問控制器實例

    Returns:
        資源訪問控制器實例
    """
    global _global_resource_controller
    if _global_resource_controller is None:
        _global_resource_controller = ResourceAccessController()
    return _global_resource_controller
