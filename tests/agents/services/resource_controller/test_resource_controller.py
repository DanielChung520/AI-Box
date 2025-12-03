# 代碼功能說明: 資源訪問控制單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""資源訪問控制單元測試"""

import pytest
from unittest.mock import Mock, patch

from agents.services.resource_controller import ResourceAccessController, ResourceType
from agents.services.registry.models import (
    AgentRegistryInfo,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
    AgentStatus,
)
from agents.services.protocol.base import AgentServiceProtocolType


@pytest.mark.asyncio
@pytest.mark.unit
class TestResourceAccessController:
    """資源訪問控制器測試類"""

    async def test_internal_agent_full_access(self):
        """測試內部 Agent 完整權限"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_agent_info = AgentRegistryInfo(
                agent_id="test-internal",
                agent_type="test",
                name="Test Internal",
                status=AgentStatus.ONLINE,
                endpoints=AgentEndpoints(
                    is_internal=True, protocol=AgentServiceProtocolType.HTTP
                ),
                capabilities=[],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(),
            )

            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = mock_agent_info
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            # 內部 Agent 應該有完整權限
            assert (
                controller.check_access(
                    "test-internal", ResourceType.MEMORY, "any-namespace"
                )
                is True
            )
            assert (
                controller.check_access("test-internal", ResourceType.TOOL, "any-tool")
                is True
            )
            assert (
                controller.check_access(
                    "test-internal", ResourceType.LLM, "any-provider"
                )
                is True
            )

    async def test_external_agent_memory_access_allowed(self):
        """測試外部 Agent Memory 訪問（允許）"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_agent_info = AgentRegistryInfo(
                agent_id="test-external",
                agent_type="test",
                name="Test External",
                status=AgentStatus.ONLINE,
                endpoints=AgentEndpoints(
                    is_internal=False, protocol=AgentServiceProtocolType.HTTP
                ),
                capabilities=[],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(
                    allowed_memory_namespaces=["allowed-namespace"],
                ),
            )

            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = mock_agent_info
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            # 允許的命名空間
            assert (
                controller.check_access(
                    "test-external", ResourceType.MEMORY, "allowed-namespace"
                )
                is True
            )
            # 不允許的命名空間
            assert (
                controller.check_access(
                    "test-external", ResourceType.MEMORY, "forbidden-namespace"
                )
                is False
            )

    async def test_external_agent_tool_access(self):
        """測試外部 Agent Tool 訪問"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_agent_info = AgentRegistryInfo(
                agent_id="test-external",
                agent_type="test",
                name="Test External",
                status=AgentStatus.ONLINE,
                endpoints=AgentEndpoints(
                    is_internal=False, protocol=AgentServiceProtocolType.HTTP
                ),
                capabilities=[],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(
                    allowed_tools=["tool1", "tool2"],
                ),
            )

            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = mock_agent_info
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            assert (
                controller.check_access("test-external", ResourceType.TOOL, "tool1")
                is True
            )
            assert (
                controller.check_access("test-external", ResourceType.TOOL, "tool2")
                is True
            )
            assert (
                controller.check_access("test-external", ResourceType.TOOL, "tool3")
                is False
            )

    async def test_external_agent_llm_access(self):
        """測試外部 Agent LLM Provider 訪問"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_agent_info = AgentRegistryInfo(
                agent_id="test-external",
                agent_type="test",
                name="Test External",
                status=AgentStatus.ONLINE,
                endpoints=AgentEndpoints(
                    is_internal=False, protocol=AgentServiceProtocolType.HTTP
                ),
                capabilities=[],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(
                    allowed_llm_providers=["ollama", "openai"],
                ),
            )

            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = mock_agent_info
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            assert (
                controller.check_access("test-external", ResourceType.LLM, "ollama")
                is True
            )
            assert (
                controller.check_access("test-external", ResourceType.LLM, "openai")
                is True
            )
            assert (
                controller.check_access("test-external", ResourceType.LLM, "gemini")
                is False
            )

    async def test_external_agent_file_access(self):
        """測試外部 Agent 文件路徑訪問"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_agent_info = AgentRegistryInfo(
                agent_id="test-external",
                agent_type="test",
                name="Test External",
                status=AgentStatus.ONLINE,
                endpoints=AgentEndpoints(
                    is_internal=False, protocol=AgentServiceProtocolType.HTTP
                ),
                capabilities=[],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(
                    allowed_file_paths=["/allowed/path/", "/another/allowed/"],
                ),
            )

            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = mock_agent_info
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            # 前綴匹配
            assert (
                controller.check_access(
                    "test-external", ResourceType.FILE, "/allowed/path/file.txt"
                )
                is True
            )
            assert (
                controller.check_access(
                    "test-external", ResourceType.FILE, "/another/allowed/sub/file.txt"
                )
                is True
            )
            assert (
                controller.check_access(
                    "test-external", ResourceType.FILE, "/forbidden/path/file.txt"
                )
                is False
            )

    async def test_agent_not_found(self):
        """測試 Agent 不存在"""
        with patch(
            "agents.services.resource_controller.get_agent_registry"
        ) as mock_registry:
            mock_registry_instance = Mock()
            mock_registry_instance.get_agent_info.return_value = None
            mock_registry.return_value = mock_registry_instance

            controller = ResourceAccessController()

            assert (
                controller.check_access(
                    "non-existent", ResourceType.MEMORY, "namespace"
                )
                is False
            )
