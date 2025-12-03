# 代碼功能說明: Protocol Client 單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Protocol Client 單元測試"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx

from agents.services.protocol.base import (
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceProtocolType,
)
from agents.services.protocol.factory import AgentServiceClientFactory
from agents.services.protocol.http_client import HTTPAgentServiceClient


@pytest.mark.asyncio
@pytest.mark.unit
class TestHTTPClient:
    """HTTP Client 測試類"""

    async def test_http_client_execute_success(self):
        """測試 HTTP Client 執行成功"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.json.return_value = {
                "task_id": "test-task",
                "status": "completed",
                "result": {"message": "success"},
            }
            mock_response.raise_for_status = Mock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            client = HTTPAgentServiceClient(
                base_url="https://example.com",
                api_key="test-key",
            )

            request = AgentServiceRequest(
                task_id="test-task",
                task_type="test",
                task_data={"test": "data"},
            )

            response = await client.execute(request)
            assert response.status == "completed"
            assert response.task_id == "test-task"

    async def test_http_client_generate_signature(self):
        """測試 HTTP Client 生成請求簽名"""
        client = HTTPAgentServiceClient(
            base_url="https://example.com",
            api_key="test-key",
        )

        request_body = {"test": "data"}
        signature = client._generate_request_signature(request_body)

        assert signature is not None
        assert isinstance(signature, str)
        assert len(signature) > 0


@pytest.mark.asyncio
@pytest.mark.unit
class TestClientFactory:
    """Client Factory 測試類"""

    async def test_create_http_client(self):
        """測試創建 HTTP Client"""
        client = AgentServiceClientFactory.create(
            protocol=AgentServiceProtocolType.HTTP,
            endpoint="https://example.com",
            api_key="test-key",
        )

        assert isinstance(client, HTTPAgentServiceClient)
        assert client.base_url == "https://example.com"
        assert client.api_key == "test-key"
