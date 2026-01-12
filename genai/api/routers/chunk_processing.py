# 代碼功能說明: 文件分塊處理路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件分塊處理路由 - 提供異步分塊處理和進度查詢功能"""

import os
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from services.api.services.config_store_service import ConfigStoreService

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.processors.chunk_processor import (
    ChunkProcessor,
    create_chunk_processor_from_config,
)
from services.api.processors.parsers.docx_parser import DocxParser
from services.api.processors.parsers.md_parser import MdParser
from services.api.processors.parsers.pdf_parser import PdfParser
from services.api.processors.parsers.txt_parser import TxtParser
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 向後兼容：如果 ConfigStoreService 不可用，使用舊的配置方式
try:
    from services.api.services.config_store_service import ConfigStoreService

    _config_service: Optional[ConfigStoreService] = None

    def get_config_store_service() -> ConfigStoreService:
        """獲取配置存儲服務實例（單例模式）"""
        global _config_service
        if _config_service is None:
            _config_service = ConfigStoreService()
        return _config_service

    CONFIG_STORE_AVAILABLE = True
except ImportError:
    CONFIG_STORE_AVAILABLE = False
    logger.warning("ConfigStoreService 不可用，將使用舊的配置方式")

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

    # 临时修复：如果配置读取失败（空字典），或者 storage_backend 未设置，强制使用本地存储
    # 这样可以避免因为配置系统问题导致无法使用本地存储
    if not config or not config.get("storage_backend"):
        from storage.file_storage import LocalFileStorage

        storage_path = config.get("storage_path", "./data/datasets/files")
        logger.warning(
            "配置读取失败或未设置 storage_backend，临时使用本地存储",
            storage_path=storage_path,
        )
        return LocalFileStorage(storage_path=storage_path, enable_encryption=False)

    return create_storage_from_config(config)


def get_chunk_processor() -> ChunkProcessor:
    """獲取分塊處理器實例（優先從 ArangoDB system_configs 讀取）"""
    config_data: Dict[str, Any] = {}

    # 優先從 ArangoDB system_configs 讀取
    if CONFIG_STORE_AVAILABLE:
        try:
            config_service = get_config_store_service()
            config = config_service.get_config("chunk_processing", tenant_id=None)
            if config and config.config_data:
                config_data = config.config_data
                logger.debug("使用 ArangoDB system_configs 中的 chunk_processing 配置")
        except Exception as e:
            logger.warning(
                "failed_to_load_config_from_arangodb",
                scope="chunk_processing",
                error=str(e),
                message="從 ArangoDB 讀取配置失敗，回退到 config.json",
            )

    # 如果 ArangoDB 中沒有配置，回退到 config.json（向後兼容）
    if not config_data:
        config = get_config_section("chunk_processing", default={}) or {}
        config_data = config
        logger.debug("使用 config.json 中的 chunk_processing 配置（向後兼容）")

    return create_chunk_processor_from_config(config_data)


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
    elif file_type_lower.startswith("image/") or file_type_lower.endswith(
        (".png", ".jpg", ".jpeg", ".bmp", ".svg", ".gif", ".webp")
    ):
        # 圖片文件解析器
        try:
            from services.api.processors.parsers.image_parser import ImageParser

            return ImageParser()
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"圖片解析器未安裝或配置錯誤: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"圖片解析器初始化失敗: {str(e)}",
            )
    else:
        # 默認使用文本解析器
        return TxtParser()


async def process_file_chunking(file_id: str, file_path: str, file_type: Optional[str] = None):
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
        if file_type is None:
            file_type = "text/plain"  # 默認使用文本類型
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
