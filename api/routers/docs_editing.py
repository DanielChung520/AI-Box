"""
代碼功能說明: 文件編輯（Doc Edit）API - preview-first 產生 patch，Apply 才寫入（md/txt/json）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:27:19 (UTC+8)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.doc_edit_request import (
    DocEditApplyResult,
    DocEditCreateRequest,
    DocEditCreateResponse,
    DocEditPreview,
    DocEditRequestRecord,
    DocEditStateResponse,
    DocEditStatus,
)
from services.api.models.doc_generation_request import (
    DocGenApplyResult,
    DocGenCreateRequest,
    DocGenCreateResponse,
    DocGenPreview,
    DocGenRequestRecord,
    DocGenStateResponse,
    DocGenStatus,
)
from services.api.models.file_metadata import FileMetadataCreate, FileMetadataUpdate
from services.api.services.change_summary_service import get_change_summary_service
from services.api.services.doc_edit_request_store_service import get_doc_edit_request_store_service
from services.api.services.doc_generation_request_store_service import (
    get_doc_generation_request_store_service,
)
from services.api.services.incremental_reindex_service import get_incremental_reindex_service
from services.api.services.doc_patch_service import (
    PatchApplyError,
    apply_json_patch,
    apply_search_replace_patches,
    apply_unified_diff,
    detect_doc_format,
)
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import get_file_permission_service
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/docs", tags=["Docs Editing"])

_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None

_request_tasks: Dict[str, asyncio.Task[None]] = {}
_request_tasks_lock = Lock()


def get_storage() -> FileStorage:
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}
        _storage = create_storage_from_config(config)
    return _storage


def get_metadata_service() -> FileMetadataService:
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


def _register_request_task(*, request_id: str, task: asyncio.Task[None]) -> None:
    with _request_tasks_lock:
        _request_tasks[request_id] = task


def _pop_request_task(*, request_id: str) -> Optional[asyncio.Task[None]]:
    with _request_tasks_lock:
        return _request_tasks.pop(request_id, None)


def _get_request_task(*, request_id: str) -> Optional[asyncio.Task[None]]:
    with _request_tasks_lock:
        return _request_tasks.get(request_id)


def _start_preview_task(*, background_tasks: BackgroundTasks, request_id: str) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(_run_preview_request(request_id=request_id))
            _register_request_task(request_id=request_id, task=task)
            return
    except RuntimeError:
        pass

    # fallback：交給 FastAPI background task 執行
    background_tasks.add_task(_run_preview_request, request_id=request_id)


def _get_doc_version(custom_metadata: Optional[Dict[str, Any]]) -> int:
    meta = custom_metadata or {}
    raw = meta.get("doc_version")
    try:
        return int(raw) if raw is not None else 1
    except Exception:
        return 1


def _get_versions(custom_metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    meta = custom_metadata or {}
    items = meta.get("doc_versions")
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def _append_version(
    *,
    custom_metadata: Optional[Dict[str, Any]],
    version: int,
    version_file_id: str,
    storage_path: str,
    summary: str,
    request_id: str,
) -> Dict[str, Any]:
    meta = dict(custom_metadata or {})
    versions = _get_versions(meta)
    versions.append(
        {
            "version": int(version),
            "version_file_id": str(version_file_id),
            "storage_path": str(storage_path),
            "summary": str(summary or ""),
            "request_id": str(request_id),
            "created_at_ms": time.time() * 1000.0,
        }
    )
    meta["doc_versions"] = versions
    return meta


async def _run_preview_request(*, request_id: str) -> None:
    store = get_doc_edit_request_store_service()
    record = store.get(request_id=request_id)
    if record is None:
        return

    try:
        if store.is_aborted(request_id=request_id):
            store.update(request_id=request_id, status=DocEditStatus.aborted)
            return

        store.update(request_id=request_id, status=DocEditStatus.running)

        storage = get_storage()
        metadata_service = get_metadata_service()

        file_meta = metadata_service.get(record.file_id)
        if file_meta is None:
            store.update(
                request_id=request_id,
                status=DocEditStatus.failed,
                error_code="FILE_NOT_FOUND",
                error_message=f"File not found: {record.file_id}",
            )
            return

        raw = storage.read_file(
            record.file_id,
            task_id=file_meta.task_id,
            metadata_storage_path=file_meta.storage_path,
        )
        if raw is None:
            store.update(
                request_id=request_id,
                status=DocEditStatus.failed,
                error_code="FILE_READ_FAILED",
                error_message="Failed to read file content",
            )
            return

        base_text = raw.decode("utf-8", errors="replace")

        # 目前 MVP：先用簡化策略生成 patch（不指定模型，走系統預設）
        prompt = _build_patch_prompt(
            doc_format=record.doc_format,
            instruction=record.instruction,
            base_content=base_text,
        )

        patch_kind, patch_payload, summary = await _call_llm_for_patch(prompt)

        # preview 立即驗證可套用
        if patch_kind == "unified_diff":
            _ = apply_unified_diff(original=base_text, diff_text=str(patch_payload))
            preview = DocEditPreview(
                patch_kind="unified_diff",
                patch=str(patch_payload),
                summary=str(summary or ""),
            )
        elif patch_kind == "search_replace":
            # Search-and-Replace 格式
            if not isinstance(patch_payload, dict) or "patches" not in patch_payload:
                raise PatchApplyError("Invalid search_replace payload")
            patches = patch_payload.get("patches", [])
            _ = apply_search_replace_patches(
                original=base_text,
                patches=patches,
                cursor_position=None,  # TODO: 從請求中獲取游標位置
            )
            preview = DocEditPreview(
                patch_kind="search_replace",
                patch=patch_payload,
                summary=str(summary or ""),
            )
        else:
            # json_patch
            if not isinstance(patch_payload, list):
                raise PatchApplyError("Invalid json_patch payload")
            _ = apply_json_patch(
                original_json_text=base_text,
                patch_ops=[dict(x) for x in patch_payload],
            )
            preview = DocEditPreview(
                patch_kind="json_patch",
                patch=[dict(x) for x in patch_payload],
                summary=str(summary or ""),
            )

        record.preview = preview
        store.update(request_id=request_id, status=DocEditStatus.succeeded, record=record)

    except asyncio.CancelledError:
        store.set_abort(request_id=request_id)
        store.update(request_id=request_id, status=DocEditStatus.aborted)
        raise
    except PatchApplyError as exc:
        store.update(
            request_id=request_id,
            status=DocEditStatus.failed,
            error_code="PATCH_INVALID",
            error_message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        store.update(
            request_id=request_id,
            status=DocEditStatus.failed,
            error_code="DOC_EDIT_FAILED",
            error_message=str(exc),
        )
    finally:
        _pop_request_task(request_id=request_id)


def _build_patch_prompt(*, doc_format: str, instruction: str, base_content: str) -> str:
    if doc_format == "json":
        return (
            "你是一個嚴格的 JSON 編輯器。\n"
            "請根據指令，輸出 RFC6902 JSON Patch（JSON array），僅包含 op/path/value（必要時）。\n"
            "不要輸出任何解釋文字，只輸出 JSON。\n\n"
            f"指令：{instruction}\n\n"
            "base_json：\n"
            f"{base_content}\n"
        )

    # md/txt
    return (
        "你是一個嚴格的文件編輯器。\n"
        "請輸出 unified diff（單檔），以 ---/+++ 與 @@ hunk 表示變更。\n"
        "不要輸出任何解釋文字，只輸出 diff。\n\n"
        f"指令：{instruction}\n\n"
        "base_text：\n"
        f"{base_content}\n"
    )


async def _call_llm_for_patch(prompt: str) -> tuple[str, Any, str]:
    """回傳 (patch_kind, patch_payload, summary)。

    支持的格式：
    - 若回傳為 JSON array → json_patch
    - 若回傳為包含 "patches" 的 JSON 對象 → search_replace
    - 否則 → unified_diff
    """

    # 延遲 import，避免啟動成本
    from llm.moe.moe_manager import LLMMoEManager

    moe = LLMMoEManager()
    result = await moe.generate(prompt)
    content = str(result.get("content") or result.get("text") or "")
    content = content.strip()

    # 嘗試 parse JSON
    try:
        parsed = json.loads(content)
        # 檢查是否為 JSON Patch（數組格式）
        if isinstance(parsed, list):
            return "json_patch", parsed, ""
        # 檢查是否為 Search-and-Replace 格式（包含 "patches" 鍵的對象）
        if isinstance(parsed, dict) and "patches" in parsed:
            patches = parsed.get("patches", [])
            if isinstance(patches, list) and len(patches) > 0:
                # 驗證 patches 格式
                for patch in patches:
                    if not isinstance(patch, dict):
                        break
                    if "search_block" not in patch or "replace_block" not in patch:
                        break
                else:
                    # 所有 patch 格式正確
                    thought_chain = parsed.get("thought_chain", "")
                    return "search_replace", parsed, thought_chain
    except Exception:
        pass

    return "unified_diff", content, ""


@router.post("/edits", status_code=status.HTTP_202_ACCEPTED)
async def create_doc_edit(
    body: DocEditCreateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    perm = get_file_permission_service()
    file_meta = get_metadata_service().get(body.file_id)
    if file_meta is None:
        return APIResponse.error(
            message="File not found",
            error_code="FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 需要更新權限
    perm.check_file_access(
        user=current_user,
        file_id=body.file_id,
        required_permission=Permission.FILE_UPDATE.value,
    )

    # 只允許 md/txt/json
    doc_format = detect_doc_format(filename=file_meta.filename, file_type=file_meta.file_type)
    if doc_format not in {"md", "txt", "json"}:
        return APIResponse.error(
            message="Unsupported document format",
            error_code="UNSUPPORTED_FORMAT",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    current_version = _get_doc_version(file_meta.custom_metadata)
    base_version = body.base_version if body.base_version is not None else current_version
    if int(base_version) != int(current_version):
        return APIResponse.error(
            message="Base version mismatch",
            error_code="BASE_VERSION_MISMATCH",
            details={"current_version": current_version, "base_version": base_version},
            status_code=status.HTTP_409_CONFLICT,
        )

    request_id = str(uuid.uuid4())
    record = DocEditRequestRecord(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        file_id=body.file_id,
        task_id=file_meta.task_id,
        doc_format=doc_format,  # type: ignore[arg-type]
        instruction=body.instruction,
        base_version=int(base_version),
        status=DocEditStatus.queued,
    )

    store = get_doc_edit_request_store_service()
    store.create(record)

    _start_preview_task(background_tasks=background_tasks, request_id=request_id)

    payload = DocEditCreateResponse(request_id=request_id, status=DocEditStatus.queued)
    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Doc edit request created",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/edits/{request_id}", status_code=status.HTTP_200_OK)
async def get_doc_edit_state(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_doc_edit_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    payload = DocEditStateResponse(
        request_id=record.request_id,
        status=record.status,
        created_at_ms=record.created_at_ms,
        updated_at_ms=record.updated_at_ms,
        file_id=record.file_id,
        base_version=record.base_version,
        preview=record.preview,
        apply_result=record.apply_result,
        error_code=record.error_code,
        error_message=record.error_message,
    )

    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Doc edit state retrieved",
    )


@router.post("/edits/{request_id}/abort", status_code=status.HTTP_200_OK)
async def abort_doc_edit(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_doc_edit_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    store.set_abort(request_id=record.request_id)

    task = _get_request_task(request_id=record.request_id)
    if task is not None and not task.done():
        task.cancel()

    store.update(request_id=record.request_id, status=DocEditStatus.aborted)
    return APIResponse.success(
        data={"request_id": record.request_id, "status": "aborted"},
        message="Doc edit aborted",
    )


@router.post("/edits/{request_id}/apply", status_code=status.HTTP_200_OK)
@audit_log(AuditAction.FILE_UPDATE, "file")
async def apply_doc_edit(
    request_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _ = request
    store = get_doc_edit_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.status != DocEditStatus.succeeded or record.preview is None:
        return APIResponse.error(
            message="Preview is not ready",
            error_code="PREVIEW_NOT_READY",
            status_code=status.HTTP_409_CONFLICT,
        )

    perm = get_file_permission_service()
    perm.check_file_access(
        user=current_user,
        file_id=record.file_id,
        required_permission=Permission.FILE_UPDATE.value,
    )

    metadata_service = get_metadata_service()
    file_meta = metadata_service.get(record.file_id)
    if file_meta is None:
        return APIResponse.error(
            message="File not found",
            error_code="FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    current_version = _get_doc_version(file_meta.custom_metadata)
    if int(current_version) != int(record.base_version):
        return APIResponse.error(
            message="Base version mismatch",
            error_code="BASE_VERSION_MISMATCH",
            details={
                "current_version": current_version,
                "base_version": record.base_version,
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    storage = get_storage()
    raw = storage.read_file(
        record.file_id,
        task_id=file_meta.task_id,
        metadata_storage_path=file_meta.storage_path,
    )
    if raw is None:
        return APIResponse.error(
            message="Failed to read file content",
            error_code="FILE_READ_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    base_text = raw.decode("utf-8", errors="replace")

    # 先套用 patch
    try:
        if record.preview.patch_kind == "unified_diff":
            new_text = apply_unified_diff(original=base_text, diff_text=str(record.preview.patch))
        elif record.preview.patch_kind == "search_replace":
            # Search-and-Replace 格式
            if not isinstance(record.preview.patch, dict) or "patches" not in record.preview.patch:
                raise PatchApplyError("Invalid search_replace payload")
            search_replace_patches = record.preview.patch.get("patches", [])
            new_text = apply_search_replace_patches(
                original=base_text,
                patches=search_replace_patches,
                cursor_position=None,  # TODO: 從請求中獲取游標位置
            )
        else:
            # json_patch
            if not isinstance(record.preview.patch, list):
                raise PatchApplyError("Invalid json_patch payload")
            new_text = apply_json_patch(
                original_json_text=base_text,
                patch_ops=[dict(x) for x in record.preview.patch],
            )
    except PatchApplyError as exc:
        return APIResponse.error(
            message=str(exc),
            error_code="PATCH_APPLY_FAILED",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 先保存舊版本快照
    version_file_id = f"{record.file_id}__v{current_version}"
    _, version_storage_path = storage.save_file(
        base_text.encode("utf-8"),
        filename=file_meta.filename,
        file_id=version_file_id,
        task_id=file_meta.task_id,
    )

    # 覆寫原檔
    storage.save_file(
        new_text.encode("utf-8"),
        filename=file_meta.filename,
        file_id=record.file_id,
        task_id=file_meta.task_id,
    )

    # 生成變更摘要（如果 preview 中沒有摘要）
    summary = record.preview.summary or ""
    if not summary:
        try:
            change_summary_service = get_change_summary_service()
            # 提取 patches 信息（如果可用）
            summary_patches: Optional[List[Dict[str, Any]]] = None
            if record.preview.patch_kind == "search_replace" and isinstance(
                record.preview.patch, dict
            ):
                summary_patches = record.preview.patch.get("patches", [])

            summary = await change_summary_service.generate_summary(
                original_content=base_text,
                modified_content=new_text,
                patches=summary_patches,
            )
            logger.info(f"生成的變更摘要: {summary[:100]}...")
        except Exception as e:
            logger.warning(f"生成變更摘要失敗，使用默認摘要: {e}")
            # 使用默認摘要
            summary = "文檔內容已修改"

    # 更新 metadata：doc_versions + doc_version
    new_version = int(current_version) + 1
    new_meta = _append_version(
        custom_metadata=file_meta.custom_metadata,
        version=int(current_version),
        version_file_id=version_file_id,
        storage_path=version_storage_path,
        summary=summary,
        request_id=record.request_id,
    )
    new_meta["doc_version"] = new_version
    metadata_service.update(
        record.file_id,
        FileMetadataUpdate(
            custom_metadata=new_meta,
            task_id=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
            folder_id=None,  # type: ignore[call-arg]
            tags=None,  # type: ignore[call-arg]
            description=None,  # type: ignore[call-arg]
            status=None,  # type: ignore[call-arg]
            processing_status=None,  # type: ignore[call-arg]
            chunk_count=None,  # type: ignore[call-arg]
            vector_count=None,  # type: ignore[call-arg]
            kg_status=None,  # type: ignore[call-arg]
        ),
    )

    # 增量重新索引（可選，如果失敗不影響提交）
    reindexed_chunks = 0
    try:
        incremental_reindex_service = get_incremental_reindex_service()
        reindex_result = await incremental_reindex_service.reindex_modified_chunks(
            file_id=record.file_id,
            original_content=base_text,
            modified_content=new_text,
            user_id=current_user.user_id,
        )
        reindexed_chunks = reindex_result.get("reindexed_chunks", 0)
        logger.info(
            "增量重新索引完成",
            file_id=record.file_id,
            reindexed_chunks=reindexed_chunks,
        )
    except Exception as e:
        # 重新索引失敗不影響提交，只記錄警告
        logger.warning(f"增量重新索引失敗，但不影響提交: {e}", exc_info=True)

    record.apply_result = DocEditApplyResult(new_version=new_version)
    store.update(request_id=record.request_id, status=DocEditStatus.applied, record=record)

    return APIResponse.success(
        data={
            "request_id": record.request_id,
            "file_id": record.file_id,
            "status": "applied",
            "new_version": new_version,
            "reindexed_chunks": reindexed_chunks,
        },
        message="Doc edit applied",
    )


@router.get("/files/{file_id}/versions", status_code=status.HTTP_200_OK)
async def list_doc_versions(
    file_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _ = tenant_id
    perm = get_file_permission_service()
    perm.check_file_access(
        user=current_user,
        file_id=file_id,
        required_permission=Permission.FILE_READ.value,
    )

    meta = get_metadata_service().get(file_id)
    if meta is None:
        return APIResponse.error(
            message="File not found",
            error_code="FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return APIResponse.success(
        data={
            "file_id": file_id,
            "doc_version": _get_doc_version(meta.custom_metadata),
            "versions": _get_versions(meta.custom_metadata),
        },
        message="Doc versions retrieved",
    )


@router.post("/files/{file_id}/rollback", status_code=status.HTTP_200_OK)
@audit_log(AuditAction.FILE_UPDATE, "file")
async def rollback_doc_version(
    file_id: str,
    to_version: int,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _ = request
    _ = tenant_id
    perm = get_file_permission_service()
    perm.check_file_access(
        user=current_user,
        file_id=file_id,
        required_permission=Permission.FILE_UPDATE.value,
    )

    metadata_service = get_metadata_service()
    meta = metadata_service.get(file_id)
    if meta is None:
        return APIResponse.error(
            message="File not found",
            error_code="FILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    versions = _get_versions(meta.custom_metadata)
    target = next(
        (v for v in versions if v.get("version") and int(v.get("version")) == int(to_version or 0)), None  # type: ignore[arg-type]  # v.get("version") 可能為 None
    )
    if target is None:
        return APIResponse.error(
            message="Version not found",
            error_code="VERSION_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    version_file_id = str(target.get("version_file_id") or "")
    version_storage_path = str(target.get("storage_path") or "")
    if not version_file_id:
        return APIResponse.error(
            message="Invalid version record",
            error_code="VERSION_RECORD_INVALID",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    storage = get_storage()
    raw = storage.read_file(
        version_file_id,
        task_id=meta.task_id,
        metadata_storage_path=version_storage_path or None,
    )
    if raw is None:
        return APIResponse.error(
            message="Failed to read version content",
            error_code="VERSION_READ_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # rollback 視為一次新的寫入：先保存當前版本
    current_version = _get_doc_version(meta.custom_metadata)
    snapshot_file_id = f"{file_id}__v{current_version}"
    current_raw = storage.read_file(
        file_id, task_id=meta.task_id, metadata_storage_path=meta.storage_path
    )
    if current_raw is not None:
        _, snapshot_path = storage.save_file(
            current_raw,
            filename=meta.filename,
            file_id=snapshot_file_id,
            task_id=meta.task_id,
        )
        new_meta = _append_version(
            custom_metadata=meta.custom_metadata,
            version=int(current_version),
            version_file_id=snapshot_file_id,
            storage_path=snapshot_path,
            summary=f"rollback_snapshot_to_v{to_version}",
            request_id=str(uuid.uuid4()),
        )
    else:
        new_meta = dict(meta.custom_metadata or {})

    # 覆寫回指定版本內容
    storage.save_file(
        raw,
        filename=meta.filename,
        file_id=file_id,
        task_id=meta.task_id,
    )

    new_meta["doc_version"] = int(current_version) + 1
    metadata_service.update(
        file_id,
        FileMetadataUpdate(
            custom_metadata=new_meta,
            task_id=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
            folder_id=None,  # type: ignore[call-arg]
            tags=None,  # type: ignore[call-arg]
            description=None,  # type: ignore[call-arg]
            status=None,  # type: ignore[call-arg]
            processing_status=None,  # type: ignore[call-arg]
            chunk_count=None,  # type: ignore[call-arg]
            vector_count=None,  # type: ignore[call-arg]
            kg_status=None,  # type: ignore[call-arg]
        ),
    )

    return APIResponse.success(
        data={
            "file_id": file_id,
            "rolled_back_to": int(to_version),
            "new_version": int(current_version) + 1,
        },
        message="Rollback completed",
    )


def _build_generation_prompt(*, doc_format: str, instruction: str, filename: str) -> str:
    if doc_format == "json":
        return (
            "你是一個嚴格的 JSON 文件產生器。\n"
            "請根據指令產生一份 JSON 文件內容（必須是有效 JSON）。\n"
            "不要輸出任何解釋文字，只輸出 JSON。\n\n"
            f"檔名：{filename}\n"
            f"指令：{instruction}\n"
        )
    if doc_format == "md":
        return (
            "你是一個嚴格的 Markdown 文件產生器。\n"
            "請根據指令產生 Markdown 文件。\n"
            "不要輸出任何解釋文字，只輸出文件內容。\n\n"
            f"檔名：{filename}\n"
            f"指令：{instruction}\n"
        )
    return (
        "你是一個嚴格的文字文件產生器。\n"
        "請根據指令產生文字文件。\n"
        "不要輸出任何解釋文字，只輸出文件內容。\n\n"
        f"檔名：{filename}\n"
        f"指令：{instruction}\n"
    )


async def _call_llm_for_generation(prompt: str) -> str:
    from llm.moe.moe_manager import LLMMoEManager

    moe = LLMMoEManager()
    result = await moe.generate(prompt)
    content = str(result.get("content") or result.get("text") or "")
    return content.strip()


async def _run_generation_request(*, request_id: str) -> None:
    store = get_doc_generation_request_store_service()
    record = store.get(request_id=request_id)
    if record is None:
        return

    try:
        if store.is_aborted(request_id=request_id):
            store.update(request_id=request_id, status=DocGenStatus.aborted)
            return

        store.update(request_id=request_id, status=DocGenStatus.running)

        prompt = _build_generation_prompt(
            doc_format=record.doc_format,
            instruction=record.instruction,
            filename=record.filename,
        )
        content = await _call_llm_for_generation(prompt)

        if record.doc_format == "json":
            # validate JSON
            json.loads(content)

        record.preview = DocGenPreview(content=content)
        store.update(request_id=request_id, status=DocGenStatus.succeeded, record=record)
    except asyncio.CancelledError:
        store.set_abort(request_id=request_id)
        store.update(request_id=request_id, status=DocGenStatus.aborted)
        raise
    except Exception as exc:  # noqa: BLE001
        store.update(
            request_id=request_id,
            status=DocGenStatus.failed,
            error_code="DOC_GEN_FAILED",
            error_message=str(exc),
        )
    finally:
        _pop_request_task(request_id=request_id)


def _start_generation_task(*, background_tasks: BackgroundTasks, request_id: str) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(_run_generation_request(request_id=request_id))
            _register_request_task(request_id=request_id, task=task)
            return
    except RuntimeError:
        pass
    background_tasks.add_task(_run_generation_request, request_id=request_id)


@router.post("/generations", status_code=status.HTTP_202_ACCEPTED)
async def create_doc_generation(
    body: DocGenCreateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    perm = get_file_permission_service()
    perm.check_upload_permission(current_user)
    if not perm.check_task_file_access(
        user=current_user,
        task_id=body.task_id,
        required_permission=Permission.FILE_UPLOAD.value,
    ):
        return APIResponse.error(
            message="Task access denied",
            error_code="TASK_ACCESS_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    request_id = str(uuid.uuid4())
    record = DocGenRequestRecord(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        task_id=body.task_id,
        filename=body.filename,
        doc_format=body.doc_format,
        instruction=body.instruction,
        status=DocGenStatus.queued,
    )
    store = get_doc_generation_request_store_service()
    store.create(record)

    _start_generation_task(background_tasks=background_tasks, request_id=request_id)

    payload = DocGenCreateResponse(request_id=request_id, status=DocGenStatus.queued)
    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Doc generation request created",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/generations/{request_id}", status_code=status.HTTP_200_OK)
async def get_doc_generation_state(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_doc_generation_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    payload = DocGenStateResponse(
        request_id=record.request_id,
        status=record.status,
        created_at_ms=record.created_at_ms,
        updated_at_ms=record.updated_at_ms,
        task_id=record.task_id,
        filename=record.filename,
        doc_format=record.doc_format,
        preview=record.preview,
        apply_result=record.apply_result,
        error_code=record.error_code,
        error_message=record.error_message,
    )
    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Doc generation state retrieved",
    )


@router.post("/generations/{request_id}/abort", status_code=status.HTTP_200_OK)
async def abort_doc_generation(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_doc_generation_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    store.set_abort(request_id=record.request_id)

    task = _get_request_task(request_id=record.request_id)
    if task is not None and not task.done():
        task.cancel()

    store.update(request_id=record.request_id, status=DocGenStatus.aborted)
    return APIResponse.success(
        data={"request_id": record.request_id, "status": "aborted"},
        message="Doc generation aborted",
    )


@router.post("/generations/{request_id}/apply", status_code=status.HTTP_200_OK)
@audit_log(AuditAction.FILE_CREATE, "file")
async def apply_doc_generation(
    request_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _ = request
    store = get_doc_generation_request_store_service()
    record = store.get(request_id=str(request_id))
    if (
        record is None
        or record.user_id != current_user.user_id
        or str(record.tenant_id) != str(tenant_id)
    ):
        return APIResponse.error(
            message="Request not found",
            error_code="REQUEST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.status != DocGenStatus.succeeded or record.preview is None:
        return APIResponse.error(
            message="Preview is not ready",
            error_code="PREVIEW_NOT_READY",
            status_code=status.HTTP_409_CONFLICT,
        )

    perm = get_file_permission_service()
    perm.check_upload_permission(current_user)
    if not perm.check_task_file_access(
        user=current_user,
        task_id=record.task_id,
        required_permission=Permission.FILE_UPLOAD.value,
    ):
        return APIResponse.error(
            message="Task access denied",
            error_code="TASK_ACCESS_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    storage = get_storage()
    content_bytes = record.preview.content.encode("utf-8")
    file_id, storage_path = storage.save_file(
        content_bytes,
        filename=record.filename,
        task_id=record.task_id,
    )

    file_type = (
        "application/json"
        if record.doc_format == "json"
        else ("text/markdown" if record.doc_format == "md" else "text/plain")
    )

    meta_create = FileMetadataCreate(
        file_id=file_id,
        filename=record.filename,
        file_type=file_type,
        file_size=len(content_bytes),
        user_id=current_user.user_id,
        task_id=record.task_id,
        folder_id=None,
        storage_path=storage_path,
        tags=[],
        description=None,
        custom_metadata={"doc_version": 1, "doc_versions": []},
        status="generated",
        processing_status=None,
        chunk_count=None,
        vector_count=None,
        kg_status=None,
    )

    get_metadata_service().create(meta_create)

    record.apply_result = DocGenApplyResult(file_id=file_id)
    store.update(request_id=record.request_id, status=DocGenStatus.applied, record=record)

    return APIResponse.success(
        data={"request_id": record.request_id, "status": "applied", "file_id": file_id},
        message="Doc generated",
    )
