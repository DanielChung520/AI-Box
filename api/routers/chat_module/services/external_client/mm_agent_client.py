# 代碼功能說明: MM-Agent 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""MM-Agent 客戶端 - 物料管理業務"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class MMAgentClient:
    """MM-Agent 客戶端 - 調用物料管理業務服務"""

    def __init__(self, base_url: str = "http://localhost:8003"):
        """初始化 MM-Agent 客戶端

        Args:
            base_url: MM-Agent 服務 base URL
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/execute"

    async def execute(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """調用 MM-Agent 處理業務

        Args:
            instruction: 業務指令
            context: 額外上下文
            session_id: 會話 ID
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            業務處理結果
        """
        payload = {
            "task_id": f"mm-{session_id or 'unknown'}",
            "task_data": {
                "instruction": instruction,
            },
            "metadata": {
                "session_id": session_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
        }

        logger.info(f"[MMAgentClient] Execute: {instruction[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"[MMAgentClient] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[MMAgentClient] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "MM-Agent 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[MMAgentClient] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[MMAgentClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }


# 全局實例
_mm_agent_client: Optional[MMAgentClient] = None


def get_mm_agent_client() -> MMAgentClient:
    """獲取全局 MMAgentClient 實例"""
    global _mm_agent_client
    if _mm_agent_client is None:
        _mm_agent_client = MMAgentClient()
    return _mm_agent_client
