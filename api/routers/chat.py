"""
代碼功能說明: 產品級 Chat API 路由（/api/v1/chat），串接 MoE Auto/Manual/Favorite 與最小觀測欄位
創建日期: 2025-12-13 17:28:02 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2026-01-14 21:41 UTC+8
"""

from __future__ import annotations

import asyncio
import json
import os
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

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.classifier import TaskClassifier
from agents.task_analyzer.models import LLMProvider, TaskAnalysisRequest
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

# 向後兼容：如果 ConfigStoreService 不可用，使用舊的配置方式
try:
    from services.api.services.config_store_service import ConfigStoreService

    _streaming_config_service: Optional[ConfigStoreService] = None

    def get_streaming_config_service() -> ConfigStoreService:
        """獲取配置存儲服務實例（單例模式）"""
        global _streaming_config_service
        if _streaming_config_service is None:
            _streaming_config_service = ConfigStoreService()
        return _streaming_config_service

    STREAMING_CONFIG_STORE_AVAILABLE = True

    def get_mcp_default_endpoint() -> str:
        """
        從 ArangoDB 系統配置讀取 MCP 默認端點

        Returns:
            MCP 默認端點 URL，如果未配置則返回 fallback 默認值
        """
        try:
            config_store = get_streaming_config_service()
            config = config_store.get_config(
                scope="mcp_gateway",
                tenant_id=None,  # 系統級配置
            )

            if config and config.config_data and "default_endpoint" in config.config_data:
                default_endpoint = config.config_data["default_endpoint"]
                logger.info(f"使用系統配置的 MCP 默認端點: {default_endpoint}")
                return default_endpoint
        except Exception as exc:
            logger.warning(f"無法讀取 MCP 系統配置，使用 fallback 默認值: {exc}")

        # Fallback 默認值
        fallback_endpoint = "https://mcp.k84.org"
        logger.info(f"使用 fallback MCP 默認端點: {fallback_endpoint}")
        return fallback_endpoint

except ImportError:
    STREAMING_CONFIG_STORE_AVAILABLE = False

    def get_mcp_default_endpoint() -> str:
        """Fallback: 如果 ConfigStoreService 不可用"""
        return "https://mcp.k84.org"

    logger.warning("ConfigStoreService 不可用，流式輸出將使用默認 chunk_size=50")


def get_streaming_chunk_size() -> int:
    """
    獲取流式輸出分塊大小（從 ArangoDB system_configs 讀取）

    Returns:
        流式輸出分塊大小（字符數），默認 50
    """
    # 優先從 ArangoDB system_configs 讀取
    if STREAMING_CONFIG_STORE_AVAILABLE:
        try:
            config_service = get_streaming_config_service()
            config = config_service.get_config("streaming", tenant_id=None)
            if config and config.config_data:
                chunk_size = config.config_data.get("chunk_size", 50)
                return int(chunk_size)
        except Exception as e:
            logger.warning(
                "failed_to_load_streaming_config_from_arangodb",
                error=str(e),
                message="從 ArangoDB 讀取流式輸出配置失敗，使用默認值 50",
            )

    # 默認值
    return 50


router = APIRouter(prefix="/chat", tags=["Chat"])

_moe_manager: Optional[LLMMoEManager] = None
_task_classifier: Optional[TaskClassifier] = None
_task_analyzer: Optional[TaskAnalyzer] = None
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


