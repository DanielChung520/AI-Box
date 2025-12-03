# 代碼功能說明: Agent Platform 集成測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Platform 集成測試"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from agents.services.registry.registry import AgentRegistry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
    AgentStatus,
)
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
    AgentServiceProtocolType,
)
from agents.services.resource_controller import ResourceAccessController, ResourceType


class MockInternalAgent(AgentServiceProtocol):
    """Mock 內部 Agent"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        return AgentServiceResponse(
            task_id=request.task_id,
            status="completed",
            result={"agent_id": self.agent_id, "executed": True},
            metadata=request.metadata,
        )

    async def health_check(self) -> AgentServiceStatus:
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> dict:
        return {"description": f"Mock agent {self.agent_id}"}


@pytest.mark.asyncio
@pytest.mark.integration
class TestAgentPlatformIntegration:
    """Agent Platform 集成測試類"""

    async def test_internal_agent_registration_and_execution(self):
        """測試內部 Agent 註冊和執行完整流程"""
        registry = AgentRegistry()

        # 註冊內部 Agent
        request = AgentRegistrationRequest(
            agent_id="integration-test-agent",
            agent_type="test",
            name="Integration Test Agent",
            endpoints=AgentEndpoints(
                is_internal=True,
                protocol=AgentServiceProtocolType.HTTP,
            ),
            capabilities=["test"],
            metadata=AgentMetadata(),
            permissions=AgentPermissionConfig(),
        )

        mock_agent = MockInternalAgent("integration-test-agent")
        success = registry.register_agent(request, instance=mock_agent)
        assert success is True

        # 獲取 Agent
        agent = registry.get_agent("integration-test-agent")
        assert agent is not None

        # 執行任務
        service_request = AgentServiceRequest(
            task_id="test-task-1",
            task_type="test",
            task_data={"test": "data"},
        )

        response = await agent.execute(service_request)
        assert response.status == "completed"
        assert response.result["agent_id"] == "integration-test-agent"

    async def test_resource_access_control_integration(self):
        """測試資源訪問控制集成"""
        registry = AgentRegistry()
        resource_controller = ResourceAccessController()

        # 註冊外部 Agent（受限權限）
        request = AgentRegistrationRequest(
            agent_id="restricted-agent",
            agent_type="test",
            name="Restricted Agent",
            endpoints=AgentEndpoints(
                is_internal=False,
                protocol=AgentServiceProtocolType.HTTP,
            ),
            capabilities=["test"],
            metadata=AgentMetadata(),
            permissions=AgentPermissionConfig(
                allowed_memory_namespaces=["allowed-ns"],
                allowed_tools=["tool1"],
            ),
        )

        registry.register_agent(request)

        # 測試資源訪問
        assert (
            resource_controller.check_access(
                "restricted-agent", ResourceType.MEMORY, "allowed-ns"
            )
            is True
        )
        assert (
            resource_controller.check_access(
                "restricted-agent", ResourceType.MEMORY, "forbidden-ns"
            )
            is False
        )
        assert (
            resource_controller.check_access(
                "restricted-agent", ResourceType.TOOL, "tool1"
            )
            is True
        )
        assert (
            resource_controller.check_access(
                "restricted-agent", ResourceType.TOOL, "tool2"
            )
            is False
        )

    async def test_agent_discovery_integration(self):
        """測試 Agent 發現集成"""
        from agents.services.registry.discovery import AgentDiscovery

        registry = AgentRegistry()
        discovery = AgentDiscovery(registry=registry)

        # 註冊多個 Agent
        for i in range(3):
            request = AgentRegistrationRequest(
                agent_id=f"discovery-agent-{i}",
                agent_type="test",
                name=f"Discovery Agent {i}",
                endpoints=AgentEndpoints(
                    is_internal=True,
                    protocol=AgentServiceProtocolType.HTTP,
                ),
                capabilities=[f"capability-{i}"],
                metadata=AgentMetadata(),
                permissions=AgentPermissionConfig(),
            )
            mock_agent = MockInternalAgent(f"discovery-agent-{i}")
            registry.register_agent(request, instance=mock_agent)

        # 發現 Agent
        agents = discovery.discover_agents(
            required_capabilities=["capability-1"],
            status=AgentStatus.ONLINE,
        )

        assert len(agents) >= 1
        assert any(agent.agent_id == "discovery-agent-1" for agent in agents)
