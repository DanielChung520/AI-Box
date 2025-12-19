# 代碼功能說明: 文件上傳狀態服務（WBS-3.7: 文件上傳流程重構）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""文件上傳狀態服務

提供文件上傳進度和處理狀態的 CRUD 操作，替代 Redis 存儲。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.upload_status import (
    ProcessingStageStatus,
    ProcessingStatusCreate,
    ProcessingStatusModel,
    ProcessingStatusUpdate,
    UploadProgressCreate,
    UploadProgressModel,
    UploadProgressUpdate,
)

logger = structlog.get_logger(__name__)

UPLOAD_PROGRESS_COLLECTION = "upload_progress"
PROCESSING_STATUS_COLLECTION = "processing_status"


def _document_to_upload_progress(doc: Dict[str, Any]) -> UploadProgressModel:
    """將 ArangoDB document 轉換為 UploadProgressModel"""
    file_id = doc.get("_key") or doc.get("file_id")
    status = doc.get("status")
    if not file_id or not isinstance(file_id, str):
        raise ValueError(f"Invalid file_id: {file_id}")
    if not status or not isinstance(status, str):
        raise ValueError(f"Invalid status: {status}")
    return UploadProgressModel(
        file_id=file_id,  # type: ignore[arg-type]  # 已檢查為 str
        status=status,  # type: ignore[arg-type]  # 已檢查為 str
        progress=doc.get("progress", 0),
        message=doc.get("message"),
        file_size=doc.get("file_size"),
        uploaded_bytes=doc.get("uploaded_bytes"),
        created_at=(
            datetime.fromisoformat(doc["created_at"])
            if doc.get("created_at")
            else datetime.utcnow()
        ),
        updated_at=(
            datetime.fromisoformat(doc["updated_at"])
            if doc.get("updated_at")
            else datetime.utcnow()
        ),
    )


def _document_to_processing_status(doc: Dict[str, Any]) -> ProcessingStatusModel:
    """將 ArangoDB document 轉換為 ProcessingStatusModel"""
    file_id = doc.get("_key") or doc.get("file_id")
    overall_status = doc.get("overall_status")
    if not file_id or not isinstance(file_id, str):
        raise ValueError(f"Invalid file_id: {file_id}")
    if not overall_status or not isinstance(overall_status, str):
        raise ValueError(f"Invalid overall_status: {overall_status}")
    return ProcessingStatusModel(
        file_id=file_id,  # type: ignore[arg-type]  # 已檢查為 str
        overall_status=overall_status,  # type: ignore[arg-type]  # 已檢查為 str
        overall_progress=doc.get("overall_progress", 0),
        message=doc.get("message"),
        chunking=ProcessingStageStatus(**doc["chunking"]) if doc.get("chunking") else None,
        vectorization=(
            ProcessingStageStatus(**doc["vectorization"]) if doc.get("vectorization") else None
        ),
        storage=ProcessingStageStatus(**doc["storage"]) if doc.get("storage") else None,
        kg_extraction=(
            ProcessingStageStatus(**doc["kg_extraction"]) if doc.get("kg_extraction") else None
        ),
        created_at=(
            datetime.fromisoformat(doc["created_at"])
            if doc.get("created_at")
            else datetime.utcnow()
        ),
        updated_at=(
            datetime.fromisoformat(doc["updated_at"])
            if doc.get("updated_at")
            else datetime.utcnow()
        ),
    )


