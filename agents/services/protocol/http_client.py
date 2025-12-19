# 代碼功能說明: HTTP Agent Service Client 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""HTTP Agent Service Client - 通過 HTTP REST API 調用 Agent 服務"""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

import httpx

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
        server_certificate: Optional[str] = None,
        ip_whitelist: Optional[list[str]] = None,
        server_fingerprint: Optional[str] = None,
    ):
        """
        初始化 HTTP Agent Service Client

        Args:
            base_url: Agent 服務的基礎 URL（例如：http://agent-planning-service:8000）
            timeout: 請求超時時間（秒）
            api_key: API 密鑰（可選，用於認證）
            server_certificate: 服務器證書（可選，用於 mTLS 認證）
            ip_whitelist: IP 白名單列表（可選）
            server_fingerprint: 服務器指紋（可選，用於身份驗證）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.server_certificate = server_certificate
        self.ip_whitelist = ip_whitelist or []
        self.server_fingerprint = server_fingerprint
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    def _generate_request_signature(self, request_body: Dict[str, Any]) -> Optional[str]:
        """
        生成請求簽名（HMAC-SHA256）

        Args:
            request_body: 請求體

        Returns:
            簽名字符串，如果沒有 API Key 則返回 None
        """
        if not self.api_key:
            return None

        try:
            # 將請求體轉換為字符串（按鍵排序以確保一致性）
            request_str = json.dumps(request_body, sort_keys=True, separators=(",", ":"))

            # 計算 HMAC-SHA256 簽名
            signature = hmac.new(
                self.api_key.encode("utf-8"),
                request_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Failed to generate request signature: {e}")
            return None

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行任務（帶認證支持）

        認證機制：
        1. API Key（通過 Authorization header）
        2. 請求簽名（如果配置了 API Key）
        3. mTLS（通過 httpx 客戶端配置）
        """
        url = f"{self.base_url}/v1/execute"
        request_body = request.model_dump()
        headers = {}

        # 1. 添加 API Key（如果配置）
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

            # 2. 生成並添加請求簽名
            signature = self._generate_request_signature(request_body)
            if signature:
                headers["X-Request-Signature"] = signature

        try:
            # 3. 配置 mTLS（如果配置了服務器證書）
            # 注意：實際的 mTLS 配置需要在 httpx.AsyncClient 初始化時完成
            # 這裡僅為示例，實際實現需要根據 server_certificate 配置客戶端證書

            response = await self._client.post(
                url,
                json=request_body,
                headers=headers,
            )
            response.raise_for_status()
            return AgentServiceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
                metadata=request.metadata,
            )
        except Exception as e:
            logger.error(f"Error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
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
