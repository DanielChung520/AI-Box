# 代碼功能說明: MM-Agent 適配器
# 創建日期: 2026-03-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-03

"""MM-Agent (物料管理) 適配器

實現與 MM-Agent 服務的整合。
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from line_integration.agents.base import AgentAdapter, register_agent_adapter

logger = logging.getLogger(__name__)


class MMAgentAdapter(AgentAdapter):
    """MM-Agent 適配器

    負責調用 MM-Agent (物料管理) 服務。
    """

    def __init__(self, agent_url: str = "http://localhost:8003"):
        """初始化 MM-Agent 適配器

        Args:
            agent_url: MM-Agent 服務 URL
        """
        super().__init__(agent_url=agent_url, agent_type="mm_agent")

    async def execute(
        self,
        instruction: str,
        session_id: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行 MM-Agent 任務

        Args:
            instruction: 用戶指令
            session_id: 會話 ID
            user_id: 用戶 ID
            conversation_history: 對話歷史
            context: 額外上下文

        Returns:
            MM-Agent 執行結果
        """
        payload = {
            "task_id": f"line-{session_id}",
            "task_type": "mm_agent",
            "task_data": {
                "instruction": instruction,
            },
            "metadata": {
                "session_id": session_id,
                "user_id": user_id,
                "tenant_id": context.get("tenant_id", "default") if context else "default",
                "channel": "line",
            },
        }

        logger.info(f"[MMAgentAdapter] Executing: {instruction[:50]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                result = response.json()

                logger.info(f"[MMAgentAdapter] Success: {result.get('status')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"[MMAgentAdapter] Timeout: {self.endpoint}")
            return {
                "status": "error",
                "error": "timeout",
                "message": "MM-Agent 請求超時",
            }

        except httpx.HTTPError as e:
            logger.error(f"[MMAgentAdapter] HTTP Error: {e}")
            return {
                "status": "error",
                "error": "http_error",
                "message": str(e),
            }

        except Exception as e:
            logger.error(f"[MMAgentAdapter] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
            }

    def get_capabilities(self) -> List[str]:
        """獲取 MM-Agent 支持的能力

        Returns:
            能力列表
        """
        return [
            "查詢料號",
            "查詢庫存",
            "缺料分析",
            "生成採購單",
            "庫存管理",
        ]


# 註冊 MM-Agent 適配器
register_agent_adapter("mm_agent", MMAgentAdapter)
