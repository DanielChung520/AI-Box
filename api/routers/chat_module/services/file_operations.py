"""
代碼功能說明: 文件操作服務（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

提取自 chat.py 的文件創建和編輯相關邏輯。
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from api.routers.chat_module.dependencies import (
    get_arango_client,
    get_file_permission_service,
    get_metadata_service,
    get_storage,
)
from api.routers.chat_module.utils.file_detection import (
    looks_like_create_file_intent,
    looks_like_edit_file_intent,
)
from api.routers.chat_module.utils.file_parsing import (
    default_filename_for_intent,
    file_type_for_filename,
    parse_file_reference,
    parse_target_path,
)
from services.api.models.doc_edit_request import DocEditRequestRecord, DocEditStatus
from services.api.models.file_metadata import FileMetadataCreate
from services.api.services.doc_edit_request_store_service import get_doc_edit_request_store_service
from services.api.services.doc_patch_service import detect_doc_format
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

_FOLDER_COLLECTION_NAME = "folder_metadata"


def find_file_by_name(
    *,
    filename: str,
    task_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    根據檔名查找檔案（後端正式檔案）。
    返回檔案元數據，包含 file_id。

    Args:
        filename: 檔名
        task_id: 任務 ID
        user_id: 用戶 ID

    Returns:
        檔案信息字典，如果未找到則返回 None
    """
    metadata_service = get_metadata_service()
    # 查詢該 task 下的檔案
    files = metadata_service.list(
        task_id=task_id,
        user_id=user_id,
        limit=100,
    )
    # 查找匹配的檔名（精確匹配）
    for file_meta in files:
        if file_meta.filename == filename:
            return {
                "file_id": file_meta.file_id,
                "filename": file_meta.filename,
                "is_draft": False,
            }
    return None


