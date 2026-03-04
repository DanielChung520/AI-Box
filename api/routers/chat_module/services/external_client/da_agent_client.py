# 代碼功能說明: DA-Agent 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""DA-Agent 客戶端 - 數據查詢"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DAAgentClient:
    """DA-Agent 客戶端 - 調用數據查詢服務"""

    def __init__(self, base_url: str = "http://localhost:8004"):
        """初始化 DA-Agent 客戶端

        Args:
            base_url: DA-Agent 服務 base URL
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/execute"

    async def query(
        self,
        natural_language_query: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """調用 DA-Agent 進行數據查詢

        Args:
            natural_language_query: 自然語言查詢
            context: 額外上下文
            session_id: 會話 ID
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            查詢結果
        """
        payload = {
            "task_id": f"da-{session_id or 'unknown'}",
            "task_type": "data_query",
            "task_data": {
                "action": "execute_structured_query",
                "natural_language_query": natural_language_query,
            },
        }

        if user_id:
            payload["user_id"] = user_id
        if tenant_id:
            payload["tenant_id"] = tenant_id

        logger.info(f"[DAAgentClient] Query: {natural_language_query[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"[DAAgentClient] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[DAAgentClient] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "DA-Agent 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[DAAgentClient] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[DAAgentClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }


# 全局實例
_da_agent_client: Optional[DAAgentClient] = None


def get_da_agent_client() -> DAAgentClient:
    """獲取全局 DAAgentClient 實例"""
    global _da_agent_client
    if _da_agent_client is None:
        _da_agent_client = DAAgentClient()
    return _da_agent_client
