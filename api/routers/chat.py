"""
代碼功能說明: 產品級 Chat API 路由（/api/v1/chat），串接 MoE Auto/Manual/Favorite 與最小觀測欄位
創建日期: 2025-12-13 17:28:02 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-01-27
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agents.task_analyzer.classifier import TaskClassifier
from agents.task_analyzer.models import LLMProvider
from api.core.response import APIResponse
from database.arangodb import ArangoDBClient
from genai.workflows.context.manager import ContextManager
from llm.moe.moe_manager import LLMMoEManager
from services.api.models.chat import ChatRequest, ChatResponse, ObservabilityInfo, RoutingInfo
from services.api.models.doc_edit_request import DocEditRequestRecord, DocEditStatus
from services.api.models.file_metadata import FileMetadataCreate
from services.api.models.genai_request import (
    GenAIChatRequestCreateResponse,
    GenAIChatRequestRecord,
    GenAIChatRequestStateResponse,
    GenAIRequestStatus,
)
from services.api.services.chat_memory_service import get_chat_memory_service
from services.api.services.data_consent_service import get_consent_service
from services.api.services.doc_edit_request_store_service import get_doc_edit_request_store_service
from services.api.services.doc_patch_service import detect_doc_format
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import FilePermissionService
from services.api.services.genai_chat_request_store_service import (
    get_genai_chat_request_store_service,
)
from services.api.services.genai_config_resolver_service import get_genai_config_resolver_service
from services.api.services.genai_metrics_service import get_genai_metrics_service
from services.api.services.genai_model_registry_service import get_genai_model_registry_service
from services.api.services.genai_policy_gate_service import get_genai_policy_gate_service
from services.api.services.genai_trace_store_service import (
    GenAITraceEvent,
    get_genai_trace_store_service,
)
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

_moe_manager: Optional[LLMMoEManager] = None
_task_classifier: Optional[TaskClassifier] = None
_context_manager: Optional[ContextManager] = None
_file_permission_service: Optional[FilePermissionService] = None
_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None
_arango_client: Optional[ArangoDBClient] = None
_request_tasks: Dict[str, asyncio.Task[None]] = {}
_request_tasks_lock = Lock()

# hybrid MVP：收藏模型先以 localStorage 可用為主；後端提供 Redis 優先、fallback memory 的同步接口
_favorite_models_by_user: Dict[str, List[str]] = {}


def get_moe_manager() -> LLMMoEManager:
    global _moe_manager
    if _moe_manager is None:
        _moe_manager = LLMMoEManager()
    return _moe_manager


def get_task_classifier() -> TaskClassifier:
    global _task_classifier
    if _task_classifier is None:
        _task_classifier = TaskClassifier()
    return _task_classifier


def get_context_manager() -> ContextManager:
    """
    Context 單例入口（G3）。

    - recorder: Redis 優先、memory fallback（由 ContextRecorder 內部處理）
    - window: ContextWindow（由 ContextManager 內部處理）
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


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


def get_arango_client() -> ArangoDBClient:
    global _arango_client
    if _arango_client is None:
        _arango_client = ArangoDBClient()
    return _arango_client


def get_file_permission_service() -> FilePermissionService:
    global _file_permission_service
    if _file_permission_service is None:
        _file_permission_service = FilePermissionService()
    return _file_permission_service


_FOLDER_COLLECTION_NAME = "folder_metadata"


def _looks_like_create_file_intent(text: str) -> bool:
    """
    Chat 輸入框：判斷是否有「新增/輸出成檔案」意圖（MVP 以 heuristic 為主）。
    """
    t = (text or "").strip()
    if not t:
        return False

    # 明確要求：新增檔案 / 建立檔案 / 產生檔案 / 另存等
    keywords = [
        "新增檔案",
        "建立檔案",
        "產生檔案",
        "生成檔案",
        "輸出成檔案",
        "輸出成文件",
        "寫成檔案",
        "寫成文件",
        "保存成",
        "存成",
        "另存",
    ]
    if any(k in t for k in keywords):
        return True

    # 隱含意圖：整理以上對話（通常是要生成文件）
    implicit = [
        "幫我整理以上對話",
        "整理以上對話",
        "整理這段對話",
        "整理對話",
        "整理成文件",
        "整理成檔案",
    ]
    if any(k in t for k in implicit):
        return True

    # 出現明確檔名（含副檔名）也視為建檔意圖
    if re.search(r"[A-Za-z0-9_\-\u4e00-\u9fff/]+\.(md|txt|json)\b", t):
        return True

    return False


