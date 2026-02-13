# 代碼功能說明: 文件上傳路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27 23:00 UTC+8

"""文件上傳路由 - 提供文件上傳、驗證和存儲功能"""

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from database.redis import get_redis_client
from database.rq.queue import FILE_PROCESSING_QUEUE, get_task_queue
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.models.audit_log import AuditAction
from services.api.models.data_consent import ConsentType, DataConsentCreate
from services.api.models.file_metadata import FileMetadataCreate, FileMetadataUpdate
from services.api.models.user_task import UserTaskCreate
from services.api.services.embedding_service import get_embedding_service
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import get_file_permission_service
from services.api.services.kg_extraction_service import get_kg_extraction_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service
from services.api.services.task_workspace_service import get_task_workspace_service
from services.api.services.user_task_service import get_user_task_service
from services.api.utils.file_validator import FileValidator, create_validator_from_config
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section

# 向後兼容：如果 ConfigStoreService 不可用，使用舊的配置方式
try:
    from services.api.services.config_store_service import ConfigStoreService

    _file_config_service: Optional[ConfigStoreService] = None

    def get_file_config_service() -> ConfigStoreService:
        """獲取配置存儲服務實例（單例模式）"""
        global _file_config_service
        if _file_config_service is None:
            _file_config_service = ConfigStoreService()
        return _file_config_service

    FILE_CONFIG_STORE_AVAILABLE = True
except ImportError:
    FILE_CONFIG_STORE_AVAILABLE = False
    # logger 尚未定義，使用 print 或跳過日誌
from system.security.audit_decorator import audit_log
from system.security.consent_middleware import require_consent
from system.security.dependencies import get_current_user
from system.security.models import Permission, User
from workers.tasks import process_file_chunking_and_vectorization_task

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["File Upload"])

# 全局驗證器、存儲和元數據服務實例（懶加載）
_validator: Optional[FileValidator] = None
_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None


class BlankMarkdownCreateRequest(BaseModel):
    """建立空白 Markdown 檔案（不走 upload multipart）。"""

    task_id: str = Field(..., description="任務ID（必填）")
    folder_id: Optional[str] = Field(
        None, description="資料夾ID（可選；None 表示任務工作區根目錄）"
    )
    filename: str = Field(..., description="檔名（會自動補 .md）")


def get_worker_job_timeout() -> int:
    """獲取 RQ Worker 任務超時時間（秒），優先從 ArangoDB system_configs 讀取"""
    # 優先從 ArangoDB system_configs 讀取
    if FILE_CONFIG_STORE_AVAILABLE:
        try:
            config_service = get_file_config_service()
            config = config_service.get_config("worker", tenant_id=None)
            if config and config.config_data:
                timeout = config.config_data.get("job_timeout", 3600)
                logger.debug(f"使用 ArangoDB system_configs 中的 worker.job_timeout: {timeout}")
                return int(timeout)
        except Exception as e:
            logger.warning(
                "failed_to_load_worker_config_from_arangodb",
                error=str(e),
                message="從 ArangoDB 讀取 worker 配置失敗，使用默認值 3600 秒（生產環境）",
            )

    # 默認值：3600 秒（1小時）- 調整為適合知識庫上傳的長時間處理
    return 3600


def get_validator() -> FileValidator:
    """獲取文件驗證器實例（單例模式，優先從 ArangoDB system_configs 讀取）"""
    global _validator
    if _validator is None:
        config_data: Dict[str, Any] = {}

        # 優先從 ArangoDB system_configs 讀取
        if FILE_CONFIG_STORE_AVAILABLE:
            try:
                config_service = get_file_config_service()
                config = config_service.get_config("file_processing", tenant_id=None)
                if config and config.config_data:
                    config_data = config.config_data
                    logger.debug("使用 ArangoDB system_configs 中的 file_processing 配置")
            except Exception as e:
                logger.warning(
                    "failed_to_load_config_from_arangodb",
                    scope="file_processing",
                    error=str(e),
                    message="從 ArangoDB 讀取配置失敗，回退到 config.json",
                )

        # 如果 ArangoDB 中沒有配置，回退到 config.json（向後兼容）
        if not config_data:
            config = get_config_section("file_upload", default={}) or {}
            config_data = config
            logger.debug("使用 config.json 中的 file_upload 配置（向後兼容）")

        _validator = create_validator_from_config(config_data)
    return _validator


def get_storage() -> FileStorage:
    """獲取文件存儲實例（單例模式）"""
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}

        # 临时修复：如果配置读取失败（空字典），或者 storage_backend 未设置，强制使用本地存储
        # 这样可以避免因为配置系统问题导致无法使用本地存储
        if not config or not config.get("storage_backend"):
            from storage.file_storage import LocalFileStorage

            storage_path = config.get("storage_path", "./data/datasets/files")
            print(f"⚠️  配置读取失败或未设置 storage_backend，临时使用本地存储: {storage_path}")
            _storage = LocalFileStorage(storage_path=storage_path, enable_encryption=False)
        else:
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


