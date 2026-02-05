"""
代碼功能說明: AI 狀態事件發布工具
創建日期: 2026-02-02
創建人: OpenCode AI
最後修改日期: 2026-02-02
"""

from datetime import datetime

from api.routers.agent_status import (
    AgentStatusEvent,
    _agent_status_subscribers,
    publish_status,
)


def create_status_event(
    request_id: str,
    step: str,
    status: str,
    message: str,
    progress: float = 0.0,
) -> AgentStatusEvent:
    """創建狀態事件"""
    return AgentStatusEvent(
        request_id=request_id,
        step=step,
        status=status,
        message=message,
        progress=progress,
        timestamp=datetime.now().isoformat(),
    )


async def send_status(
    request_id: str,
    step: str,
    status: str,
    message: str,
    progress: float = 0.0,
) -> None:
    """發送狀態事件（異步）"""
    event = create_status_event(request_id, step, status, message, progress)
    await publish_status(request_id, event)


def sync_send_status(
    request_id: str,
    step: str,
    status: str,
    message: str,
    progress: float = 0.0,
) -> None:
    """同步發送狀態事件（用於同步函數中）"""
    event = create_status_event(request_id, step, status, message, progress)
    if request_id in _agent_status_subscribers:
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_loop(loop)
            loop.run_until_complete(_agent_status_subscribers[request_id].put(event.model_dump_json()))
            loop.close()
        except Exception:
            pass


class StatusTracker:
    """狀態追蹤器 - 用於在函數中追蹤狀態"""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.step_count = 0

    async def update(
        self,
        step: str,
        status: str,
        message: str,
        progress: float,
    ) -> None:
        """更新狀態"""
        await send_status(
            request_id=self.request_id,
            step=step,
            status=status,
            message=message,
            progress=progress,
        )

    async def start(self, step: str = "開始執行", message: str = "AI 正在分析問題") -> None:
        """開始追蹤"""
        self.step_count += 1
        await self.update(step, "processing", message, 0.1)

    async def progress(self, step: str, message: str, progress: float) -> None:
        """進度更新"""
        self.step_count += 1
        await self.update(step, "processing", message, progress)

    async def complete(self, step: str = "完成", message: str = "處理完成") -> None:
        """完成追蹤"""
        await self.update(step, "completed", message, 1.0)

    async def error(self, step: str = "錯誤", message: str = "處理失敗") -> None:
        """錯誤"""
        await self.update(step, "error", message, 0)
