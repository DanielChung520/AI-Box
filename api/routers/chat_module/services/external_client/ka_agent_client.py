# 代碼功能說明: KA-Agent 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""KA-Agent 客戶端 - 知識庫問答"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class KAAgentClient:
    """KA-Agent 客戶端 - 調用知識庫問答服務"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化 KA-Agent 客戶端

        Args:
            base_url: KA-Agent 服務 base URL
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/ka-agent/query"

    async def query(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """調用 KA-Agent 進行知識庫檢索

        Args:
            question: 用戶問題
            context: 額外上下文
            session_id: 會話 ID
            user_id: 用戶 ID

        Returns:
            檢索結果
        """
        payload = {
            "question": question,
            "context": context or {},
        }

        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id

        logger.info(f"[KAAgentClient] Query: {question[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"[KAAgentClient] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[KAAgentClient] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "KA-Agent 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[KAAgentClient] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[KAAgentClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }


# 全局實例
_ka_agent_client: Optional[KAAgentClient] = None


def get_ka_agent_client() -> KAAgentClient:
    """獲取全局 KAAgentClient 實例"""
    global _ka_agent_client
    if _ka_agent_client is None:
        _ka_agent_client = KAAgentClient()
    return _ka_agent_client
