# 代碼功能說明: 文件上傳路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""文件上傳路由 - 提供文件上傳、驗證和存儲功能"""

import os
import json
from typing import List, Optional, Dict, Any
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    status,
    Depends,
    BackgroundTasks,
    Query,
)
from fastapi.responses import JSONResponse
import structlog

from api.core.response import APIResponse
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.consent_middleware import require_consent
from services.api.models.data_consent import ConsentType
from system.security.audit_decorator import audit_log
from services.api.models.audit_log import AuditAction
from fastapi import Request
from database.redis import get_redis_client
from services.api.utils.file_validator import (
    FileValidator,
    create_validator_from_config,
)
from storage.file_storage import (
    FileStorage,
    create_storage_from_config,
)
from services.api.services.file_metadata_service import FileMetadataService
from services.api.models.file_metadata import FileMetadataCreate
from system.infra.config.config import get_config_section
from services.api.services.embedding_service import get_embedding_service
from services.api.services.vector_store_service import get_vector_store_service
from services.api.services.kg_extraction_service import get_kg_extraction_service
from services.api.services.file_permission_service import get_file_permission_service
from services.api.services.file_scanner import get_file_scanner
from system.security.models import Permission

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["File Upload"])

# 全局驗證器、存儲和元數據服務實例（懶加載）
_validator: Optional[FileValidator] = None
_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None


def get_validator() -> FileValidator:
    """獲取文件驗證器實例（單例模式）"""
    global _validator
    if _validator is None:
        config = get_config_section("file_upload", default={}) or {}
        _validator = create_validator_from_config(config)
    return _validator


def get_storage() -> FileStorage:
    """獲取文件存儲實例（單例模式）"""
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}
        _storage = create_storage_from_config(config)
    return _storage