def get_task_analyzer() -> TaskAnalyzer:
    """获取 Task Analyzer 单例"""
    global _task_analyzer
    if _task_analyzer is None:
        _task_analyzer = TaskAnalyzer()
    return _task_analyzer


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
        "生成文件",  # 修改時間：2026-01-06 - 添加「生成文件」關鍵詞
        "幫我生成文件",  # 修改時間：2026-01-06 - 添加「幫我生成文件」關鍵詞
        "幫我生成檔案",  # 修改時間：2026-01-06 - 添加「幫我生成檔案」關鍵詞
        "輸出成檔案",
        "輸出成文件",
        "寫成檔案",
        "寫成文件",
        "保存成",
        "存成",
        "另存",
        "做成一份文件",
        "做成一份檔案",
        "做成文件",
        "做成檔案",
        "做成一份",
        "製作成文件",
        "製作成檔案",
        "製作文件",
        "製作檔案",
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
    """
    根據用戶意圖生成默認文件名

    修改時間：2026-01-06 - 增強文件名生成邏輯，支持更多意圖識別
    """
    t = (text or "").strip()

    # 檢查是否包含特定主題（如 "Data Agent"）
    import re

    # 優先匹配 "主題：XXX" 或 "主題: XXX" 模式
    topic_pattern = r"主題[：:]\s*([A-Za-z0-9_\-\u4e00-\u9fff\s]+?)(?:\s|，|,|$)"
    topic_match = re.search(topic_pattern, t, re.IGNORECASE)
    if topic_match:
        topic = topic_match.group(1).strip()
        # 清理主題名稱，移除特殊字符，保留字母、數字、中文、連字符和下劃線
        topic_clean = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", topic)
        # 限制長度
        if len(topic_clean) > 50:
            topic_clean = topic_clean[:50]
        if topic_clean:
            return f"{topic_clean}.md"

    # 匹配 "產生XXX文件"、"生成XXX文件"、"創建XXX文件" 等模式
    pattern = r"(?:產生|生成|創建|建立|製作|做成|寫成|輸出成|整理成)\s*([A-Za-z0-9_\-\u4e00-\u9fff\s]+?)\s*(?:文件|檔案|文檔|document)"
    match = re.search(pattern, t, re.IGNORECASE)
    if match:
        topic = match.group(1).strip()
        # 清理主題名稱，移除特殊字符，保留字母、數字、中文、連字符和下劃線
        topic_clean = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", topic)
        # 限制長度
        if len(topic_clean) > 50:
            topic_clean = topic_clean[:50]
        return f"{topic_clean}.md"

    # 原有邏輯
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
    """
    # 修改時間：2026-01-06 - 添加詳細日誌追蹤文件創建流程
    logger.info(
        "try_create_file_start",
        task_id=task_id,
        user_id=current_user.user_id if current_user else None,
        user_text=user_text[:200],
        assistant_text_length=len(assistant_text),
        force_create=force_create,
    )

    if not task_id:
        logger.warning(
            "try_create_file_no_task_id",
            user_text=user_text[:200],
            note="task_id is None, cannot create file",
        )
        return None

    # 如果 force_create=True，跳過關鍵詞匹配（用於 Task Analyzer 語義分析識別的意圖）
    if not force_create:
        if not _looks_like_create_file_intent(user_text):
            logger.info(
                "try_create_file_no_intent_match",
                task_id=task_id,
                user_text=user_text[:200],
                note="does not look like create file intent",
            )
            return None

    folder_path, filename = _parse_target_path(user_text)
    logger.info(
        "try_create_file_parsed_path",
        task_id=task_id,
        folder_path=folder_path,
        filename=filename,
        user_text=user_text[:200],
    )

    if not filename:
        filename = _default_filename_for_intent(user_text)
        logger.info(
            "try_create_file_using_default_filename",
            task_id=task_id,
            default_filename=filename,
            user_text=user_text[:200],
        )

    # 只允許 md/txt/json
    ext = Path(filename).suffix.lower()
    logger.info(
        "try_create_file_checking_extension",
        task_id=task_id,
        filename=filename,
        extension=ext,
    )

    if ext not in (".md", ".txt", ".json"):
        logger.warning(
            "try_create_file_invalid_extension",
            task_id=task_id,
            filename=filename,
            extension=ext,
            note="only .md, .txt, .json are allowed",
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
            "try_create_file_permission_check_passed",
            task_id=task_id,
            filename=filename,
        )
    except Exception as perm_error:
        logger.error(
            "try_create_file_permission_check_failed",
            task_id=task_id,
            filename=filename,
            error=str(perm_error),
            exc_info=True,
        )
        return None

    folder_id = None
    if folder_path:
        try:
            folder_id = _ensure_folder_path(
                task_id=task_id,
                user_id=current_user.user_id,
                folder_path=folder_path,
            )
            logger.info(
                "try_create_file_folder_ensured",
                task_id=task_id,
                folder_path=folder_path,
                folder_id=folder_id,
            )
        except Exception as folder_error:
            logger.error(
                "try_create_file_folder_creation_failed",
                task_id=task_id,
                folder_path=folder_path,
                error=str(folder_error),
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
            "try_create_file_storage_saved",
            task_id=task_id,
            filename=filename,
            file_id=file_id,
            storage_path=storage_path,
            content_size=len(content_bytes),
        )
    except Exception as storage_error:
        logger.error(
            "try_create_file_storage_save_failed",
            task_id=task_id,
            filename=filename,
            error=str(storage_error),
            exc_info=True,
        )
        return None

    try:
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
        logger.info(
            "try_create_file_metadata_created",
            task_id=task_id,
            filename=filename,
            file_id=file_id,
        )
    except Exception as metadata_error:
        logger.error(
            "try_create_file_metadata_creation_failed",
            task_id=task_id,
            filename=filename,
            file_id=file_id,
            error=str(metadata_error),
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
        "try_create_file_success",
        task_id=task_id,
        filename=filename,
        file_id=file_id,
        result=result,
    )

    return result


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

    # ============================================
    # 集成 Task Analyzer（4 层渐进式路由架构）
    # ============================================
    task_analyzer_result = None
    try:
        # 修改時間：2026-01-06 - 添加調試日誌確認代碼執行路徑
        import sys

        sys.stderr.write(
            f"\n[task_analyzer] 🔍 開始調用 Task Analyzer (非流式)，用戶查詢: {last_user_text[:100]}...\n"
        )
        sys.stderr.flush()

        task_analyzer = get_task_analyzer()
        # 修改時間：2026-01-06 - 將 allowed_tools 傳遞給 Task Analyzer，讓 Capability Matcher 優先考慮啟用的工具
        # 注意：allowed_tools 需要從 request_body 中獲取
        allowed_tools_for_analyzer = request_body.allowed_tools or []
        # 修改時間：2026-01-27 - 如果用戶明確選擇了 agent_id，優先使用用戶選擇的 Agent
        user_selected_agent_id = request_body.agent_id

        # 修改時間：2026-01-27 - 添加完整的請求參數日誌
        import sys

        sys.stderr.write(
            f"\n[chatMessage] 📥 後端接收聊天請求（非流式）：\n"
            f"  - request_id: {request_id}\n"
            f"  - task_id: {task_id}\n"
            f"  - session_id: {session_id}\n"
            f"  - user_id: {current_user.user_id}\n"
            f"  - assistant_id: {request_body.assistant_id or '未選擇'}\n"
            f"  - agent_id: {request_body.agent_id or '未選擇'}\n"
            f"  - model_selector: {request_body.model_selector}\n"
            f"  - allowed_tools: {request_body.allowed_tools or []}\n"
            f"  - message_count: {len(messages)}\n"
            f"  - last_user_text: {last_user_text[:100]}...\n"
            f"  - attachments_count: {len(request_body.attachments) if request_body.attachments else 0}\n"
            f"  - timestamp: {datetime.now().isoformat()}\n"
        )
        sys.stderr.flush()

        logger.info(
            f"chatMessage request received: request_id={request_id}, task_id={task_id}, "
            f"session_id={session_id}, user_id={current_user.user_id}, agent_id={request_body.agent_id}"
        )

        logger.info(
            f"Preparing Task Analyzer request: agent_id={user_selected_agent_id}, "
            f"task_id={task_id}, session_id={session_id}"
        )

        analysis_result = await task_analyzer.analyze(
            TaskAnalysisRequest(
                task=last_user_text,
                context={
                    "user_id": current_user.user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "request_id": request_id,
                    "allowed_tools": allowed_tools_for_analyzer,  # ✅ 傳遞 allowed_tools
                    "agent_id": user_selected_agent_id,  # ✅ 傳遞用戶選擇的 agent_id
                },
                user_id=current_user.user_id,
                session_id=session_id,
                specified_agent_id=user_selected_agent_id,  # ✅ 設置 specified_agent_id，讓 Task Analyzer 優先使用用戶選擇的 Agent
            )
        )
        task_analyzer_result = analysis_result

        # 添加詳細日誌追蹤分析結果
        sys.stderr.write(
            f"\n[chat] 📊 Task Analyzer 結果檢查：\n"
            f"  - has_result: {task_analyzer_result is not None}\n"
            f"  - has_decision_result: {task_analyzer_result.decision_result is not None if task_analyzer_result else False}\n"
            f"  - chosen_agent: {task_analyzer_result.decision_result.chosen_agent if task_analyzer_result and task_analyzer_result.decision_result else None}\n"
            f"  - fast_path: {task_analyzer_result.analysis_details.get('fast_path', False) if task_analyzer_result and task_analyzer_result.analysis_details else False}\n"
            f"  - direct_answer: {task_analyzer_result.analysis_details.get('direct_answer', False) if task_analyzer_result and task_analyzer_result.analysis_details else False}\n"
        )
        sys.stderr.flush()

        # 修改時間：2026-01-06 - 添加詳細的 Console Log 輸出 Task Analyzer 分析結果
        # 使用 sys.stderr 確保輸出到控制台（不被重定向）
        import sys

        log_lines = []
        log_lines.append("\n" + "=" * 80)
        log_lines.append("[task_analyzer] Task Analyzer 分析結果")
        log_lines.append("=" * 80)
        log_lines.append(f"[task_analyzer] 用戶查詢: {last_user_text}")
        log_lines.append(f"[task_analyzer] Request ID: {request_id}")
        log_lines.append(f"[task_analyzer] Task ID: {task_id}")
        log_lines.append(f"[task_analyzer] Session ID: {session_id}")
        log_lines.append(f"[task_analyzer] Allowed Tools: {allowed_tools_for_analyzer}")
        # 修改時間：2026-01-27 - 記錄用戶選擇的 agent_id
        if user_selected_agent_id:
            log_lines.append(f"[task_analyzer] 用戶選擇的 Agent ID: {user_selected_agent_id}")
            log_lines.append("[task_analyzer] ⚠️  用戶明確選擇了 Agent，將優先使用用戶選擇的 Agent")

        if task_analyzer_result:
            # Router Decision 信息
            router_decision = (
                task_analyzer_result.router_decision
                if hasattr(task_analyzer_result, "router_decision")
                else None
            )
            if router_decision:
                log_lines.append("\n[task_analyzer] Router Decision:")
                log_lines.append(f"  - Intent Type: {router_decision.intent_type}")
                log_lines.append(f"  - Complexity: {router_decision.complexity}")
                log_lines.append(f"  - Needs Agent: {router_decision.needs_agent}")
                log_lines.append(f"  - Needs Tools: {router_decision.needs_tools}")
                log_lines.append(
                    f"  - Determinism Required: {router_decision.determinism_required}"
                )
                log_lines.append(f"  - Risk Level: {router_decision.risk_level}")
                log_lines.append(f"  - Confidence: {router_decision.confidence}")

            # Decision Result 信息
            decision_result = (
                task_analyzer_result.decision_result
                if hasattr(task_analyzer_result, "decision_result")
                else None
            )
            if decision_result:
                log_lines.append("\n[task_analyzer] Decision Result:")
                log_lines.append(f"  - Chosen Agent: {decision_result.chosen_agent}")
                log_lines.append(f"  - Chosen Tools: {decision_result.chosen_tools}")
                log_lines.append(f"  - Chosen Model: {decision_result.chosen_model}")
                log_lines.append(f"  - Score: {decision_result.score}")
                log_lines.append(f"  - Reasoning: {decision_result.reasoning}")
                log_lines.append(f"  - Fallback Used: {decision_result.fallback_used}")

            # Analysis Details
            analysis_details = (
                task_analyzer_result.analysis_details
                if hasattr(task_analyzer_result, "analysis_details")
                else {}
            )
            if analysis_details:
                log_lines.append("\n[task_analyzer] Analysis Details:")
                log_lines.append(f"  - Layer: {analysis_details.get('layer', 'N/A')}")
                log_lines.append(
                    f"  - Direct Answer: {analysis_details.get('direct_answer', False)}"
                )
                if analysis_details.get("direct_answer"):
                    log_lines.append(
                        f"  - Response: {str(analysis_details.get('response', ''))[:200]}..."
                    )

            # 特別標註文件創建相關的判斷
            decision_result = (
                task_analyzer_result.decision_result
                if hasattr(task_analyzer_result, "decision_result")
                else None
            )
            if decision_result and decision_result.chosen_tools:
                has_doc_editing = (
                    "document_editing" in decision_result.chosen_tools
                    or "file_editing" in decision_result.chosen_tools
                )
                log_lines.append("\n[task_analyzer] 📁 文件創建判斷:")
                log_lines.append(f"  - Document Editing Tool Selected: {has_doc_editing}")
                if has_doc_editing:
                    log_lines.append("  - ✅ 系統將嘗試創建文件")
                else:
                    log_lines.append("  - ⚠️  未選擇 document_editing 工具，將使用關鍵詞匹配作為 fallback")
        else:
            log_lines.append("\n[task_analyzer] ⚠️  Task Analyzer 結果為 None")

        log_lines.append("=" * 80 + "\n")

        # 輸出到 stderr（確保顯示在控制台）
        for line in log_lines:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()

        # 修改時間：2026-01-27 - Agent 調用優先級檢查
        # 優先級順序：
        # 1. 用戶明確選擇 Agent（快速路徑）-> 直接調用 Agent，跳過所有其他檢查
        # 2. Task Analyzer 選擇了 Agent -> 調用 Agent
        # 3. Direct Answer -> 返回直接答案
        is_fast_path = (
            analysis_result.analysis_details.get("fast_path", False)
            if analysis_result.analysis_details
            else False
        )
        has_direct_answer = (
            analysis_result.analysis_details.get("direct_answer", False)
            if analysis_result.analysis_details
            else False
        )
        has_chosen_agent = (
            (
                analysis_result.decision_result is not None
                and analysis_result.decision_result.chosen_agent is not None
            )
            if analysis_result
            else False
        )

        import sys

        sys.stderr.write(
            f"\n[chat] 🔍 Agent 調用優先級檢查：\n"
            f"  - is_fast_path: {is_fast_path} (用戶明確選擇 Agent)\n"
            f"  - has_chosen_agent: {has_chosen_agent} (Task Analyzer 選擇了 Agent)\n"
            f"  - has_direct_answer: {has_direct_answer} (直接答案)\n"
            f"  - 優先級：{'快速路徑 -> Agent' if is_fast_path else ('Agent' if has_chosen_agent else ('Direct Answer' if has_direct_answer else 'None'))}\n"
        )
        sys.stderr.flush()

        # 如果用戶明確選擇了 Agent（快速路徑），直接跳過 direct_answer 檢查，進入 Agent 調用流程
        if is_fast_path:
            logger.info(
                f"Fast path detected: request_id={request_id}, "
                f"agent_id={analysis_result.analysis_details.get('specified_agent_id')}, "
                f"agent_name={analysis_result.analysis_details.get('agent_name')}"
            )
        # 如果 Task Analyzer 選擇了 Agent，也跳過 direct_answer 檢查
        elif has_chosen_agent:
            logger.info(
                f"Task Analyzer selected agent: request_id={request_id}, "
                f"chosen_agent_id={analysis_result.decision_result.chosen_agent if analysis_result.decision_result else None}"
            )
        # 只有在沒有選擇 Agent 的情況下，才返回直接答案
        elif has_direct_answer:
            logger.info(
                f"Task Analyzer direct answer: request_id={request_id}, "
                f"layer={analysis_result.analysis_details.get('layer')}, "
                f"model={analysis_result.analysis_details.get('model')}"
            )

            # 获取直接答案内容
            response_content = analysis_result.analysis_details.get("response", "")
            if response_content:
                # 构建响应
                from services.api.models.chat import ChatResponse

                response = ChatResponse(
                    content=response_content,
                    request_id=request_id,
                    session_id=session_id,
                    task_id=task_id,
                    routing=RoutingInfo(
                        provider=(
                            analysis_result.llm_provider.value
                            if hasattr(analysis_result.llm_provider, "value")
                            else str(analysis_result.llm_provider)
                        ),
                        model=analysis_result.analysis_details.get("model", "unknown"),
                        task_classification="direct_answer",
                    ),
                    observability=observability,
                )
                return response
    except Exception as analyzer_error:
        # Task Analyzer 失败不影响主流程，记录日志后继续
        import sys

        sys.stderr.write(f"\n[task_analyzer] ❌ Task Analyzer 執行失敗 (非流式): {str(analyzer_error)}\n")
        sys.stderr.flush()
        logger.warning(
            f"Task Analyzer failed: request_id={request_id}, error={str(analyzer_error)}",
            exc_info=True,
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
            user=current_user,  # 修改時間：2026-01-02 - 傳遞 user 對象用於權限檢查
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

    # 修改時間：2026-01-27 - 如果選擇了 Agent，先調用 Agent 的工具獲取結果
    agent_tool_results = []
    if task_analyzer_result and task_analyzer_result.decision_result:
        chosen_agent_id = task_analyzer_result.decision_result.chosen_agent
        is_fast_path = (
            task_analyzer_result.analysis_details.get("fast_path", False)
            if task_analyzer_result.analysis_details
            else False
        )

        logger.info(
            f"Agent execution check: request_id={request_id}, chosen_agent_id={chosen_agent_id}, "
            f"is_fast_path={is_fast_path}, user_selected_agent_id={user_selected_agent_id}"
        )

        if chosen_agent_id:
            import sys

            sys.stderr.write(
                f"\n[chat] 🤖 Agent 執行檢查：\n"
                f"  - chosen_agent_id: {chosen_agent_id}\n"
                f"  - is_fast_path: {is_fast_path}\n"
                f"  - 準備調用 Agent...\n"
            )
            sys.stderr.flush()

            try:
                from agents.services.registry.registry import get_agent_registry
                from mcp.client.client import MCPClient

                registry = get_agent_registry()
                agent_info = registry.get_agent_info(chosen_agent_id)

                sys.stderr.write(
                    f"\n[chat] 📦 Agent Registry 查詢結果：\n"
                    f"  - agent_info exists: {agent_info is not None}\n"
                    f"  - agent_status: {agent_info.status.value if agent_info else 'N/A'}\n"
                    f"  - agent_name: {agent_info.name if agent_info else 'N/A'}\n"
                    f"  - agent_capabilities: {agent_info.capabilities if agent_info else []}\n"
                )
                sys.stderr.flush()

                if agent_info and agent_info.status.value == "online":
                    logger.info(
                        f"Agent selected for execution: agent_id={chosen_agent_id}, "
                        f"agent_name={agent_info.name}, capabilities={agent_info.capabilities}"
                    )

                    sys.stderr.write("\n[chat] ✅ Agent 狀態正常，準備調用工具\n")
                    sys.stderr.flush()

                    # 修改時間：2026-01-27 - 外部 Agent 允許僅在 agent_display_configs 設定
                    # 因此即使沒有 endpoints.mcp / capabilities，也要優先嘗試透過 MCP Gateway 調用對應工具
                    mcp_endpoint = (
                        agent_info.endpoints.mcp
                        if agent_info.endpoints and agent_info.endpoints.mcp
                        else "gateway_default"
                    )
                    logger.info(
                        f"Calling agent MCP tools: agent_id={chosen_agent_id}, "
                        f"mcp_endpoint={mcp_endpoint}, query='{last_user_text[:200]}...'"
                    )

                    # 根據用戶查詢選擇合適的工具
                    # 例如：如果查詢包含「料號」，使用 warehouse_query_part
                    # 如果查詢包含「列出」，使用 warehouse_execute_task
                    tool_name: Optional[str] = None

                    # 優先匹配：根據查詢內容選擇最合適的工具
                    query_lower = last_user_text.lower()
                    if "料號" in last_user_text or "料" in last_user_text or "part" in query_lower:
                        # 查找 warehouse_query_part 或類似的查詢工具
                        for cap in agent_info.capabilities:
                            cap_lower = cap.lower()
                            if "query_part" in cap_lower or (
                                "query" in cap_lower and "part" in cap_lower
                            ):
                                tool_name = cap
                                break
                        # 如果沒找到，嘗試其他查詢工具
                        if not tool_name:
                            for cap in agent_info.capabilities:
                                if "query" in cap.lower():
                                    tool_name = cap
                                    break
                    elif "列出" in last_user_text or "前" in last_user_text or "list" in query_lower:
                        # 查找 warehouse_execute_task 或類似的執行工具
                        for cap in agent_info.capabilities:
                            cap_lower = cap.lower()
                            if "execute" in cap_lower or "task" in cap_lower:
                                tool_name = cap
                                break

                    # 如果沒有找到特定工具，使用第一個可用的工具
                    if not tool_name and agent_info.capabilities:
                        tool_name = agent_info.capabilities[0]
                        logger.info(
                            f"Using first available agent tool: agent_id={chosen_agent_id}, "
                            f"tool_name={tool_name}, all_capabilities={agent_info.capabilities}"
                        )

                    # 修改時間：2026-01-27 - 若外部 Agent 沒有 capabilities，依名稱/領域做合理預設
                    if not tool_name and not agent_info.capabilities:
                        agent_name = agent_info.name or ""
                        agent_name_lower = agent_name.lower()
                        if (
                            "庫存" in agent_name
                            or "物料" in agent_name
                            or "inventory" in agent_name_lower
                            or "warehouse" in agent_name_lower
                        ):
                            tool_name = "warehouse_execute_task"
                        elif "財務" in agent_name or "finance" in agent_name_lower:
                            tool_name = "finance_execute_task"
                        elif "office" in agent_name_lower:
                            tool_name = "office_execute_task"

                        if tool_name:
                            logger.info(
                                f"Agent tool default selected: agent_id={chosen_agent_id}, "
                                f"agent_name={agent_name}, tool_name={tool_name} (no capabilities in registry)"
                            )

                    if tool_name:
                        import sys

                        sys.stderr.write(
                            f"\n[chat] 🔧 準備調用 Agent 工具：\n"
                            f"  - tool_name: {tool_name}\n"
                            f"  - mcp_endpoint: {mcp_endpoint}\n"
                            f"  - user_query: {last_user_text[:100]}...\n"
                        )
                        sys.stderr.flush()

                        try:
                            # 通過 MCP Gateway 調用工具
                            gateway_endpoint = os.getenv(
                                "MCP_GATEWAY_ENDPOINT", "https://mcp.k84.org"
                            )

                            sys.stderr.write(
                                f"\n[chat] 🔗 連接 MCP Gateway：\n"
                                f"  - gateway_endpoint: {gateway_endpoint}\n"
                            )
                            sys.stderr.flush()

                            mcp_client = MCPClient(endpoint=gateway_endpoint, timeout=30.0)
                            await mcp_client.initialize()

                            sys.stderr.write("\n[chat] ✅ MCP Client 初始化成功\n")
                            sys.stderr.flush()

                            # 構建工具參數（根據用戶查詢）
                            tool_arguments = {
                                "query": last_user_text,
                                "task": last_user_text,
                            }

                            sys.stderr.write(
                                f"\n[chat] 📤 調用工具：\n"
                                f"  - tool_name: {tool_name}\n"
                                f"  - tool_arguments: {tool_arguments}\n"
                            )
                            sys.stderr.flush()

                            # 調用工具
                            tool_result = await mcp_client.call_tool(
                                name=tool_name,
                                arguments=tool_arguments,
                            )

                            sys.stderr.write(
                                f"\n[chat] ✅ 工具調用成功：\n"
                                f"  - tool_result type: {type(tool_result)}\n"
                                f"  - tool_result length: {len(str(tool_result)) if tool_result else 0}\n"
                            )
                            sys.stderr.flush()

                            await mcp_client.close()

                            # 將工具結果添加到消息中
                            if tool_result:
                                # 將工具結果格式化為消息，注入到 LLM 上下文
                                tool_result_text = str(
                                    tool_result.get("text", tool_result)
                                    if isinstance(tool_result, dict)
                                    else tool_result
                                )
                                agent_result_message = {
                                    "role": "system",
                                    "content": (
                                        f"Agent '{agent_info.name}' 執行工具 '{tool_name}' 的結果：\n"
                                        f"{tool_result_text}"
                                    ),
                                }
                                # 將 Agent 工具結果消息添加到列表中，稍後插入到 messages_for_llm
                                agent_tool_results.append(
                                    {
                                        "tool_name": tool_name,
                                        "result": tool_result,
                                        "message": agent_result_message,
                                    }
                                )

                                logger.info(
                                    "agent_tool_executed",
                                    request_id=request_id,
                                    agent_id=chosen_agent_id,
                                    tool_name=tool_name,
                                    result_length=len(tool_result_text),
                                )
                        except Exception as agent_error:
                            import sys

                            sys.stderr.write(
                                f"\n[chat] ❌ Agent 工具執行失敗：\n"
                                f"  - agent_id: {chosen_agent_id}\n"
                                f"  - tool_name: {tool_name}\n"
                                f"  - error: {str(agent_error)}\n"
                                f"  - error_type: {type(agent_error).__name__}\n"
                            )
                            sys.stderr.flush()

                            logger.error(
                                "agent_tool_execution_failed",
                                request_id=request_id,
                                agent_id=chosen_agent_id,
                                tool_name=tool_name,
                                error=str(agent_error),
                                exc_info=True,
                            )
                            # Agent 工具執行失敗不影響主流程，繼續執行
            except Exception as agent_registry_error:
                import sys

                sys.stderr.write(
                    f"\n[chat] ❌ Agent Registry 查找失敗：\n"
                    f"  - chosen_agent_id: {chosen_agent_id}\n"
                    f"  - error: {str(agent_registry_error)}\n"
                    f"  - error_type: {type(agent_registry_error).__name__}\n"
                )
                sys.stderr.flush()

                logger.warning(
                    "agent_registry_lookup_failed",
                    request_id=request_id,
                    error=str(agent_registry_error),
                    exc_info=True,
                )
                # Agent 查找失敗不影響主流程，繼續執行
        else:
            import sys

            sys.stderr.write(
                f"\n[chat] ⚠️  Agent 執行檢查失敗：\n"
                f"  - chosen_agent_id is None or empty\n"
                f"  - has_task_analyzer_result: {task_analyzer_result is not None}\n"
                f"  - has_decision_result: {task_analyzer_result.decision_result is not None if task_analyzer_result else False}\n"
                f"  - user_selected_agent_id: {user_selected_agent_id}\n"
            )
            sys.stderr.flush()

    base_system = system_messages[:1] if system_messages else []
    messages_for_llm = base_system + memory_result.injection_messages + windowed_history

    # 將 Agent 工具結果消息插入到 messages_for_llm 開頭（優先級最高）
    for tool_result_item in agent_tool_results:
        if "message" in tool_result_item:
            messages_for_llm.insert(0, tool_result_item["message"])

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
            # 修改時間：2026-01-06 - 如果 Task Analyzer 選擇了 document_editing 工具，強制創建文件
            force_create = False
            if task_analyzer_result:
                decision_result = task_analyzer_result.decision_result
                if (
                    decision_result
                    and decision_result.chosen_tools
                    and (
                        "document_editing" in decision_result.chosen_tools
                        or "file_editing" in decision_result.chosen_tools
                    )
                ):
                    force_create = True
                    logger.info(
                        "force_create_file_based_on_task_analyzer",
                        request_id=request_id,
                        chosen_tools=decision_result.chosen_tools,
                        note="Task Analyzer identified document creation intent via semantic analysis",
                    )

            create_action = _try_create_file_from_chat_output(
                user_text=last_user_text,
                assistant_text=content,
                task_id=task_id,
                current_user=current_user,
                force_create=force_create,
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
    import time

    stream_start_time = time.time()

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
    last_user_text = messages[-1].get("content", "") if messages else ""

    # 修改時間：2026-01-06 - 在入口處添加詳細日誌，使用標準 logging 確保日誌被記錄
    import logging

    std_logger = logging.getLogger("api.routers.chat")
    std_logger.info(
        f"[{request_id}] chat_product_stream START - task_id={task_id}, user_id={current_user.user_id}, "
        f"user_text={last_user_text[:100]}, session_id={session_id}"
    )

    # 記錄工具信息
    allowed_tools = request_body.allowed_tools or []

    # 修改時間：2026-01-06 - 文件編輯時自動添加 datetime 工具
    # 如果 Assistant 支持文件編輯（document_editing），自動添加 datetime 工具用於記錄時間戳
    if "document_editing" in allowed_tools or "file_editing" in allowed_tools:
        if "datetime" not in allowed_tools:
            allowed_tools.append("datetime")
            logger.info(f"Auto-added datetime tool for file editing: request_id={request_id}")

    # 添加详细的工具日志
    logger.info(
        f"Chat request tools received: request_id={request_id}, allowed_tools={allowed_tools}"
    )
    logger.info(f"Chat request tools: session_id={session_id}, task_id={task_id}")

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

            # ============================================
            # 快速路径：直接检测时间查询并执行 DateTimeTool（绕过 Task Analyzer）
            # ============================================
            time_keywords = ["時間", "時刻", "現在幾點", "現在時間", "current time", "what time"]
            last_user_text_lower = last_user_text.lower().strip()
            is_time_query = any(keyword in last_user_text_lower for keyword in time_keywords)

            if is_time_query:
                logger.info(f"Quick path datetime query: request_id={request_id}")
                try:
                    from tools.time import DateTimeInput, DateTimeTool

                    datetime_tool = DateTimeTool()
                    datetime_input = DateTimeInput(
                        tenant_id=(
                            current_user.tenant_id if hasattr(current_user, "tenant_id") else None
                        ),
                        user_id=current_user.user_id,
                    )
                    tool_result = await datetime_tool.execute(datetime_input)

                    # 格式化时间结果
                    time_response = f"現在的時間是：{tool_result.datetime}"
                    if hasattr(tool_result, "timezone"):
                        time_response += f"（時區：{tool_result.timezone}）"

                    logger.info(f"Quick path datetime success: {tool_result.datetime}")

                    # 返回 SSE 格式的流式响应
                    yield f"data: {json.dumps({'type': 'start', 'data': {'request_id': request_id, 'session_id': session_id}})}\n\n"
                    yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': time_response}})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"
                    return
                except Exception as e:
                    logger.error(
                        f"Quick path datetime failed: {str(e)}",
                        exc_info=True,
                    )
                    # 如果快速路径失败，继续执行 Task Analyzer 流程

            # ============================================
            # 集成 Task Analyzer（4 层渐进式路由架构）
            # ============================================
            task_analyzer_result = None
            try:
                # 修改時間：2026-01-06 - 添加調試日誌確認代碼執行路徑
                import sys

                sys.stderr.write(
                    f"\n[task_analyzer] 🔍 開始調用 Task Analyzer，用戶查詢: {last_user_text[:100]}...\n"
                )
                sys.stderr.flush()

                task_analyzer = get_task_analyzer()
                # 修改時間：2026-01-27 - 如果用戶明確選擇了 agent_id，優先使用用戶選擇的 Agent（流式版本）
                user_selected_agent_id = request_body.agent_id

                # 修改時間：2026-01-27 - 添加完整的請求參數日誌（流式版本）
                import sys
                from datetime import datetime

                sys.stderr.write(
                    f"\n[chatMessage] 📥 後端接收聊天請求（流式）：\n"
                    f"  - request_id: {request_id}\n"
                    f"  - task_id: {task_id}\n"
                    f"  - session_id: {session_id}\n"
                    f"  - user_id: {current_user.user_id}\n"
                    f"  - assistant_id: {request_body.assistant_id or '未選擇'}\n"
                    f"  - agent_id: {request_body.agent_id or '未選擇'}\n"
                    f"  - model_selector: {request_body.model_selector}\n"
                    f"  - allowed_tools: {request_body.allowed_tools or []}\n"
                    f"  - message_count: {len(messages)}\n"
                    f"  - last_user_text: {last_user_text[:100]}...\n"
                    f"  - attachments_count: {len(request_body.attachments) if request_body.attachments else 0}\n"
                    f"  - timestamp: {datetime.now().isoformat()}\n"
                )
                sys.stderr.flush()

                logger.info(
                    f"chatMessage stream request: request_id={request_id}, task_id={task_id}, "
                    f"agent_id={request_body.agent_id}"
                )

                logger.info(
                    f"Preparing Task Analyzer (stream): agent_id={user_selected_agent_id}, task_id={task_id}"
                )

                # 修改時間：2026-01-06 - 將 allowed_tools 傳遞給 Task Analyzer，讓 Capability Matcher 優先考慮啟用的工具
                analysis_result = await task_analyzer.analyze(
                    TaskAnalysisRequest(
                        task=last_user_text,
                        context={
                            "user_id": current_user.user_id,
                            "session_id": session_id,
                            "task_id": task_id,
                            "request_id": request_id,
                            "allowed_tools": allowed_tools,  # ✅ 傳遞 allowed_tools
                            "agent_id": user_selected_agent_id,  # ✅ 傳遞用戶選擇的 agent_id
                        },
                        user_id=current_user.user_id,
                        session_id=session_id,
                        specified_agent_id=user_selected_agent_id,  # ✅ 設置 specified_agent_id，讓 Task Analyzer 優先使用用戶選擇的 Agent
                    )
                )

                logger.info("[DEBUG-A] Task Analyzer 調用完成")

                task_analyzer_result = analysis_result

                logger.info(
                    f"[DEBUG-B] task_analyzer_result 賦值完成: {task_analyzer_result is not None}"
                )

                # 添加詳細日誌追蹤分析結果（流式版本）
                if task_analyzer_result:
                    logger.info(
                        f"[DEBUG-C] chosen_agent={task_analyzer_result.decision_result.chosen_agent if task_analyzer_result.decision_result else None}, "
                        f"fast_path={task_analyzer_result.analysis_details.get('fast_path', False) if task_analyzer_result.analysis_details else False}"
                    )

                # 修改時間：2026-01-06 - 添加詳細的 Console Log 輸出 Task Analyzer 分析結果
                # 使用 sys.stderr 確保輸出到控制台（不被重定向）

                log_lines = []
                log_lines.append("\n" + "=" * 80)
                log_lines.append("[task_analyzer] Task Analyzer 分析結果 (流式)")
                log_lines.append("=" * 80)
                log_lines.append(f"[task_analyzer] 用戶查詢: {last_user_text}")
                log_lines.append(f"[task_analyzer] Request ID: {request_id}")
                log_lines.append(f"[task_analyzer] Task ID: {task_id}")
                log_lines.append(f"[task_analyzer] Session ID: {session_id}")
                log_lines.append(f"[task_analyzer] Allowed Tools: {allowed_tools}")

                if task_analyzer_result:
                    # Router Decision 信息
                    router_decision = (
                        task_analyzer_result.router_decision
                        if hasattr(task_analyzer_result, "router_decision")
                        else None
                    )
                    if router_decision:
                        log_lines.append("\n[task_analyzer] Router Decision:")
                        log_lines.append(f"  - Intent Type: {router_decision.intent_type}")
                        log_lines.append(f"  - Complexity: {router_decision.complexity}")
                        log_lines.append(f"  - Needs Agent: {router_decision.needs_agent}")
                        log_lines.append(f"  - Needs Tools: {router_decision.needs_tools}")
                        log_lines.append(
                            f"  - Determinism Required: {router_decision.determinism_required}"
                        )
                        log_lines.append(f"  - Risk Level: {router_decision.risk_level}")
                        log_lines.append(f"  - Confidence: {router_decision.confidence}")

                    # Decision Result 信息
                    decision_result = (
                        task_analyzer_result.decision_result
                        if hasattr(task_analyzer_result, "decision_result")
                        else None
                    )
                    if decision_result:
                        log_lines.append("\n[task_analyzer] Decision Result:")
                        log_lines.append(f"  - Chosen Agent: {decision_result.chosen_agent}")
                        log_lines.append(f"  - Chosen Tools: {decision_result.chosen_tools}")
                        log_lines.append(f"  - Chosen Model: {decision_result.chosen_model}")
                        log_lines.append(f"  - Score: {decision_result.score}")
                        log_lines.append(f"  - Reasoning: {decision_result.reasoning}")
                        log_lines.append(f"  - Fallback Used: {decision_result.fallback_used}")

                    # Analysis Details
                    analysis_details = (
                        task_analyzer_result.analysis_details
                        if hasattr(task_analyzer_result, "analysis_details")
                        else {}
                    )
                    if analysis_details:
                        log_lines.append("\n[task_analyzer] Analysis Details:")
                        log_lines.append(f"  - Layer: {analysis_details.get('layer', 'N/A')}")
                        log_lines.append(
                            f"  - Direct Answer: {analysis_details.get('direct_answer', False)}"
                        )
                        if analysis_details.get("direct_answer"):
                            log_lines.append(
                                f"  - Response: {str(analysis_details.get('response', ''))[:200]}..."
                            )

                    # 特別標註文件創建相關的判斷
                    if decision_result and decision_result.chosen_tools:
                        has_doc_editing = (
                            "document_editing" in decision_result.chosen_tools
                            or "file_editing" in decision_result.chosen_tools
                        )
                        log_lines.append("\n[task_analyzer] 📁 文件創建判斷:")
                        log_lines.append(f"  - Document Editing Tool Selected: {has_doc_editing}")
                        if has_doc_editing:
                            log_lines.append("  - ✅ 系統將嘗試創建文件")
                        else:
                            log_lines.append("  - ⚠️  未選擇 document_editing 工具，將使用關鍵詞匹配作為 fallback")
                else:
                    log_lines.append("\n[task_analyzer] ⚠️  Task Analyzer 結果為 None")

                log_lines.append("=" * 80 + "\n")

                # 輸出到 stderr（確保顯示在控制台）
                sys.stderr.write("\n🔍 [DEBUG-1] 準備輸出 log_lines\n")
                sys.stderr.flush()
                for line in log_lines:
                    sys.stderr.write(line + "\n")
                    sys.stderr.flush()

                sys.stderr.write("\n🔍 [DEBUG-2] log_lines 輸出完成，準備記錄 logger.info\n")
                sys.stderr.flush()

                # 修改時間：2026-01-06 - 添加詳細日誌追蹤 Task Analyzer 結果
                logger.info(
                    f"Task Analyzer result assigned (stream): has_result={task_analyzer_result is not None}, "
                    f"chosen_tools={task_analyzer_result.decision_result.chosen_tools if task_analyzer_result and task_analyzer_result.decision_result else None}"
                )

                sys.stderr.write("\n🔍 [DEBUG-3] logger.info 執行完成\n")
                sys.stderr.flush()

                # 修改時間：2026-01-27 - Agent 調用優先級檢查（流式版本）
                # 優先級順序：
                # 1. 用戶明確選擇 Agent（快速路徑）-> 直接調用 Agent，跳過所有其他檢查
                # 2. Task Analyzer 選擇了 Agent -> 調用 Agent
                # 3. Direct Answer -> 返回直接答案
                is_fast_path = (
                    analysis_result.analysis_details.get("fast_path", False)
                    if analysis_result.analysis_details
                    else False
                )
                has_direct_answer = (
                    analysis_result.analysis_details.get("direct_answer", False)
                    if analysis_result.analysis_details
                    else False
                )
                has_chosen_agent = (
                    (
                        analysis_result.decision_result is not None
                        and analysis_result.decision_result.chosen_agent is not None
                    )
                    if analysis_result
                    else False
                )

                sys.stderr.write(
                    f"\n[chat_stream] 🔍 Agent 調用優先級檢查（流式）：\n"
                    f"  - is_fast_path: {is_fast_path} (用戶明確選擇 Agent)\n"
                    f"  - has_chosen_agent: {has_chosen_agent} (Task Analyzer 選擇了 Agent)\n"
                    f"  - has_direct_answer: {has_direct_answer} (直接答案)\n"
                    f"  - 優先級：{'快速路徑 -> Agent' if is_fast_path else ('Agent' if has_chosen_agent else ('Direct Answer' if has_direct_answer else 'None'))}\n"
                )
                sys.stderr.flush()

                # 如果用戶明確選擇了 Agent（快速路徑），直接跳過 direct_answer 檢查，進入 Agent 調用流程
                if is_fast_path:
                    logger.info(
                        f"Fast path detected (stream): agent_id={analysis_result.analysis_details.get('specified_agent_id')}"
                    )
                # 如果 Task Analyzer 選擇了 Agent，也跳過 direct_answer 檢查
                elif has_chosen_agent:
                    logger.info(
                        f"Task Analyzer selected agent (stream): {analysis_result.decision_result.chosen_agent if analysis_result.decision_result else None}"
                    )
                # 只有在沒有選擇 Agent 的情況下，才返回直接答案
                elif has_direct_answer:
                    logger.info(
                        f"Task Analyzer direct answer (stream): layer={analysis_result.analysis_details.get('layer')}"
                    )
                    # 获取直接答案内容
                    response_content = analysis_result.analysis_details.get("response", "")
                    if response_content:
                        # 返回 SSE 格式的流式响应
                        yield f"data: {json.dumps({'type': 'start', 'data': {'request_id': request_id, 'session_id': session_id}})}\n\n"

                        # 流式输出（从 ArangoDB system_configs 读取配置）
                        chunk_size = get_streaming_chunk_size()
                        for i in range(0, len(response_content), chunk_size):
                            chunk = response_content[i : i + chunk_size]
                            yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': chunk}})}\n\n"
                            # 添加小延迟以模拟流式输出
                            await asyncio.sleep(0.01)

                        # 发送完成标记
                        yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"
                        return
            except Exception as analyzer_error:
                # Task Analyzer 失败不影响主流程，记录日志后继续
                import sys
                import traceback

                sys.stderr.write(f"\n[task_analyzer] ❌ Task Analyzer 執行失敗: {str(analyzer_error)}\n")
                sys.stderr.write(f"[task_analyzer] ❌ 錯誤堆棧:\n{traceback.format_exc()}\n")
                sys.stderr.flush()
                logger.warning(
                    f"Task Analyzer failed (stream): {str(analyzer_error)}",
                    exc_info=True,
                )

            # G3：用 windowed history 作為 MoE 的 messages（並保留前端提供的 system message）
            system_messages = [m for m in messages if m.get("role") == "system"]
            windowed_history = context_manager.get_context_with_window(session_id=session_id)

            # ============================================
            # WebSearch Fallback 逻辑：如果 Task Analyzer 需要工具但没有匹配的工具，fallback 到 WebSearch
            # ============================================
            should_trigger_web_search = False
            task_analyzer_has_chosen_tools = False

            if task_analyzer_result:
                # 检查 Task Analyzer 是否已经选择了工具
                decision_result = task_analyzer_result.decision_result
                router_decision = task_analyzer_result.router_decision

                logger.info(
                    f"Task Analyzer result check (stream): has_decision={decision_result is not None}, "
                    f"tools={decision_result.chosen_tools if decision_result else None}"
                )

                if (
                    decision_result
                    and decision_result.chosen_tools
                    and len(decision_result.chosen_tools) > 0
                ):
                    # Task Analyzer 已经选择了工具，应该优先使用这些工具
                    task_analyzer_has_chosen_tools = True
                    logger.info(
                        f"Task Analyzer has chosen tools (stream): {decision_result.chosen_tools}"
                    )

                    # 执行 Task Analyzer 选择的工具
                    try:
                        from tools import get_tool_registry
                        from tools.time import DateTimeInput, DateTimeTool
                        from tools.web_search import WebSearchInput, WebSearchTool

                        tool_registry = get_tool_registry()
                        tool_results = []

                        for tool_name in decision_result.chosen_tools:
                            tool = tool_registry.get_tool(tool_name)
                            if not tool:
                                logger.warning(
                                    "tool_not_found_in_registry",
                                    request_id=request_id,
                                    tool_name=tool_name,
                                )
                                continue

                            logger.info(
                                "executing_task_analyzer_tool",
                                request_id=request_id,
                                tool_name=tool_name,
                                user_text=last_user_text[:200],
                            )

                            # 根据工具类型执行工具
                            if tool_name == "datetime":
                                # 执行 DateTimeTool
                                datetime_tool = DateTimeTool()
                                datetime_input = DateTimeInput(
                                    tenant_id=(
                                        current_user.tenant_id
                                        if hasattr(current_user, "tenant_id")
                                        else None
                                    ),
                                    user_id=current_user.user_id,
                                )
                                tool_result = await datetime_tool.execute(datetime_input)
                                tool_results.append(
                                    {
                                        "tool_name": tool_name,
                                        "result": (
                                            tool_result.model_dump()
                                            if hasattr(tool_result, "model_dump")
                                            else str(tool_result)
                                        ),
                                    }
                                )

                                # 格式化时间结果用于返回给用户
                                if hasattr(tool_result, "datetime"):
                                    time_response = f"現在的時間是：{tool_result.datetime}"
                                    if hasattr(tool_result, "timezone"):
                                        time_response += f"（時區：{tool_result.timezone}）"

                                    # 返回 SSE 格式的流式响应
                                    yield f"data: {json.dumps({'type': 'start', 'data': {'request_id': request_id, 'session_id': session_id}})}\n\n"
                                    yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': time_response}})}\n\n"
                                    yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"
                                    return
                            elif tool_name == "web_search":
                                # WebSearchTool 会在后面的代码中处理
                                should_trigger_web_search = True
                            elif tool_name in ["document_editing", "file_editing"]:
                                # document_editing 工具：Task Analyzer 通過語義分析識別出需要文檔編輯工具
                                # 注意：這裡不依賴關鍵詞匹配，而是依賴 Task Analyzer 的語義分析結果
                                logger.info(
                                    "document_editing_tool_selected_by_task_analyzer",
                                    request_id=request_id,
                                    user_text=last_user_text[:200],
                                    note="Task Analyzer identified document editing intent via semantic analysis",
                                )
                                # document_editing 工具的執行會在 AI 回復生成後，通過 _try_create_file_from_chat_output 處理
                                # 這裡只記錄日志，實際的文檔生成會在 System Prompt 增強後由 AI 完成
                            else:
                                # 其他工具：尝试通用执行方式
                                logger.warning(
                                    "unknown_tool_type",
                                    request_id=request_id,
                                    tool_name=tool_name,
                                )

                        if tool_results:
                            logger.info(
                                "task_analyzer_tools_executed",
                                request_id=request_id,
                                tool_results_count=len(tool_results),
                            )
                    except Exception as tool_error:
                        logger.error(
                            "task_analyzer_tool_execution_failed",
                            request_id=request_id,
                            error=str(tool_error),
                            exc_info=True,
                        )
                        # 工具执行失败不影响主流程，继续执行
                elif (
                    router_decision
                    and router_decision.needs_tools
                    and decision_result
                    and (not decision_result.chosen_tools or len(decision_result.chosen_tools) == 0)
                ):
                    # 需要工具但没有匹配的工具，如果有 web_search 权限，则 fallback 到 WebSearch
                    if "web_search" in allowed_tools:
                        logger.info(
                            "task_analyzer_web_search_fallback",
                            request_id=request_id,
                            user_text=last_user_text[:200],
                            reason="needs_tools_but_no_matching_tools",
                        )
                        should_trigger_web_search = True

            # 工具调用：如果启用了 web_search 且（消息中包含搜索意图 或 Task Analyzer 建议 fallback 到 WebSearch），直接调用工具
            # 但是，如果 Task Analyzer 已经选择了工具，应该优先使用 Task Analyzer 的选择，而不是执行关键词匹配
            logger.info(
                "web_search_check",
                request_id=request_id,
                allowed_tools=allowed_tools,
                has_web_search="web_search" in (allowed_tools or []),
                user_text=last_user_text[:200],
                task_analyzer_has_chosen_tools=task_analyzer_has_chosen_tools,
            )

            # 添加 print 调试输出
            print(
                f"\n[DEBUG] web_search_check: allowed_tools={allowed_tools}, has_web_search={'web_search' in (allowed_tools or [])}, task_analyzer_has_chosen_tools={task_analyzer_has_chosen_tools}"
            )

            # 如果 Task Analyzer 已经选择了工具，跳过关键词匹配，优先使用 Task Analyzer 的选择
            # 但是，如果 Task Analyzer 选择的是 web_search，则允许执行 web_search
            if (
                (not task_analyzer_has_chosen_tools or should_trigger_web_search)
                and allowed_tools
                and "web_search" in allowed_tools
            ):
                # 检测是否需要搜索（简单的关键词检测）
                # 扩展关键词列表，包括更多搜索意图
                # 注意：从关键词列表中移除了"時間"和"時刻"，因为时间查询应该使用 DateTimeTool
                search_keywords = [
                    "上網",
                    "查詢",
                    "搜索",
                    "搜尋",
                    "現在",
                    # "時間",  # 移除：应该使用 DateTimeTool
                    # "時刻",  # 移除：应该使用 DateTimeTool
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
                    "股價",  # 股价查询
                    "股票",  # 股票查询
                    "天氣",  # 天气查询
                    "匯率",  # 汇率查询
                    "stock price",  # 股价查询（英文）
                    "weather",  # 天气查询（英文）
                    "exchange rate",  # 汇率查询（英文）
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

                if needs_search or should_trigger_web_search:
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
                    user=current_user,  # 修改時間：2026-01-02 - 傳遞 user 對象用於權限檢查
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

            # 修改時間：2026-01-27 - 如果選擇了 Agent，先調用 Agent 的工具獲取結果（流式版本）
            import sys

            sys.stderr.write(
                f"\n🔍 [DEBUG] 檢查 task_analyzer_result: {task_analyzer_result is not None}\n"
            )
            sys.stderr.write(
                f"🔍 [DEBUG] decision_result: {task_analyzer_result.decision_result is not None if task_analyzer_result else False}\n"
            )
            if task_analyzer_result and task_analyzer_result.decision_result:
                sys.stderr.write(
                    f"🔍 [DEBUG] chosen_agent from result: {task_analyzer_result.decision_result.chosen_agent}\n"
                )
            sys.stderr.flush()

            if task_analyzer_result and task_analyzer_result.decision_result:
                chosen_agent_id = task_analyzer_result.decision_result.chosen_agent
                is_fast_path = (
                    task_analyzer_result.analysis_details.get("fast_path", False)
                    if task_analyzer_result.analysis_details
                    else False
                )

                sys.stderr.write(
                    f"\n🤖 [DEBUG] Agent 執行檢查：chosen_agent_id={chosen_agent_id}, is_fast_path={is_fast_path}\n"
                )
                sys.stderr.flush()

                logger.info(
                    f"Agent execution check (stream): chosen_agent_id={chosen_agent_id}, "
                    f"is_fast_path={is_fast_path}"
                )

                if chosen_agent_id:
                    sys.stderr.write(f"\n✅ [DEBUG] chosen_agent_id 有值：{chosen_agent_id}\n")
                    sys.stderr.flush()
                    try:
                        from agents.services.registry.registry import get_agent_registry

                        registry = get_agent_registry()
                        agent_info = registry.get_agent_info(chosen_agent_id)

                        sys.stderr.write(f"📦 [DEBUG] agent_info: exists={agent_info is not None}, ")
                        if agent_info:
                            sys.stderr.write(
                                f"status={agent_info.status.value}, name={agent_info.name}\n"
                            )
                        else:
                            sys.stderr.write("agent_info is None!\n")
                        sys.stderr.flush()

                        # 临时跳过状态检查（用于测试）
                        # if agent_info and agent_info.status.value == "online":
                        if agent_info:  # 允许任何状态的 Agent 执行
                            logger.info(
                                f"Agent selected for execution (stream): agent_id={chosen_agent_id}, "
                                f"agent_name={agent_info.name}"
                            )

                            # 修改時間：2026-01-27 - 外部 Agent 允許僅在 agent_display_configs 設定
                            # 因此即使沒有 endpoints.mcp / capabilities，也要優先嘗試透過 MCP Gateway 調用對應工具（流式版本）
                            mcp_endpoint = (
                                agent_info.endpoints.mcp
                                if agent_info.endpoints and agent_info.endpoints.mcp
                                else "gateway_default"
                            )
                            logger.info(
                                f"Calling agent MCP tools (stream): agent_id={chosen_agent_id}, "
                                f"mcp_endpoint={mcp_endpoint}"
                            )

                            # 根據用戶查詢選擇合適的工具
                            tool_name: Optional[str] = None

                            # 優先匹配：根據查詢內容選擇最合適的工具
                            query_lower = last_user_text.lower()
                            if (
                                "料號" in last_user_text
                                or "料" in last_user_text
                                or "part" in query_lower
                            ):
                                # 查找 warehouse_query_part 或類似的查詢工具
                                for cap in agent_info.capabilities:
                                    cap_lower = cap.lower()
                                    if "query_part" in cap_lower or (
                                        "query" in cap_lower and "part" in cap_lower
                                    ):
                                        tool_name = cap
                                        break
                                # 如果沒找到，嘗試其他查詢工具
                                if not tool_name:
                                    for cap in agent_info.capabilities:
                                        if "query" in cap.lower():
                                            tool_name = cap
                                            break
                            elif (
                                "列出" in last_user_text
                                or "前" in last_user_text
                                or "list" in query_lower
                            ):
                                # 查找 warehouse_execute_task 或類似的執行工具
                                for cap in agent_info.capabilities:
                                    cap_lower = cap.lower()
                                    if "execute" in cap_lower or "task" in cap_lower:
                                        tool_name = cap
                                        break

                            # 如果沒有找到特定工具，使用第一個可用的工具
                            if not tool_name and agent_info.capabilities:
                                tool_name = agent_info.capabilities[0]
                                logger.info(
                                    f"Using first available agent tool (stream): agent_id={chosen_agent_id}, tool_name={tool_name}"
                                )

                            # 修改時間：2026-01-27 - 若外部 Agent 沒有 capabilities，依名稱/領域做合理預設（流式）
                            if not tool_name and not agent_info.capabilities:
                                agent_name = agent_info.name or ""
                                agent_name_lower = agent_name.lower()
                                if (
                                    "庫存" in agent_name
                                    or "物料" in agent_name
                                    or "inventory" in agent_name_lower
                                    or "warehouse" in agent_name_lower
                                ):
                                    tool_name = "warehouse_execute_task"
                                elif "財務" in agent_name or "finance" in agent_name_lower:
                                    tool_name = "finance_execute_task"
                                elif "office" in agent_name_lower:
                                    tool_name = "office_execute_task"

                                if tool_name:
                                    logger.info(
                                        "agent_tool_default_selected_stream",
                                        request_id=request_id,
                                        agent_id=chosen_agent_id,
                                        agent_name=agent_name,
                                        tool_name=tool_name,
                                        reason="agent_has_no_capabilities_in_registry",
                                    )

                            if tool_name:
                                import sys

                                sys.stderr.write(
                                    f"\n🔥 [DEBUG] if tool_name 块被执行！tool_name={tool_name}, chosen_agent_id={chosen_agent_id}\n"
                                )
                                sys.stderr.flush()
                                try:
                                    # 【修改】从 Agent Registry 读取正确的 endpoint 和 protocol
                                    import httpx

                                    # 从 Agent Registry 获取 endpoint 配置
                                    agent_endpoint_url = None
                                    agent_protocol = "http"  # 默认

                                    if agent_info.endpoints:
                                        if agent_info.endpoints.mcp:
                                            agent_endpoint_url = agent_info.endpoints.mcp
                                            agent_protocol = "mcp"
                                        elif agent_info.endpoints.http:
                                            agent_endpoint_url = agent_info.endpoints.http
                                            agent_protocol = "http"

                                    # 如果没有配置 endpoint，使用系统配置的默认值
                                    if not agent_endpoint_url:
                                        agent_endpoint_url = get_mcp_default_endpoint()
                                        agent_protocol = "mcp"  # 默认使用 MCP 协议
                                        logger.warning(
                                            f"No endpoint configured for agent {chosen_agent_id}, "
                                            f"using MCP default: {agent_endpoint_url}"
                                        )

                                    sys.stderr.write(
                                        f"\n✅ [DEBUG] 准备调用 Agent：protocol={agent_protocol}, endpoint={agent_endpoint_url}\n"
                                    )
                                    sys.stderr.flush()

                                    logger.info(
                                        f"Calling Agent: agent_id={chosen_agent_id}, "
                                        f"protocol={agent_protocol}, endpoint={agent_endpoint_url}, tool_name={tool_name}"
                                    )

                                    # 構建標準 MCP JSON-RPC 請求（匹配 Warehouse Manager Agent 的格式）
                                    mcp_request = {
                                        "jsonrpc": "2.0",
                                        "id": 1,
                                        "method": "tools/call",
                                        "params": {
                                            "name": tool_name,
                                            "arguments": {
                                                "task_id": task_id,
                                                "task_type": "warehouse_query",
                                                "task_data": {
                                                    "instruction": last_user_text,  # Agent 期望的字段
                                                },
                                                "context": {
                                                    "request_id": request_id,
                                                    "session_id": session_id,
                                                },
                                                "metadata": {
                                                    "user_id": current_user.user_id,
                                                    "tenant_id": tenant_id or "default",
                                                },
                                            },
                                        },
                                    }

                                    # 構建請求頭（包含 Gateway Secret）
                                    headers = {
                                        "Content-Type": "application/json",
                                        "X-User-ID": current_user.user_id,
                                        "X-Tenant-ID": tenant_id or "default",
                                        "X-Tool-Name": tool_name,
                                    }

                                    # 添加 Gateway Secret（如果配置了）
                                    gateway_secret = os.getenv("MCP_GATEWAY_SECRET")
                                    if gateway_secret:
                                        headers["X-Gateway-Secret"] = gateway_secret
                                        logger.info(
                                            f"🔐 已添加 Gateway Secret: {gateway_secret[:16]}..."
                                        )

                                    # 調用 Gateway（根路徑，使用標準 MCP JSON-RPC 格式）
                                    async with httpx.AsyncClient(
                                        timeout=30.0, follow_redirects=True
                                    ) as client:
                                        logger.info(
                                            f"🚀 準備調用 Gateway: {agent_endpoint_url} (MCP JSON-RPC)"
                                        )
                                        logger.info(
                                            f"📦 MCP 請求: method={mcp_request['method']}, tool={tool_name}"
                                        )

                                        try:
                                            response = await client.post(
                                                agent_endpoint_url,  # 根路徑，不加 /execute
                                                json=mcp_request,
                                                headers=headers,
                                            )
                                            response.raise_for_status()
                                            mcp_response = response.json()
                                            logger.info(
                                                f"✅ Gateway 調用成功: status={response.status_code}"
                                            )

                                            # 打印完整的 MCP 響應（調試用）
                                            import json as json_lib

                                            mcp_response_str = json_lib.dumps(
                                                mcp_response, ensure_ascii=False, indent=2
                                            )[:1000]
                                            logger.info(
                                                f"📦 完整 MCP 響應（前1000字符）:\n{mcp_response_str}"
                                            )

                                            # 檢查 MCP JSON-RPC 錯誤
                                            if (
                                                isinstance(mcp_response, dict)
                                                and "error" in mcp_response
                                            ):
                                                error_info = mcp_response.get("error", {})
                                                logger.error(
                                                    f"❌ Gateway 返回錯誤: "
                                                    f"code={error_info.get('code')}, "
                                                    f"message={error_info.get('message')}, "
                                                    f"data={error_info.get('data')}"
                                                )
                                                logger.error(f"完整錯誤響應: {mcp_response}")
                                                # 將錯誤信息作為工具結果返回
                                                tool_result = {
                                                    "error": True,
                                                    "message": error_info.get(
                                                        "message", "Unknown error"
                                                    ),
                                                    "details": error_info.get("data"),
                                                }
                                            elif (
                                                isinstance(mcp_response, dict)
                                                and "result" in mcp_response
                                            ):
                                                # 從 MCP JSON-RPC 響應中提取 result
                                                tool_result = mcp_response["result"]
                                                logger.info(
                                                    f"✅ 從 MCP 響應提取結果: {type(tool_result).__name__}"
                                                )

                                                # 檢查 result 中是否包含失敗狀態
                                                if isinstance(tool_result, dict):
                                                    # 檢查標準 MCP 工具調用結果
                                                    if "content" in tool_result and isinstance(
                                                        tool_result["content"], list
                                                    ):
                                                        for content_item in tool_result["content"]:
                                                            if (
                                                                isinstance(content_item, dict)
                                                                and content_item.get("type")
                                                                == "text"
                                                            ):
                                                                text_content = content_item.get(
                                                                    "text", ""
                                                                )
                                                                # 嘗試解析 JSON
                                                                try:
                                                                    result_json = json_lib.loads(
                                                                        text_content
                                                                    )
                                                                    if isinstance(
                                                                        result_json, dict
                                                                    ):
                                                                        if (
                                                                            result_json.get(
                                                                                "status"
                                                                            )
                                                                            == "failed"
                                                                            or result_json.get(
                                                                                "success"
                                                                            )
                                                                            is False
                                                                        ):
                                                                            logger.error(
                                                                                f"❌ Agent 執行失敗: {result_json}"
                                                                            )
                                                                except Exception:
                                                                    pass
                                            else:
                                                logger.warning(
                                                    f"⚠️ 未預期的 MCP 響應格式: {list(mcp_response.keys()) if isinstance(mcp_response, dict) else type(mcp_response)}"
                                                )
                                                tool_result = mcp_response
                                        except httpx.HTTPStatusError as http_exc:
                                            logger.error(
                                                f"❌ Agent HTTP 錯誤: status={http_exc.response.status_code}, response={http_exc.response.text}"
                                            )
                                            raise
                                        except httpx.RequestError as req_exc:
                                            logger.error(
                                                f"❌ Agent 請求錯誤: {type(req_exc).__name__} - {str(req_exc)}"
                                            )
                                            raise

                                    # 將工具結果格式化為消息，注入到 LLM 上下文
                                    if tool_result:
                                        tool_result_text = str(
                                            tool_result.get("text", tool_result)
                                            if isinstance(tool_result, dict)
                                            else tool_result
                                        )
                                        agent_result_message = {
                                            "role": "system",
                                            "content": (
                                                f"Agent '{agent_info.name}' 執行工具 '{tool_name}' 的結果：\n"
                                                f"{tool_result_text}"
                                            ),
                                        }
                                        base_system.insert(0, agent_result_message)  # 插入到開頭，優先級最高

                                        logger.info(
                                            "agent_tool_executed_stream",
                                            request_id=request_id,
                                            agent_id=chosen_agent_id,
                                            tool_name=tool_name,
                                            result_length=len(tool_result_text),
                                        )
                                except Exception as agent_error:
                                    logger.error(
                                        "agent_tool_execution_failed_stream",
                                        request_id=request_id,
                                        agent_id=chosen_agent_id,
                                        tool_name=tool_name,
                                        error=str(agent_error),
                                        exc_info=True,
                                    )
                                    # Agent 工具執行失敗不影響主流程，繼續執行
                    except Exception as agent_registry_error:
                        logger.warning(
                            "agent_registry_lookup_failed_stream",
                            request_id=request_id,
                            error=str(agent_registry_error),
                            exc_info=True,
                        )
                        # Agent 查找失敗不影響主流程，繼續執行

            # 修改時間：2026-01-06 - 如果 Task Analyzer 選擇了 document_editing 工具，增強 System Prompt 指示 AI 生成文檔內容
            # 注意：這裡不依賴關鍵詞匹配，而是依賴 Task Analyzer 的語義分析結果
            if task_analyzer_result:
                decision_result = task_analyzer_result.decision_result
                if (
                    decision_result
                    and decision_result.chosen_tools
                    and (
                        "document_editing" in decision_result.chosen_tools
                        or "file_editing" in decision_result.chosen_tools
                    )
                ):
                    # Task Analyzer 通過語義分析識別出需要 document_editing 工具
                    # 解析目標文件名（如果用戶指定了）
                    folder_path, filename = _parse_target_path(last_user_text)
                    if not filename:
                        filename = _default_filename_for_intent(last_user_text)

                    # 構建文檔生成指示
                    doc_format = Path(filename).suffix.lower().lstrip(".")
                    if doc_format not in ["md", "txt", "json"]:
                        doc_format = "md"

                    # 添加 System Prompt 指示
                    document_generation_instruction = (
                        f"\n\n【重要：用戶要求生成文檔】\n"
                        f"用戶指令：{last_user_text}\n"
                        f"目標文件名：{filename}\n"
                        f"文檔格式：{doc_format}\n\n"
                        f"請根據用戶指令生成完整的文檔內容（Markdown 格式）。\n"
                        f"- 不要輸出解釋文字，只輸出文檔內容\n"
                        f"- 文檔應該包含完整的結構和內容\n"
                        f"- 如果用戶要求生成特定主題的文檔（如「Data Agent 的說明」），請生成該主題的完整文檔\n"
                        f"- 文檔應該包含標題、章節、詳細說明等完整內容\n"
                    )

                    # 將指示添加到 System Message
                    if base_system and len(base_system) > 0:
                        base_system[0]["content"] = (
                            base_system[0].get("content", "") + document_generation_instruction
                        )
                    else:
                        base_system = [
                            {"role": "system", "content": document_generation_instruction}
                        ]

                    logger.info(
                        "document_generation_intent_detected_via_task_analyzer",
                        request_id=request_id,
                        user_text=last_user_text[:200],
                        filename=filename,
                        doc_format=doc_format,
                        chosen_tools=decision_result.chosen_tools,
                        note="Task Analyzer identified document creation intent, added instruction to system prompt",
                    )

            messages_for_llm = base_system + memory_result.injection_messages + windowed_history

            # 調試：打印發送給 LLM 的消息
            logger.info(f"📨 發送給 LLM 的消息數量: {len(messages_for_llm)}")
            for idx, msg in enumerate(messages_for_llm):
                content_preview = str(msg.get("content", ""))[:200]
                logger.info(
                    f"  消息 {idx}: role={msg.get('role')}, content_length={len(str(msg.get('content', '')))}, preview={content_preview}"
                )

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

                logger.debug(
                    "model_selection_manual",
                    selected_model_id=selected_model_id,
                    inferred_provider=provider.value,
                    tenant_id=tenant_id,
                    user_id=current_user.user_id,
                )

                # G6：manual/favorite allowlist gate
                if not policy_gate.is_model_allowed(provider.value, selected_model_id):
                    logger.warning(
                        "model_not_allowed_by_policy",
                        model_id=selected_model_id,
                        provider=provider.value,
                        tenant_id=tenant_id,
                        user_id=current_user.user_id,
                    )
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
                    model_selector_mode=model_selector.mode,
                    task_classification=task_classification.type if task_classification else None,
                    tenant_id=tenant_id,
                    user_id=current_user.user_id,
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

            # 修改時間：2026-01-06 - 如果 Task Analyzer 選擇了 document_editing 工具，嘗試創建文件
            # 注意：這裡不依賴關鍵詞匹配，而是依賴 Task Analyzer 的語義分析結果
            try:
                # 添加詳細日誌追蹤
                logger.info(
                    "checking_file_creation_intent",
                    request_id=request_id,
                    has_task_analyzer_result=task_analyzer_result is not None,
                    task_id=task_id,
                    user_text=last_user_text[:200],
                    content_length=len(full_content),
                )

                if task_analyzer_result:
                    decision_result = task_analyzer_result.decision_result
                    logger.info(
                        f"Task Analyzer decision result check: has_decision={decision_result is not None}, "
                        f"chosen_tools={decision_result.chosen_tools if decision_result else None}"
                    )

                    if (
                        decision_result
                        and decision_result.chosen_tools
                        and (
                            "document_editing" in decision_result.chosen_tools
                            or "file_editing" in decision_result.chosen_tools
                        )
                    ):
                        # Task Analyzer 通過語義分析識別出需要 document_editing 工具
                        logger.info(
                            "document_editing_tool_detected_for_file_creation",
                            request_id=request_id,
                            chosen_tools=decision_result.chosen_tools,
                            task_id=task_id,
                            note="Attempting to create file",
                        )

                        # 嘗試創建文件（不依賴關鍵詞匹配）
                        create_action = _try_create_file_from_chat_output(
                            user_text=last_user_text,
                            assistant_text=full_content,
                            task_id=task_id,
                            current_user=current_user,
                            force_create=True,  # 強制創建，不依賴關鍵詞匹配
                        )
                        if create_action:
                            logger.info(
                                "file_created_from_stream",
                                request_id=request_id,
                                file_id=create_action.get("file_id"),
                                filename=create_action.get("filename"),
                                note="File created based on Task Analyzer semantic analysis",
                            )
                            # 發送文件創建事件
                            yield f"data: {json.dumps({'type': 'file_created', 'data': create_action})}\n\n"
                        else:
                            logger.warning(
                                "file_creation_returned_none",
                                request_id=request_id,
                                task_id=task_id,
                                user_text=last_user_text[:200],
                                note="File creation function returned None, check logs for details",
                            )
                    else:
                        # 修改時間：2026-01-06 - 添加詳細日誌追蹤為什麼沒有選擇 document_editing 工具
                        router_decision = (
                            task_analyzer_result.router_decision
                            if task_analyzer_result
                            and hasattr(task_analyzer_result, "router_decision")
                            else None
                        )
                        logger.info(
                            "document_editing_tool_not_detected",
                            request_id=request_id,
                            has_decision_result=decision_result is not None,
                            chosen_tools=decision_result.chosen_tools if decision_result else None,
                            router_needs_tools=(
                                router_decision.needs_tools if router_decision else None
                            ),
                            router_intent_type=(
                                router_decision.intent_type if router_decision else None
                            ),
                            router_confidence=(
                                router_decision.confidence if router_decision else None
                            ),
                            user_text=last_user_text[:200],
                            note="❌ Task Analyzer did not select document_editing tool - check Router LLM, Capability Matcher, and Decision Engine logs",
                        )

                        # 修改時間：2026-01-06 - Fallback：如果 Task Analyzer 沒有選擇 document_editing 工具，但用戶文本包含文件創建關鍵詞，也嘗試創建文件
                        if _looks_like_create_file_intent(last_user_text):
                            logger.info(
                                "fallback_to_keyword_matching_for_file_creation",
                                request_id=request_id,
                                task_id=task_id,
                                user_text=last_user_text[:200],
                                note="Task Analyzer did not select document_editing tool, but user text contains file creation keywords - attempting file creation via keyword matching",
                            )

                            # 嘗試創建文件（使用關鍵詞匹配）
                            create_action = _try_create_file_from_chat_output(
                                user_text=last_user_text,
                                assistant_text=full_content,
                                task_id=task_id,
                                current_user=current_user,
                                force_create=False,  # 使用關鍵詞匹配
                            )
                            if create_action:
                                logger.info(
                                    "file_created_from_stream_via_keyword_fallback",
                                    request_id=request_id,
                                    file_id=create_action.get("file_id"),
                                    filename=create_action.get("filename"),
                                    note="File created via keyword matching fallback",
                                )
                                # 發送文件創建事件
                                yield f"data: {json.dumps({'type': 'file_created', 'data': create_action})}\n\n"
                            else:
                                logger.warning(
                                    "file_creation_fallback_returned_none",
                                    request_id=request_id,
                                    task_id=task_id,
                                    user_text=last_user_text[:200],
                                    note="File creation via keyword matching returned None, check logs for details",
                                )
                else:
                    logger.info(
                        "no_task_analyzer_result",
                        request_id=request_id,
                        note="Task Analyzer result is None, cannot check for document creation intent",
                    )

                    # 修改時間：2026-01-06 - Fallback：如果 Task Analyzer 結果為 None，但用戶文本包含文件創建關鍵詞，也嘗試創建文件
                    if _looks_like_create_file_intent(last_user_text):
                        logger.info(
                            "fallback_to_keyword_matching_no_task_analyzer",
                            request_id=request_id,
                            task_id=task_id,
                            user_text=last_user_text[:200],
                            note="Task Analyzer result is None, but user text contains file creation keywords - attempting file creation via keyword matching",
                        )

                        # 嘗試創建文件（使用關鍵詞匹配）
                        create_action = _try_create_file_from_chat_output(
                            user_text=last_user_text,
                            assistant_text=full_content,
                            task_id=task_id,
                            current_user=current_user,
                            force_create=False,  # 使用關鍵詞匹配
                        )
                        if create_action:
                            logger.info(
                                "file_created_from_stream_via_keyword_fallback_no_analyzer",
                                request_id=request_id,
                                file_id=create_action.get("file_id"),
                                filename=create_action.get("filename"),
                                note="File created via keyword matching fallback (no Task Analyzer result)",
                            )
                            # 發送文件創建事件
                            yield f"data: {json.dumps({'type': 'file_created', 'data': create_action})}\n\n"
                        else:
                            logger.warning(
                                "file_creation_fallback_no_analyzer_returned_none",
                                request_id=request_id,
                                task_id=task_id,
                                user_text=last_user_text[:200],
                                note="File creation via keyword matching returned None (no Task Analyzer result), check logs for details",
                            )
            except Exception as file_create_exc:
                stream_elapsed_time = time.time() - stream_start_time
                std_logger.error(
                    f"[{request_id}] file_creation_failed_in_stream after {stream_elapsed_time:.2f}s - {file_create_exc}",
                    exc_info=True,
                )
                logger.error(
                    "file_creation_failed_in_stream",
                    request_id=request_id,
                    error=str(file_create_exc),
                    exc_info=True,
                )

        except Exception as exc:
            stream_elapsed_time = time.time() - stream_start_time
            std_logger.error(
                f"[{request_id}] chat_product_stream ERROR after {stream_elapsed_time:.2f}s - {exc}",
                exc_info=True,
            )
            logger.error(f"Streaming chat error: {exc}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(exc)}})}\n\n"

        # 修改時間：2026-01-06 - 在流式響應結束時記錄完成日誌
        stream_elapsed_time = time.time() - stream_start_time
        std_logger.info(
            f"[{request_id}] chat_product_stream COMPLETE - elapsed_time={stream_elapsed_time:.2f}s, "
            f"task_id={task_id}, user_id={current_user.user_id}"
        )

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
                user=current_user,  # 修改時間：2026-01-02 - 傳遞 user 對象用於權限檢查
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
    logger.debug(
        "models_before_policy_filter",
        count=len(items),
        providers=[m.get("provider") for m in items[:10]],  # 只记录前10个
    )

    if not include_disallowed:
        items = [
            m
            for m in items
            if policy_gate.is_model_allowed(
                str(m.get("provider") or ""),
                str(m.get("model_id") or ""),
            )
        ]
        logger.debug(
            "models_after_policy_filter",
            count=len(items),
            providers=[m.get("provider") for m in items[:10]],
        )

    # 過濾掉未激活的模型（只返回已配置 API key 或 Ollama 模型）
    try:
        # 使用 config_resolver 檢查 API key（支持全局、租戶、用戶三級配置）
        # 緩存每個 provider 的 API key 狀態
        provider_status_cache: Dict[str, bool] = {}

        active_items = []
        for m in items:
            provider = str(m.get("provider") or "").lower()
            model_id = str(m.get("model_id") or "")

            # Auto 模型和 Ollama 模型默認可用
            if provider in ("auto", "ollama"):
                active_items.append(m)
                continue

            # 對於需要 API key 的 provider，檢查是否已配置（檢查全局、租戶、用戶三級配置）
            if provider not in provider_status_cache:
                # 使用 config_resolver 檢查 API key（優先級：用戶 > 租戶）
                api_key = config_resolver.resolve_api_key(
                    tenant_id=tenant_id,
                    user_id=current_user.user_id,
                    provider=provider,
                )
                # 如果沒有找到 API key，也檢查全局配置（llm_provider_config_service）
                if not api_key:
                    try:
                        from services.api.models.llm_model import LLMProvider
                        from services.api.services.llm_provider_config_service import (
                            get_llm_provider_config_service,
                        )

                        global_config_service = get_llm_provider_config_service()
                        provider_enum = LLMProvider(provider)
                        status_obj = global_config_service.get_status(provider_enum)
                        has_global_key = status_obj.has_api_key if status_obj else False
                        provider_status_cache[provider] = has_global_key
                        if not has_global_key:
                            logger.debug(
                                "model_not_active_no_api_key",
                                provider=provider,
                                model_id=model_id,
                                tenant_id=tenant_id,
                                user_id=current_user.user_id,
                            )
                    except (ValueError, Exception) as e:
                        # Provider 不存在或檢查失敗，視為未激活
                        provider_status_cache[provider] = False
                        logger.debug(
                            "model_not_active_provider_error",
                            provider=provider,
                            model_id=model_id,
                            error=str(e),
                        )
                else:
                    # 找到了 API key（來自用戶或租戶配置）
                    provider_status_cache[provider] = True
                    logger.debug(
                        "model_active_api_key_found",
                        provider=provider,
                        model_id=model_id,
                        source="tenant_or_user",
                    )

            # 只有已配置 API key 的 provider 的模型才返回
            if provider_status_cache.get(provider, False):
                active_items.append(m)

        items = active_items
        logger.debug(
            "models_after_active_filter",
            count=len(items),
            providers=[m.get("provider") for m in items[:10]],
            provider_status=provider_status_cache,
        )
    except Exception as e:
        logger.warning("active_status_check_failed", error=str(e))
        # 如果檢查失敗，返回所有模型（保持向後兼容）

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
    import logging

    std_logger = logging.getLogger("api.routers.chat")

    user_id = current_user.user_id
    normalized: list[str] = []  # 修改時間：2026-01-06 - 確保 normalized 變量始終被定義

    std_logger.info(
        f"set_favorite_models START - user_id={user_id}, model_ids_count={len(request_body.model_ids)}"
    )

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

        std_logger.info(
            f"set_favorite_models SUCCESS - user_id={user_id}, normalized_count={len(normalized)}"
        )
    except Exception as exc:  # noqa: BLE001
        std_logger.error(
            f"set_favorite_models ERROR - user_id={user_id}, error={exc}",
            exc_info=True,
        )
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

        std_logger.info(
            f"set_favorite_models FALLBACK - user_id={user_id}, normalized_count={len(normalized)}"
        )

    return APIResponse.success(
        data={"model_ids": normalized},
        message="Favorite models updated",
    )
