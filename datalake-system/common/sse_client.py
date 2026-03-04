# AI-Box SSE Status Client
# 用於 MM-Agent 和 Data-Agent 向 AI-Box 發送狀態事件

import httpx
import os
from typing import Optional
from datetime import datetime


class AIBoxSSEClient:
    """AI-Box SSE 狀態客戶端

    用於向 AI-Box 的 /api/v1/agent-status/event 端點發送狀態事件，
    前端可以通過 /api/v1/agent-status/stream/{request_id} 訂閱這些事件。
    """

    def __init__(self, ai_box_url: Optional[str] = None):
        self.ai_box_url = ai_box_url or os.getenv("AI_BOX_API_URL", "http://localhost:8000")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def publish_event(
        self,
        request_id: str,
        step: str,
        status: str,
        message: str,
        progress: float = 0.0,
    ) -> bool:
        """發送狀態事件到 AI-Box

        Args:
            request_id: 請求 ID
            step: 步驟名稱
            status: 狀態 (processing/completed/error)
            message: 狀態描述
            progress: 進度 0-1

        Returns:
            是否發送成功
        """
        try:
            event_data = {
                "request_id": request_id,
                "step": step,
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat(),
            }

            response = await self.client.post(
                f"{self.ai_box_url}/api/v1/agent-status/event",
                json=event_data,
            )

            if response.status_code == 200:
                return True
            else:
                print(f"[SSE Client] Failed to publish event: {response.status_code}")
                return False
        except Exception as e:
            print(f"[SSE Client] Error publishing event: {e}")
            return False

    async def start_tracking(self, request_id: str) -> bool:
        """開始追蹤"""
        try:
            response = await self.client.post(
                f"{self.ai_box_url}/api/v1/agent-status/start",
                json={"request_id": request_id},
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[SSE Client] Error starting tracking: {e}")
            return False

    async def end_tracking(self, request_id: str) -> bool:
        """結束追蹤"""
        try:
            response = await self.client.post(
                f"{self.ai_box_url}/api/v1/agent-status/end",
                params={"request_id": request_id},
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[SSE Client] Error ending tracking: {e}")
            return False

    # 便捷方法

    async def notify_start(self, request_id: str, task_name: str):
        """通知任務開始"""
        await self.publish_event(
            request_id=request_id,
            step="task_started",
            status="processing",
            message=f"開始處理：{task_name}",
            progress=0.0,
        )

    async def notify_progress(self, request_id: str, step: str, message: str, progress: float):
        """通知進度"""
        await self.publish_event(
            request_id=request_id,
            step=step,
            status="processing",
            message=message,
            progress=progress,
        )

    async def notify_complete(self, request_id: str, message: str = "完成"):
        """通知完成"""
        await self.publish_event(
            request_id=request_id,
            step="task_completed",
            status="completed",
            message=message,
            progress=1.0,
        )

    async def notify_error(self, request_id: str, error: str):
        """通知錯誤"""
        await self.publish_event(
            request_id=request_id,
            step="task_error",
            status="error",
            message=f"錯誤：{error}",
            progress=0.0,
        )

    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()


# 全局客戶端實例
_sse_client: Optional[AIBoxSSEClient] = None


def get_sse_client() -> AIBoxSSEClient:
    """獲取 SSE 客戶端實例"""
    global _sse_client
    if _sse_client is None:
        _sse_client = AIBoxSSEClient()
    return _sse_client
