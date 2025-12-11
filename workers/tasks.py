# 代碼功能說明: RQ Worker 任務處理函數
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ Worker 任務處理函數 - 定義所有需要在 Worker 中執行的任務"""

from __future__ import annotations

import asyncio
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


def process_file_chunking_and_vectorization_task(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
) -> dict:
    """
    處理文件分塊和向量化任務（RQ Worker 版本）

    Args:
        file_id: 文件ID
        file_path: 文件路徑
        file_type: 文件類型（MIME類型）
        user_id: 用戶ID

    Returns:
        處理結果字典
    """
    try:
        # 導入異步處理函數
        from api.routers.file_upload import process_file_chunking_and_vectorization

        # 在 Worker 中運行異步函數
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                process_file_chunking_and_vectorization(
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                )
            )
            return {"success": True, "file_id": file_id}
        finally:
            loop.close()

    except Exception as e:
        logger.error(
            "Failed to process file chunking and vectorization",
            file_id=file_id,
            error=str(e),
        )
        return {"success": False, "file_id": file_id, "error": str(e)}


def process_vectorization_only_task(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
) -> dict:
    """
    處理向量化任務（RQ Worker 版本）

    Args:
        file_id: 文件ID
        file_path: 文件路徑
        file_type: 文件類型（MIME類型）
        user_id: 用戶ID

    Returns:
        處理結果字典
    """
    try:
        from api.routers.file_upload import process_vectorization_only

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                process_vectorization_only(
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                )
            )
            return {"success": True, "file_id": file_id}
        finally:
            loop.close()

    except Exception as e:
        logger.error(
            "Failed to process vectorization",
            file_id=file_id,
            error=str(e),
        )
        return {"success": False, "file_id": file_id, "error": str(e)}


def process_kg_extraction_only_task(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
    force_rechunk: bool = False,
) -> dict:
    """
    處理知識圖譜提取任務（RQ Worker 版本）

    Args:
        file_id: 文件ID
        file_path: 文件路徑
        file_type: 文件類型（MIME類型）
        user_id: 用戶ID
        force_rechunk: 是否強制重新分塊

    Returns:
        處理結果字典
    """
    try:
        from api.routers.file_upload import process_kg_extraction_only

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                process_kg_extraction_only(
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=user_id,
                    force_rechunk=force_rechunk,
                )
            )
            return {"success": True, "file_id": file_id}
        finally:
            loop.close()

    except Exception as e:
        logger.error(
            "Failed to process KG extraction",
            file_id=file_id,
            error=str(e),
        )
        return {"success": False, "file_id": file_id, "error": str(e)}