def ensure_folder_path(
    *,
    task_id: str,
    user_id: str,
    folder_path: str,
) -> Optional[str]:
    """
    確保 folder_path（例如 a/b/c）存在於 folder_metadata。
    回傳最深層 folder_id（用於 file_metadata.folder_id）。

    注意：folder_metadata 是 UI/查詢用的「邏輯資料夾」，檔案實體仍在 task workspace 根目錄。

    Args:
        task_id: 任務 ID
        user_id: 用戶 ID
        folder_path: 資料夾路徑（例如 "a/b/c"）

    Returns:
        最深層 folder_id，如果失敗則返回 None
    """
    folder_path = (folder_path or "").strip().strip("/")
    if not folder_path:
        return None

    client = get_arango_client()
    if client.db is None or client.db.aql is None:
        return None

    # 確保集合存在
    if not client.db.has_collection(_FOLDER_COLLECTION_NAME):
        client.db.create_collection(_FOLDER_COLLECTION_NAME)
        col = client.db.collection(_FOLDER_COLLECTION_NAME)
        col.add_index({"type": "persistent", "fields": ["task_id"]})
        col.add_index({"type": "persistent", "fields": ["user_id"]})

    parent_task_id: str = f"{task_id}_workspace"
    folder_id: Optional[str] = None

    for seg in [p for p in folder_path.split("/") if p]:
        # 查詢是否已存在同名資料夾（同一 parent 下）
        query = f"""
            FOR folder IN {_FOLDER_COLLECTION_NAME}
                FILTER folder.task_id == @task_id
                FILTER folder.user_id == @user_id
                FILTER folder.parent_task_id == @parent_task_id
                FILTER folder.folder_name == @folder_name
                LIMIT 1
                RETURN folder
        """
        cursor = client.db.aql.execute(
            query,
            bind_vars={
                "task_id": task_id,
                "user_id": user_id,
                "parent_task_id": parent_task_id,
                "folder_name": seg,
            },
        )
        existing = next(cursor, None) if cursor else None  # type: ignore[arg-type]
        if existing and isinstance(existing, dict) and existing.get("_key"):
            folder_id = str(existing["_key"])
            parent_task_id = folder_id
            continue

        # 建立新資料夾
        new_id = str(uuid.uuid4())
        now_iso = datetime.utcnow().isoformat()
        doc = {
            "_key": new_id,
            "task_id": task_id,
            "folder_name": seg,
            "user_id": user_id,
            "parent_task_id": parent_task_id,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        client.db.collection(_FOLDER_COLLECTION_NAME).insert(doc)
        folder_id = new_id
        parent_task_id = new_id

    return folder_id


def try_create_file_from_chat_output(
    *,
    user_text: str,
    assistant_text: str,
    task_id: Optional[str],
    current_user: User,
    force_create: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    若 user_text 呈現建檔意圖，將 assistant_text 寫入 task workspace（預設根目錄）。
    若指定目錄（如 docs/a.md），則建立對應邏輯資料夾（folder_metadata）並將 file_metadata.folder_id 指向該資料夾。

    Args:
        user_text: 用戶輸入文本
        assistant_text: AI 生成的文本內容
        task_id: 任務 ID
        current_user: 當前用戶
        force_create: 如果為 True，強制創建文件（不依賴關鍵詞匹配），用於 Task Analyzer 識別出的文檔創建意圖

    Returns:
        文件創建結果字典，如果未創建則返回 None
    """
    logger.info(
        f"try_create_file_start: task_id={task_id}, "
        f"user_id={current_user.user_id if current_user else None}, "
        f"user_text={user_text[:200]}, "
        f"assistant_text_length={len(assistant_text)}, "
        f"force_create={force_create}"
    )

    if not task_id:
        logger.warning(
            f"try_create_file_no_task_id: user_text={user_text[:200]}, "
            f"note=task_id is None, cannot create file"
        )
        return None

    # 如果 force_create=True，跳過關鍵詞匹配（用於 Task Analyzer 語義分析識別的意圖）
    if not force_create:
        if not looks_like_create_file_intent(user_text):
            logger.info(
                f"try_create_file_no_intent_match: task_id={task_id}, "
                f"user_text={user_text[:200]}, note=does not look like create file intent"
            )
            return None

    folder_path, filename = parse_target_path(user_text)
    logger.info(
        f"try_create_file_parsed_path: task_id={task_id}, "
        f"folder_path={folder_path}, filename={filename}, user_text={user_text[:200]}"
    )

    if not filename:
        filename = default_filename_for_intent(user_text)
        logger.info(
            f"try_create_file_using_default_filename: task_id={task_id}, "
            f"default_filename={filename}, user_text={user_text[:200]}"
        )

    # 只允許 md/txt/json
    ext = Path(filename).suffix.lower()
    logger.info(
        f"try_create_file_checking_extension: task_id={task_id}, "
        f"filename={filename}, extension={ext}"
    )

    if ext not in (".md", ".txt", ".json"):
        logger.warning(
            f"try_create_file_invalid_extension: task_id={task_id}, "
            f"filename={filename}, extension={ext}, note=only .md, .txt, .json are allowed"
        )
        return None

    # 權限：需要能在 task 下新增/更新檔案
    try:
        perm = get_file_permission_service()
        perm.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_UPDATE.value,
        )
        perm.check_upload_permission(user=current_user)
        logger.info(
            f"try_create_file_permission_check_passed: task_id={task_id}, filename={filename}"
        )
    except Exception as perm_error:
        logger.error(
            f"try_create_file_permission_check_failed: task_id={task_id}, "
            f"filename={filename}, error={str(perm_error)}",
            exc_info=True,
        )
        return None

    folder_id = None
    if folder_path:
        try:
            folder_id = ensure_folder_path(
                task_id=task_id,
                user_id=current_user.user_id,
                folder_path=folder_path,
            )
            logger.info(
                f"try_create_file_folder_ensured: task_id={task_id}, "
                f"folder_path={folder_path}, folder_id={folder_id}"
            )
        except Exception as folder_error:
            logger.error(
                f"try_create_file_folder_creation_failed: task_id={task_id}, "
                f"folder_path={folder_path}, error={str(folder_error)}",
                exc_info=True,
            )
            return None

    try:
        content_bytes = (assistant_text or "").rstrip("\n").encode("utf-8") + b"\n"
        storage = get_storage()
        file_id, storage_path = storage.save_file(
            file_content=content_bytes,
            filename=filename,
            task_id=task_id,
        )
        logger.info(
            f"try_create_file_storage_saved: task_id={task_id}, "
            f"filename={filename}, file_id={file_id}, storage_path={storage_path}, "
            f"content_size={len(content_bytes)}"
        )
    except Exception as storage_error:
        logger.error(
            f"try_create_file_storage_save_failed: task_id={task_id}, "
            f"filename={filename}, error={str(storage_error)}",
            exc_info=True,
        )
        return None

    try:
        metadata_service = get_metadata_service()
        metadata_service.create(
            FileMetadataCreate(
                file_id=file_id,
                filename=filename,
                file_type=file_type_for_filename(filename),
                file_size=len(content_bytes),
                processing_status=None,  # type: ignore[call-arg]
                chunk_count=None,  # type: ignore[call-arg]
                vector_count=None,  # type: ignore[call-arg]
                kg_status=None,  # type: ignore[call-arg]
                user_id=current_user.user_id,
                task_id=task_id,
                folder_id=folder_id,
                storage_path=storage_path,
                tags=["genai", "chat"],
                description="Created from chat intent",
                status="generated",
            )
        )
        logger.info(
            f"try_create_file_metadata_created: task_id={task_id}, "
            f"filename={filename}, file_id={file_id}"
        )
    except Exception as metadata_error:
        logger.error(
            f"try_create_file_metadata_creation_failed: task_id={task_id}, "
            f"filename={filename}, file_id={file_id}, error={str(metadata_error)}",
            exc_info=True,
        )
        # 即使 metadata 創建失敗，也返回文件創建結果（因為文件已經保存）
        # 但記錄錯誤以便後續修復

    result = {
        "type": "file_created",
        "file_id": file_id,
        "filename": filename,
        "task_id": task_id,
        "folder_id": folder_id,
        "folder_path": folder_path,
    }

    logger.info(
        f"try_create_file_success: task_id={task_id}, "
        f"filename={filename}, file_id={file_id}, result={result}"
    )

    return result


def try_edit_file_from_chat_output(
    *,
    user_text: str,
    assistant_text: str,
    task_id: Optional[str],
    current_user: User,
    tenant_id: str,
) -> Optional[Dict[str, Any]]:
    """
    若 user_text 呈現編輯檔案意圖，創建編輯請求並返回預覽。

    流程：
    1. 檢測編輯意圖
    2. 解析檔案引用
    3. 查找檔案（後端）
    4. 創建編輯請求（調用 docs_editing API）
    5. 返回預覽和 request_id

    Args:
        user_text: 用戶輸入文本
        assistant_text: AI 生成的文本內容
        task_id: 任務 ID
        current_user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        編輯請求結果字典，如果未創建則返回 None
    """
    if not task_id:
        return None
    if not looks_like_edit_file_intent(user_text):
        return None

    filename = parse_file_reference(user_text)
    if not filename:
        return None

    # 查找檔案（只查找後端正式檔案，草稿檔由前端處理）
    file_info = find_file_by_name(
        filename=filename,
        task_id=task_id,
        user_id=current_user.user_id,
    )
    if not file_info:
        # 檔案不存在，返回 None（前端可以處理草稿檔）
        return None

    # 權限檢查
    perm = get_file_permission_service()
    try:
        perm.check_file_access(
            user=current_user,
            file_id=file_info["file_id"],
            required_permission=Permission.FILE_UPDATE.value,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"genai_chat_file_edit_permission_denied: error={str(exc)}, "
            f"file_id={file_info['file_id']}, user_id={current_user.user_id}"
        )
        return None

    # 獲取檔案元數據
    metadata_service = get_metadata_service()
    file_meta = metadata_service.get(file_info["file_id"])
    if file_meta is None:
        return None

    # 檢測文件格式
    doc_format = detect_doc_format(filename=file_meta.filename, file_type=file_meta.file_type)
    if doc_format not in {"md", "txt", "json"}:
        return None

    # 獲取當前版本
    from api.routers.docs_editing import _get_doc_version

    current_version = _get_doc_version(file_meta.custom_metadata)

    # 創建編輯請求
    # 使用 assistant_text 作為編輯指令（簡化處理：將 AI 回復作為「替換整個檔案」的指令）
    # 實際應用中，可以讓 LLM 生成更精確的編輯指令
    instruction = f"根據以下內容更新檔案：\n\n{assistant_text}"

    request_id = str(uuid.uuid4())
    record = DocEditRequestRecord(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        file_id=file_info["file_id"],
        task_id=task_id,
        doc_format=doc_format,  # type: ignore[arg-type]
        instruction=instruction,
        base_version=int(current_version),
        status=DocEditStatus.queued,
    )

    store = get_doc_edit_request_store_service()
    store.create(record)

    # 啟動預覽任務（使用 asyncio.create_task）
    try:
        from api.routers.docs_editing import _run_preview_request, _register_request_task

        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(_run_preview_request(request_id=request_id))
            # 註冊任務（如果需要追蹤）
            _register_request_task(request_id=request_id, task=task)
        else:
            # 如果沒有運行中的 loop，使用 run_until_complete（不應該發生）
            logger.warning(
                f"genai_chat_file_edit_no_event_loop: request_id={request_id}, "
                f"file_id={file_info['file_id']}"
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"genai_chat_file_edit_start_preview_failed: error={str(exc)}, "
            f"request_id={request_id}, file_id={file_info['file_id']}"
        )

    return {
        "type": "file_edited",
        "file_id": file_info["file_id"],
        "filename": filename,
        "request_id": request_id,
        "task_id": task_id,
        "is_draft": False,
    }
