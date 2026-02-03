# 代碼功能說明: Chat 模塊 BatchHandler（批處理：並行/串行調用 chat）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""BatchHandler：接受 requests、mode、max_concurrent，並行/串行調用 chat，返回 batch_id、results、summary。"""

import asyncio
import logging
import time
import uuid
from typing import List

from api.routers.chat_module.dependencies import get_chat_pipeline
from api.routers.chat_module.handlers.base import ChatHandlerRequest
from api.routers.chat_module.models.response import (
    BatchChatResponse,
    BatchResultItem,
    BatchSummary,
)
from services.api.models.chat import ChatRequest

logger = logging.getLogger(__name__)


class BatchHandler:
    """批處理 Chat：並行或串行調用 pipeline.process，匯總結果。"""

    async def process(
        self,
        requests: List[ChatRequest],
        mode: str,
        max_concurrent: int,
        tenant_id: str,
        current_user: object,
    ) -> BatchChatResponse:
        """
        執行批處理：依 mode 並行或串行調用 pipeline，返回 batch_id、results、summary。

        Args:
            requests: Chat 請求列表
            mode: "parallel" 或 "serial"
            max_concurrent: 並行時最大並發數
            tenant_id: 租戶 ID
            current_user: 當前用戶

        Returns:
            BatchChatResponse
        """
        batch_id = str(uuid.uuid4())
        pipeline = get_chat_pipeline()
        start = time.perf_counter()
        results: List[BatchResultItem] = []
        succeeded = 0
        failed = 0

        async def process_one(index: int, req: ChatRequest) -> BatchResultItem:
            request_id = f"{batch_id}_{index}"
            handler_req = ChatHandlerRequest(
                request_body=req,
                request_id=request_id,
                tenant_id=tenant_id,
                current_user=current_user,
            )
            try:
                response = await pipeline.process(handler_req)
                return BatchResultItem(
                    index=index,
                    success=True,
                    request_id=request_id,
                    data=response.model_dump(mode="json"),
                    error=None,
                )
            except Exception as exc:
                logger.warning(
                    f"Batch item failed: batch_id={batch_id}, index={index}, error={str(exc)}"
                )
                return BatchResultItem(
                    index=index,
                    success=False,
                    request_id=request_id,
                    data=None,
                    error=str(exc),
                )

        if mode == "serial":
            for i, req in enumerate(requests):
                item = await process_one(i, req)
                results.append(item)
                if item.success:
                    succeeded += 1
                else:
                    failed += 1
        else:
            sem = asyncio.Semaphore(max_concurrent)

            async def with_sem(index: int, req: ChatRequest) -> BatchResultItem:
                async with sem:
                    return await process_one(index, req)

            tasks = [with_sem(i, req) for i, req in enumerate(requests)]
            outcome = await asyncio.gather(*tasks, return_exceptions=True)
            for i, o in enumerate(outcome):
                if isinstance(o, Exception):
                    results.append(
                        BatchResultItem(
                            index=i,
                            success=False,
                            request_id=f"{batch_id}_{i}",
                            data=None,
                            error=str(o),
                        )
                    )
                    failed += 1
                else:
                    results.append(o)
                    if o.success:
                        succeeded += 1
                    else:
                        failed += 1

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        summary = BatchSummary(
            total=len(requests),
            succeeded=succeeded,
            failed=failed,
            total_time_ms=round(elapsed_ms, 2),
        )
        return BatchChatResponse(
            batch_id=batch_id,
            results=results,
            summary=summary,
        )
