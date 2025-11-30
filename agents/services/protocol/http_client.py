# 代碼功能說明: HTTP Agent Service Client 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""HTTP Agent Service Client - 通過 HTTP REST API 調用 Agent 服務"""

import logging
from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class HTTPAgentServiceClient(AgentServiceProtocol):
    """HTTP Agent Service Client

    通過 HTTP REST API 調用遠程 Agent 服務。
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        api_key: Optional[str] = None,
    ):
        """
        初始化 HTTP Agent Service Client

        Args:
            base_url: Agent 服務的基礎 URL（例如：http://agent-planning-service:8000）
            timeout: 請求超時時間（秒）
            api_key: API 密鑰（可選，用於認證）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """執行任務"""
        url = f"{self.base_url}/v1/execute"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self._client.post(
                url,
                json=request.model_dump(),
                headers=headers,
            )
            response.raise_for_status()
            return AgentServiceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=str(e),
            )

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        url = f"{self.base_url}/v1/health"
        try:
            response = await self._client.get(url, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return AgentServiceStatus(data.get("status", "unavailable"))
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力"""
        url = f"{self.base_url}/v1/capabilities"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get capabilities: {e}")
            return {}

    async def close(self):
        """關閉客戶端連接"""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