class UploadStatusService:
    """文件上傳狀態服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化上傳狀態服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.logger = logger
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """確保集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 創建 upload_progress 集合
        if not self.client.db.has_collection(UPLOAD_PROGRESS_COLLECTION):
            self.client.db.create_collection(UPLOAD_PROGRESS_COLLECTION)
            collection = self.client.db.collection(UPLOAD_PROGRESS_COLLECTION)
            collection.add_index({"type": "persistent", "fields": ["file_id"]})
            collection.add_index({"type": "persistent", "fields": ["status"]})
            collection.add_index(
                {"type": "ttl", "fields": ["updated_at"], "expireAfter": 3600}
            )  # 1小時TTL

        # 創建 processing_status 集合
        if not self.client.db.has_collection(PROCESSING_STATUS_COLLECTION):
            self.client.db.create_collection(PROCESSING_STATUS_COLLECTION)
            collection = self.client.db.collection(PROCESSING_STATUS_COLLECTION)
            collection.add_index({"type": "persistent", "fields": ["file_id"]})
            collection.add_index({"type": "persistent", "fields": ["overall_status"]})
            collection.add_index(
                {"type": "ttl", "fields": ["updated_at"], "expireAfter": 86400}
            )  # 24小時TTL

    def create_upload_progress(self, progress: UploadProgressCreate) -> UploadProgressModel:
        """
        創建上傳進度記錄

        Args:
            progress: 上傳進度創建請求

        Returns:
            創建的上傳進度模型
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        now = datetime.utcnow()
        doc = {
            "_key": progress.file_id,
            "file_id": progress.file_id,
            "status": progress.status,
            "progress": progress.progress,
            "message": progress.message,
            "file_size": progress.file_size,
            "uploaded_bytes": progress.uploaded_bytes,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        collection = self.client.db.collection(UPLOAD_PROGRESS_COLLECTION)
        collection.insert(doc)

        self.logger.info(
            "upload_progress_created", file_id=progress.file_id, status=progress.status
        )
        return _document_to_upload_progress(doc)

    def get_upload_progress(self, file_id: str) -> Optional[UploadProgressModel]:
        """
        獲取上傳進度

        Args:
            file_id: 文件ID

        Returns:
            上傳進度模型，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(UPLOAD_PROGRESS_COLLECTION)
        doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None，不是 AsyncJob/BatchJob

        if doc is None:
            return None

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return None

        return _document_to_upload_progress(doc)

    def update_upload_progress(
        self, file_id: str, update: UploadProgressUpdate
    ) -> Optional[UploadProgressModel]:
        """
        更新上傳進度

        Args:
            file_id: 文件ID
            update: 更新請求

        Returns:
            更新後的上傳進度模型，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(UPLOAD_PROGRESS_COLLECTION)
        doc = collection.get(file_id)

        if doc is None:
            return None

        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
        if update.status is not None:
            update_data["status"] = update.status
        if update.progress is not None:
            update_data["progress"] = update.progress
        if update.message is not None:
            update_data["message"] = update.message
        if update.uploaded_bytes is not None:
            update_data["uploaded_bytes"] = update.uploaded_bytes

        collection.update({"_key": file_id, **update_data})

        updated_doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None
        self.logger.info("upload_progress_updated", file_id=file_id, status=update.status)
        if updated_doc is None or not isinstance(updated_doc, dict):
            return None
        return _document_to_upload_progress(updated_doc)

    def delete_upload_progress(self, file_id: str) -> bool:
        """
        刪除上傳進度記錄

        Args:
            file_id: 文件ID

        Returns:
            是否成功刪除
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(UPLOAD_PROGRESS_COLLECTION)
        try:
            collection.delete(file_id)
            self.logger.info("upload_progress_deleted", file_id=file_id)
            return True
        except Exception as e:
            self.logger.error("upload_progress_delete_failed", file_id=file_id, error=str(e))
            return False

    def create_processing_status(self, status: ProcessingStatusCreate) -> ProcessingStatusModel:
        """
        創建處理狀態記錄

        Args:
            status: 處理狀態創建請求

        Returns:
            創建的處理狀態模型
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        now = datetime.utcnow()
        doc = {
            "_key": status.file_id,
            "file_id": status.file_id,
            "overall_status": status.overall_status,
            "overall_progress": status.overall_progress,
            "message": status.message,
            "chunking": None,
            "vectorization": None,
            "storage": None,
            "kg_extraction": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        collection = self.client.db.collection(PROCESSING_STATUS_COLLECTION)
        collection.insert(doc)

        self.logger.info(
            "processing_status_created",
            file_id=status.file_id,
            overall_status=status.overall_status,
        )
        return _document_to_processing_status(doc)

    def get_processing_status(self, file_id: str) -> Optional[ProcessingStatusModel]:
        """
        獲取處理狀態

        Args:
            file_id: 文件ID

        Returns:
            處理狀態模型，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(PROCESSING_STATUS_COLLECTION)
        doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None

        if doc is None:
            return None

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return None

        return _document_to_processing_status(doc)

    def update_processing_status(
        self, file_id: str, update: ProcessingStatusUpdate
    ) -> Optional[ProcessingStatusModel]:
        """
        更新處理狀態

        Args:
            file_id: 文件ID
            update: 更新請求

        Returns:
            更新後的處理狀態模型，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(PROCESSING_STATUS_COLLECTION)
        doc = collection.get(file_id)

        if doc is None:
            return None

        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}
        if update.overall_status is not None:
            update_data["overall_status"] = update.overall_status
        if update.overall_progress is not None:
            update_data["overall_progress"] = update.overall_progress
        if update.message is not None:
            update_data["message"] = update.message

        # 更新各階段狀態
        for stage_name in ["chunking", "vectorization", "storage", "kg_extraction"]:
            stage_data = getattr(update, stage_name, None)
            if stage_data is not None:
                if stage_data.get("started_at"):
                    stage_data["started_at"] = datetime.utcnow().isoformat()
                if stage_data.get("completed_at"):
                    stage_data["completed_at"] = datetime.utcnow().isoformat()
                update_data[stage_name] = stage_data

        collection.update({"_key": file_id, **update_data})

        updated_doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None
        self.logger.info(
            "processing_status_updated", file_id=file_id, overall_status=update.overall_status
        )
        if updated_doc is None or not isinstance(updated_doc, dict):
            return None
        return _document_to_processing_status(updated_doc)

    def delete_processing_status(self, file_id: str) -> bool:
        """
        刪除處理狀態記錄

        Args:
            file_id: 文件ID

        Returns:
            是否成功刪除
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(PROCESSING_STATUS_COLLECTION)
        try:
            collection.delete(file_id)
            self.logger.info("processing_status_deleted", file_id=file_id)
            return True
        except Exception as e:
            self.logger.error("processing_status_delete_failed", file_id=file_id, error=str(e))
            return False


_service: Optional[UploadStatusService] = None


def get_upload_status_service() -> UploadStatusService:
    """獲取 UploadStatusService 單例"""
    global _service
    if _service is None:
        _service = UploadStatusService()
    return _service
