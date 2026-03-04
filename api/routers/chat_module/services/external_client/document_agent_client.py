# 代碼功能說明: Document Agent 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""Document Agent 客戶端 - 文件編輯"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DocumentAgentClient:
    """Document Agent 客戶端 - 調用文件編輯服務"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化 Document Agent 客戶端

        Args:
            base_url: Document Agent 服務 base URL
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/document-editing/execute"

    async def execute(
        self,
        instruction: str,
        file_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """調用 Document Agent 執行文件編輯

        Args:
            instruction: 文件編輯指令
            file_path: 文件路徑
            context: 額外上下文
            session_id: 會話 ID
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            執行結果
        """
        payload = {
            "task_id": f"doc-{session_id or 'unknown'}",
            "task_type": "document_editing",
            "task_data": {
                "instruction": instruction,
            },
        }

        if file_path:
            payload["task_data"]["file_path"] = file_path

        if user_id:
            payload["user_id"] = user_id
        if tenant_id:
            payload["tenant_id"] = tenant_id

        logger.info(f"[DocumentAgentClient] Execute: {instruction[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"[DocumentAgentClient] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[DocumentAgentClient] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "Document Agent 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[DocumentAgentClient] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[DocumentAgentClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }


# 全局實例
_document_agent_client: Optional[DocumentAgentClient] = None


def get_document_agent_client() -> DocumentAgentClient:
    """獲取全局 DocumentAgentClient 實例"""
    global _document_agent_client
    if _document_agent_client is None:
        _document_agent_client = DocumentAgentClient()
    return _document_agent_client