@router.post("/blank-md")
@audit_log(
    action=AuditAction.FILE_CREATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def create_blank_markdown(
    request: Request,
    body: BlankMarkdownCreateRequest,
    current_user: User = Depends(require_consent(ConsentType.FILE_UPLOAD)),
) -> JSONResponse:
    """
    建立空白 Markdown 檔案（.md），不走 multipart upload 與後續向量化流程。
    """
    permission_service = get_file_permission_service()
    permission_service.check_upload_permission(current_user)

    task_id = (body.task_id or "").strip()
    if not task_id:
        return APIResponse.error(
            message="任務ID不能為空，文件必須關聯到任務工作區",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 若 task 不存在：比照 /files/upload 行為，自動建立任務與工作區
    task_service = get_user_task_service()
    existing_task = task_service.get(user_id=current_user.user_id, task_id=task_id)
    if existing_task is None:
        # 修改時間：2026-01-21 - 後台/系統任務：使用 task_id 作為任務標題
        # 對於 blank-md 端點，task_id 是必填的，因此直接使用 task_id 作為標題
        task_title = task_id
        try:
            task_service.create(
                UserTaskCreate(
                    task_id=task_id,
                    user_id=current_user.user_id,
                    title=task_title,
                    status="pending",
                    messages=[],
                    fileTree=[],
                    label_color=None,  # type: ignore[call-arg]  # label_color 有默認值
                    dueDate=None,  # type: ignore[call-arg]  # dueDate 有默認值
                )
            )
            logger.info(
                "blank_md_task_auto_created",
                task_id=task_id,
                user_id=current_user.user_id,
                task_title=task_title,
            )
        except Exception as exc:
            logger.error(
                "blank_md_task_auto_create_failed",
                task_id=task_id,
                user_id=current_user.user_id,
                error=str(exc),
                exc_info=True,
            )
            return APIResponse.error(
                message=f"創建任務失敗: {str(exc)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    permission_service.check_task_file_access(
        user=current_user,
        task_id=task_id,
        required_permission=Permission.FILE_UPLOAD.value,
    )

    filename = (body.filename or "").strip()
    if not filename:
        return APIResponse.error(
            message="檔名不能為空",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not filename.lower().endswith(".md"):
        filename = f"{os.path.splitext(filename)[0]}.md"

    # 內容至少 1 byte，避免某些系統對 0 byte 的處理差異
    content = b"\n"

    storage = get_storage()
    file_id, file_path = storage.save_file(
        file_content=content,
        filename=filename,
        task_id=task_id,
    )

    metadata_service = get_metadata_service()
    metadata_service.create(
        FileMetadataCreate(
            file_id=file_id,
            filename=filename,
            file_type="text/markdown",
            chunk_count=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
            vector_count=None,  # type: ignore[call-arg]
            kg_status=None,  # type: ignore[call-arg]
            file_size=len(content),
            user_id=current_user.user_id,
            task_id=task_id,
            folder_id=body.folder_id,
            storage_path=file_path,
            tags=["blank", "markdown"],
            description="Blank markdown file created from FileTree",
            status="uploaded",
            processing_status=None,
        )
    )

    logger.info(
        "blank_markdown_created",
        file_id=file_id,
        filename=filename,
        task_id=task_id,
        folder_id=body.folder_id,
        user_id=current_user.user_id,
        request_path=request.url.path,
    )

    return APIResponse.success(
        data={
            "file_id": file_id,
            "filename": filename,
            "task_id": task_id,
            "folder_id": body.folder_id,
        },
        message="Blank markdown created",
    )


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
    dual_track: Optional[Dict[str, Any]] = None,
    overall_status: Optional[str] = None,
    overall_progress: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    """更新處理狀態到 Redis 和 ArangoDB（雙寫模式，確保數據一致性）。

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

        # 嘗試讀取現有狀態（從 Redis）
        existing_key = f"processing:status:{file_id}"
        existing_data_str = redis_client.get(existing_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]
        if existing_data_str:
            status_data = json.loads(existing_data_str)  # type: ignore[arg-type]  # existing_data_str 已檢查不為 None，且 decode_responses=True 返回 str
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
        if dual_track is not None:
            if "dual_track" not in status_data:
                status_data["dual_track"] = {}
            status_data["dual_track"].update(dual_track)
        if overall_status is not None:
            status_data["status"] = overall_status
        if overall_progress is not None:
            status_data["progress"] = overall_progress
        if message is not None:
            status_data["message"] = message

        # 1. 更新 Redis（API 端點目前從這裡讀取，保持向後兼容）
        redis_client.setex(
            existing_key,
            7200,  # TTL: 2小時（處理可能需要更長時間）
            json.dumps(status_data),
        )

        # 2. 同時更新 ArangoDB（用於持久化和審計）
        try:
            from services.api.models.upload_status import (
                ProcessingStatusCreate,
                ProcessingStatusUpdate,
            )
            from services.api.services.upload_status_service import get_upload_status_service

            upload_status_service = get_upload_status_service()

            # 檢查是否已存在記錄
            existing_status = upload_status_service.get_processing_status(file_id)
            if existing_status:
                # 更新現有記錄
                update = ProcessingStatusUpdate(
                    overall_status=status_data.get("status"),
                    overall_progress=status_data.get("progress"),
                    message=status_data.get("message"),
                    chunking=status_data.get("chunking"),
                    vectorization=status_data.get("vectorization"),
                    storage=status_data.get("storage"),
                    kg_extraction=status_data.get("kg_extraction"),
                    dual_track=status_data.get("dual_track"),
                )
                upload_status_service.update_processing_status(file_id, update)
            else:
                # 創建新記錄
                create = ProcessingStatusCreate(
                    file_id=file_id,
                    overall_status=status_data.get("status", "pending"),
                    overall_progress=status_data.get("progress", 0),
                    message=status_data.get("message"),
                    chunking=status_data.get("chunking"),
                    vectorization=status_data.get("vectorization"),
                    storage=status_data.get("storage"),
                    kg_extraction=status_data.get("kg_extraction"),
                    dual_track=status_data.get("dual_track"),
                )
                upload_status_service.create_processing_status(create)

            logger.debug("Processing status updated in ArangoDB", file_id=file_id)
        except Exception as arango_error:
            # ArangoDB 更新失敗不應影響 Redis 更新，記錄警告即可
            logger.warning(
                "Failed to update processing status in ArangoDB (Redis update succeeded)",
                file_id=file_id,
                error=str(arango_error),
            )

        # 3. 同步更新 file_metadata.status（當處理完成時）
        if overall_status in ("completed", "failed", "partial_completed"):
            try:
                from services.api.models.file_metadata import FileMetadataUpdate
                from services.api.services.file_metadata_service import get_metadata_service

                metadata_service = get_metadata_service()
                metadata_service.update(
                    file_id,
                    FileMetadataUpdate(
                        status=overall_status,
                        chunk_count=status_data.get("chunking", {}).get("chunk_count"),
                        vector_count=status_data.get("vectorization", {}).get("vector_count"),
                        kg_status=status_data.get("kg_extraction", {}).get("status"),
                    ),
                )
                logger.debug(
                    "file_metadata.status updated",
                    file_id=file_id,
                    status=overall_status,
                )
            except Exception as metadata_error:
                logger.error(
                    "Failed to update file_metadata status",
                    file_id=file_id,
                    error=str(metadata_error),
                )

    except Exception as e:
        logger.warning(
            "Failed to update processing status",
            file_id=file_id,
            error=str(e),
        )


async def _generate_file_summary_for_metadata(
    file_id: str,
    file_name: str,
    full_text: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    生成文件摘要（符合 Prompt A 語意摘要員規格）

    為整份文件生成一個強大的「全局錨點」，防止後續切割後斷章取義。

    Args:
        file_id: 文件 ID
        file_name: 文件名
        full_text: 完整文件文本
        user_id: 用戶 ID

    Returns:
        結構化摘要字典，格式：
        {
            "theme": "核心主題",
            "structure_outline": [
                {"chapter": "章節名稱", "core_logic": "核心邏輯"}
            ],
            "key_terms": ["術語1", "術語2", ...],
            "target_audience": "技術員/投資人/一般用戶"
        }
        如果生成失敗，返回 None
    """
    import re

    from llm.moe.moe_manager import LLMMoEManager

    try:
        max_text_length = 50000
        text_for_summary = full_text[:max_text_length]
        if len(full_text) > max_text_length:
            text_for_summary += f"\n\n[文檔被截斷，總長度: {len(full_text)} 字符]"

        prompt = f"""你現在是一名專業的文件架構分析師。請閱讀這份文件，並完成以下任務：

1. **主題定義**：用一句話概括這份文件的核心主題（例如：國琿機械熱解爐操作手冊）
2. **結構大綱**：列出文件主要章節與對應的核心邏輯
3. **關鍵術語**：提取 5-10 個貫穿全文的核心技術術語
4. **目標受眾**：判斷此文件是給技術員、投資人還是一般用戶看的

文件內容（前 {len(text_for_summary)} 字符）：
{text_for_summary}

請以 JSON 格式返回：
{{
    "theme": "核心主題",
    "structure_outline": [
        {{"chapter": "章節名稱", "core_logic": "核心邏輯"}}
    ],
    "key_terms": ["術語1", "術語2", ...],
    "target_audience": "技術員/投資人/一般用戶"
}}"""

        moe = LLMMoEManager()
        result = await moe.generate(
            prompt,
            scene="semantic_understanding",
            temperature=0.3,
            max_tokens=1000,
            user_id=user_id,
            file_id=file_id,
        )

        summary_text = result.get("text") or result.get("content", "")

        json_match = re.search(r"\{[\s\S]*\}", summary_text)
        if json_match:
            summary_json = json.loads(json_match.group(0))
            logger.info(
                f"文件摘要生成成功: theme={summary_json.get('theme', 'N/A')}",
                file_id=file_id,
                key_terms_count=len(summary_json.get("key_terms", [])),
            )
            return summary_json

        logger.warning(
            "文件摘要 JSON 解析失敗，無法提取結構化摘要",
            file_id=file_id,
            summary_preview=summary_text[:200],
        )
        return None

    except json.JSONDecodeError as e:
        logger.warning(
            "文件摘要 JSON 格式錯誤",
            file_id=file_id,
            error=str(e),
        )
        return None
    except Exception as e:
        logger.error(
            "生成文件摘要失敗",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def _encode_knowledge_asset_async(
    file_id: str,
    filename: str,
    file_content_preview: Optional[str],
    file_type: Optional[str],
    user_id: str,
    task_id: Optional[str],
    vector_refs: Optional[List[str]] = None,
    graph_refs: Optional[Dict[str, Any]] = None,
) -> None:
    """異步執行知識資產編碼並寫入 file_metadata（規格 13.6.2）。編碼失敗不影響上傳。"""
    try:
        from services.api.models.file_metadata import FileMetadataUpdate
        from services.api.services.file_metadata_service import get_metadata_service
        from services.api.services.knowledge_asset_encoding_service import (
            KnowledgeAssetEncodingService,
        )

        enc_svc = KnowledgeAssetEncodingService()
        enc = await enc_svc.encode_file(
            file_id=file_id,
            filename=filename,
            file_content_preview=file_content_preview,
            file_metadata={"file_type": file_type, "user_id": user_id, "task_id": task_id},
        )
        meta = get_metadata_service()
        update_kw: Dict[str, Any] = {
            "knw_code": enc["knw_code"],
            "ka_id": enc["ka_id"],
            "domain": enc["domain"],
            "major": enc.get("major"),
            "lifecycle_state": enc["lifecycle_state"],
            "version": enc["version"],
        }
        if vector_refs is not None:
            update_kw["vector_refs"] = vector_refs
        if graph_refs is not None:
            update_kw["graph_refs"] = graph_refs
        meta.update(file_id, FileMetadataUpdate(**update_kw))
        logger.info(f"知識資產編碼完成: file_id={file_id}, knw_code={enc['knw_code']}")
    except Exception as e:
        logger.warning(
            f"知識資產編碼失敗，使用默認值不影響上傳: file_id={file_id}, error={e}",
            exc_info=True,
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
    # 時間記錄字典
    timing_records: Dict[str, Any] = {
        "total": {"start": time.time(), "end": None, "duration_seconds": None},
        "pdf_parsing": {"start": None, "end": None, "duration_seconds": None},
        "chunking": {
            "start": None,
            "end": None,
            "duration_seconds": None,
            "chunk_count": None,
        },
        "vectorization": {
            "start": None,
            "end": None,
            "duration_seconds": None,
            "vector_count": None,
            "avg_per_vector_seconds": None,
        },
        "storage": {"start": None, "end": None, "duration_seconds": None},
    }

    try:
        # 初始化狀態
        _update_processing_status(
            file_id=file_id,
            overall_status="processing",
            overall_progress=0,
            message="開始處理文件",
        )

        # 導入分塊處理相關模塊
        from genai.api.routers.chunk_processing import get_chunk_processor, get_parser
        from genai.api.routers.chunk_processing import get_storage as get_chunk_storage

        # ========== 階段1: 文件解析和分塊 (0-50%) ==========
        _update_processing_status(
            file_id=file_id,
            chunking={"status": "processing", "progress": 0, "message": "開始解析文件"},
            overall_progress=10,
        )

        # 記錄 PDF 解析開始時間
        timing_records["pdf_parsing"]["start"] = time.time()

        # 獲取解析器
        if file_type is None:
            file_type = "text/plain"
        parser = get_parser(file_type)

        # 解析文件
        storage = get_chunk_storage()
        # 修改時間：2025-12-12 - 從元數據取得 task_id / storage_path，避免在任務工作區存儲時讀不到文件
        task_id_from_metadata: Optional[str] = None
        metadata_storage_path: Optional[str] = None
        try:
            metadata_service = get_metadata_service()
            file_metadata_obj = metadata_service.get(file_id)
            if file_metadata_obj:
                task_id_from_metadata = getattr(file_metadata_obj, "task_id", None)
                metadata_storage_path = getattr(file_metadata_obj, "storage_path", None)
        except Exception as e:
            logger.warning(
                "Failed to get file metadata for reading content",
                file_id=file_id,
                error=str(e),
            )

        # LocalFileStorage.read_file 支持 (task_id, metadata_storage_path)
        try:
            file_content = storage.read_file(  # type: ignore[call-arg]
                file_id,
                task_id=task_id_from_metadata,
                metadata_storage_path=metadata_storage_path,
            )
        except TypeError:
            # 向後兼容：如果 storage 不支持額外參數
            file_content = storage.read_file(file_id)

        # 最後保底：直接用 file_path 讀取（避免 metadata/路徑異常）
        if file_content is None and file_path:
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()
            except Exception:
                file_content = None
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
                "message": ("文件解析完成，開始分塊" if not is_image_file else "圖片描述生成完成"),
            },
            overall_progress=25,
        )

        # ========== 生成文件摘要（用於後續 Ontology 選擇） ==========
        full_text = parse_result.get("text", "")
        if full_text and len(full_text) > 500:  # 只對足夠長的文件生成摘要
            try:
                # 獲取文件名
                metadata_service = get_metadata_service()
                file_metadata_obj = metadata_service.get(file_id)
                file_name = file_metadata_obj.filename if file_metadata_obj else "unknown"

                # 為摘要生成添加超時保護（最多30秒）
                import asyncio

                try:
                    file_summary = await asyncio.wait_for(
                        _generate_file_summary_for_metadata(
                            file_id=file_id,
                            file_name=file_name,
                            full_text=full_text,
                            user_id=user_id,
                        ),
                        timeout=30.0,  # 30秒超時
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "文件摘要生成超時（30秒），跳過摘要生成",
                        file_id=file_id,
                    )
                    file_summary = None

                # 將摘要存儲到 custom_metadata
                if file_summary:
                    # 獲取現有的 custom_metadata（如果存在）
                    existing_metadata = (
                        file_metadata_obj.custom_metadata if file_metadata_obj else {}
                    )
                    existing_metadata = existing_metadata.copy() if existing_metadata else {}

                    # 更新 custom_metadata
                    existing_metadata.update(
                        {
                            "file_summary": file_summary,
                            "summary_generated_at": datetime.utcnow().isoformat(),
                        }
                    )

                    metadata_service.update(
                        file_id,
                        FileMetadataUpdate(
                            custom_metadata=existing_metadata,
                        ),
                    )
                    logger.info(
                        "文件摘要已生成並保存",
                        file_id=file_id,
                        summary_theme=file_summary.get("theme", "N/A"),
                        key_terms_count=len(file_summary.get("key_terms", [])),
                    )
            except Exception as e:
                logger.warning(
                    "生成文件摘要失敗，繼續處理",
                    file_id=file_id,
                    error=str(e),
                )
        # ========== 摘要生成結束 ==========

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
                    "description_confidence": image_metadata.get("description_confidence"),
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

        # ========== 階段2: 向量化（獨立錯誤處理）(50-90%) ==========
        vectorization_success = False
        stats = None
        try:
            # 記錄向量化開始時間
            timing_records["vectorization"]["start"] = time.time()

            _update_processing_status(
                file_id=file_id,
                vectorization={
                    "status": "processing",
                    "progress": 0,
                    "message": "開始向量化",
                },
                overall_progress=50,
            )

            embedding_service = get_embedding_service()

            # 批量生成向量（帶進度回調）
            chunk_texts = [chunk.get("text", "") for chunk in chunks]

            # 定義進度回調函數
            def update_vectorization_progress(processed: int, total: int) -> None:
                """更新向量化進度"""
                progress = int((processed / total) * 100) if total > 0 else 0
                _update_processing_status(
                    file_id=file_id,
                    vectorization={
                        "status": "processing",
                        "progress": progress,
                        "message": f"向量化進行中: {processed}/{total}",
                    },
                    overall_progress=50 + int((processed / total) * 40),  # 50-90%
                )

            embeddings = await embedding_service.generate_embeddings_batch(
                chunk_texts, progress_callback=update_vectorization_progress
            )

            # 記錄向量化結束時間
            timing_records["vectorization"]["end"] = time.time()
            timing_records["vectorization"]["duration_seconds"] = (
                timing_records["vectorization"]["end"] - timing_records["vectorization"]["start"]
            )
            timing_records["vectorization"]["vector_count"] = len(embeddings)
            if len(embeddings) > 0:
                timing_records["vectorization"]["avg_per_vector_seconds"] = timing_records[
                    "vectorization"
                ]["duration_seconds"] / len(embeddings)

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
                timing=timing_records["vectorization"],
            )

            # ========== 階段3: 存儲到 Qdrant (90-100%) ==========
            # 記錄存儲開始時間
            timing_records["storage"]["start"] = time.time()

            _update_processing_status(
                file_id=file_id,
                storage={"status": "processing", "progress": 0, "message": "開始存儲向量"},
                overall_progress=90,
            )

            vector_store_service = get_qdrant_vector_store_service()

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

            # 記錄存儲結束時間
            timing_records["storage"]["end"] = time.time()
            timing_records["storage"]["duration_seconds"] = (
                timing_records["storage"]["end"] - timing_records["storage"]["start"]
            )

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
                timing=timing_records["storage"],
            )
            vectorization_success = True
        except Exception as e:
            logger.error(
                "向量化失敗（不影響知識圖譜提取）",
                file_id=file_id,
                error=str(e),
                exc_info=True,
            )
            _update_processing_status(
                file_id=file_id,
                vectorization={
                    "status": "failed",
                    "progress": 0,
                    "message": f"向量化失敗: {str(e)}",
                    "error": str(e),
                },
            )
            # ⚠️ 不拋出異常，繼續執行知識圖譜提取

        # ========== 階段4: 知識圖譜提取（獨立錯誤處理）(90-100%) ==========
        kg_extraction_success = False
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
                    # 獲取文件元數據用於 Ontology 選擇
                    metadata_service = get_metadata_service()
                    file_metadata_obj = metadata_service.get(file_id)
                    file_metadata_dict = None
                    if file_metadata_obj:
                        file_metadata_dict = {
                            "file_name": file_metadata_obj.filename,
                            "file_type": file_metadata_obj.file_type,
                            "file_size": file_metadata_obj.file_size,
                        }

                    # 將文件信息添加到 options 中
                    kg_config_with_metadata = {
                        **kg_config,
                        "file_name": (
                            file_metadata_obj.filename
                            if (file_metadata_obj and hasattr(file_metadata_obj, "filename"))
                            else None
                        ),
                        "file_metadata": file_metadata_dict,
                    }

                    await process_kg_extraction(
                        file_id=file_id,
                        chunks=chunks,  # ✅ 使用分塊結果，不依賴向量化
                        user_id=user_id,
                        options=kg_config_with_metadata,
                    )
                    # 若 KG 提取因 time budget 提早結束，依最新需求自動續跑（加鎖避免重複 enqueue）
                    try:
                        # 讀取剛寫入的 processing status 取得 remaining_chunks
                        redis_client = get_redis_client()
                        status_key = f"processing:status:{file_id}"
                        status_raw = redis_client.get(status_key)
                        if status_raw:
                            status_data = json.loads(status_raw)
                        else:
                            status_data = {}
                        remaining_chunks = (status_data.get("kg_extraction") or {}).get(
                            "remaining_chunks"
                        ) or []
                        if remaining_chunks:
                            from database.rq.queue import KG_EXTRACTION_QUEUE, get_task_queue
                            from workers.tasks import process_kg_extraction_only_task

                            queue = get_task_queue(KG_EXTRACTION_QUEUE)
                            lock_key = f"kg:continue_lock:{file_id}"
                            # 120 秒內只允許 enqueue 一次續跑
                            got_lock = bool(redis_client.set(lock_key, "1", nx=True, ex=120))
                            next_job_id: Optional[str] = None
                            if got_lock:
                                job_timeout = get_worker_job_timeout()
                                next_job = queue.enqueue(
                                    process_kg_extraction_only_task,
                                    file_id=file_id,
                                    file_path=file_path,
                                    file_type=file_type,
                                    user_id=user_id,
                                    force_rechunk=False,
                                    job_timeout=job_timeout,
                                )
                                next_job_id = next_job.id

                            _update_processing_status(
                                file_id=file_id,
                                kg_extraction={
                                    "status": "processing",
                                    "message": f"續跑已排程（剩餘 {len(remaining_chunks)} 個分塊）",
                                    "next_job_id": next_job_id,
                                    "remaining_chunks": remaining_chunks,
                                },
                            )
                            logger.info(
                                "KG extraction continuation enqueued (from upload pipeline)",
                                file_id=file_id,
                                next_job_id=next_job_id,
                                remaining_chunks=len(remaining_chunks),
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to enqueue KG extraction continuation from upload pipeline",
                            file_id=file_id,
                            error=str(e),
                        )
                    # 檢查是否有剩餘分塊需要續跑
                    redis_client = get_redis_client()
                    status_key = f"processing:status:{file_id}"
                    status_raw = redis_client.get(status_key)
                    status_data = json.loads(status_raw) if status_raw else {}
                    remaining_chunks = (status_data.get("kg_extraction") or {}).get(
                        "remaining_chunks"
                    ) or []
                    if remaining_chunks:
                        kg_extraction_success = False  # 還有剩餘分塊，未完全完成
                    else:
                        kg_extraction_success = True  # 完全完成
                except Exception as e:
                    logger.error(
                        "知識圖譜提取失敗（不影響向量化）",
                        file_id=file_id,
                        error=str(e),
                        exc_info=True,
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
                    # ⚠️ 不拋出異常，繼續執行
        else:
            # 圖片文件：跳過知識圖譜提取
            logger.info(
                "圖片文件跳過知識圖譜提取",
                file_id=file_id,
            )
            kg_extraction_success = True  # 圖片文件跳過視為成功

        # ========== 記錄總時間 ==========
        timing_records["total"]["end"] = time.time()
        timing_records["total"]["duration_seconds"] = (
            timing_records["total"]["end"] - timing_records["total"]["start"]
        )

        # 轉換時間戳為可讀格式（用於日誌和報告）
        for key in timing_records:
            if timing_records[key].get("start"):
                timing_records[key]["start_datetime"] = datetime.fromtimestamp(
                    timing_records[key]["start"]
                ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if timing_records[key].get("end"):
                timing_records[key]["end_datetime"] = datetime.fromtimestamp(
                    timing_records[key]["end"]
                ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # ========== 更新最終狀態 ==========
        if vectorization_success and kg_extraction_success:
            overall_status = "completed"
            final_message = "文件處理完成"
        elif vectorization_success:
            overall_status = "partial_completed"
            final_message = "向量化完成，知識圖譜提取失敗"
        elif kg_extraction_success:
            overall_status = "partial_completed"
            final_message = "知識圖譜提取完成，向量化失敗"
        else:
            overall_status = "failed"
            final_message = "文件處理失敗（向量化和知識圖譜提取都失敗）"

        if is_image_file:
            final_message = "圖片文件處理完成（描述已生成並向量化）"

        _update_processing_status(
            file_id=file_id,
            overall_status=overall_status,
            overall_progress=100,
            message=final_message,
        )

        logger.info(
            "文件處理完成",
            file_id=file_id,
            chunk_count=len(chunks),
            vectorization_success=vectorization_success,
            kg_extraction_success=kg_extraction_success,
            overall_status=overall_status,
            collection_name=stats["collection_name"] if stats else None,
        )

        # 知識資產編碼（v4.4）：completed / partial_completed 時執行並寫入 file_metadata
        # 必須 await，否則 RQ Worker 的 loop.run_until_complete 結束後 loop.close() 會取消
        # create_task 的編碼任務，導致 KA 屬性從未寫入（規格 5.2、5.4.1）。
        if overall_status in ("completed", "partial_completed"):
            filename_for_encoding = Path(file_path).name if file_path else "unknown"
            preview = (
                (chunks[0].get("text") or "")[:2000]
                if chunks and isinstance(chunks[0], dict)
                else None
            )
            vec_refs: Optional[List[str]] = None
            if stats and stats.get("collection_name"):
                vec_refs = [str(stats["collection_name"])]
            graph_refs_val: Optional[Dict[str, Any]] = None
            if kg_extraction_success and not is_image_file:
                graph_refs_val = {
                    "entities_collection": "entities",
                    "relations_collection": "relations",
                }
            await _encode_knowledge_asset_async(
                file_id=file_id,
                filename=filename_for_encoding,
                file_content_preview=preview,
                file_type=file_type,
                user_id=user_id,
                task_id=task_id_from_metadata,
                vector_refs=vec_refs,
                graph_refs=graph_refs_val,
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


async def process_vectorization_only(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
) -> None:
    """
    異步處理文件向量化（只執行分塊+向量化+存儲，跳過知識圖譜提取）

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
            message="開始向量化處理",
        )

        # 導入分塊處理相關模塊
        from genai.api.routers.chunk_processing import get_chunk_processor, get_parser
        from genai.api.routers.chunk_processing import get_storage as get_chunk_storage

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
        # 從文件元數據獲取 task_id 和 storage_path（如果可用）
        metadata_service = get_metadata_service()
        file_metadata_obj = metadata_service.get(file_id)
        task_id = file_metadata_obj.task_id if file_metadata_obj else None
        metadata_storage_path = file_metadata_obj.storage_path if file_metadata_obj else None

        storage = get_chunk_storage()
        # 使用 task_id 和 metadata_storage_path 來正確讀取文件
        file_content = storage.read_file(
            file_id=file_id,
            task_id=task_id,
            metadata_storage_path=metadata_storage_path,
        )
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
                    task_id=task_id,  # 使用從元數據獲取的 task_id
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
                "message": ("文件解析完成，開始分塊" if not is_image_file else "圖片描述生成完成"),
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
                    "image_path": file_path,
                    "image_format": image_metadata.get("format"),
                    "image_width": image_metadata.get("width"),
                    "image_height": image_metadata.get("height"),
                    "vision_model": image_metadata.get("vision_model"),
                    "description_confidence": image_metadata.get("description_confidence"),
                    **image_metadata,
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

        # ========== 階段2: 清理舊向量（重新生成時）==========
        vector_store_service = get_qdrant_vector_store_service()
        try:
            # 檢查是否存在舊向量
            existing_stats = vector_store_service.get_collection_stats(file_id, user_id)
            if existing_stats.get("vector_count", 0) > 0:
                logger.info(
                    "清理舊向量以重新生成",
                    file_id=file_id,
                    existing_vector_count=existing_stats.get("vector_count", 0),
                )
                vector_store_service.delete_vectors_by_file_id(file_id, user_id)
                logger.info(
                    "舊向量清理完成",
                    file_id=file_id,
                )
        except Exception as e:
            logger.warning(
                "清理舊向量時發生錯誤（繼續執行）",
                file_id=file_id,
                error=str(e),
            )
            # 不阻止重新生成流程

        # ========== 階段3: 向量化 (50-90%) ==========
        _update_processing_status(
            file_id=file_id,
            vectorization={
                "status": "processing",
                "progress": 0,
                "message": "開始向量化",
            },
            overall_progress=50,
        )

        embedding_service = get_embedding_service()

        # 批量生成向量（帶進度回調）
        chunk_texts = [chunk.get("text", "") for chunk in chunks]

        # 定義進度回調函數
        def update_vectorization_progress(processed: int, total: int) -> None:
            """更新向量化進度"""
            progress = int((processed / total) * 100) if total > 0 else 0
            _update_processing_status(
                file_id=file_id,
                vectorization={
                    "status": "processing",
                    "progress": progress,
                    "message": f"向量化進行中: {processed}/{total}",
                },
                overall_progress=50 + int((processed / total) * 40),  # 50-90%
            )

        embeddings = await embedding_service.generate_embeddings_batch(
            chunk_texts, progress_callback=update_vectorization_progress
        )

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

        # ========== 階段4: 存儲到 Qdrant (90-100%) ==========
        _update_processing_status(
            file_id=file_id,
            storage={"status": "processing", "progress": 0, "message": "開始存儲向量"},
            overall_progress=90,
        )

        # 為圖片文件添加圖片路徑到元數據
        if is_image_file and chunks:
            if "image_path" not in chunks[0]:
                chunks[0]["image_path"] = file_path

        # 將 task_id 添加到每個 chunk 的元數據中（task_id 已在上面從元數據獲取）
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
            overall_progress=100,
        )

        logger.info(
            "向量存儲完成",
            file_id=file_id,
            chunk_count=len(chunks),
            vector_count=len(embeddings),
            collection_name=stats["collection_name"],
        )

        # 更新最終狀態（跳過 KG 提取）
        final_message = "向量化處理完成"
        if is_image_file:
            final_message = "圖片文件向量化完成（描述已生成並向量化）"

        _update_processing_status(
            file_id=file_id,
            overall_status="completed",
            overall_progress=100,
            message=final_message,
        )

        logger.info(
            "向量化處理完成（分塊+向量化+存儲）",
            file_id=file_id,
            chunk_count=len(chunks),
            vector_count=len(embeddings),
            collection_name=stats["collection_name"],
        )

    except Exception as e:
        logger.error(
            "向量化處理失敗",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        # 修改時間：2026-02-01 - 失敗時也要更新 vectorization 狀態，確保 file_metadata.vector_count 被正確更新
        _update_processing_status(
            file_id=file_id,
            vectorization={
                "status": "failed",
                "progress": 0,
                "message": f"向量化失敗: {str(e)}",
                "vector_count": 0,  # 明確設置 vector_count 為 0
            },
            overall_status="failed",
            overall_progress=0,
            message=f"向量化處理失敗: {str(e)}",
        )
        raise


async def _reconstruct_chunks_from_vectors(
    file_id: str,
    user_id: str,
) -> Optional[List[Dict[str, Any]]]:
    """
    從 Qdrant 中已存在的向量重構 chunks

    Args:
        file_id: 文件ID
        user_id: 用戶ID

    Returns:
        chunks 列表，如果沒有向量數據則返回 None
    """
    try:
        vector_store_service = get_qdrant_vector_store_service()

        # 獲取所有向量
        vectors = vector_store_service.get_vectors_by_file_id(
            file_id=file_id,
            user_id=user_id,
            limit=None,
        )

        if not vectors or len(vectors) == 0:
            return None

        # 從向量重構 chunks
        chunks = []
        for vector in vectors:
            payload = vector.get("payload", {})
            chunk = {
                "text": payload.get("chunk_text", ""),
                "file_id": file_id,
            }

            # 從 payload 提取信息
            metadata = payload
            if metadata:
                chunk["chunk_index"] = metadata.get("chunk_index", 0)
                chunk["content_type"] = metadata.get("content_type", "text")

                # 保留其他元數據
                chunk_metadata = {}
                for key, value in metadata.items():
                    if key not in [
                        "chunk_index",
                        "content_type",
                        "file_id",
                        "user_id",
                        "chunk_text",
                    ]:
                        if isinstance(value, str) and (
                            value.startswith("{") or value.startswith("[")
                        ):
                            try:
                                value = json.loads(value)
                            except (json.JSONDecodeError, ValueError):
                                pass
                        chunk_metadata[key] = value

                if chunk_metadata:
                    chunk["metadata"] = chunk_metadata

                # 圖片文件特殊處理
                if metadata.get("content_type") == "image":
                    chunk["image_path"] = metadata.get("image_path", "")
                    chunk["image_format"] = metadata.get("image_format")
                    chunk["image_width"] = metadata.get("image_width")
                    chunk["image_height"] = metadata.get("image_height")
                    chunk["vision_model"] = metadata.get("vision_model")
                    chunk["description_confidence"] = metadata.get("description_confidence")

            chunks.append(chunk)

        # 按 chunk_index 排序
        chunks.sort(key=lambda x: x.get("chunk_index", 0))

        logger.info(
            "從向量重構 chunks 完成",
            file_id=file_id,
            chunk_count=len(chunks),
        )

        return chunks

    except Exception as e:
        logger.warning(
            "從向量重構 chunks 失敗",
            file_id=file_id,
            error=str(e),
        )
        return None


async def process_kg_extraction(
    file_id: str,
    chunks: List[Dict[str, Any]],
    user_id: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
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
        # 修改時間：2025-12-13 (UTC+8) - 寫入正確 job_id，方便前端追蹤
        try:
            from rq import get_current_job

            current_job = get_current_job()
            current_job_id = current_job.id if current_job else None
        except Exception:
            current_job_id = None

        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "processing",
                "progress": 0,
                "message": "開始知識圖譜提取",
                "mode": options.get("mode", "all_chunks"),
                "job_id": current_job_id,
            },
            overall_progress=90,
        )

        kg_service = get_kg_extraction_service()

        # 修改時間：2025-12-13 (UTC+8) - 以「分塊可續跑」方式提取並逐塊寫入 KG（不靠拉高 timeout）
        # 修改時間：2026-01-01 - 短期優化：增加並發數從3到5，提升KG提取性能
        # 修改時間：2026-01-01 - 性能測試後確認：並發數5為最優值
        result = await kg_service.extract_and_build_incremental(
            file_id=file_id,
            chunks=chunks,
            user_id=user_id,
            options=options,
            concurrency=5,
            time_budget_seconds=150,
        )

        # 統計實體和關係數量
        entities_count = int(result.get("entities_created", 0) or 0)
        relations_count = int(result.get("relations_created", 0) or 0)
        triples_count = int(result.get("triples_count", 0) or 0)
        remaining = result.get("remaining_chunks") or []

        if remaining:
            _update_processing_status(
                file_id=file_id,
                kg_extraction={
                    "status": "processing",
                    "progress": int(
                        len(result.get("completed_chunks", []))
                        / max(int(result.get("total_chunks", 1) or 1), 1)
                        * 100
                    ),
                    "message": f"已完成部分圖譜分塊，剩餘 {len(remaining)} 個分塊等待續跑",
                    "triples_count": triples_count,
                    "entities_count": entities_count,
                    "relations_count": relations_count,
                    "remaining_chunks": remaining,
                    "failed_chunks": result.get("failed_chunks", []),
                    "failed_permanent_chunks": result.get("failed_permanent_chunks", []),
                    "mode": options.get("mode", "all_chunks"),
                    "job_id": current_job_id,
                },
                overall_status="processing",  # 明確設置為 processing，因為還有剩餘分塊
                overall_progress=95,
            )
        else:
            # KG 構建完成後，從 ArangoDB 查詢實際數據並更新 Redis 緩存
            try:
                from api.routers.file_management import get_arangodb_client

                arangodb_client = get_arangodb_client()
                if arangodb_client.db and arangodb_client.db.aql:
                    # 查詢實際實體數量
                    entities_query = """
                    FOR entity IN entities
                        FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                        COLLECT WITH COUNT INTO count
                        RETURN count
                    """
                    entities_result = list(
                        arangodb_client.db.aql.execute(
                            entities_query, bind_vars={"file_id": file_id}
                        )
                    )
                    db_entities_count = entities_result[0] if entities_result else 0

                    # 查詢實際關係數量
                    relations_query = """
                    FOR relation IN relations
                        FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                        COLLECT WITH COUNT INTO count
                        RETURN count
                    """
                    relations_result = list(
                        arangodb_client.db.aql.execute(
                            relations_query, bind_vars={"file_id": file_id}
                        )
                    )
                    db_relations_count = relations_result[0] if relations_result else 0

                    # 使用 ArangoDB 的實際數據（如果查詢成功）
                    if db_entities_count > 0 or db_relations_count > 0:
                        entities_count = db_entities_count
                        relations_count = db_relations_count
                        triples_count = db_relations_count  # 三元組數量 = 關係數量
                        logger.info(
                            "Updated KG stats from ArangoDB",
                            file_id=file_id,
                            entities_count=entities_count,
                            relations_count=relations_count,
                            triples_count=triples_count,
                        )
            except Exception as e:
                logger.warning(
                    "Failed to query ArangoDB for KG stats after completion",
                    file_id=file_id,
                    error=str(e),
                )

            _update_processing_status(
                file_id=file_id,
                kg_extraction={
                    "status": "completed",
                    "progress": 100,
                    "message": "知識圖譜構建完成",
                    "triples_count": triples_count,
                    "entities_count": entities_count,
                    "relations_count": relations_count,
                    "failed_chunks": result.get("failed_chunks", []),
                    "failed_permanent_chunks": result.get("failed_permanent_chunks", []),
                    "mode": options.get("mode", "all_chunks"),
                    "job_id": current_job_id,
                },
                overall_status="completed",
                overall_progress=100,
                message="文件處理完成（分塊+向量化+存儲+KG提取）",
            )

        logger.info(
            "知識圖譜構建完成",
            file_id=file_id,
            triples_count=triples_count,
            entities_count=entities_count,
            relations_count=relations_count,
            remaining_chunks=len(remaining),
        )
        return result

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


async def process_kg_extraction_only(
    file_id: str,
    file_path: str,
    file_type: Optional[str],
    user_id: str,
    force_rechunk: bool = False,
) -> None:
    """
    異步處理知識圖譜提取（只執行圖譜提取，嘗試重用已存在的 chunks）

    Args:
        file_id: 文件ID
        file_path: 文件路徑
        file_type: 文件類型（MIME類型）
        user_id: 用戶ID
        force_rechunk: 是否強制重新分塊（即使有已存在的 chunks）
    """
    try:
        # 修改時間：2025-12-12 - 在函數開始處初始化 metadata_service，避免作用域問題
        metadata_service = None

        # 檢查是否為圖片文件（圖片文件跳過 KG 提取）
        if file_type and file_type.startswith("image/"):
            logger.info(
                "圖片文件跳過知識圖譜提取",
                file_id=file_id,
            )
            _update_processing_status(
                file_id=file_id,
                kg_extraction={
                    "status": "skipped",
                    "progress": 100,
                    "message": "圖片文件不適合提取知識圖譜",
                },
            )
            return

        # 初始化狀態
        _update_processing_status(
            file_id=file_id,
            overall_status="processing",
            overall_progress=0,
            message="開始圖譜提取處理",
        )

        # ========== 清理舊圖譜數據（僅在 force_rechunk=True 時重新生成）==========
        # 修改時間：2026-01-27 - 修復續跑流程：只在 force_rechunk=True 時清理 chunk_state
        # 續跑任務應該保留已完成的 chunks 狀態，只處理剩餘的分塊
        if force_rechunk:
            try:
                kg_builder_service = KGBuilderService()
                cleanup_result = kg_builder_service.remove_file_associations(file_id)
                if (
                    cleanup_result.get("relations_deleted", 0) > 0
                    or cleanup_result.get("entities_deleted", 0) > 0
                ):
                    logger.info(
                        "清理舊圖譜數據以重新生成",
                        file_id=file_id,
                        relations_deleted=cleanup_result.get("relations_deleted", 0),
                        entities_deleted=cleanup_result.get("entities_deleted", 0),
                    )
                # 清理 chunk 狀態（僅在重新生成時重置續跑狀態）
                # 清理 Redis 中的 chunk 狀態
                redis_client = get_redis_client()  # noqa: F823
                chunk_state_key = f"kg:chunk_state:{file_id}"
                redis_client.delete(chunk_state_key)
                logger.info(
                    "舊圖譜數據和狀態清理完成（force_rechunk=True）",
                    file_id=file_id,
                )
            except Exception as e:
                logger.warning(
                    "清理舊圖譜數據時發生錯誤（繼續執行）",
                    file_id=file_id,
                    error=str(e),
                )
                # 不阻止重新生成流程
        else:
            # 續跑任務：保留已完成的 chunks 狀態，只處理剩餘分塊
            logger.info(
                "續跑任務：保留已完成的 chunks 狀態",
                file_id=file_id,
                force_rechunk=force_rechunk,
            )

        chunks = None

        # 嘗試從已存在的向量中獲取 chunks
        if not force_rechunk:
            chunks = await _reconstruct_chunks_from_vectors(file_id, user_id)
            if chunks:
                logger.info(
                    "重用已存在的 chunks 進行圖譜提取",
                    file_id=file_id,
                    chunk_count=len(chunks),
                )

        # 如果無法獲取已存在的 chunks，則重新解析和分塊
        if chunks is None or len(chunks) == 0:
            logger.info(
                "重新解析和分塊以進行圖譜提取",
                file_id=file_id,
            )

            # 導入分塊處理相關模塊
            from genai.api.routers.chunk_processing import get_chunk_processor, get_parser
            from genai.api.routers.chunk_processing import get_storage as get_chunk_storage

            # 獲取解析器
            if file_type is None:
                file_type = "text/plain"
            parser = get_parser(file_type)

            # 解析文件
            # 優先從文件元數據獲取 task_id 和 storage_path
            # 如果元數據不存在，嘗試從文件路徑直接讀取
            task_id = None
            metadata_storage_path = None
            file_content = None
            # 修改時間：2025-12-12 - metadata_service 已在函數開始處初始化

            try:
                if metadata_service is None:
                    metadata_service = get_metadata_service()
                file_metadata_obj = metadata_service.get(file_id)
                if file_metadata_obj:
                    task_id = file_metadata_obj.task_id
                    metadata_storage_path = file_metadata_obj.storage_path
            except Exception as e:
                logger.warning(
                    "無法獲取文件元數據，將嘗試直接讀取文件",
                    file_id=file_id,
                    error=str(e),
                )

            # 嘗試從存儲讀取文件
            if task_id or metadata_storage_path:
                try:
                    storage = get_chunk_storage()
                    file_content = storage.read_file(
                        file_id=file_id,
                        task_id=task_id,
                        metadata_storage_path=metadata_storage_path,
                    )
                except Exception as e:
                    logger.warning(
                        "從存儲讀取文件失敗，嘗試直接讀取文件系統",
                        file_id=file_id,
                        error=str(e),
                    )

            # 如果無法從存儲讀取，嘗試直接從文件系統讀取
            if file_content is None and file_path and os.path.exists(file_path):
                logger.info(
                    "直接從文件系統讀取文件",
                    file_id=file_id,
                    file_path=file_path,
                )
                with open(file_path, "rb") as f:
                    file_content = f.read()

            if file_content is None:
                raise ValueError(f"無法讀取文件: {file_id}，請檢查文件是否存在")

            # 解析文件
            if hasattr(parser, "parse_from_bytes"):
                import inspect

                if inspect.iscoroutinefunction(parser.parse_from_bytes):
                    parse_result = await parser.parse_from_bytes(
                        file_content,
                        file_id=file_id,
                        user_id=user_id,
                        task_id=None,
                    )
                else:
                    parse_result = parser.parse_from_bytes(file_content)
            elif hasattr(parser, "parse"):
                parse_result = parser.parse(file_path)
            else:
                raise ValueError(f"解析器不支持此文件類型: {file_type}")

            # 獲取分塊處理器
            chunk_processor = get_chunk_processor()

            # 文本文件正常分塊
            chunks = chunk_processor.process(
                text=parse_result["text"],
                file_id=file_id,
                metadata=parse_result.get("metadata", {}),
            )

            logger.info(
                "文件重新分塊完成",
                file_id=file_id,
                chunk_count=len(chunks),
            )

        # 讀取 KG 提取配置
        services_config = get_config_section("services", default={}) or {}
        kg_config = services_config.get("kg_extraction", {})
        if not kg_config:
            kg_config = {
                "enabled": True,
                "mode": "all_chunks",
                "min_confidence": 0.5,
                "chunk_filter": {},
            }

        # 獲取文件元數據用於 Ontology 選擇
        # 修改時間：2025-12-12 - 確保 metadata_service 已初始化
        if metadata_service is None:
            metadata_service = get_metadata_service()

        file_metadata_obj = None
        try:
            file_metadata_obj = metadata_service.get(file_id)
        except Exception as e:
            logger.warning(
                "無法獲取文件元數據用於 Ontology 選擇",
                file_id=file_id,
                error=str(e),
            )

        file_metadata_dict = None
        if file_metadata_obj:
            file_metadata_dict = {
                "file_name": file_metadata_obj.filename,
                "file_type": file_metadata_obj.file_type,
                "file_size": file_metadata_obj.file_size,
            }

        # 將文件信息添加到 options 中
        kg_config_with_metadata = {
            **kg_config,
            "file_name": (
                file_metadata_obj.filename
                if (file_metadata_obj and hasattr(file_metadata_obj, "filename"))
                else None
            ),
            "file_metadata": file_metadata_dict,
        }

        # 執行知識圖譜提取（分塊可續跑）
        result = await process_kg_extraction(
            file_id=file_id,
            chunks=chunks,
            user_id=user_id,
            options=kg_config_with_metadata,
        )

        # 若未完成（time budget 到期），自動排程下一輪續跑（加鎖避免重複 enqueue）
        remaining_chunks = (result or {}).get("remaining_chunks") or []
        if remaining_chunks:
            try:
                from rq import get_current_job

                from database.rq.queue import KG_EXTRACTION_QUEUE, get_task_queue
                from workers.tasks import process_kg_extraction_only_task

                # 獲取當前 job_id（如果有的話）
                try:
                    current_job = get_current_job()
                    current_job_id = current_job.id if current_job else None
                except Exception:
                    current_job_id = None

                queue = get_task_queue(KG_EXTRACTION_QUEUE)
                redis_client = get_redis_client()
                lock_key = f"kg:continue_lock:{file_id}"
                # 120 秒內只允許 enqueue 一次續跑，避免 worker/重試造成連環排程
                got_lock = bool(redis_client.set(lock_key, "1", nx=True, ex=120))
                if got_lock:
                    job_timeout = get_worker_job_timeout()
                    next_job = queue.enqueue(
                        process_kg_extraction_only_task,
                        file_id=file_id,
                        file_path=file_path,
                        file_type=file_type,
                        user_id=user_id,
                        force_rechunk=False,
                        job_timeout=job_timeout,
                    )
                    next_job_id = next_job.id
                else:
                    next_job_id = None

                _update_processing_status(
                    file_id=file_id,
                    kg_extraction={
                        "status": "processing",
                        "message": f"續跑已排程（剩餘 {len(remaining_chunks)} 個分塊）",
                        "next_job_id": next_job_id,
                        "remaining_chunks": remaining_chunks,
                        "job_id": current_job_id,
                    },
                )
                logger.info(
                    "KG extraction continuation enqueued",
                    file_id=file_id,
                    next_job_id=next_job_id,
                    remaining_chunks=len(remaining_chunks),
                )
            except Exception as e:
                logger.warning(
                    "Failed to enqueue KG extraction continuation",
                    file_id=file_id,
                    error=str(e),
                )

        # 更新最終狀態為 completed（如果所有階段都完成）
        _update_processing_status(
            file_id=file_id,
            kg_extraction={
                "status": "completed",
                "progress": 100,
                "message": "知識圖譜提取完成",
            },
            overall_status="completed",
            overall_progress=100,
            message="圖譜提取處理完成",
        )

        logger.info(
            "圖譜提取處理完成",
            file_id=file_id,
            chunk_count=len(chunks),
        )

    except Exception as e:
        logger.error(
            "圖譜提取處理失敗",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        _update_processing_status(
            file_id=file_id,
            overall_status="failed",
            overall_progress=0,
            message=f"圖譜提取處理失敗: {str(e)}",
        )
        raise


@router.post("/v2/upload")
@audit_log(
    action=AuditAction.FILE_UPLOAD,
    resource_type="file",
    get_resource_id=_extract_file_ids,
)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    task_id: Optional[str] = Form(None, description="任務ID（可選，用於組織文件到工作區）"),
    target_folder_id: Optional[str] = Form(
        None, description="目標資料夾ID（可選，未提供則放任務工作區）"
    ),
    kb_folder_id: Optional[str] = Form(
        None, description="知識庫資料夾ID（可選，用於知識庫文件上傳）"
    ),
    current_user: User = Depends(require_consent(ConsentType.FILE_UPLOAD)),
) -> JSONResponse:
    # 修改時間：2025-01-27 - 添加日誌記錄以便調試 JWT 認證問題
    # 修改時間：2026-02-13 - 添加 kb_folder_id 支持知識庫文件上傳
    logger.debug(
        "File upload request received",
        user_id=current_user.user_id,
        username=current_user.username,
        task_id=task_id,
        kb_folder_id=kb_folder_id,
        file_count=len(files) if files else 0,
        request_path=request.url.path,
    )
    """
    上傳文件（支持多文件上傳）

    Args:
        files: 上傳的文件列表
        task_id: 任務ID（可選，用於組織文件到工作區）
        current_user: 當前認證用戶（從 Token 獲取）

    Returns:
        上傳結果，包含文件 ID 和元數據
    """
    # 修改時間：2025-01-27 - 添加日誌記錄以便調試 JWT 認證問題
    logger.info(
        "File upload request received",
        user_id=current_user.user_id,
        username=getattr(current_user, "username", None),
        task_id=task_id,
        file_count=len(files) if files else 0,
        request_path=request.url.path,
        request_method=request.method,
    )

    if not files:
        return APIResponse.error(
            message="未提供文件",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 檢查上傳權限
    permission_service = get_file_permission_service()
    permission_service.check_upload_permission(current_user)

    # 修改時間：2025-01-27 - 重構任務工作區邏輯，移除 temp-workspace
    # 任務創建邏輯：如果沒有提供 task_id，必須創建新任務
    # 任務命名：如果是第一次上傳文件，使用第一個文件名（不含擴展名）作為任務標題
    task_service = get_user_task_service()
    final_task_id: Optional[str] = None
    task_title: Optional[str] = None
    final_folder_id: Optional[str] = target_folder_id
    skip_task_creation = False  # 是否跳過任務創建

    if task_id:
        # 提供了 task_id，檢查任務是否存在且屬於當前用戶
        existing_task = task_service.get(
            user_id=current_user.user_id,
            task_id=task_id,
        )

        if existing_task is None:
            # 任務不存在或屬於其他用戶，生成新的 UUID 任務 ID
            # 修改時間：2026-01-21 - 使用 UUID 避免任務 ID 衝突
            new_task_id = str(uuid.uuid4())

            # 使用第一個文件名（不含擴展名）作為任務標題
            if files and len(files) > 0:
                first_filename = files[0].filename or "新任務"
                task_title = os.path.splitext(first_filename)[0] or "新任務"
            else:
                task_title = task_id  # 如果沒有文件名，使用提供的 task_id 作為標題

            logger.info(
                "提供的 task_id 不可用，自動創建新任務（使用 UUID）",
                original_task_id=task_id,
                new_task_id=new_task_id,
                user_id=current_user.user_id,
                task_title=task_title,
            )

            try:
                # 創建新任務（任務工作區會自動創建）
                task_service.create(
                    UserTaskCreate(
                        task_id=new_task_id,
                        user_id=current_user.user_id,
                        title=task_title,
                        status="pending",
                        messages=[],
                        fileTree=[],
                        label_color=None,
                        dueDate=None,
                    )
                )
                final_task_id = new_task_id
                logger.info(
                    "新任務創建成功",
                    task_id=new_task_id,
                    user_id=current_user.user_id,
                    task_title=task_title,
                )
            except Exception as e:
                logger.error(
                    "創建任務失敗",
                    task_id=new_task_id,
                    user_id=current_user.user_id,
                    error=str(e),
                    exc_info=True,
                )
                return APIResponse.error(
                    message=f"創建任務失敗: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            # 任務已存在且屬於當前用戶，直接使用該任務
            final_task_id = task_id
            logger.debug(
                "任務已存在，使用現有任務",
                task_id=task_id,
                user_id=current_user.user_id,
            )

        # 檢查任務文件訪問權限
        permission_service.check_task_file_access(
            user=current_user,
            task_id=final_task_id,
            required_permission=Permission.FILE_UPLOAD.value,
        )
    elif kb_folder_id:
        # 修改時間：2026-02-13 - 知識庫文件上傳邏輯
        # 知識庫文件不關聯到任務，而是關聯到知識庫資料夾
        # 但為了保持 S3 存儲和向量處理的統一，我們仍然需要一個 task_id
        # 這裡我們使用 kb_folder_id 作為標識，創建一個虛擬任務

        # 驗證 KB 資料夾是否存在且屬於當前用戶
        from api.routers.knowledge_base import get_kb_folder_by_id

        kb_folder = get_kb_folder_by_id(kb_folder_id, current_user.user_id)

        if kb_folder is None:
            return APIResponse.error(
                message="知識庫資料夾不存在或無權訪問",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 使用 KB 資料夾 ID 作為標識，創建虛擬任務 ID
        # 格式：kb_{kb_folder_id}
        final_task_id = f"kb_{kb_folder_id}"
        final_folder_id = kb_folder_id  # 關聯到 KB 資料夾

        logger.info(
            "知識庫文件上傳，使用 KB 資料夾",
            kb_folder_id=kb_folder_id,
            task_id=final_task_id,
            user_id=current_user.user_id,
        )

        # KB 文件不需要檢查任務權限，也不需要創建任務工作區
        # 跳過任務創建和工作區創建
        # 直接跳到文件保存邏輯
        skip_task_creation = True
    else:
        # 未提供 task_id，必須創建新任務
        # 生成新的 task_id
        final_task_id = str(uuid.uuid4())

        # 使用第一個文件名（不含擴展名）作為任務標題
        if files and len(files) > 0:
            first_filename = files[0].filename or "新任務"
            # 移除文件擴展名作為任務名稱
            task_title = os.path.splitext(first_filename)[0] or "新任務"
        else:
            task_title = "新任務"

        logger.info(
            "未提供 task_id，創建新任務及任務工作區",
            task_id=final_task_id,
            user_id=current_user.user_id,
            task_title=task_title,
        )
        try:
            # 創建新任務（任務工作區會自動創建）
            task_service.create(
                UserTaskCreate(
                    task_id=final_task_id,
                    user_id=current_user.user_id,
                    title=task_title,
                    status="pending",
                    messages=[],
                    fileTree=[],
                    label_color=None,  # type: ignore[call-arg]  # label_color 有默認值
                    dueDate=None,  # type: ignore[call-arg]  # dueDate 有默認值
                )
            )
            logger.info(
                "新任務及任務工作區創建成功",
                task_id=final_task_id,
                user_id=current_user.user_id,
                task_title=task_title,
            )
        except Exception as e:
            logger.error(
                "創建任務失敗",
                task_id=final_task_id,
                user_id=current_user.user_id,
                error=str(e),
                exc_info=True,
            )
            return APIResponse.error(
                message=f"創建任務失敗: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    validator = get_validator()
    storage = get_storage()

    # 確保任務工作區存在（知識庫文件跳過）
    if not skip_task_creation:
        workspace_service = get_task_workspace_service()
        workspace_service.create_workspace(task_id=final_task_id, user_id=current_user.user_id)

    # 驗證目標資料夾；若未提供，預設為該任務的工作區
    # 知識庫文件跳過驗證（因爲是 KB 資料夾，不是任務資料夾）
    if final_folder_id and not skip_task_creation:
        from api.routers.file_management import get_arangodb_client

        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        folder_col = arangodb_client.db.collection("folder_metadata")
        folder_doc = folder_col.get(final_folder_id)
        if (
            folder_doc is None
            or folder_doc.get("user_id") != current_user.user_id
            or folder_doc.get("task_id") != final_task_id
        ):
            return APIResponse.error(
                message="目標資料夾不存在或不屬於當前用戶/任務",
                status_code=status.HTTP_403_FORBIDDEN,
            )
    elif not final_folder_id:
        final_folder_id = f"{final_task_id}_workspace"

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

            # 修改時間：2025-01-27 - 確保任務工作區存在
            if final_task_id:
                workspace_service = get_task_workspace_service()
                workspace_service.ensure_workspace_exists(
                    task_id=final_task_id,
                    user_id=current_user.user_id,
                )

            # 保存文件（使用清理後的文件名，傳遞 task_id）
            file_id, file_path = storage.save_file(
                file_content, sanitized_filename, task_id=final_task_id
            )

            # 更新進度：文件保存完成
            _update_upload_progress(file_id, 50, "uploading", "文件已保存，正在處理...")

            # 獲取文件類型
            file_type = (
                validator.get_file_type(file.filename)
                if file.filename
                else "application/octet-stream"
            )  # type: ignore[arg-type]  # file.filename 可能為 None

            # 創建元數據
            try:
                metadata_service = get_metadata_service()
                # 修改時間：2025-01-27 - 移除 temp-workspace，所有文件必須關聯到任務工作區
                # final_task_id 已在上方確保存在（如果沒有則已創建）
                if not final_task_id:
                    raise ValueError("任務ID不能為空，文件必須關聯到任務工作區")

                # 確保文件放在任務工作區下（task_id 就是任務工作區的標識）
                metadata_create = FileMetadataCreate(
                    file_id=file_id,
                    filename=sanitized_filename,  # 使用清理後的文件名
                    file_type=file_type or "application/octet-stream",
                    file_size=len(file_content),
                    user_id=current_user.user_id,
                    task_id=final_task_id,  # 文件位置在該任務的任務工作區下
                    folder_id=final_folder_id,
                    storage_path=str(file_path),  # 保存文件存儲路徑
                    description=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
                    status=None,  # type: ignore[call-arg]
                    processing_status=None,  # type: ignore[call-arg]
                    chunk_count=None,  # type: ignore[call-arg]
                    vector_count=None,  # type: ignore[call-arg]
                    kg_status=None,  # type: ignore[call-arg]
                )
                logger.info(
                    "創建文件元數據",
                    file_id=file_id,
                    filename=sanitized_filename,
                    task_id=final_task_id,
                    user_id=current_user.user_id,
                )
                metadata_service.create(metadata_create)
                logger.info("文件元數據創建成功", file_id=file_id)
            except Exception as e:
                logger.error(
                    "元數據創建失敗（文件已上傳）",
                    file_id=file_id,
                    error=str(e),
                    exc_info=True,
                )
                # 重新拋出異常，讓上傳失敗
                raise

            # 構建結果
            result = {
                "file_id": file_id,
                "filename": sanitized_filename,  # 使用清理後的文件名
                "file_type": file_type,
                "file_size": len(file_content),
                "file_path": file_path,
                "task_id": final_task_id,
                "folder_id": final_folder_id,
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

            # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄文件創建操作日誌
            try:
                from services.api.services.operation_log_service import get_operation_log_service

                operation_log_service = get_operation_log_service()

                # 獲取文件元數據以獲取創建時間
                try:
                    file_metadata = metadata_service.get(file_id)
                    file_created_at = None
                    if (
                        file_metadata
                        and hasattr(file_metadata, "created_at")
                        and file_metadata.created_at
                    ):
                        if isinstance(file_metadata.created_at, datetime):
                            file_created_at = file_metadata.created_at.isoformat() + "Z"
                        elif isinstance(file_metadata.created_at, str):
                            file_created_at = (
                                file_metadata.created_at
                                if file_metadata.created_at.endswith("Z")
                                else file_metadata.created_at + "Z"
                            )
                except Exception:
                    file_created_at = datetime.utcnow().isoformat() + "Z"

                operation_log_service.log_operation(
                    user_id=current_user.user_id,
                    resource_id=file_id,
                    resource_type="document",
                    resource_name=sanitized_filename,
                    operation_type="create",
                    created_at=file_created_at or datetime.utcnow().isoformat() + "Z",
                    updated_at=None,
                    archived_at=None,
                    deleted_at=None,
                    notes=f"文件上傳，任務ID: {final_task_id}，任務標題: {task_title or 'N/A'}",
                )
            except Exception as e:
                logger.warning("記錄文件創建操作日誌失敗", file_id=file_id, error=str(e))

            # 觸發異步處理任務（分塊+向量化+圖譜）- 使用 RQ 隊列
            # 注意：task_id 會從文件元數據中獲取，不需要額外傳遞
            try:
                queue = get_task_queue(FILE_PROCESSING_QUEUE)
                job_timeout = get_worker_job_timeout()
                job = queue.enqueue(
                    process_file_chunking_and_vectorization_task,
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=current_user.user_id,
                    job_timeout=job_timeout,
                )
                logger.info(
                    "文件處理任務已提交到 RQ 隊列",
                    file_id=file_id,
                    job_id=job.id,
                    queue=FILE_PROCESSING_QUEUE,
                )
            except Exception as e:
                logger.error(
                    "提交文件處理任務到 RQ 隊列失敗",
                    file_id=file_id,
                    error=str(e),
                )
                # 不拋出異常，讓文件上傳成功，但記錄錯誤

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

    # 修改時間：2026-01-28 - 文件上傳/知識上架成功時，為上傳者自動寫入 AI 處理同意（若尚未同意）
    if results:
        try:
            from services.api.services.data_consent_service import get_consent_service

            consent_service = get_consent_service()
            consent_service.record_consent(
                current_user.user_id,
                DataConsentCreate(
                    consent_type=ConsentType.AI_PROCESSING,
                    purpose="文件上傳/知識上架時自動同意",
                    granted=True,
                    expires_at=None,
                ),
            )
            logger.info(
                f"ai_processing_consent_recorded_after_upload: "
                f"user_id={current_user.user_id}, success_count={len(results)}"
            )
        except Exception as e:
            logger.warning(
                f"record_ai_consent_after_upload_failed: "
                f"user_id={current_user.user_id}, error={str(e)}"
            )

    # 構建響應
    response_data = {
        "uploaded": results,
        "errors": errors,
        "total": len(files),
        "success_count": len(results),
        "error_count": len(errors),
        "task_id": final_task_id,
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
        # fileTree 不再緩存到任務文檔中，因此不需要更新
        # 前端需要 fileTree 時會從 /api/v1/files/tree API 動態獲取

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

    修改時間：2026-01-02 - 添加基於 ACL 的權限檢查

    Args:
        file_id: 文件 ID

    Returns:
        文件信息
    """
    # 獲取文件元數據
    metadata_service = get_metadata_service()
    file_metadata = metadata_service.get(file_id)

    if file_metadata is None:
        return APIResponse.error(
            message="文件不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 使用 ACL 權限檢查
    permission_service = get_file_permission_service()
    if not permission_service.check_file_access_with_acl(
        user=current_user,
        file_metadata=file_metadata,
        required_permission=Permission.FILE_READ.value,
        request=request,
    ):
        return APIResponse.error(
            message="無權訪問此文件",
            status_code=status.HTTP_403_FORBIDDEN,
        )

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
        progress_data_str = redis_client.get(progress_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]

        if not progress_data_str:
            return APIResponse.error(
                message="進度記錄不存在或已過期",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        progress_data = json.loads(progress_data_str)  # type: ignore[arg-type]  # progress_data_str 已檢查不為 None，且 decode_responses=True 返回 str

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
        # 修改時間：2025-12-12 - 任務工作區文件需要 task_id / storage_path 才能正確判斷存在
        task_id: Optional[str] = None
        metadata_storage_path: Optional[str] = None
        try:
            metadata_service = get_metadata_service()
            file_metadata_obj = metadata_service.get(file_id)
            if file_metadata_obj:
                task_id = getattr(file_metadata_obj, "task_id", None)
                metadata_storage_path = getattr(file_metadata_obj, "storage_path", None)
        except Exception:
            pass

        file_exists = False
        try:
            file_exists = storage.file_exists(  # type: ignore[call-arg]
                file_id=file_id,
                task_id=task_id,
                metadata_storage_path=metadata_storage_path,
            )
        except TypeError:
            file_exists = storage.file_exists(file_id)

        if not file_exists:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從 Redis 讀取處理狀態
        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]

        if status_data_str:
            status_data = json.loads(status_data_str)  # type: ignore[arg-type]  # status_data_str 已檢查不為 None，且 decode_responses=True 返回 str
            return APIResponse.success(
                data=status_data,
                message="處理狀態查詢成功",
            )
        else:
            # Redis 中沒有狀態，嘗試從 ArangoDB 讀取持久化狀態
            try:
                from services.api.services.upload_status_service import get_upload_status_service

                status_service = get_upload_status_service()
                processing_status = status_service.get_processing_status(file_id)

                if processing_status:
                    # 將 ArangoDB 的狀態轉換為 API 響應格式
                    status_data = {
                        "file_id": file_id,
                        "status": processing_status.overall_status or "pending",
                        "progress": processing_status.overall_progress or 0,
                        "message": getattr(processing_status, "message", None),
                        "chunking": (
                            processing_status.chunking.model_dump()
                            if processing_status.chunking
                            else {"status": "pending", "progress": 0}
                        ),
                        "vectorization": (
                            processing_status.vectorization.model_dump()
                            if processing_status.vectorization
                            else {"status": "pending", "progress": 0}
                        ),
                        "storage": (
                            processing_status.storage.model_dump()
                            if processing_status.storage
                            else {"status": "pending", "progress": 0}
                        ),
                        "kg_extraction": (
                            processing_status.kg_extraction.model_dump()
                            if processing_status.kg_extraction
                            else {"status": "pending", "progress": 0}
                        ),
                    }

                    # 將狀態同步回 Redis（如果已完成，設置較長的 TTL；如果進行中，設置較短的 TTL）
                    ttl = (
                        86400 if (processing_status.overall_status == "completed") else 7200
                    )  # 已完成：24小時，進行中：2小時
                    redis_client.setex(
                        status_key,
                        ttl,
                        json.dumps(status_data, default=str),
                    )

                    return APIResponse.success(
                        data=status_data,
                        message="處理狀態查詢成功（從 ArangoDB 恢復）",
                    )
            except Exception as e:
                logger.warning(
                    "從 ArangoDB 讀取處理狀態失敗",
                    file_id=file_id,
                    error=str(e),
                )

            # 如果沒有處理狀態記錄，檢查是否已上傳
            # 可能文件剛上傳，處理還未開始
            upload_progress_key = f"upload:progress:{file_id}"
            upload_progress_str = redis_client.get(upload_progress_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]

            if upload_progress_str:
                upload_progress = json.loads(upload_progress_str)  # type: ignore[arg-type]  # upload_progress_str 已檢查不為 None，且 decode_responses=True 返回 str
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


@router.get("/{file_id}/kg/chunk-status")
async def get_kg_chunk_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取 KG 分塊續跑狀態（completed/failed/remaining/錯誤訊息）。"""
    try:
        redis_client = get_redis_client()
        state_key = f"kg:chunk_state:{file_id}"
        state_str = redis_client.get(state_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]
        if not state_str:
            return APIResponse.success(
                data={
                    "file_id": file_id,
                    "exists": False,
                    "total_chunks": 0,
                    "completed_chunks": [],
                    "failed_chunks": [],
                    "failed_permanent_chunks": [],
                    "errors": {},
                },
                message="KG chunk 狀態不存在（尚未開始或已過期）",
            )

        state = json.loads(state_str)  # type: ignore[arg-type]  # state_str 已檢查不為 None，且 decode_responses=True 返回 str
        return APIResponse.success(
            data={
                "file_id": file_id,
                "exists": True,
                "total_chunks": state.get("total_chunks", 0),
                "completed_chunks": state.get("completed_chunks", []) or [],
                "failed_chunks": state.get("failed_chunks", []) or [],
                "failed_permanent_chunks": state.get("failed_permanent_chunks", []) or [],
                "attempts": state.get("attempts", {}) or {},
                "errors": state.get("errors", {}) or {},
                "chunks": state.get("chunks", {}) or {},
            },
            message="KG chunk 狀態查詢成功",
        )
    except Exception as e:
        logger.error(
            "Failed to get KG chunk status",
            file_id=file_id,
            error=str(e),
        )
        return APIResponse.error(
            message=f"查詢 KG chunk 狀態失敗: {str(e)}",
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
        task_id: Optional[str] = None
        metadata_storage_path: Optional[str] = None
        try:
            metadata_service = get_metadata_service()
            file_metadata_obj = metadata_service.get(file_id)
            if file_metadata_obj:
                task_id = getattr(file_metadata_obj, "task_id", None)
                metadata_storage_path = getattr(file_metadata_obj, "storage_path", None)
        except Exception:
            pass

        file_exists = False
        try:
            file_exists = storage.file_exists(  # type: ignore[call-arg]
                file_id=file_id,
                task_id=task_id,
                metadata_storage_path=metadata_storage_path,
            )
        except TypeError:
            file_exists = storage.file_exists(file_id)

        if not file_exists:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從處理狀態中獲取KG統計
        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]

        if status_data_str:
            status_data = json.loads(status_data_str)  # type: ignore[arg-type]  # status_data_str 已檢查不為 None，且 decode_responses=True 返回 str
            kg_extraction = status_data.get("kg_extraction", {})

            if kg_extraction.get("status") == "completed":
                # 從 Redis 獲取的統計數據
                redis_entities_count = kg_extraction.get("entities_count", 0)
                redis_relations_count = kg_extraction.get("relations_count", 0)
                redis_triples_count = kg_extraction.get("triples_count", 0)

                # 驗證數據是否為 0，如果是則從 ArangoDB 查詢實際數據
                if redis_entities_count == 0 and redis_relations_count == 0:
                    # 從 ArangoDB 查詢實際數據
                    try:
                        from api.routers.file_management import get_arangodb_client

                        arangodb_client = get_arangodb_client()
                        if arangodb_client.db and arangodb_client.db.aql:
                            # 查詢實體數量
                            entities_query = """
                            FOR entity IN entities
                                FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                                COLLECT WITH COUNT INTO count
                                RETURN count
                            """
                            entities_result = list(
                                arangodb_client.db.aql.execute(
                                    entities_query, bind_vars={"file_id": file_id}
                                )
                            )
                            db_entities_count = entities_result[0] if entities_result else 0

                            # 查詢關係數量
                            relations_query = """
                            FOR relation IN relations
                                FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                                COLLECT WITH COUNT INTO count
                                RETURN count
                            """
                            relations_result = list(
                                arangodb_client.db.aql.execute(
                                    relations_query, bind_vars={"file_id": file_id}
                                )
                            )
                            db_relations_count = relations_result[0] if relations_result else 0

                            # 三元組數量 = 關係數量（每個關係對應一個三元組）
                            db_triples_count = db_relations_count

                            # 如果 ArangoDB 中有數據，使用 ArangoDB 的數據並更新 Redis
                            if db_entities_count > 0 or db_relations_count > 0:
                                kg_extraction["entities_count"] = db_entities_count
                                kg_extraction["relations_count"] = db_relations_count
                                kg_extraction["triples_count"] = db_triples_count
                                status_data["kg_extraction"] = kg_extraction
                                redis_client.setex(
                                    status_key,
                                    86400,  # 24小時
                                    json.dumps(status_data),
                                )
                                return APIResponse.success(
                                    data={
                                        "file_id": file_id,
                                        "triples_count": db_triples_count,
                                        "entities_count": db_entities_count,
                                        "relations_count": db_relations_count,
                                        "mode": kg_extraction.get("mode", "all_chunks"),
                                        "source": "arangodb",  # 標記數據來源
                                    },
                                    message="KG統計信息查詢成功（從ArangoDB）",
                                )
                    except Exception as e:
                        logger.warning(
                            "Failed to query ArangoDB for KG stats",
                            file_id=file_id,
                            error=str(e),
                        )

                return APIResponse.success(
                    data={
                        "file_id": file_id,
                        "triples_count": redis_triples_count,
                        "entities_count": redis_entities_count,
                        "relations_count": redis_relations_count,
                        "mode": kg_extraction.get("mode", "all_chunks"),
                        "source": "redis",  # 標記數據來源
                    },
                    message="KG統計信息查詢成功",
                )

        # 如果沒有處理狀態，嘗試從ArangoDB查詢實際數據
        try:
            from api.routers.file_management import get_arangodb_client

            arangodb_client = get_arangodb_client()
            if arangodb_client.db and arangodb_client.db.aql:
                # 查詢實體數量
                entities_query = """
                FOR entity IN entities
                    FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                    COLLECT WITH COUNT INTO count
                    RETURN count
                """
                entities_result = list(
                    arangodb_client.db.aql.execute(entities_query, bind_vars={"file_id": file_id})
                )
                db_entities_count = entities_result[0] if entities_result else 0

                # 查詢關係數量
                relations_query = """
                FOR relation IN relations
                    FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                    COLLECT WITH COUNT INTO count
                    RETURN count
                """
                relations_result = list(
                    arangodb_client.db.aql.execute(relations_query, bind_vars={"file_id": file_id})
                )
                db_relations_count = relations_result[0] if relations_result else 0

                # 三元組數量 = 關係數量（每個關係對應一個三元組）
                db_triples_count = db_relations_count

                return APIResponse.success(
                    data={
                        "file_id": file_id,
                        "triples_count": db_triples_count,
                        "entities_count": db_entities_count,
                        "relations_count": db_relations_count,
                        "status": "processed" if db_entities_count > 0 else "not_processed",
                        "source": "arangodb",  # 標記數據來源
                    },
                    message="KG統計信息查詢成功（從ArangoDB）",
                )
        except Exception as e:
            logger.warning(
                "Failed to query ArangoDB for KG stats",
                file_id=file_id,
                error=str(e),
            )

        # 如果都失敗，返回未處理狀態
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
        # 權限檢查（以文件權限為準）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )
        if not file_metadata:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 檢查文件是否存在（使用正確的參數）
        storage = get_storage()
        try:
            exists = storage.file_exists(  # type: ignore[call-arg]
                file_id=file_id,
                task_id=getattr(file_metadata, "task_id", None),
                metadata_storage_path=getattr(file_metadata, "storage_path", None),
            )
        except TypeError:
            exists = storage.file_exists(file_id)

        if not exists:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從 ArangoDB 依 file_id 查詢 triples（relations edge + subject/object）
        # 修改時間：2026-01-02 - 使用帶 ACL 權限檢查的方法
        kg_builder = KGBuilderService()
        result = kg_builder.list_triples_by_file_id_with_acl(
            file_id=file_id, user=current_user, limit=limit, offset=offset
        )

        return APIResponse.success(
            data={
                "file_id": file_id,
                "triples": result.get("triples", []) or [],
                "total": int(result.get("total", 0) or 0),
                "limit": int(result.get("limit", limit) or limit),
                "offset": int(result.get("offset", offset) or offset),
            },
            message="三元組查詢成功",
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
        # 權限檢查（以文件權限為準）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_DELETE.value,
        )
        if not file_metadata:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        storage = get_storage()

        # 檢查文件是否存在（使用正確的參數）
        try:
            exists = storage.file_exists(  # type: ignore[call-arg]
                file_id=file_id,
                task_id=getattr(file_metadata, "task_id", None),
                metadata_storage_path=getattr(file_metadata, "storage_path", None),
            )
        except TypeError:
            exists = storage.file_exists(file_id)

        if not exists:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 1. 刪除 Qdrant 中的向量
        try:
            vector_store_service = get_qdrant_vector_store_service()
            vector_store_service.delete_vectors_by_file_id(
                file_id=file_id, user_id=current_user.user_id
            )
            logger.info("已刪除文件關聯的向量", file_id=file_id)
        except Exception as e:
            logger.warning("刪除向量失敗（繼續刪除文件）", file_id=file_id, error=str(e))

        # 2. 刪除 ArangoDB 中的知識圖譜關聯（依 file_id 移除 file_ids 關聯；必要時刪除孤立點/邊）
        try:
            kg_builder = KGBuilderService()
            cleanup = kg_builder.remove_file_associations(file_id=file_id)
            logger.info("已清理文件關聯的知識圖譜資料", file_id=file_id, **cleanup)
        except Exception as e:
            logger.warning("清理知識圖譜失敗（繼續刪除文件）", file_id=file_id, error=str(e))

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
                redis_client.delete(f"kg:chunk_state:{file_id}")
                redis_client.delete(f"kg:continue_lock:{file_id}")
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
