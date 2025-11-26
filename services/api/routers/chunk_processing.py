# 代碼功能說明: 文件分塊處理路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件分塊處理路由 - 提供異步分塊處理和進度查詢功能"""

import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog
from enum import Enum

from services.api.core.response import APIResponse
from services.api.storage.file_storage import FileStorage, create_storage_from_config
from services.api.processors.chunk_processor import (
    ChunkProcessor,
    create_chunk_processor_from_config,
)
from services.api.processors.parsers.txt_parser import TxtParser
from services.api.processors.parsers.md_parser import MdParser
from services.api.processors.parsers.pdf_parser import PdfParser
from services.api.processors.parsers.docx_parser import DocxParser
from core.config import get_config_section

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["Chunk Processing"])

# 處理狀態存儲（內存，生產環境應使用 Redis）
_processing_status: Dict[str, Dict[str, Any]] = {}


class ProcessingStatus(Enum):
    """處理狀態枚舉"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def get_storage() -> FileStorage:
    """獲取文件存儲實例"""
    config = get_config_section("file_upload", default={}) or {}
    return create_storage_from_config(config)


def get_chunk_processor() -> ChunkProcessor:
    """獲取分塊處理器實例"""
    config = get_config_section("chunk_processing", default={}) or {}
    return create_chunk_processor_from_config(config)


def get_parser(file_type: str):
    """根據文件類型獲取解析器"""
    file_type_lower = file_type.lower() if file_type else ""

    if file_type_lower == "text/plain" or file_type_lower.endswith(".txt"):
        return TxtParser()
    elif file_type_lower == "text/markdown" or file_type_lower.endswith(".md"):
        return MdParser()
    elif file_type_lower == "application/pdf" or file_type_lower.endswith(".pdf"):
        try:
            return PdfParser()
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF 解析器未安裝，請安裝 PyPDF2",
            )
    elif "wordprocessingml" in file_type_lower or file_type_lower.endswith(".docx"):
        try:
            return DocxParser()
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DOCX 解析器未安裝，請安裝 python-docx",
            )
    else:
        # 默認使用文本解析器
        return TxtParser()


async def process_file_chunking(
    file_id: str, file_path: str, file_type: Optional[str] = None
):
    """
    異步處理文件分塊

    Args:
        file_id: 文件 ID
        file_path: 文件路徑
        file_type: 文件類型（MIME 類型）
    """
    try:
        # 更新狀態為處理中
        _processing_status[file_id] = {
            "status": ProcessingStatus.PROCESSING.value,
            "progress": 0,
            "message": "開始解析文件",
        }

        # 獲取解析器
        parser = get_parser(file_type)

        # 解析文件
        if hasattr(parser, "parse"):
            result = parser.parse(file_path)
        else:
            # 如果沒有 parse 方法，嘗試從字節讀取
            storage = get_storage()
            file_content = storage.read_file(file_id)
            if file_content is None:
                raise ValueError(f"無法讀取文件: {file_id}")

            if hasattr(parser, "parse_from_bytes"):
                result = parser.parse_from_bytes(file_content)
            else:
                raise ValueError(f"解析器不支持此文件類型: {file_type}")

        _processing_status[file_id]["progress"] = 50
        _processing_status[file_id]["message"] = "文件解析完成，開始分塊"

        # 獲取分塊處理器
        chunk_processor = get_chunk_processor()

        # 生成分塊
        chunks = chunk_processor.process(
            text=result["text"],
            file_id=file_id,
            metadata=result.get("metadata", {}),
        )

        # 更新狀態為完成
        _processing_status[file_id] = {
            "status": ProcessingStatus.COMPLETED.value,
            "progress": 100,
            "message": "分塊處理完成",
            "chunks": chunks,
            "chunk_count": len(chunks),
        }

        logger.info(
            "文件分塊處理完成",
            file_id=file_id,
            chunk_count=len(chunks),
        )

    except Exception as e:
        logger.error(
            "文件分塊處理失敗",
            file_id=file_id,
            error=str(e),
        )
        _processing_status[file_id] = {
            "status": ProcessingStatus.FAILED.value,
            "progress": 0,
            "message": f"處理失敗: {str(e)}",
            "error": str(e),
        }


@router.post("/{file_id}/chunk")
async def trigger_chunk_processing(
    file_id: str,
    background_tasks: BackgroundTasks,
    strategy: Optional[str] = None,
    chunk_size: Optional[int] = None,
) -> JSONResponse:
    """
    觸發文件分塊處理

    Args:
        file_id: 文件 ID
        background_tasks: FastAPI 後台任務
        strategy: 分塊策略（可選）
        chunk_size: 分塊大小（可選）

    Returns:
        處理任務已啟動
    """
    storage = get_storage()

    # 檢查文件是否存在
    if not storage.file_exists(file_id):
        return APIResponse.error(
            message="文件不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 檢查是否已在處理中
    if file_id in _processing_status:
        status_info = _processing_status[file_id]
        if status_info["status"] == ProcessingStatus.PROCESSING.value:
            return APIResponse.error(
                message="文件正在處理中",
                details=status_info,
                status_code=status.HTTP_409_CONFLICT,
            )

    # 獲取文件路徑和類型
    file_path = storage.get_file_path(file_id)
    if file_path is None:
        return APIResponse.error(
            message="無法獲取文件路徑",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 從文件擴展名推斷文件類型
    file_ext = os.path.splitext(file_path)[1].lower()
    file_type_map = {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    file_type = file_type_map.get(file_ext)

    # 初始化處理狀態
    _processing_status[file_id] = {
        "status": ProcessingStatus.PENDING.value,
        "progress": 0,
        "message": "等待處理",
    }

    # 添加後台任務
    background_tasks.add_task(process_file_chunking, file_id, file_path, file_type)

    return APIResponse.success(
        data={
            "file_id": file_id,
            "status": ProcessingStatus.PENDING.value,
            "message": "分塊處理任務已啟動",
        },
        message="分塊處理任務已啟動",
    )


@router.get("/{file_id}/chunk/status")
async def get_chunk_status(file_id: str) -> JSONResponse:
    """
    查詢文件分塊處理狀態

    Args:
        file_id: 文件 ID

    Returns:
        處理狀態和結果
    """
    if file_id not in _processing_status:
        return APIResponse.error(
            message="未找到處理任務",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    status_info = _processing_status[file_id].copy()

    # 如果處理完成，返回分塊信息（但不返回完整分塊內容，只返回統計信息）
    if status_info["status"] == ProcessingStatus.COMPLETED.value:
        chunk_count = status_info.get("chunk_count", 0)
        return APIResponse.success(
            data={
                "file_id": file_id,
                "status": status_info["status"],
                "progress": status_info["progress"],
                "message": status_info["message"],
                "chunk_count": chunk_count,
            },
            message="處理完成",
        )

    return APIResponse.success(
        data={
            "file_id": file_id,
            "status": status_info["status"],
            "progress": status_info.get("progress", 0),
            "message": status_info.get("message", ""),
        },
    )


@router.get("/{file_id}/chunks")
async def get_file_chunks(
    file_id: str, limit: Optional[int] = None, offset: Optional[int] = None
) -> JSONResponse:
    """
    獲取文件的分塊列表

    Args:
        file_id: 文件 ID
        limit: 返回數量限制
        offset: 偏移量

    Returns:
        分塊列表
    """
    if file_id not in _processing_status:
        return APIResponse.error(
            message="未找到處理任務",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    status_info = _processing_status[file_id]

    if status_info["status"] != ProcessingStatus.COMPLETED.value:
        return APIResponse.error(
            message="文件尚未完成分塊處理",
            details={"status": status_info["status"]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    chunks = status_info.get("chunks", [])

    # 應用分頁
    if offset is not None:
        chunks = chunks[offset:]
    if limit is not None:
        chunks = chunks[:limit]

    return APIResponse.success(
        data={
            "file_id": file_id,
            "chunks": chunks,
            "total": len(status_info.get("chunks", [])),
            "returned": len(chunks),
        },
    )