def get_metadata_service() -> FileMetadataService:
    """獲取元數據服務實例（單例模式）"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


def _extract_file_ids(response_body: dict) -> Optional[str]:
    """從響應中提取文件ID（用於審計日誌）。"""
    uploaded = response_body.get("data", {}).get("uploaded", [])
    if uploaded:
        # 返回第一個文件的ID
        return uploaded[0].get("file_id")
    return None


def _update_upload_progress(
    file_id: str,
    progress: int,
    status: str,
    message: str = "",
) -> None:
    """更新上傳進度到 Redis。

    Args:
        file_id: 文件ID
        progress: 進度百分比 (0-100)
        status: 狀態 ("uploading", "completed", "failed")
        message: 狀態消息
    """
    try:
        redis_client = get_redis_client()
        progress_data = {
            "file_id": file_id,
            "status": status,
            "progress": progress,
            "message": message,
        }
        redis_client.setex(
            f"upload:progress:{file_id}",
            3600,  # TTL: 1小時
            json.dumps(progress_data),
        )
    except Exception as e:
        logger.warning(
            "Failed to update upload progress",
            file_id=file_id,
            error=str(e),
        )


def _update_processing_status(
    file_id: str,
    chunking: Optional[Dict[str, Any]] = None,
    vectorization: Optional[Dict[str, Any]] = None,
    storage: Optional[Dict[str, Any]] = None,
    kg_extraction: Optional[Dict[str, Any]] = None,
    overall_status: Optional[str] = None,
    overall_progress: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    """更新處理狀態到 Redis。

    Args:
        file_id: 文件ID
        chunking: 分塊狀態字典
        vectorization: 向量化狀態字典
        storage: 存儲狀態字典
        kg_extraction: 知識圖譜提取狀態字典
        overall_status: 總體狀態
        overall_progress: 總體進度 (0-100)
        message: 狀態消息
    """
    try:
        redis_client = get_redis_client()

        # 嘗試讀取現有狀態
        existing_key = f"processing:status:{file_id}"
        existing_data_str = redis_client.get(existing_key)
        if existing_data_str:
            status_data = json.loads(existing_data_str)
        else:
            status_data = {
                "file_id": file_id,
                "status": "pending",
                "progress": 0,
                "chunking": {"status": "pending", "progress": 0},
                "vectorization": {"status": "pending", "progress": 0},
                "storage": {"status": "pending", "progress": 0},
                "kg_extraction": {"status": "pending", "progress": 0},
            }

        # 更新各階段狀態
        if chunking is not None:
            if "chunking" not in status_data:
                status_data["chunking"] = {}
            status_data["chunking"].update(chunking)
        if vectorization is not None:
            if "vectorization" not in status_data:
                status_data["vectorization"] = {}
            status_data["vectorization"].update(vectorization)
        if storage is not None:
            if "storage" not in status_data:
                status_data["storage"] = {}
            status_data["storage"].update(storage)
        if kg_extraction is not None:
            if "kg_extraction" not in status_data:
                status_data["kg_extraction"] = {}
            status_data["kg_extraction"].update(kg_extraction)
        if overall_status is not None:
            status_data["status"] = overall_status
        if overall_progress is not None:
            status_data["progress"] = overall_progress
        if message is not None:
            status_data["message"] = message

        redis_client.setex(
            existing_key,
            7200,  # TTL: 2小時（處理可能需要更長時間）
            json.dumps(status_data),
        )
    except Exception as e:
        logger.warning(
            "Failed to update processing status",
            file_id=file_id,
            error=str(e),
        )


async def process_file_chunking_and_vectorization(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
) -> None:
    """
    異步處理文件分塊和向量化

    Args:
        file_id: 文件ID
        file_path: 文件路徑
        file_type: 文件類型（MIME類型）
        user_id: 用戶ID
    """
    try:
        # 初始化狀態
        _update_processing_status(
            file_id=file_id,
            overall_status="processing",
            overall_progress=0,
            message="開始處理文件",
        )

        # 導入分塊處理相關模塊
        from genai.api.routers.chunk_processing import (
            get_parser,
            get_chunk_processor,
            get_storage as get_chunk_storage,
        )

        # ========== 階段1: 文件解析和分塊 (0-50%) ==========
        _update_processing_status(
            file_id=file_id,
            chunking={"status": "processing", "progress": 0, "message": "開始解析文件"},
            overall_progress=10,
        )

        # 獲取解析器
        if file_type is None:
            file_type = "text/plain"
        parser = get_parser(file_type)

        # 解析文件
        storage = get_chunk_storage()
        file_content = storage.read_file(file_id)
        if file_content is None:
            raise ValueError(f"無法讀取文件: {file_id}")

        # 檢查是否為圖片文件
        is_image_file = file_type and file_type.startswith("image/")

        # 解析文件（圖片解析器是異步的）
        if hasattr(parser, "parse_from_bytes"):
            # 檢查是否是異步方法
            import inspect

            if inspect.iscoroutinefunction(parser.parse_from_bytes):
                parse_result = await parser.parse_from_bytes(
                    file_content,
                    file_id=file_id,
                    user_id=user_id,
                    task_id=None,  # 可以從上下文獲取
                )
            else:
                parse_result = parser.parse_from_bytes(file_content)
        elif hasattr(parser, "parse"):
            parse_result = parser.parse(file_path)
        else:
            raise ValueError(f"解析器不支持此文件類型: {file_type}")

        _update_processing_status(
            file_id=file_id,
            chunking={
                "status": "processing",
                "progress": 50,
                "message": "文件解析完成，開始分塊" if not is_image_file else "圖片描述生成完成",
            },
            overall_progress=25,
        )

        # 獲取分塊處理器
        chunk_processor = get_chunk_processor()

        # 圖片文件特殊處理：描述文本作為單個 chunk，不需要分塊
        if is_image_file:
            # 圖片描述作為單個 chunk
            image_metadata = parse_result.get("metadata", {})
            chunks = [
                {
                    "text": parse_result.get("text", ""),
                    "chunk_index": 0,
                    "file_id": file_id,
                    "content_type": "image",
                    "image_path": file_path,  # 保存圖片文件路徑
                    "image_format": image_metadata.get("format"),
                    "image_width": image_metadata.get("width"),
                    "image_height": image_metadata.get("height"),
                    "vision_model": image_metadata.get("vision_model"),
                    "description_confidence": image_metadata.get(
                        "description_confidence"
                    ),
                    **image_metadata,  # 包含所有圖片元數據
                }
            ]
        else:
            # 文本文件正常分塊
            chunks = chunk_processor.process(
                text=parse_result["text"],
                file_id=file_id,
                metadata=parse_result.get("metadata", {}),
            )

        _update_processing_status(
            file_id=file_id,
            chunking={
                "status": "completed",
                "progress": 100,
                "message": "分塊處理完成",
                "chunk_count": len(chunks),
            },
            overall_progress=50,
        )

        logger.info(
            "文件分塊處理完成",
            file_id=file_id,
            chunk_count=len(chunks),
        )

        # ========== 階段2: 向量化 (50-90%) ==========
        _update_processing_status(
            file_id=file_id,
            vectorization={"status": "processing", "progress": 0, "message": "開始向量化"},
            overall_progress=50,
        )

        embedding_service = get_embedding_service()

        # 批量生成向量
        chunk_texts = [chunk.get("text", "") for chunk in chunks]
        embeddings = await embedding_service.generate_embeddings_batch(chunk_texts)

        _update_processing_status(
            file_id=file_id,
            vectorization={
                "status": "completed",
                "progress": 100,
                "message": "向量化完成",
                "vector_count": len(embeddings),
            },
            overall_progress=90,
        )

        logger.info(
            "文件向量化完成",
            file_id=file_id,
            vector_count=len(embeddings),
        )

        # ========== 階段3: 存儲到 ChromaDB (90-100%) ==========
        _update_processing_status(
            file_id=file_id,
            storage={"status": "processing", "progress": 0, "message": "開始存儲向量"},
            overall_progress=90,
        )

        vector_store_service = get_vector_store_service()

        # 為圖片文件添加圖片路徑到元數據
        if is_image_file and chunks:
            # 確保圖片路徑在元數據中
            if "image_path" not in chunks[0]:
                chunks[0]["image_path"] = file_path

        # 從文件元數據獲取 task_id（如果存在）
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(file_id)
        task_id = file_metadata.task_id if file_metadata else None

        # 將 task_id 添加到每個 chunk 的元數據中
        if task_id:
            for chunk in chunks:
                if "metadata" not in chunk:
                    chunk["metadata"] = {}
                chunk["metadata"]["task_id"] = task_id

        vector_store_service.store_vectors(
            file_id=file_id,
            chunks=chunks,
            embeddings=embeddings,
            user_id=user_id,
        )

        # 獲取存儲統計信息
        stats = vector_store_service.get_collection_stats(file_id, user_id)

        _update_processing_status(
            file_id=file_id,
            storage={
                "status": "completed",
                "progress": 100,
                "message": "向量存儲完成",
                "collection_name": stats["collection_name"],
                "vector_count": stats["vector_count"],
            },
            overall_progress=90,
        )

        logger.info(
            "向量存儲完成",
            file_id=file_id,
            chunk_count=len(chunks),
            vector_count=len(embeddings),
            collection_name=stats["collection_name"],
        )

        # ========== 階段4: 知識圖譜提取 (90-100%) ==========
        # 圖片文件跳過知識圖譜提取（圖片描述不適合提取實體和關係）
        if not is_image_file:
            # 讀取KG提取配置（從 services.kg_extraction 讀取）
            services_config = get_config_section("services", default={}) or {}
            kg_config = services_config.get("kg_extraction", {})
            # 如果配置為空，使用默認值
            if not kg_config:
                kg_config = {
                    "enabled": True,
                    "mode": "all_chunks",
                    "min_confidence": 0.5,
                    "chunk_filter": {},
                }

            kg_enabled = kg_config.get("enabled", True)

            if kg_enabled:
                try:
                    await process_kg_extraction(
                        file_id=file_id,
                        chunks=chunks,
                        user_id=user_id,
                        options=kg_config,
                    )
                except Exception as e:
                    logger.error(
                        "知識圖譜提取失敗（不影響其他處理）",
                        file_id=file_id,
                        error=str(e),
                    )
                    # KG提取失敗不影響整體處理狀態，但記錄錯誤
                    _update_processing_status(
                        file_id=file_id,
                        kg_extraction={
                            "status": "failed",
                            "progress": 0,
                            "message": f"KG提取失敗: {str(e)}",
                            "error": str(e),
                        },
                    )
        else:
            # 圖片文件：跳過知識圖譜提取
            logger.info(
                "圖片文件跳過知識圖譜提取",
                file_id=file_id,
            )

        # 如果KG提取未啟用或已完成，更新最終狀態
        # 更新最終狀態
        final_message = "文件處理完成"
        if is_image_file:
            final_message = "圖片文件處理完成（描述已生成並向量化）"

        _update_processing_status(
            file_id=file_id,
            overall_status="completed",
            overall_progress=100,
            message=final_message,
        )

        logger.info(
            "文件處理完成（分塊+向量化+存儲+KG提取）",
            file_id=file_id,
            chunk_count=len(chunks),
            vector_count=len(embeddings),
            collection_name=stats["collection_name"],
        )

    except Exception as e:
        logger.error(
            "文件處理失敗",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        _update_processing_status(
            file_id=file_id,
            overall_status="failed",
            overall_progress=0,
            message=f"處理失敗: {str(e)}",
        )


async def process_kg_extraction(
    file_id: str,
    chunks: List[Dict[str, Any]],
    user_id: str,
    options: Dict[str, Any],
) -> None:
    """
    異步處理知識圖譜提取

    Args:
        file_id: 文件ID
        chunks: 分塊列表
        user_id: 用戶ID
        options: KG提取選項
    """
    try:
        # 初始化KG提取狀態
        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "processing",
                "progress": 0,
                "message": "開始知識圖譜提取",
                "mode": options.get("mode", "all_chunks"),
            },
            overall_progress=90,
        )

        kg_service = get_kg_extraction_service()

        # 提取三元組
        triples = await kg_service.extract_triples_from_chunks(chunks, options)

        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "processing",
                "progress": 50,
                "message": "三元組提取完成，開始構建知識圖譜",
                "triples_count": len(triples),
            },
            overall_progress=95,
        )

        logger.info(
            "三元組提取完成",
            file_id=file_id,
            triples_count=len(triples),
        )

        # 構建知識圖譜
        result = await kg_service.build_kg_from_file(file_id, triples, user_id)

        # 統計實體和關係數量
        entities_count = result.get("entities_created", 0)
        relations_count = result.get("relations_created", 0)

        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "completed",
                "progress": 100,
                "message": "知識圖譜構建完成",
                "triples_count": len(triples),
                "entities_count": entities_count,
                "relations_count": relations_count,
                "mode": options.get("mode", "all_chunks"),
            },
            overall_progress=100,
        )

        logger.info(
            "知識圖譜構建完成",
            file_id=file_id,
            triples_count=len(triples),
            entities_count=entities_count,
            relations_count=relations_count,
        )

    except Exception as e:
        logger.error(
            "知識圖譜提取失敗",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "failed",
                "progress": 0,
                "message": f"KG提取失敗: {str(e)}",
                "error": str(e),
            },
        )
        raise


@router.post("/upload")
@audit_log(
    action=AuditAction.FILE_UPLOAD,
    resource_type="file",
    get_resource_id=_extract_file_ids,
)
async def upload_files(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    task_id: Optional[str] = Form(None, description="任務ID（可選，用於組織文件到工作區）"),
    current_user: User = Depends(require_consent(ConsentType.FILE_UPLOAD)),
) -> JSONResponse:
    """
    上傳文件（支持多文件上傳）

    Args:
        files: 上傳的文件列表
        task_id: 任務ID（可選，用於組織文件到工作區）
        current_user: 當前認證用戶（從 Token 獲取）

    Returns:
        上傳結果，包含文件 ID 和元數據
    """
    if not files:
        return APIResponse.error(
            message="未提供文件",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 檢查上傳權限
    permission_service = get_file_permission_service()
    permission_service.check_upload_permission(current_user)

    # 如果提供了task_id，檢查任務文件訪問權限
    if task_id:
        permission_service.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_UPLOAD.value,
        )

    validator = get_validator()
    storage = get_storage()

    results = []
    errors = []

    # 預先更新進度（開始上傳）
    # 注意：由於 FastAPI multipart 上傳是同步的，我們在開始時先更新一次進度

    for file in files:
        try:
            # 讀取文件內容
            file_content = await file.read()

            # 驗證文件
            is_valid, error_msg = validator.validate_upload_file(
                file_content, file.filename or "unknown"
            )

            if not is_valid:
                errors.append(
                    {
                        "filename": file.filename,
                        "error": error_msg,
                    }
                )
                continue

            # 更新進度：開始上傳
            # 注意：FastAPI 的 multipart 上傳是同步的，我們只能在開始和結束時更新進度
            # 實際的上傳進度由前端 XMLHttpRequest 追蹤

            # 清理文件名（移除特殊字符，防止路徑遍歷攻擊）
            sanitized_filename = os.path.basename(file.filename or "unknown")
            # 移除路徑分隔符和其他危險字符
            sanitized_filename = sanitized_filename.replace("/", "_").replace("\\", "_")
            sanitized_filename = sanitized_filename.replace("..", "_")

            # 保存文件（使用清理後的文件名）
            file_id, file_path = storage.save_file(file_content, sanitized_filename)

            # 更新進度：文件保存完成
            _update_upload_progress(file_id, 50, "uploading", "文件已保存，正在處理...")

            # 獲取文件類型
            file_type = validator.get_file_type(file.filename)

            # 創建元數據
            try:
                metadata_service = get_metadata_service()
                # 如果未提供 task_id，默認使用 "temp-workspace"（任務工作區）
                default_task_id = task_id or "temp-workspace"
                metadata_create = FileMetadataCreate(
                    file_id=file_id,
                    filename=sanitized_filename,  # 使用清理後的文件名
                    file_type=file_type or "application/octet-stream",
                    file_size=len(file_content),
                    user_id=current_user.user_id,
                    task_id=default_task_id,
                )
                metadata_service.create(metadata_create)
            except Exception as e:
                logger.warning(
                    "元數據創建失敗（文件已上傳）",
                    file_id=file_id,
                    error=str(e),
                )

            # 構建結果
            result = {
                "file_id": file_id,
                "filename": sanitized_filename,  # 使用清理後的文件名
                "file_type": file_type,
                "file_size": len(file_content),
                "file_path": file_path,
            }

            results.append(result)

            # 更新進度：上傳完成
            _update_upload_progress(file_id, 100, "completed", "文件上傳成功")

            logger.info(
                "文件上傳成功，觸發異步處理",
                file_id=file_id,
                filename=file.filename,
                file_size=len(file_content),
            )

            # 觸發異步處理任務（分塊+向量化）
            background_tasks.add_task(
                process_file_chunking_and_vectorization,
                file_id=file_id,
                file_path=file_path,
                file_type=file_type,
                user_id=current_user.user_id,
            )

        except Exception as e:
            error_message = f"上傳失敗: {str(e)}"
            logger.error(
                "文件上傳失敗",
                filename=file.filename,
                error=str(e),
            )

            # 如果有 file_id，更新進度為失敗
            # 注意：如果保存失敗，可能沒有 file_id
            try:
                # 嘗試從錯誤中提取 file_id（如果有的話）
                # 這裡我們不更新進度，因為可能還沒有 file_id
                pass
            except Exception:
                pass

            errors.append(
                {
                    "filename": file.filename,
                    "error": error_message,
                }
            )

    # 構建響應
    response_data = {
        "uploaded": results,
        "errors": errors,
        "total": len(files),
        "success_count": len(results),
        "error_count": len(errors),
    }

    if errors and not results:
        # 所有文件都失敗
        return APIResponse.error(
            message="所有文件上傳失敗",
            details=response_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    elif errors:
        # 部分文件失敗
        return APIResponse.success(
            data=response_data,
            message=f"部分文件上傳成功（{len(results)}/{len(files)}）",
            status_code=status.HTTP_207_MULTI_STATUS,
        )
    else:
        # 所有文件成功
        return APIResponse.success(
            data=response_data,
            message=f"所有文件上傳成功（{len(results)} 個文件）",
        )


@router.get("/{file_id}")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def get_file_info(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取文件信息

    Args:
        file_id: 文件 ID

    Returns:
        文件信息
    """
    storage = get_storage()

    if not storage.file_exists(file_id):
        return APIResponse.error(
            message="文件不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    file_path = storage.get_file_path(file_id)
    if file_path:
        file_size = os.path.getsize(file_path)
        return APIResponse.success(
            data={
                "file_id": file_id,
                "file_path": file_path,
                "file_size": file_size,
            }
        )

    return APIResponse.error(
        message="無法獲取文件信息",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@router.get("/upload/{file_id}/progress")
async def get_upload_progress(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查詢文件上傳進度。

    Args:
        file_id: 文件ID
        current_user: 當前認證用戶

    Returns:
        上傳進度信息
    """
    try:
        redis_client = get_redis_client()
        progress_key = f"upload:progress:{file_id}"
        progress_data_str = redis_client.get(progress_key)

        if not progress_data_str:
            return APIResponse.error(
                message="進度記錄不存在或已過期",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        progress_data = json.loads(progress_data_str)

        return APIResponse.success(
            data=progress_data,
            message="進度查詢成功",
        )
    except Exception as e:
        logger.error(
            "Failed to get upload progress",
            file_id=file_id,
            error=str(e),
        )
        return APIResponse.error(
            message=f"查詢進度失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/processing-status")
async def get_processing_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查詢文件處理狀態（分塊、向量化等）。

    Args:
        file_id: 文件ID
        current_user: 當前認證用戶

    Returns:
        處理狀態信息
    """
    try:
        # 檢查文件是否存在
        storage = get_storage()
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從 Redis 讀取處理狀態
        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)

        if status_data_str:
            status_data = json.loads(status_data_str)
            return APIResponse.success(
                data=status_data,
                message="處理狀態查詢成功",
            )
        else:
            # 如果沒有處理狀態記錄，檢查是否已上傳
            # 可能文件剛上傳，處理還未開始
            upload_progress_key = f"upload:progress:{file_id}"
            upload_progress_str = redis_client.get(upload_progress_key)

            if upload_progress_str:
                upload_progress = json.loads(upload_progress_str)
                if upload_progress.get("status") == "completed":
                    # 文件已上傳完成，但處理尚未開始或已過期
                    return APIResponse.success(
                        data={
                            "file_id": file_id,
                            "status": "pending",
                            "progress": 0,
                            "chunking": {"status": "pending", "progress": 0},
                            "vectorization": {"status": "pending", "progress": 0},
                            "storage": {"status": "pending", "progress": 0},
                            "kg_extraction": {"status": "pending", "progress": 0},
                            "message": "文件已上傳，等待處理",
                        },
                        message="處理狀態查詢成功",
                    )

            # 沒有找到任何狀態記錄
            return APIResponse.success(
                data={
                    "file_id": file_id,
                    "status": "pending",
                    "progress": 0,
                    "chunking": {"status": "pending", "progress": 0},
                    "vectorization": {"status": "pending", "progress": 0},
                    "storage": {"status": "pending", "progress": 0},
                    "kg_extraction": {"status": "pending", "progress": 0},
                    "message": "處理狀態未找到",
                },
                message="處理狀態查詢成功",
            )

    except Exception as e:
        logger.error(
            "Failed to get processing status",
            file_id=file_id,
            error=str(e),
        )
        return APIResponse.error(
            message=f"查詢處理狀態失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/kg/stats")
async def get_kg_stats(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取文件相關的知識圖譜統計信息。

    Args:
        file_id: 文件ID
        current_user: 當前認證用戶

    Returns:
        KG統計信息
    """
    try:
        # 檢查文件是否存在
        storage = get_storage()
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從處理狀態中獲取KG統計
        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)

        if status_data_str:
            status_data = json.loads(status_data_str)
            kg_extraction = status_data.get("kg_extraction", {})

            if kg_extraction.get("status") == "completed":
                return APIResponse.success(
                    data={
                        "file_id": file_id,
                        "triples_count": kg_extraction.get("triples_count", 0),
                        "entities_count": kg_extraction.get("entities_count", 0),
                        "relations_count": kg_extraction.get("relations_count", 0),
                        "mode": kg_extraction.get("mode", "all_chunks"),
                    },
                    message="KG統計信息查詢成功",
                )

        # 如果沒有處理狀態，嘗試從ArangoDB查詢（需要實現文件ID關聯）
        # 暫時返回未處理狀態
        return APIResponse.success(
            data={
                "file_id": file_id,
                "triples_count": 0,
                "entities_count": 0,
                "relations_count": 0,
                "status": "not_processed",
            },
            message="KG統計信息查詢成功（未處理）",
        )

    except Exception as e:
        logger.error(
            "Failed to get KG stats",
            file_id=file_id,
            error=str(e),
        )
        return APIResponse.error(
            message=f"查詢KG統計信息失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/kg/triples")
async def get_kg_triples(
    file_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取文件提取的三元組列表。

    Args:
        file_id: 文件ID
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        三元組列表
    """
    try:
        # 檢查文件是否存在
        storage = get_storage()
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # TODO: 實現從ArangoDB查詢文件相關的三元組
        # 目前需要實現文件ID與三元組的關聯機制
        # 暫時返回空列表
        return APIResponse.success(
            data={
                "file_id": file_id,
                "triples": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
            },
            message="三元組查詢成功（功能待實現）",
        )

    except Exception as e:
        logger.error(
            "Failed to get KG triples",
            file_id=file_id,
            error=str(e),
        )
        return APIResponse.error(
            message=f"查詢三元組失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{file_id}")
@audit_log(
    action=AuditAction.FILE_DELETE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def delete_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除文件（級聯刪除：文件、向量、知識圖譜）

    Args:
        file_id: 文件 ID
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        storage = get_storage()

        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 1. 刪除ChromaDB中的向量
        try:
            vector_store_service = get_vector_store_service()
            vector_store_service.delete_vectors_by_file_id(
                file_id=file_id, user_id=current_user.user_id
            )
            logger.info("已刪除文件關聯的向量", file_id=file_id)
        except Exception as e:
            logger.warning("刪除向量失敗（繼續刪除文件）", file_id=file_id, error=str(e))

        # 2. 刪除ArangoDB中的知識圖譜數據
        # 注意：KG數據可能分散在多個集合中，這裡暫時只記錄日誌
        # 完整的KG刪除功能可以在後續實現
        logger.info("知識圖譜數據刪除待實現", file_id=file_id)

        # 3. 刪除文件元數據
        try:
            metadata_service = get_metadata_service()
            metadata_service.delete(file_id)
            logger.info("已刪除文件元數據", file_id=file_id)
        except Exception as e:
            logger.warning("刪除文件元數據失敗（繼續刪除文件）", file_id=file_id, error=str(e))

        # 4. 刪除實際文件
        success = storage.delete_file(file_id)

        if success:
            # 5. 刪除Redis中的處理狀態
            try:
                redis_client = get_redis_client()
                redis_client.delete(f"upload:progress:{file_id}")
                redis_client.delete(f"processing:status:{file_id}")
                logger.info("已刪除Redis中的處理狀態", file_id=file_id)
            except Exception as e:
                logger.warning("刪除Redis狀態失敗", file_id=file_id, error=str(e))

            return APIResponse.success(
                data={"file_id": file_id},
                message="文件及相關數據刪除成功",
            )
        else:
            return APIResponse.error(
                message="文件刪除失敗",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    except Exception as e:
        logger.error("刪除文件時發生錯誤", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"刪除文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
