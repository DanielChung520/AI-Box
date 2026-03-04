# 代碼功能說明: Task Orchestrator 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""Task Orchestrator 客戶端 - 複雜任務編排"""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class TaskOrchestratorClient:
    """Task Orchestrator 客戶端 - 調用任務編排服務"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化 Task Orchestrator 客戶端

        Args:
            base_url: Task Orchestrator 服務 base URL
        """
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/task/orchestrate"

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """調用 Task Orchestrator 執行複雜任務

        Args:
            task: 任務描述
            context: 額外上下文
            session_id: 會話 ID
            user_id: 用戶 ID

        Returns:
            任務執行結果
        """
        payload = {
            "task": task,
            "context": context or {},
        }

        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id

        logger.info(f"[TaskOrchestratorClient] Execute: {task[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"[TaskOrchestratorClient] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[TaskOrchestratorClient] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "Task Orchestrator 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[TaskOrchestratorClient] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[TaskOrchestratorClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }


# 全局實例
_task_orchestrator_client: Optional[TaskOrchestratorClient] = None


def get_task_orchestrator_client() -> TaskOrchestratorClient:
    """獲取全局 TaskOrchestratorClient 實例"""
    global _task_orchestrator_client
    if _task_orchestrator_client is None:
        _task_orchestrator_client = TaskOrchestratorClient()
    return _task_orchestrator_client
