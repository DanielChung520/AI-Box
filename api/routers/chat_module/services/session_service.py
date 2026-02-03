# 代碼功能說明: 會話服務（歸檔等）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""會話管理服務：archive_session（歸檔會話）。"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ArchiveSessionResult:
    """歸檔結果。"""

    session_id: str
    archive_id: str
    message_count: int
    memory_consolidated: bool
    archived_at: str


async def archive_session(
    session_id: str,
    consolidate_memory: bool = True,
    delete_messages: bool = False,
    user_id: Optional[str] = None,
) -> ArchiveSessionResult:
    """
    歸檔會話：MVP 返回 archive_id、message_count 等；可後續接 ContextManager/存儲。

    Args:
        session_id: 會話 ID
        consolidate_memory: 是否鞏固記憶
        delete_messages: 是否刪除消息（MVP 不實際刪除）
        user_id: 用戶 ID（可選，用於權限）

    Returns:
        ArchiveSessionResult
    """
    # MVP：不實際讀取消息或寫入存儲，僅生成 archive_id 與佔位 message_count
    archive_id = str(uuid.uuid4())
    # 可選：從 ContextManager 或存儲查詢該 session 的消息數
    message_count = 0
    try:
        from api.routers.chat_module.dependencies import get_context_manager

        ctx = get_context_manager()
        if hasattr(ctx, "get_session_message_count"):
            message_count = getattr(ctx, "get_session_message_count")(session_id) or 0
    except Exception as exc:
        logger.debug(f"archive_session message count fallback: {exc}")
    return ArchiveSessionResult(
        session_id=session_id,
        archive_id=archive_id,
        message_count=message_count,
        memory_consolidated=consolidate_memory,
        archived_at=datetime.now(tz=timezone.utc).isoformat(),
    )
