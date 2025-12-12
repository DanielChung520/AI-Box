# 代碼功能說明: Agent Registry 單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry 單元測試"""

import pytest

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


class MockAgent(AgentServiceProtocol):
    """Mock Agent 實現"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        return AgentServiceResponse(
            task_id=request.task_id,
            status="completed",
            result={"agent_id": self.agent_id, "message": "Mock execution"},
            metadata=request.metadata,
        )

    async def health_check(self) -> AgentServiceStatus:
        return AgentServiceStatus.AVAILABLE

    async def get_capabilities(self) -> dict:
        return {"description": f"Mock agent {self.agent_id}"}


@pytest.fixture
def registry():
    """創建一個新的 Registry 實例"""
    return AgentRegistry()


@pytest.fixture
def internal_agent_request():
    """創建內部 Agent 註冊請求"""
    return AgentRegistrationRequest(
        agent_id="test-internal-agent",
        agent_type="test",
        name="Test Internal Agent",
        endpoints=AgentEndpoints(
            http=None,
            mcp=None,
            protocol=AgentServiceProtocolType.HTTP,
            is_internal=True,
        ),
        capabilities=["test"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="Test internal agent",
        ),
        permissions=AgentPermissionConfig(),
    )


@pytest.fixture
def external_agent_request():
    """創建外部 Agent 註冊請求"""
    return AgentRegistrationRequest(
        agent_id="test-external-agent",
        agent_type="test",
        name="Test External Agent",
        endpoints=AgentEndpoints(
            http="https://example.com/api",
            mcp=None,
            protocol=AgentServiceProtocolType.HTTP,
            is_internal=False,
        ),
        capabilities=["test"],
        metadata=AgentMetadata(
            version="1.0.0",
            description="Test external agent",
        ),
        permissions=AgentPermissionConfig(
            api_key="test-api-key",
            ip_whitelist=["192.168.1.0/24"],
        ),
    )


@pytest.mark.asyncio
@pytest.mark.unit
class TestAgentRegistry:
    """Agent Registry 測試類"""

    async def test_register_internal_agent_with_instance(
        self, registry, internal_agent_request
    ):
        """測試註冊內部 Agent（帶實例）"""
        mock_agent = MockAgent("test-internal-agent")
        success = registry.register_agent(internal_agent_request, instance=mock_agent)

        assert success is True
        assert "test-internal-agent" in registry._agents

        # 驗證實例已存儲
        agent_info = registry.get_agent_info("test-internal-agent")
        assert agent_info is not None
        assert agent_info.endpoints.is_internal is True

        # 驗證可以獲取實例
        agent = registry.get_agent("test-internal-agent")
        assert agent is not None
        assert agent is not None
        assert isinstance(agent, MockAgent)

    async def test_register_external_agent(self, registry, external_agent_request):
        """測試註冊外部 Agent"""
        success = registry.register_agent(external_agent_request)

        assert success is True
        assert "test-external-agent" in registry._agents

        # 驗證 Agent 信息
        agent_info = registry.get_agent_info("test-external-agent")
        assert agent_info is not None
        assert agent_info.endpoints.is_internal is False
        assert agent_info.endpoints.http == "https://example.com/api"

    async def test_get_agent_internal(self, registry, internal_agent_request):
        """測試獲取內部 Agent（應返回實例）"""
        mock_agent = MockAgent("test-internal-agent")
        registry.register_agent(internal_agent_request, instance=mock_agent)

        agent = registry.get_agent("test-internal-agent")
        agent_info = registry.get_agent_info("test-internal-agent")
        assert agent_info is not None
        assert agent_info.agent_id == "test-internal-agent"
        assert agent_info.endpoints.is_internal is True

    async def test_unregister_agent(self, registry, internal_agent_request):
        """測試取消註冊 Agent"""
        mock_agent = MockAgent("test-internal-agent")
        registry.register_agent(internal_agent_request, instance=mock_agent)

        success = registry.unregister_agent("test-internal-agent")
        assert success is True
        assert "test-internal-agent" not in registry._agents
        assert "test-internal-agent" not in registry._agent_instances

    async def test_update_agent_status(self, registry, internal_agent_request):
        """測試更新 Agent 狀態"""
        mock_agent = MockAgent("test-internal-agent")
        registry.register_agent(internal_agent_request, instance=mock_agent)

        success = await registry.update_agent_status(
            "test-internal-agent", AgentStatus.ONLINE
        )
        assert success is True

        agent_info = registry.get_agent_info("test-internal-agent")
        assert agent_info.status == AgentStatus.ONLINE

    async def test_list_agents(
        self, registry, internal_agent_request, external_agent_request
    ):
        """測試列出 Agent"""
        mock_agent = MockAgent("test-internal-agent")
        registry.register_agent(internal_agent_request, instance=mock_agent)
        success = registry.register_agent(external_agent_request)
        assert success is True

        agents = registry.list_agents()
        assert len(agents) == 2

        # 測試過濾
        filtered_agents = registry.list_agents(agent_type="test")
        assert len(filtered_agents) == 2