def _parse_target_path(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    從 user text 嘗試解析出 "dir/file.ext"；只支援 md/txt/json。
    回傳 (folder_path, filename)；folder_path 以 "a/b" 形式（不含末尾 /）。
    """
    t = (text or "").strip()
    matches = re.findall(
        r"([A-Za-z0-9_\-\u4e00-\u9fff/]+\.(?:md|txt|json))\b",
        t,
    )
    if matches:
        raw_path = matches[-1].lstrip("/").strip()
        parts = [p for p in raw_path.split("/") if p]
        if not parts:
            return None, None
        if len(parts) == 1:
            return None, parts[0]
        return "/".join(parts[:-1]), parts[-1]

    # 只有指定目錄但未指定檔名（例如：放到 docs 目錄）
    m = re.search(r"在\s*([A-Za-z0-9_\-\u4e00-\u9fff/]+)\s*目錄", t)
    if m:
        folder = m.group(1).strip().strip("/").strip()
        return folder or None, None

    return None, None


def _default_filename_for_intent(text: str) -> str:
    t = (text or "").strip()
    if "整理" in t and "對話" in t:
        return "conversation-summary.md"
    return "ai-output.md"


def _file_type_for_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".md":
        return "text/markdown"
    if ext == ".txt":
        return "text/plain"
    if ext == ".json":
        return "application/json"
    return "text/plain"


def _looks_like_edit_file_intent(text: str) -> bool:
    """
    檢測是否為編輯檔案意圖。
    模式：
    - "幫我修改 @xxx.md"
    - "在 @xxx.md 中增加"
    - "編輯 @xxx.md"
    - "更新 @xxx.md"
    - "幫我在 @xxx.md 增加一些文字"
    """
    t = (text or "").strip()
    if not t:
        return False

    # 檢測 @filename 模式
    if re.search(r"@[A-Za-z0-9_\-\u4e00-\u9fff/]+\.(md|txt|json)\b", t):
        # 配合編輯關鍵詞
        edit_keywords = [
            "修改",
            "編輯",
            "更新",
            "增加",
            "添加",
            "刪除",
            "移除",
            "幫我",
            "請",
            "在",
            "中",
            "裡",
        ]
        if any(k in t for k in edit_keywords):
            return True

    return False


def _parse_file_reference(text: str) -> Optional[str]:
    """
    從文本中提取檔案引用（@filename）。
    返回檔名（不含 @ 符號）。
    """
    t = (text or "").strip()
    # 匹配 @filename.ext 模式
    match = re.search(r"@([A-Za-z0-9_\-\u4e00-\u9fff/]+\.(?:md|txt|json))\b", t)
    if match:
        return match.group(1)
    return None


def _find_file_by_name(
    *,
    filename: str,
    task_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """
    根據檔名查找檔案（後端正式檔案）。
    返回檔案元數據，包含 file_id。
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


def _try_edit_file_from_chat_output(
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
    """
    if not task_id:
        return None
    if not _looks_like_edit_file_intent(user_text):
        return None

    filename = _parse_file_reference(user_text)
    if not filename:
        return None

    # 查找檔案（只查找後端正式檔案，草稿檔由前端處理）
    file_info = _find_file_by_name(
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
            "genai_chat_file_edit_permission_denied",
            error=str(exc),
            file_id=file_info["file_id"],
            user_id=current_user.user_id,
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
        from api.routers.docs_editing import _run_preview_request

        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(_run_preview_request(request_id=request_id))
            # 註冊任務（如果需要追蹤）
            from api.routers.docs_editing import _register_request_task

            _register_request_task(request_id=request_id, task=task)
        else:
            # 如果沒有運行中的 loop，使用 run_until_complete（不應該發生）
            logger.warning(
                "genai_chat_file_edit_no_event_loop",
                request_id=request_id,
                file_id=file_info["file_id"],
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "genai_chat_file_edit_start_preview_failed",
            error=str(exc),
            request_id=request_id,
            file_id=file_info["file_id"],
        )

    return {
        "type": "file_edited",
        "file_id": file_info["file_id"],
        "filename": filename,
        "request_id": request_id,
        "task_id": task_id,
        "is_draft": False,
    }


def _ensure_folder_path(
    *,
    task_id: str,
    user_id: str,
    folder_path: str,
) -> Optional[str]:
    """
    確保 folder_path（例如 a/b/c）存在於 folder_metadata。
    回傳最深層 folder_id（用於 file_metadata.folder_id）。

    注意：folder_metadata 是 UI/查詢用的「邏輯資料夾」，檔案實體仍在 task workspace 根目錄。
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
        existing = next(cursor, None) if cursor else None  # type: ignore[arg-type]  # cursor 可能為 None
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


def _try_create_file_from_chat_output(
    *,
    user_text: str,
    assistant_text: str,
    task_id: Optional[str],
    current_user: User,
) -> Optional[Dict[str, Any]]:
    """
    若 user_text 呈現建檔意圖，將 assistant_text 寫入 task workspace（預設根目錄）。
    若指定目錄（如 docs/a.md），則建立對應邏輯資料夾（folder_metadata）並將 file_metadata.folder_id 指向該資料夾。
    """
    if not task_id:
        return None
    if not _looks_like_create_file_intent(user_text):
        return None

    folder_path, filename = _parse_target_path(user_text)
    if not filename:
        filename = _default_filename_for_intent(user_text)

    # 只允許 md/txt/json
    ext = Path(filename).suffix.lower()
    if ext not in (".md", ".txt", ".json"):
        return None

    # 權限：需要能在 task 下新增/更新檔案
    perm = get_file_permission_service()
    perm.check_task_file_access(
        user=current_user,
        task_id=task_id,
        required_permission=Permission.FILE_UPDATE.value,
    )
    perm.check_upload_permission(user=current_user)

    folder_id = None
    if folder_path:
        folder_id = _ensure_folder_path(
            task_id=task_id,
            user_id=current_user.user_id,
            folder_path=folder_path,
        )

    content_bytes = (assistant_text or "").rstrip("\n").encode("utf-8") + b"\n"
    storage = get_storage()
    file_id, storage_path = storage.save_file(
        file_content=content_bytes,
        filename=filename,
        task_id=task_id,
    )

    metadata_service = get_metadata_service()
    metadata_service.create(
        FileMetadataCreate(
            file_id=file_id,
            filename=filename,
            file_type=_file_type_for_filename(filename),
            file_size=len(content_bytes),
            processing_status=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
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

    return {
        "type": "file_created",
        "file_id": file_id,
        "filename": filename,
        "task_id": task_id,
        "folder_id": folder_id,
        "folder_path": folder_path,
    }


def _record_if_changed(
    *,
    context_manager: ContextManager,
    session_id: str,
    role: str,
    content: str,
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    防止前端重送 history 造成重複記錄：
    若最後一筆（role, content）相同，則跳過寫入。
    """
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return False

    try:
        last_messages = context_manager.get_messages(session_id=session_id, limit=1)
        if last_messages:
            last = last_messages[-1]
            if str(last.role) == role and str(last.content).strip() == normalized_content:
                return False
    except Exception:  # noqa: BLE001
        # 取最後消息失敗時不阻擋寫入
        pass

    return context_manager.record_message(
        session_id=session_id,
        role=role,
        content=normalized_content,
        agent_name=agent_name,
        metadata=metadata,
    )


def _infer_provider_from_model_id(model_id: str) -> LLMProvider:
    """以約定優先的 heuristic 推導 provider（MVP）。"""
    m = model_id.lower()

    # 具備 ollama 常見標記（本地模型或帶 tag）
    if ":" in m or m in {"llama2", "gpt-oss:20b", "qwen3-coder:30b"}:
        return LLMProvider.OLLAMA

    if m.startswith("gpt-") or m.startswith("openai") or "gpt" in m:
        return LLMProvider.CHATGPT
    if m.startswith("gemini"):
        return LLMProvider.GEMINI
    if m.startswith("grok"):
        return LLMProvider.GROK
    if m.startswith("qwen"):
        # qwen-turbo / qwen-plus 等雲端 provider
        return LLMProvider.QWEN

    # fallback：盡量不阻擋（預設本地）
    return LLMProvider.OLLAMA


def _extract_content(result: Dict[str, Any]) -> str:
    return str(result.get("content") or result.get("message") or result.get("text") or "")


def _register_request_task(*, request_id: str, task: asyncio.Task[None]) -> None:
    with _request_tasks_lock:
        _request_tasks[request_id] = task


def _pop_request_task(*, request_id: str) -> Optional[asyncio.Task[None]]:
    with _request_tasks_lock:
        return _request_tasks.pop(request_id, None)


def _get_request_task(*, request_id: str) -> Optional[asyncio.Task[None]]:
    with _request_tasks_lock:
        return _request_tasks.get(request_id)


async def _process_chat_request(
    *,
    request_body: ChatRequest,
    request_id: str,
    tenant_id: str,
    current_user: User,
) -> ChatResponse:
    """
    可重用的 chat pipeline（同步入口 / 非同步 request 入口共用）。

    注意：此函數會沿用現有的可觀測性（trace/metrics）與記憶/上下文流程。
    """
    moe = get_moe_manager()
    classifier = get_task_classifier()
    context_manager = get_context_manager()
    memory_service = get_chat_memory_service()
    trace_store = get_genai_trace_store_service()
    metrics = get_genai_metrics_service()
    config_resolver = get_genai_config_resolver_service()
    policy_gate = config_resolver.get_effective_policy_gate(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
    )
    file_permission_service = get_file_permission_service()

    session_id = request_body.session_id or str(uuid.uuid4())
    task_id = request_body.task_id

    messages = [m.model_dump() for m in request_body.messages]
    model_selector = request_body.model_selector

    routing: Dict[str, Any] = {}
    observability = ObservabilityInfo(
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        token_input=None,  # type: ignore[call-arg]  # token_input 有默認值
    )

    start_time = time.perf_counter()

    # G5：入口事件（log + trace）
    logger.info(
        "genai_chat_request_received",
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        user_id=current_user.user_id,
        model_selector_mode=model_selector.mode,
        model_id=model_selector.model_id,
    )
    trace_store.add_event(
        GenAITraceEvent(
            event="chat.request_received",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            status="ok",
        )
    )

    # 取最後一則 user message（若找不到就取最後一則）
    user_messages = [m for m in messages if m.get("role") == "user"]
    last_user_text = (str(user_messages[-1].get("content", "")) if user_messages else "").strip()
    if not last_user_text and messages:
        last_user_text = str(messages[-1].get("content", "")).strip()

    # G3：記錄 user message（避免重複寫入）
    _record_if_changed(
        context_manager=context_manager,
        session_id=session_id,
        role="user",
        content=last_user_text,
        metadata={
            "user_id": current_user.user_id,
            "session_id": session_id,
            "task_id": task_id,
            "request_id": request_id,
        },
    )

    # G3：用 windowed history 作為 MoE 的 messages（並保留前端提供的 system message）
    system_messages = [m for m in messages if m.get("role") == "system"]
    windowed_history = context_manager.get_context_with_window(session_id=session_id)
    observability.context_message_count = len(windowed_history)

    # G6：附件 file_id 權限檢查（避免透過 RAG 讀到不屬於自己的文件）
    if request_body.attachments:
        for att in request_body.attachments:
            file_permission_service.check_file_access(
                user=current_user,
                file_id=att.file_id,
                required_permission=Permission.FILE_READ.value,
            )

    # G6：Data consent gate（AI_PROCESSING）- 未同意則不檢索/不注入/不寫入
    has_ai_consent = False
    try:
        from services.api.models.data_consent import ConsentType

        consent_service = get_consent_service()
        has_ai_consent = consent_service.check_consent(
            current_user.user_id, ConsentType.AI_PROCESSING
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "genai_consent_check_failed",
            error=str(exc),
            request_id=request_id,
            user_id=current_user.user_id,
        )
        has_ai_consent = False

    if has_ai_consent:
        memory_result = await memory_service.retrieve_for_prompt(
            user_id=current_user.user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=request_id,
            query=last_user_text,
            attachments=request_body.attachments,
        )
        observability.memory_hit_count = memory_result.memory_hit_count
        observability.memory_sources = memory_result.memory_sources
        observability.retrieval_latency_ms = memory_result.retrieval_latency_ms
    else:
        from services.api.services.chat_memory_service import MemoryRetrievalResult

        memory_result = MemoryRetrievalResult(
            injection_messages=[],
            memory_hit_count=0,
            memory_sources=[],
            retrieval_latency_ms=0.0,
        )
        observability.memory_hit_count = 0
        observability.memory_sources = []
        observability.retrieval_latency_ms = 0.0

    trace_store.add_event(
        GenAITraceEvent(
            event="chat.memory_retrieved",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            memory_hit_count=observability.memory_hit_count,
            memory_sources=observability.memory_sources,
            retrieval_latency_ms=observability.retrieval_latency_ms,
            status="ok",
        )
    )

    base_system = system_messages[:1] if system_messages else []
    messages_for_llm = base_system + memory_result.injection_messages + windowed_history

    # 呼叫 MoE
    llm_call_start = time.perf_counter()
    if model_selector.mode == "auto":
        allowed_providers = policy_gate.get_allowed_providers()

        # 獲取用戶的收藏模型列表（用於 Auto 模式優先選擇）
        favorite_model_ids: List[str] = []
        try:
            from services.api.services.user_preference_service import get_user_preference_service

            preference_service = get_user_preference_service()
            favorite_model_ids = preference_service.get_favorite_models(
                user_id=current_user.user_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"Failed to get favorite models for user {current_user.user_id}: {exc}")
            # fallback 到內存緩存
            favorite_model_ids = _favorite_models_by_user.get(current_user.user_id, [])

        llm_api_keys = config_resolver.resolve_api_keys_map(
            tenant_id=tenant_id,
            user_id=current_user.user_id,
            providers=allowed_providers,
        )
        task_classification = classifier.classify(
            last_user_text,
            context={
                "user_id": current_user.user_id,
                "session_id": session_id,
                "task_id": task_id,
            },
        )

        result = await moe.chat(
            messages_for_llm,
            task_classification=task_classification,
            context={
                "user_id": current_user.user_id,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "task_id": task_id,
                "allowed_providers": allowed_providers,
                "llm_api_keys": llm_api_keys,
                "favorite_models": favorite_model_ids,  # 傳遞收藏模型列表
            },
        )
    else:
        selected_model_id = model_selector.model_id or ""
        provider = _infer_provider_from_model_id(selected_model_id)
        if not policy_gate.is_model_allowed(provider.value, selected_model_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Model is not allowed by policy",
                    "error_code": "MODEL_NOT_ALLOWED",
                    "provider": provider.value,
                    "model_id": selected_model_id,
                },
            )
        llm_api_keys = config_resolver.resolve_api_keys_map(
            tenant_id=tenant_id,
            user_id=current_user.user_id,
            providers=[provider.value],
        )
        result = await moe.chat(
            messages_for_llm,
            provider=provider,
            model=selected_model_id,
            context={
                "user_id": current_user.user_id,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "task_id": task_id,
                "llm_api_keys": llm_api_keys,
            },
        )

    llm_latency_ms = (time.perf_counter() - llm_call_start) * 1000.0
    total_latency_ms = (time.perf_counter() - start_time) * 1000.0

    content = _extract_content(result)
    routing = (result.get("_routing") if isinstance(result, dict) else None) or {}
    routing_info = RoutingInfo(
        provider=str(routing.get("provider") or "unknown"),
        model=routing.get("model"),
        strategy=str(routing.get("strategy") or "unknown"),
        latency_ms=routing.get("latency_ms"),
        failover_used=bool(routing.get("failover_used") or False),
        fallback_provider=routing.get("fallback_provider"),
    )

    trace_store.add_event(
        GenAITraceEvent(
            event="chat.llm_completed",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            provider=routing_info.provider,
            model=routing_info.model,
            strategy=routing_info.strategy,
            failover_used=routing_info.failover_used,
            fallback_provider=routing_info.fallback_provider,
            llm_latency_ms=llm_latency_ms,
            status="ok",
        )
    )

    # G3：記錄 assistant message（避免重複寫入）
    _record_if_changed(
        context_manager=context_manager,
        session_id=session_id,
        role="assistant",
        content=content,
        metadata={
            "user_id": current_user.user_id,
            "session_id": session_id,
            "task_id": task_id,
            "request_id": request_id,
            "routing": routing,
        },
    )

    if has_ai_consent:
        await memory_service.write_from_turn(
            user_id=current_user.user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=request_id,
            user_text=last_user_text,
            assistant_text=content,
        )

    actions: Optional[List[Dict[str, Any]]] = None
    try:
        # 優先嘗試編輯檔案（如果檢測到編輯意圖）
        edit_action = _try_edit_file_from_chat_output(
            user_text=last_user_text,
            assistant_text=content,
            task_id=task_id,
            current_user=current_user,
            tenant_id=tenant_id,
        )
        if edit_action:
            actions = [edit_action]
        else:
            # 如果沒有編輯意圖，嘗試創建檔案
            create_action = _try_create_file_from_chat_output(
                user_text=last_user_text,
                assistant_text=content,
                task_id=task_id,
                current_user=current_user,
            )
            if create_action:
                actions = [create_action]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "genai_chat_file_action_failed",
            error=str(exc),
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
        )

    response = ChatResponse(
        content=content,
        session_id=session_id,
        task_id=task_id,
        routing=routing_info,
        observability=observability,
        actions=actions,
    )

    final_event = GenAITraceEvent(
        event="chat.response_sent",
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        user_id=current_user.user_id,
        provider=routing_info.provider,
        model=routing_info.model,
        strategy=routing_info.strategy,
        failover_used=routing_info.failover_used,
        fallback_provider=routing_info.fallback_provider,
        memory_hit_count=observability.memory_hit_count,
        memory_sources=observability.memory_sources,
        retrieval_latency_ms=observability.retrieval_latency_ms,
        context_message_count=observability.context_message_count,
        total_latency_ms=total_latency_ms,
        llm_latency_ms=llm_latency_ms,
        status="ok",
    )
    trace_store.add_event(final_event)
    metrics.record_final_event(final_event)

    logger.info(
        "genai_chat_response_sent",
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        user_id=current_user.user_id,
        provider=routing_info.provider,
        model=routing_info.model,
        strategy=routing_info.strategy,
        failover_used=routing_info.failover_used,
        fallback_provider=routing_info.fallback_provider,
        memory_hit_count=observability.memory_hit_count,
        memory_sources=observability.memory_sources,
        retrieval_latency_ms=observability.retrieval_latency_ms,
        context_message_count=observability.context_message_count,
        total_latency_ms=total_latency_ms,
        llm_latency_ms=llm_latency_ms,
    )

    return response


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_product_stream(
    request_body: ChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    產品級 Chat 流式入口：返回 SSE 格式的流式響應。

    - Auto：TaskClassifier → task_classification → 選擇 provider → 調用客戶端 stream
    - Manual/Favorite：以 model_id 推導 provider，並做 provider/model override
    """
    moe = get_moe_manager()
    classifier = get_task_classifier()
    context_manager = get_context_manager()
    memory_service = get_chat_memory_service()
    policy_gate = get_genai_policy_gate_service()
    config_resolver = get_genai_config_resolver_service()

    session_id = request_body.session_id or str(uuid.uuid4())
    task_id = request_body.task_id
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    messages = [m.model_dump() for m in request_body.messages]
    model_selector = request_body.model_selector

    # 記錄工具信息
    allowed_tools = request_body.allowed_tools or []

    # 添加详细的工具日志
    logger.info(
        "chat_request_tools_received",
        request_id=request_id,
        allowed_tools=allowed_tools,
        has_web_search="web_search" in allowed_tools,
        allowed_tools_count=len(allowed_tools),
    )
    logger.info(
        "chat_request_tools",
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        allowed_tools=allowed_tools,
        has_web_search="web_search" in allowed_tools,
    )

    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成 SSE 格式的流式數據"""
        try:
            # 取最後一則 user message
            user_messages = [m for m in messages if m.get("role") == "user"]
            last_user_text = str(user_messages[-1].get("content", "")) if user_messages else ""
            if not last_user_text and messages:
                last_user_text = str(messages[-1].get("content", ""))

            # 記錄 user message
            _record_if_changed(
                context_manager=context_manager,
                session_id=session_id,
                role="user",
                content=last_user_text,
                metadata={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "request_id": request_id,
                },
            )

            # G3：用 windowed history 作為 MoE 的 messages（並保留前端提供的 system message）
            system_messages = [m for m in messages if m.get("role") == "system"]
            windowed_history = context_manager.get_context_with_window(session_id=session_id)

            # 工具调用：如果启用了 web_search 且消息中包含搜索意图，直接调用工具
            logger.info(
                "web_search_check",
                request_id=request_id,
                allowed_tools=allowed_tools,
                has_web_search="web_search" in (allowed_tools or []),
                user_text=last_user_text[:200],  # 记录前200个字符
            )

            # 添加 print 调试输出
            print(
                f"\n[DEBUG] web_search_check: allowed_tools={allowed_tools}, has_web_search={'web_search' in (allowed_tools or [])}"
            )

            if allowed_tools and "web_search" in allowed_tools:
                # 检测是否需要搜索（简单的关键词检测）
                # 扩展关键词列表，包括更多搜索意图
                search_keywords = [
                    "上網",
                    "查詢",
                    "搜索",
                    "搜尋",
                    "現在",
                    "時間",
                    "時刻",
                    "最新",
                    "當前",
                    "http",
                    "https",
                    "www.",
                    ".com",
                    ".net",
                    ".org",  # URL 关键词
                    "網站",
                    "網頁",
                    "連結",
                    "鏈接",
                    "網址",  # 网站相关
                    "查找",
                    "找",
                    "搜",
                    "查",  # 搜索相关
                ]
                needs_search = any(keyword in last_user_text for keyword in search_keywords)
                matched_keywords = [kw for kw in search_keywords if kw in last_user_text]

                logger.info(
                    "web_search_intent_check",
                    request_id=request_id,
                    needs_search=needs_search,
                    matched_keywords=matched_keywords,
                    user_text=last_user_text[:200],
                    search_keywords_count=len(search_keywords),
                )

                # 添加 print 调试输出
                print(
                    f"[DEBUG] web_search_intent_check: needs_search={needs_search}, matched_keywords={matched_keywords}"
                )

                if needs_search:
                    try:
                        # 直接导入 web_search 模块，避免触发 tools/__init__.py 中的其他导入
                        from tools.web_search.web_search_tool import WebSearchInput, WebSearchTool

                        logger.info(
                            "web_search_triggered",
                            request_id=request_id,
                            query=last_user_text,
                        )

                        # 添加 print 调试输出
                        print(f"[DEBUG] web_search_triggered: query={last_user_text[:100]}")

                        # 调用 web_search 工具
                        search_tool = WebSearchTool()
                        search_input = WebSearchInput(query=last_user_text, num=5)
                        search_result = await search_tool.execute(search_input)

                        # 添加 print 调试输出
                        print(
                            f"[DEBUG] web_search_result: status={search_result.status}, results_count={len(search_result.results) if search_result.results else 0}"
                        )

                        # 将搜索结果添加到消息中
                        logger.info(
                            "web_search_result",
                            request_id=request_id,
                            status=search_result.status,
                            results_count=(
                                len(search_result.results) if search_result.results else 0
                            ),
                            provider=search_result.provider,
                        )

                        if search_result.status == "success" and search_result.results:
                            search_summary = "\n\n=== 🔍 網絡搜索結果（來自真實搜索） ===\n"
                            search_summary += f"搜索提供商: {search_result.provider}\n"
                            search_summary += f"結果數量: {len(search_result.results)}\n"
                            search_summary += "---\n"
                            logger.debug(
                                "web_search_formatting_results",
                                request_id=request_id,
                                results_type=type(search_result.results).__name__,
                                results_count=len(search_result.results),
                            )

                            for i, result in enumerate(search_result.results[:3], 1):
                                # 处理不同的结果格式（可能是 dict 或对象）
                                try:
                                    if isinstance(result, dict):
                                        title = result.get("title", "無標題")
                                        snippet = result.get("snippet", "無摘要")
                                        link = result.get("link", "無鏈接")
                                    elif hasattr(result, "model_dump"):
                                        # 如果是 Pydantic 模型（SearchResult），使用 model_dump
                                        result_dict = result.model_dump()
                                        title = result_dict.get("title", "無標題")
                                        snippet = result_dict.get("snippet", "無摘要")
                                        link = result_dict.get("link", "無鏈接")
                                    elif hasattr(result, "to_dict"):
                                        # 如果是 SearchResultItem 对象，转换为字典
                                        result_dict = result.to_dict()
                                        title = result_dict.get("title", "無標題")
                                        snippet = result_dict.get("snippet", "無摘要")
                                        link = result_dict.get("link", "無鏈接")
                                    else:
                                        # 如果是对象，尝试直接访问属性（Pydantic 模型支持属性访问）
                                        title = getattr(result, "title", "無標題") or "無標題"
                                        snippet = getattr(result, "snippet", "無摘要") or "無摘要"
                                        link = getattr(result, "link", "無鏈接") or "無鏈接"

                                    search_summary += f"\n【搜索結果 {i}】\n"
                                    search_summary += f"標題: {title}\n"
                                    search_summary += f"摘要: {snippet}\n"
                                    search_summary += f"來源鏈接: {link}\n"
                                except Exception as format_error:
                                    logger.warning(
                                        "web_search_result_format_error",
                                        request_id=request_id,
                                        result_index=i,
                                        error=str(format_error),
                                        result_type=type(result).__name__,
                                        result_repr=str(result)[:200],
                                    )
                                    # 如果格式化失败，至少添加基本信息
                                    search_summary += (
                                        f"{i}. 搜索結果 {i} (格式化失敗: {str(format_error)[:50]})\n\n"
                                    )

                            logger.info(
                                "web_search_summary_created",
                                request_id=request_id,
                                summary_length=len(search_summary),
                                summary_preview=search_summary[:500],  # 记录前500字符
                            )

                            # 添加 print 调试输出
                            print(
                                f"[DEBUG] web_search_summary_created: length={len(search_summary)}"
                            )
                            print(f"[DEBUG] search_summary_preview:\n{search_summary[:500]}")

                            # 更新最後一條用戶消息，添加搜索結果
                            # 在搜索結果前添加明确的提示，让AI知道这是真实搜索结果
                            search_summary_with_note = (
                                "\n\n【重要提示：以下是真實的網絡搜索結果，請基於這些結果回答問題。"
                                "如果搜索結果中沒有相關信息，請明確說明，不要編造內容。】\n" + search_summary
                            )

                            if windowed_history:
                                windowed_history[-1]["content"] = (
                                    windowed_history[-1].get("content", "")
                                    + search_summary_with_note
                                )
                            else:
                                # 如果沒有歷史消息，創建一條包含搜索結果的消息
                                windowed_history.append(
                                    {
                                        "role": "user",
                                        "content": last_user_text + search_summary_with_note,
                                    }
                                )

                            logger.info(
                                "web_search_completed",
                                request_id=request_id,
                                results_count=len(search_result.results),
                            )
                        else:
                            logger.warning(
                                "web_search_failed",
                                request_id=request_id,
                                status=search_result.status,
                            )
                    except Exception as tool_error:
                        logger.error(
                            "web_search_error",
                            request_id=request_id,
                            error=str(tool_error),
                            exc_info=True,
                        )
                        # 工具調用失敗不影響正常流程，繼續執行

            # G6：Data consent gate（AI_PROCESSING）- 未同意則不檢索/不注入/不寫入
            has_ai_consent = False
            try:
                from services.api.models.data_consent import ConsentType

                consent_service = get_consent_service()
                has_ai_consent = consent_service.check_consent(
                    current_user.user_id, ConsentType.AI_PROCESSING
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Failed to check AI consent, assuming no consent", error=str(exc), exc_info=True
                )
                has_ai_consent = False

            if has_ai_consent:
                memory_result = await memory_service.retrieve_for_prompt(
                    user_id=current_user.user_id,
                    session_id=session_id,
                    task_id=task_id,
                    request_id=request_id,
                    query=last_user_text,
                    attachments=request_body.attachments,
                )
            else:
                from services.api.services.chat_memory_service import MemoryRetrievalResult

                memory_result = MemoryRetrievalResult(
                    injection_messages=[],
                    memory_hit_count=0,
                    memory_sources=[],
                    retrieval_latency_ms=0.0,
                )

            base_system = system_messages[:1] if system_messages else []
            messages_for_llm = base_system + memory_result.injection_messages + windowed_history

            # 準備 MoE context
            task_classification = None
            provider = None
            model = None

            if model_selector.mode == "auto":
                # G6：provider allowlist（Auto）- 將 allowlist 傳給 MoE 做 provider 過濾
                allowed_providers = policy_gate.get_allowed_providers()

                # 獲取用戶的收藏模型列表（用於 Auto 模式優先選擇）
                favorite_model_ids: List[str] = []
                try:
                    from services.api.services.user_preference_service import (
                        get_user_preference_service,
                    )

                    preference_service = get_user_preference_service()
                    favorite_model_ids = preference_service.get_favorite_models(
                        user_id=current_user.user_id
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug(
                        f"Failed to get favorite models for user {current_user.user_id}: {exc}"
                    )
                    # fallback 到內存緩存
                    favorite_model_ids = _favorite_models_by_user.get(current_user.user_id, [])

                # 任务分析：使用 TaskClassifier 对用户输入进行分类
                logger.info(
                    "task_analysis_start",
                    request_id=request_id,
                    user_text=last_user_text[:200],
                    user_id=current_user.user_id,
                    session_id=session_id,
                    task_id=task_id,
                )

                task_classification = classifier.classify(
                    last_user_text,
                    context={
                        "user_id": current_user.user_id,
                        "session_id": session_id,
                        "task_id": task_id,
                    },
                )

                logger.info(
                    "task_analysis_completed",
                    request_id=request_id,
                    task_type=task_classification.type.value if task_classification else None,
                    confidence=task_classification.confidence if task_classification else None,
                    reasoning=(
                        task_classification.reasoning[:200]
                        if task_classification and task_classification.reasoning
                        else None
                    ),
                )

                # 添加 print 调试输出
                print("\n[DEBUG] Task Analysis Result:")
                print(
                    f"  Type: {task_classification.type.value if task_classification else 'None'}"
                )
                print(
                    f"  Confidence: {task_classification.confidence if task_classification else 'None'}"
                )
                print(
                    f"  Reasoning: {task_classification.reasoning[:200] if task_classification and task_classification.reasoning else 'None'}"
                )
                print()

                # 獲取 API keys（所有允許的 providers）
                llm_api_keys = config_resolver.resolve_api_keys_map(
                    tenant_id=tenant_id,
                    user_id=current_user.user_id,
                    providers=allowed_providers,
                )
            else:
                # manual/favorite：provider/model override
                selected_model_id = model_selector.model_id or ""
                provider = _infer_provider_from_model_id(selected_model_id)
                model = selected_model_id

                # G6：manual/favorite allowlist gate
                if not policy_gate.is_model_allowed(provider.value, selected_model_id):
                    yield f"data: {json.dumps({'type': 'error', 'data': {'error': f'Model {selected_model_id} is not allowed by policy'}})}\n\n"
                    return

                # 獲取 API keys（指定的 provider）
                llm_api_keys = config_resolver.resolve_api_keys_map(
                    tenant_id=tenant_id,
                    user_id=current_user.user_id,
                    providers=[provider.value],
                )

            # 構建 MoE context
            moe_context: Dict[str, Any] = {
                "user_id": current_user.user_id,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "task_id": task_id,
                "llm_api_keys": llm_api_keys,
            }

            if model_selector.mode == "auto":
                moe_context["allowed_providers"] = allowed_providers
                moe_context["favorite_models"] = favorite_model_ids

            # 添加工具信息到 context
            # allowed_tools 已在函数开始处定义（第1069行）
            if allowed_tools:
                moe_context["allowed_tools"] = allowed_tools
                logger.debug(
                    "tools_enabled",
                    request_id=request_id,
                    allowed_tools=allowed_tools,
                )

            # 發送開始消息（此時還不知道 provider 和 model，先發送基本信息）
            logger.info(
                "stream_start",
                request_id=request_id,
                messages_count=len(messages_for_llm),
                has_web_search_results=any(
                    "網絡搜索結果" in str(m.get("content", "")) for m in messages_for_llm
                ),
            )
            yield f"data: {json.dumps({'type': 'start', 'data': {'request_id': request_id, 'session_id': session_id}})}\n\n"

            # 累積完整內容（用於後續記錄）
            full_content = ""
            chunk_count = 0

            # 調用 MoE Manager 的 chat_stream 方法
            try:
                logger.info(
                    "moe_chat_stream_start",
                    request_id=request_id,
                    provider=provider.value if provider else None,
                    model=model,
                    task_classification=task_classification.type if task_classification else None,
                )
                async for chunk in moe.chat_stream(
                    messages_for_llm,
                    task_classification=task_classification,
                    provider=provider,
                    model=model,
                    temperature=0.7,
                    max_tokens=2000,
                    context=moe_context,
                ):
                    chunk_count += 1
                    full_content += chunk
                    # 發送內容塊
                    yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': chunk}})}\n\n"

                logger.info(
                    "moe_chat_stream_completed",
                    request_id=request_id,
                    chunk_count=chunk_count,
                    content_length=len(full_content),
                )
            except Exception as stream_exc:
                logger.error(
                    "moe_chat_stream_error",
                    request_id=request_id,
                    error=str(stream_exc),
                    chunk_count=chunk_count,
                    content_length=len(full_content),
                    exc_info=True,
                )
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(stream_exc)}})}\n\n"
                return

            # 發送結束消息
            yield f"data: {json.dumps({'type': 'done', 'data': {'request_id': request_id}})}\n\n"

            # 記錄 assistant message（異步執行，不阻塞流式響應）
            _record_if_changed(
                context_manager=context_manager,
                session_id=session_id,
                role="assistant",
                content=full_content,
                metadata={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "request_id": request_id,
                },
            )

        except Exception as exc:
            logger.error(f"Streaming chat error: {exc}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 緩衝
        },
    )


@router.post("", status_code=status.HTTP_200_OK)
async def chat_product(
    request_body: ChatRequest,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    產品級 Chat 入口：前端輸入框統一入口。

    - Auto：TaskClassifier → task_classification → MoE chat
    - Manual/Favorite：以 model_id 推導 provider，並做 provider/model override
    """
    moe = get_moe_manager()
    classifier = get_task_classifier()
    context_manager = get_context_manager()
    memory_service = get_chat_memory_service()
    trace_store = get_genai_trace_store_service()
    metrics = get_genai_metrics_service()
    policy_gate = get_genai_policy_gate_service()
    file_permission_service = get_file_permission_service()

    session_id = request_body.session_id or str(uuid.uuid4())
    task_id = request_body.task_id
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())

    messages = [m.model_dump() for m in request_body.messages]
    model_selector = request_body.model_selector

    routing: Dict[str, Any] = {}
    observability = ObservabilityInfo(
        request_id=request_id,
        session_id=session_id,
        task_id=task_id,
        token_input=None,  # type: ignore[call-arg]  # token_input 有默認值
    )

    start_time = time.perf_counter()

    try:
        # 新增：抽出可重用 pipeline（供 /chat 與 /chat/requests 共用）
        response = await _process_chat_request(
            request_body=request_body,
            request_id=request_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )
        return APIResponse.success(
            data=response.model_dump(mode="json"),
            message="Chat success",
        )

        # G5：入口事件（log + trace）
        logger.info(
            "genai_chat_request_received",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            model_selector_mode=model_selector.mode,
            model_id=model_selector.model_id,
        )
        trace_store.add_event(
            GenAITraceEvent(
                event="chat.request_received",
                request_id=request_id,
                session_id=session_id,
                task_id=task_id,
                user_id=current_user.user_id,
                status="ok",
            )
        )

        # 取最後一則 user message（若找不到就取最後一則）
        user_messages = [m for m in messages if m.get("role") == "user"]
        last_user_text = str(user_messages[-1].get("content", "")) if user_messages else ""
        if not last_user_text and messages:
            last_user_text = str(messages[-1].get("content", ""))

        # G3：先記錄 user message（避免重複寫入）
        _record_if_changed(
            context_manager=context_manager,
            session_id=session_id,
            role="user",
            content=last_user_text,
            metadata={
                "user_id": current_user.user_id,
                "session_id": session_id,
                "task_id": task_id,
                "request_id": request_id,
            },
        )

        # G3：用 windowed history 作為 MoE 的 messages（並保留前端提供的 system message）
        system_messages = [m for m in messages if m.get("role") == "system"]
        windowed_history = context_manager.get_context_with_window(session_id=session_id)
        observability.context_message_count = (
            len(windowed_history) if isinstance(windowed_history, list) else 0
        )
        # G6：附件 file_id 權限檢查（避免透過 RAG 讀到不屬於自己的文件）
        if request_body.attachments:
            for att in request_body.attachments:
                file_permission_service.check_file_access(
                    user=current_user,
                    file_id=att.file_id,
                    required_permission=Permission.FILE_READ.value,
                )

        # G6：Data consent gate（AI_PROCESSING）- 未同意則不檢索/不注入/不寫入
        has_ai_consent = False
        try:
            from services.api.models.data_consent import ConsentType

            consent_service = get_consent_service()
            has_ai_consent = consent_service.check_consent(
                current_user.user_id, ConsentType.AI_PROCESSING
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "genai_consent_check_failed",
                error=str(exc),
                request_id=request_id,
                user_id=current_user.user_id,
            )
            has_ai_consent = False

        if has_ai_consent:
            memory_result = await memory_service.retrieve_for_prompt(
                user_id=current_user.user_id,
                session_id=session_id,
                task_id=task_id,
                request_id=request_id,
                query=last_user_text,
                attachments=request_body.attachments,
            )
            observability.memory_hit_count = memory_result.memory_hit_count
            observability.memory_sources = memory_result.memory_sources
            observability.retrieval_latency_ms = memory_result.retrieval_latency_ms
        else:
            from services.api.services.chat_memory_service import MemoryRetrievalResult

            memory_result = MemoryRetrievalResult(
                injection_messages=[],
                memory_hit_count=0,
                memory_sources=[],
                retrieval_latency_ms=0.0,
            )
            observability.memory_hit_count = 0
            observability.memory_sources = []
            observability.retrieval_latency_ms = 0.0

        base_system = system_messages[:1] if system_messages else []
        messages_for_llm = base_system + memory_result.injection_messages + windowed_history

        trace_store.add_event(
            GenAITraceEvent(
                event="chat.memory_retrieved",
                request_id=request_id,
                session_id=session_id,
                task_id=task_id,
                user_id=current_user.user_id,
                memory_hit_count=observability.memory_hit_count,
                memory_sources=observability.memory_sources,
                retrieval_latency_ms=observability.retrieval_latency_ms,
                context_message_count=observability.context_message_count,
                status="ok",
            )
        )

        llm_call_start = time.perf_counter()
        if model_selector.mode == "auto":
            # G6：provider allowlist（Auto）- 將 allowlist 傳給 MoE 做 provider 過濾
            allowed_providers = policy_gate.get_allowed_providers()

            # 獲取用戶的收藏模型列表（用於 Auto 模式優先選擇）
            favorite_model_ids: List[str] = []
            try:
                from services.api.services.user_preference_service import (
                    get_user_preference_service,
                )

                preference_service = get_user_preference_service()
                favorite_model_ids = preference_service.get_favorite_models(
                    user_id=current_user.user_id
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    f"Failed to get favorite models for user {current_user.user_id}: {exc}"
                )
                # fallback 到內存緩存
                favorite_model_ids = _favorite_models_by_user.get(current_user.user_id, [])

            task_classification = classifier.classify(
                last_user_text,
                context={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                },
            )

            result = await moe.chat(
                messages_for_llm,
                task_classification=task_classification,
                context={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "allowed_providers": allowed_providers,
                    "favorite_models": favorite_model_ids,  # 傳遞收藏模型列表
                },
            )

        else:
            # manual/favorite：provider/model override
            selected_model_id = model_selector.model_id or ""
            provider = _infer_provider_from_model_id(selected_model_id)
            # G6：manual/favorite allowlist gate
            if not policy_gate.is_model_allowed(provider.value, selected_model_id):
                return APIResponse.error(
                    message="Model is not allowed by policy",
                    error_code="MODEL_NOT_ALLOWED",
                    details={
                        "provider": provider.value,
                        "model_id": selected_model_id,
                    },
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            result = await moe.chat(
                messages_for_llm,
                provider=provider,
                model=selected_model_id,
                context={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                },
            )

        content = _extract_content(result)
        routing = (result.get("_routing", {}) if isinstance(result, dict) else {}) or {}

        llm_latency_ms = (time.perf_counter() - llm_call_start) * 1000.0
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0

        trace_store.add_event(
            GenAITraceEvent(
                event="chat.llm_completed",
                request_id=request_id,
                session_id=session_id,
                task_id=task_id,
                user_id=current_user.user_id,
                provider=str(routing.get("provider") or "unknown"),
                model=routing.get("model"),
                strategy=str(routing.get("strategy") or "unknown"),
                failover_used=bool(routing.get("failover_used") or False),
                fallback_provider=routing.get("fallback_provider"),
                memory_hit_count=observability.memory_hit_count,
                memory_sources=observability.memory_sources,
                retrieval_latency_ms=observability.retrieval_latency_ms,
                context_message_count=observability.context_message_count,
                total_latency_ms=total_latency_ms,
                llm_latency_ms=llm_latency_ms,
                status="ok",
            )
        )

        # G3：記錄 assistant message（避免重複寫入）
        _record_if_changed(
            context_manager=context_manager,
            session_id=session_id,
            role="assistant",
            content=content,
            metadata={
                "user_id": current_user.user_id,
                "session_id": session_id,
                "task_id": task_id,
                "request_id": request_id,
                "routing": routing,
            },
        )

        # G6：同意才寫入 long-term（MVP：snippet；失敗不阻擋回覆）
        if has_ai_consent:
            await memory_service.write_from_turn(
                user_id=current_user.user_id,
                session_id=session_id,
                task_id=task_id,
                request_id=request_id,
                user_text=last_user_text,
                assistant_text=content,
            )

        routing_info = RoutingInfo(
            provider=str(routing.get("provider") or "unknown"),
            model=routing.get("model"),
            strategy=str(routing.get("strategy") or "unknown"),
            latency_ms=routing.get("latency_ms"),
            failover_used=bool(routing.get("failover_used") or False),
            fallback_provider=routing.get("fallback_provider"),
        )

        response = ChatResponse(
            content=content,
            session_id=session_id,
            task_id=task_id,
            routing=routing_info,
            observability=observability,
        )

        final_event = GenAITraceEvent(
            event="chat.response_sent",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            provider=routing_info.provider,
            model=routing_info.model,
            strategy=routing_info.strategy,
            failover_used=routing_info.failover_used,
            fallback_provider=routing_info.fallback_provider,
            memory_hit_count=observability.memory_hit_count,
            memory_sources=observability.memory_sources,
            retrieval_latency_ms=observability.retrieval_latency_ms,
            context_message_count=observability.context_message_count,
            total_latency_ms=total_latency_ms,
            llm_latency_ms=llm_latency_ms,
            status="ok",
        )
        trace_store.add_event(final_event)
        metrics.record_final_event(final_event)

        logger.info(
            "genai_chat_response_sent",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            provider=routing_info.provider,
            model=routing_info.model,
            strategy=routing_info.strategy,
            failover_used=routing_info.failover_used,
            fallback_provider=routing_info.fallback_provider,
            memory_hit_count=observability.memory_hit_count,
            memory_sources=observability.memory_sources,
            retrieval_latency_ms=observability.retrieval_latency_ms,
            context_message_count=observability.context_message_count,
            total_latency_ms=total_latency_ms,
            llm_latency_ms=llm_latency_ms,
        )

        return APIResponse.success(
            data=response.model_dump(mode="json"),
            message="Chat success",
        )
    except HTTPException as exc:
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message") or "Request failed")
            error_code = str(detail.get("error_code") or "CHAT_HTTP_ERROR")

            failed_event = GenAITraceEvent(
                event="chat.failed",
                request_id=request_id,
                session_id=session_id,
                task_id=task_id,
                user_id=current_user.user_id,
                status="error",
                error_code=error_code,
                error_message=message,
                total_latency_ms=total_latency_ms,
            )
            trace_store.add_event(failed_event)
            metrics.record_final_event(failed_event)

            return APIResponse.error(
                message=message,
                error_code=error_code,
                details=detail,
                status_code=exc.status_code,
            )

        logger.warning(
            "chat_product_http_error",
            error=str(detail),
            status_code=exc.status_code,
            user_id=current_user.user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=request_id,
        )
        failed_event = GenAITraceEvent(
            event="chat.failed",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            status="error",
            error_code="CHAT_HTTP_ERROR",
            error_message=str(detail),
            total_latency_ms=total_latency_ms,
            memory_hit_count=observability.memory_hit_count,
            memory_sources=observability.memory_sources,
            retrieval_latency_ms=observability.retrieval_latency_ms,
            context_message_count=observability.context_message_count,
        )
        trace_store.add_event(failed_event)
        metrics.record_final_event(failed_event)
        return APIResponse.error(
            message=str(detail),
            error_code="CHAT_HTTP_ERROR",
            status_code=exc.status_code,
        )
    except Exception as exc:  # noqa: BLE001
        total_latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            "chat_product_failed",
            error=str(exc),
            user_id=current_user.user_id,
            session_id=session_id,
            task_id=task_id,
            request_id=request_id,
        )

        failed_event = GenAITraceEvent(
            event="chat.failed",
            request_id=request_id,
            session_id=session_id,
            task_id=task_id,
            user_id=current_user.user_id,
            status="error",
            error_code="CHAT_PRODUCT_FAILED",
            error_message=str(exc),
            total_latency_ms=total_latency_ms,
            memory_hit_count=observability.memory_hit_count,
            memory_sources=observability.memory_sources,
            retrieval_latency_ms=observability.retrieval_latency_ms,
            context_message_count=observability.context_message_count,
        )
        trace_store.add_event(failed_event)
        metrics.record_final_event(failed_event)

        return APIResponse.error(
            message=f"Chat failed: {exc}",
            error_code="CHAT_PRODUCT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def _run_async_request(
    *, request_id: str, request_body: ChatRequest, tenant_id: str, current_user: User
) -> None:
    store = get_genai_chat_request_store_service()

    try:
        if store.is_aborted(request_id=request_id):
            store.update(request_id=request_id, status=GenAIRequestStatus.aborted)
            return

        store.update(request_id=request_id, status=GenAIRequestStatus.running)

        response = await _process_chat_request(
            request_body=request_body,
            request_id=request_id,
            tenant_id=tenant_id,
            current_user=current_user,
        )

        store.update(
            request_id=request_id,
            status=GenAIRequestStatus.succeeded,
            response=response.model_dump(mode="json"),
        )
    except asyncio.CancelledError:
        store.set_abort(request_id=request_id)
        store.update(request_id=request_id, status=GenAIRequestStatus.aborted)
        raise
    except HTTPException as exc:
        # abort：使用 409 統一視為 aborted
        if exc.status_code == status.HTTP_409_CONFLICT:
            store.set_abort(request_id=request_id)
            store.update(request_id=request_id, status=GenAIRequestStatus.aborted)
            return

        detail = exc.detail
        if isinstance(detail, dict):
            store.update(
                request_id=request_id,
                status=GenAIRequestStatus.failed,
                error_code=str(detail.get("error_code") or "CHAT_HTTP_ERROR"),
                error_message=str(detail.get("message") or "Request failed"),
            )
        else:
            store.update(
                request_id=request_id,
                status=GenAIRequestStatus.failed,
                error_code="CHAT_HTTP_ERROR",
                error_message=str(detail),
            )
    except Exception as exc:  # noqa: BLE001
        store.update(
            request_id=request_id,
            status=GenAIRequestStatus.failed,
            error_code="CHAT_REQUEST_FAILED",
            error_message=str(exc),
        )
    finally:
        _pop_request_task(request_id=request_id)


@router.post("/requests", status_code=status.HTTP_202_ACCEPTED)
async def create_chat_request(
    request_body: ChatRequest,
    background_tasks: BackgroundTasks,
    executor: str = "local",  # local/rq
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    非同步 Chat 請求：立即回 request_id，後端在背景處理；前端可輪詢狀態或 abort。
    """
    store = get_genai_chat_request_store_service()

    request_id = str(uuid.uuid4())
    session_id = request_body.session_id or str(uuid.uuid4())

    request_dict = request_body.model_dump(mode="json")
    request_dict["session_id"] = session_id

    record = GenAIChatRequestRecord(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        session_id=session_id,
        task_id=request_body.task_id,
        status=GenAIRequestStatus.queued,
        request=request_dict,
    )
    store.create(record)

    # executor=rq：適合長任務/Agent（若 rq 不可用則自動 fallback to local）
    if executor == "rq":
        try:
            from database.rq.queue import GENAI_CHAT_QUEUE, get_task_queue
            from workers.genai_chat_job import run_genai_chat_request

            q = get_task_queue(queue_name=GENAI_CHAT_QUEUE)
            q.enqueue(
                run_genai_chat_request,
                request_id,
                request_dict,
                tenant_id,
                current_user.to_dict(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "genai_chat_request_enqueue_failed_fallback_local",
                request_id=request_id,
                error=str(exc),
            )
            executor = "local"

    # executor=local：同一進程內背景任務（MVP）
    if executor != "rq":
        background_tasks.add_task(
            _run_async_request,
            request_id=request_id,
            request_body=ChatRequest.model_validate(request_dict),
            tenant_id=tenant_id,
            current_user=current_user,
        )

    payload = GenAIChatRequestCreateResponse(
        request_id=request_id,
        session_id=session_id,
        status=GenAIRequestStatus.queued,
    )
    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Chat request created",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/requests/{request_id}", status_code=status.HTTP_200_OK)
async def get_chat_request_state(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_genai_chat_request_store_service()
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

    payload = GenAIChatRequestStateResponse(
        request_id=record.request_id,
        status=record.status,
        created_at_ms=record.created_at_ms,
        updated_at_ms=record.updated_at_ms,
        tenant_id=record.tenant_id,
        session_id=record.session_id,
        task_id=record.task_id,
        response=record.response,
        error_code=record.error_code,
        error_message=record.error_message,
    )
    return APIResponse.success(
        data=payload.model_dump(mode="json"),
        message="Chat request state retrieved",
    )


@router.post("/requests/{request_id}/abort", status_code=status.HTTP_200_OK)
async def abort_chat_request(
    request_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    store = get_genai_chat_request_store_service()
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

    store.update(request_id=record.request_id, status=GenAIRequestStatus.aborted)
    return APIResponse.success(
        data={"request_id": record.request_id, "status": "aborted"},
        message="Chat request aborted",
    )


@router.get("/observability/stats", status_code=status.HTTP_200_OK)
async def get_chat_observability_stats(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：產品級 Chat 指標彙總（JSON）。"""
    metrics = get_genai_metrics_service()
    return APIResponse.success(
        data={"stats": metrics.get_stats(), "user_id": current_user.user_id},
        message="Chat observability stats retrieved",
    )


@router.get("/observability/traces/{request_id}", status_code=status.HTTP_200_OK)
async def get_chat_observability_trace(
    request_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：依 request_id 回放事件序列（MVP：in-memory）。"""
    trace_store = get_genai_trace_store_service()
    events = trace_store.get_trace(request_id=str(request_id))
    return APIResponse.success(
        data={
            "request_id": request_id,
            "events": events,
            "user_id": current_user.user_id,
        },
        message="Chat trace retrieved",
    )


@router.get("/observability/recent", status_code=status.HTTP_200_OK)
async def get_chat_observability_recent(
    limit: int = 50,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    event: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G5：列出最近 N 筆事件（MVP：in-memory）。"""
    trace_store = get_genai_trace_store_service()
    items = trace_store.list_recent(
        limit=limit,
        user_id=current_user.user_id,
        session_id=session_id,
        task_id=task_id,
        event=event,
    )
    return APIResponse.success(
        data={"events": items, "user_id": current_user.user_id},
        message="Recent chat observability events retrieved",
    )


@router.get("/models", status_code=status.HTTP_200_OK)
async def list_available_models(
    refresh: bool = False,
    include_disallowed: bool = False,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    產品級模型清單（JSON）。

    - config: genai.model_registry.models
    - ollama: (可選) /api/tags 動態發現（genai.model_registry.enable_ollama_discovery）
    - 預設會套用 genai.policy allowlist 過濾
    """
    registry = get_genai_model_registry_service()
    config_resolver = get_genai_config_resolver_service()
    policy_gate = config_resolver.get_effective_policy_gate(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
    )

    items = await registry.list_models(refresh=refresh)
    if not include_disallowed:
        items = [
            m
            for m in items
            if policy_gate.is_model_allowed(
                str(m.get("provider") or ""),
                str(m.get("model_id") or ""),
            )
        ]

    return APIResponse.success(
        data={"models": items, "user_id": current_user.user_id},
        message="Model list retrieved",
    )


@router.get("/sessions/{session_id}/messages", status_code=status.HTTP_200_OK)
async def get_session_messages(
    session_id: str,
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """G3：Session 回放（最小可用）。"""
    context_manager = get_context_manager()
    safe_limit = int(limit) if isinstance(limit, int) and limit and limit > 0 else None
    try:
        messages = context_manager.get_messages(session_id=session_id, limit=safe_limit)
        payload = [m.model_dump(mode="json") for m in messages]
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "get_session_messages_failed",
            error=str(exc),
            user_id=current_user.user_id,
            session_id=session_id,
        )
        payload = []
    return APIResponse.success(
        data={"session_id": session_id, "messages": payload},
        message="Session messages retrieved",
    )


class FavoriteModelsUpdateRequest(BaseModel):
    """收藏模型更新請求（MVP）。"""

    model_ids: List[str] = Field(default_factory=list, description="收藏 model_id 列表")


@router.get("/preferences/models", status_code=status.HTTP_200_OK)
async def get_favorite_models(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    user_id = current_user.user_id
    try:
        from services.api.services.user_preference_service import get_user_preference_service

        service = get_user_preference_service()
        model_ids = service.get_favorite_models(user_id=user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("favorite_models_service_failed", user_id=user_id, error=str(exc))
        model_ids = _favorite_models_by_user.get(user_id, [])
    return APIResponse.success(
        data={"model_ids": model_ids},
        message="Favorite models retrieved",
    )


@router.put("/preferences/models", status_code=status.HTTP_200_OK)
async def set_favorite_models(
    request_body: FavoriteModelsUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    user_id = current_user.user_id
    try:
        # G6：收藏模型寫入前先做 allowlist 過濾（去除不允許者）
        config_resolver = get_genai_config_resolver_service()
        policy_gate = config_resolver.get_effective_policy_gate(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        filtered = policy_gate.filter_favorite_models(request_body.model_ids)

        from services.api.services.user_preference_service import get_user_preference_service

        service = get_user_preference_service()
        normalized = service.set_favorite_models(user_id=user_id, model_ids=filtered)
    except Exception as exc:  # noqa: BLE001
        logger.warning("favorite_models_service_failed", user_id=user_id, error=str(exc))
        # 去重且保序（fallback）
        seen: set[str] = set()
        normalized = []
        for mid in request_body.model_ids:
            mid = str(mid).strip()
            if not mid or mid in seen:
                continue
            seen.add(mid)
            normalized.append(mid)
        _favorite_models_by_user[user_id] = normalized
    return APIResponse.success(
        data={"model_ids": normalized},
        message="Favorite models updated",
    )
