"""
代碼功能說明: Chat 路由依賴注入函數（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

提取自 chat.py 的依賴注入函數，提供統一的服務實例管理。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from api.routers.chat_module.services.chat_pipeline import ChatPipeline

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.classifier import TaskClassifier
from database.arangodb import ArangoDBClient
from genai.workflows.context.manager import ContextManager
from llm.moe.moe_manager import LLMMoEManager
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import FilePermissionService
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section

# 全局單例變量
_moe_manager: Optional[LLMMoEManager] = None
_task_classifier: Optional[TaskClassifier] = None
_task_analyzer: Optional[TaskAnalyzer] = None
_context_manager: Optional[ContextManager] = None
_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None
_arango_client: Optional[ArangoDBClient] = None
_file_permission_service: Optional[FilePermissionService] = None


def get_moe_manager() -> LLMMoEManager:
    """獲取 MoE Manager 單例"""
    global _moe_manager
    if _moe_manager is None:
        _moe_manager = LLMMoEManager()
    return _moe_manager


def get_task_classifier() -> TaskClassifier:
    """獲取 Task Classifier 單例"""
    global _task_classifier
    if _task_classifier is None:
        _task_classifier = TaskClassifier()
    return _task_classifier


def get_task_analyzer() -> TaskAnalyzer:
    """獲取 Task Analyzer 單例"""
    global _task_analyzer
    if _task_analyzer is None:
        _task_analyzer = TaskAnalyzer()
    return _task_analyzer


def get_context_manager() -> ContextManager:
    """
    Context 單例入口。

    - recorder: Redis 優先、memory fallback（由 ContextRecorder 內部處理）
    - window: ContextWindow（由 ContextManager 內部處理）
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def get_storage() -> FileStorage:
    """獲取 File Storage 單例"""
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}
        _storage = create_storage_from_config(config)
    return _storage


def get_metadata_service() -> FileMetadataService:
    """獲取 File Metadata Service 單例"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


def get_arango_client() -> ArangoDBClient:
    """獲取 ArangoDB Client 單例"""
    global _arango_client
    if _arango_client is None:
        _arango_client = ArangoDBClient()
    return _arango_client


def get_file_permission_service() -> FilePermissionService:
    """獲取 File Permission Service 單例"""
    global _file_permission_service
    if _file_permission_service is None:
        _file_permission_service = FilePermissionService()
    return _file_permission_service


# 階段一：限流與緩存單例
_rate_limiter: Optional[object] = None
_cache_middleware: Optional[object] = None


def get_rate_limiter() -> object:
    """獲取限流器單例（用於 Depends）。"""
    global _rate_limiter
    if _rate_limiter is None:
        from api.routers.chat_module.middleware.rate_limiter import get_rate_limiter as _get

        _rate_limiter = _get()
    return _rate_limiter


def get_cache_middleware() -> object:
    """獲取緩存中間件單例（用於 Depends）。"""
    global _cache_middleware
    if _cache_middleware is None:
        from api.routers.chat_module.middleware.cache_middleware import (
            get_cache_middleware_instance,
        )

        _cache_middleware = get_cache_middleware_instance()
    return _cache_middleware


# 階段二 b：Chat Pipeline 單例
_chat_pipeline: Optional[object] = None


def get_chat_pipeline() -> "ChatPipeline":
    """獲取 ChatPipeline 單例（用於 SyncHandler.handle）。"""
    global _chat_pipeline
    if _chat_pipeline is None:
        from api.routers.chat_module.services.chat_pipeline import ChatPipeline

        _chat_pipeline = ChatPipeline()
    return _chat_pipeline  # type: ignore[return-value]
