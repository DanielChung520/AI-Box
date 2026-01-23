# 代碼功能說明: 任務刪除事務管理器
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""任務刪除事務管理器 - 實現刪除操作追蹤和回滾機制"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoDBClient
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.folder_metadata_service import FolderMetadataService
from services.api.services.qdrant_vector_store_service import QdrantVectorStoreService
from storage.file_storage import FileStorage

logger = structlog.get_logger(__name__)


@dataclass
class DeletionOperation:
    """刪除操作記錄"""

    file_id: str
    operation_type: str  # "vector", "kg_entity", "kg_relation", "metadata", "file"
    status: str  # "pending", "success", "failed"
    error: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TaskDeletionTransaction:
    """任務刪除事務"""

    task_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    operations: List[DeletionOperation] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    status: str = "in_progress"  # "in_progress", "completed", "partially_failed", "failed"

    def add_operation(self, file_id: str, operation_type: str) -> DeletionOperation:
        """添加刪除操作"""
        op = DeletionOperation(
            file_id=file_id,
            operation_type=operation_type,
            status="pending",
            started_at=datetime.utcnow(),
        )
        self.operations.append(op)
        return op

    def mark_success(self, file_id: str, operation_type: str) -> Optional[DeletionOperation]:
        """標記操作成功"""
        for op in self.operations:
            if op.file_id == file_id and op.operation_type == operation_type:
                op.status = "success"
                op.completed_at = datetime.utcnow()
                op.retry_count = 0
                return op
        return None

    def mark_failed(
        self, file_id: str, operation_type: str, error: str, retry_count: int = 0
    ) -> Optional[DeletionOperation]:
        """標記操作失敗"""
        for op in self.operations:
            if op.file_id == file_id and op.operation_type == operation_type:
                op.status = "failed"
                op.completed_at = datetime.utcnow()
                op.error = error
                op.retry_count = retry_count
                return op
        return None

    def get_pending_operations(self) -> List[DeletionOperation]:
        """獲取待執行的操作"""
        return [op for op in self.operations if op.status == "pending"]

    def get_failed_operations(self) -> List[DeletionOperation]:
        """獲取失敗的操作"""
        return [op for op in self.operations if op.status == "failed"]

    def get_success_count(self) -> int:
        """獲取成功操作的數量"""
        return sum(1 for op in self.operations if op.status == "success")

    def get_failed_count(self) -> int:
        """獲取失敗操作的數量"""
        return sum(1 for op in self.operations if op.status == "failed")

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "total_operations": len(self.operations),
            "success_count": self.get_success_count(),
            "failed_count": self.get_failed_count(),
            "operations": [
                {
                    "file_id": op.file_id,
                    "operation_type": op.operation_type,
                    "status": op.status,
                    "error": op.error,
                    "retry_count": op.retry_count,
                }
                for op in self.operations
            ],
        }


class DeletionRollbackManager:
    """刪除回滾管理器

    職責：
    1. 記錄所有刪除操作
    2. 實現操作重試機制
    3. 追蹤刪除狀態
    4. 提供部分失敗時的清理建議
    """

    MAX_RETRY_COUNT = 3
    RETRY_DELAY_SECONDS = 1

    def __init__(
        self,
        task_id: str,
        user_id: str,
        vector_store_service: Optional[QdrantVectorStoreService] = None,
        file_metadata_service: Optional[FileMetadataService] = None,
        folder_metadata_service: Optional[FolderMetadataService] = None,
        storage: Optional[FileStorage] = None,
        arangodb_client: Optional[ArangoDBClient] = None,
    ):
        self.task_id = task_id
        self.user_id = user_id
        self.transaction = TaskDeletionTransaction(task_id=task_id, user_id=user_id)

        self.vector_store_service = vector_store_service
        self.file_metadata_service = file_metadata_service
        self.folder_metadata_service = folder_metadata_service
        self.storage = storage
        self.arangodb_client = arangodb_client

    def _with_retry(self, operation, max_retries: int = None) -> tuple:
        """帶重試的執行操作

        Args:
            operation: 要執行的操作（函數）
            max_retries: 最大重試次數

        Returns:
            (success: bool, result: Any, error: Optional[str])
        """
        max_retries = max_retries or self.MAX_RETRY_COUNT

        for attempt in range(max_retries):
            try:
                result = operation()
                return True, result, None
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    logger.warning(
                        "Operation failed, will retry",
                        operation=operation.__name__
                        if hasattr(operation, "__name__")
                        else str(operation),
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=error_msg,
                    )
                else:
                    return False, None, error_msg

        return False, None, "Max retries exceeded"

    def delete_vector_with_rollback(
        self, file_id: str, storage_path: Optional[str] = None
    ) -> tuple:
        """刪除向量數據（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(file_id, "vector")

        def _delete():
            if self.vector_store_service:
                return self.vector_store_service.delete_vectors_by_file_id(
                    file_id=file_id, user_id=self.user_id
                )
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(file_id, "vector")
            logger.info("Vector deleted successfully", file_id=file_id, task_id=self.task_id)
        else:
            self.transaction.mark_failed(file_id, "vector", error or "Unknown error")
            logger.error(
                "Failed to delete vector",
                file_id=file_id,
                task_id=self.task_id,
                error=error,
            )

        return success, error

    def delete_kg_entities_with_rollback(self, file_id: str) -> tuple:
        """刪除知識圖譜實體（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(file_id, "kg_entity")

        def _delete():
            if self.arangodb_client and self.arangodb_client.db and self.arangodb_client.db.aql:
                if self.arangodb_client.db.has_collection("entities"):
                    aql_query = """
                    FOR entity IN entities
                        FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                        REMOVE entity IN entities
                    """
                    self.arangodb_client.db.aql.execute(aql_query, bind_vars={"file_id": file_id})
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(file_id, "kg_entity")
        else:
            self.transaction.mark_failed(file_id, "kg_entity", error or "Unknown error")

        return success, error

    def delete_kg_relations_with_rollback(self, file_id: str) -> tuple:
        """刪除知識圖譜關係（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(file_id, "kg_relation")

        def _delete():
            if self.arangodb_client and self.arangodb_client.db and self.arangodb_client.db.aql:
                if self.arangodb_client.db.has_collection("relations"):
                    aql_query = """
                    FOR relation IN relations
                        FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                        REMOVE relation IN relations
                    """
                    self.arangodb_client.db.aql.execute(aql_query, bind_vars={"file_id": file_id})
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(file_id, "kg_relation")
        else:
            self.transaction.mark_failed(file_id, "kg_relation", error or "Unknown error")

        return success, error

    def delete_metadata_with_rollback(self, file_id: str) -> tuple:
        """刪除文件元數據（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(file_id, "metadata")

        def _delete():
            if self.file_metadata_service:
                return self.file_metadata_service.delete(file_id)
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(file_id, "metadata")
            logger.info("File metadata deleted", file_id=file_id, task_id=self.task_id)
        else:
            self.transaction.mark_failed(file_id, "metadata", error or "Unknown error")

        return success, error

    def delete_file_with_rollback(self, file_id: str, storage_path: Optional[str] = None) -> tuple:
        """刪除實體文件（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(file_id, "file")

        def _delete():
            if self.storage:
                return self.storage.delete_file(file_id, metadata_storage_path=storage_path)
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(file_id, "file")
            logger.info("File deleted", file_id=file_id, task_id=self.task_id)
        else:
            self.transaction.mark_failed(file_id, "file", error or "Unknown error")

        return success, error

    def delete_folder_with_rollback(self, folder_id: str) -> tuple:
        """刪除資料夾（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(folder_id, "folder")

        def _delete():
            if self.folder_metadata_service:
                return self.folder_metadata_service.delete(folder_id)
            return True

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(folder_id, "folder")
        else:
            self.transaction.mark_failed(folder_id, "folder", error or "Unknown error")

        return success, error

    def delete_task_with_rollback(self, task_id: str) -> tuple:
        """刪除任務本身（帶回滾追蹤）

        Returns:
            (success: bool, error: Optional[str])
        """
        self.transaction.add_operation(task_id, "task")

        def _delete():
            from services.api.services.user_task_service import get_user_task_service

            task_service = get_user_task_service()
            return task_service.delete(user_id=self.user_id, task_id=task_id)

        success, result, error = self._with_retry(_delete)

        if success:
            self.transaction.mark_success(task_id, "task")
        else:
            self.transaction.mark_failed(task_id, "task", error or "Unknown error")

        return success, error

    def complete(self) -> TaskDeletionTransaction:
        """完成事務"""
        self.transaction.completed_at = datetime.utcnow()

        failed_count = self.transaction.get_failed_count()
        if failed_count == 0:
            self.transaction.status = "completed"
        elif failed_count < len(self.transaction.operations):
            self.transaction.status = "partially_failed"
        else:
            self.transaction.status = "failed"

        return self.transaction

    def get_summary(self) -> Dict[str, Any]:
        """獲取事務摘要"""
        return self.transaction.to_dict()

    def get_rollback_report(self) -> Dict[str, Any]:
        """獲取回滾報告（失敗操作的詳細信息）"""
        failed_ops = self.transaction.get_failed_operations()

        report = {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "status": self.transaction.status,
            "total_operations": len(self.transaction.operations),
            "success_count": self.transaction.get_success_count(),
            "failed_count": len(failed_ops),
            "failed_operations": [
                {
                    "file_id": op.file_id,
                    "operation_type": op.operation_type,
                    "error": op.error,
                    "retry_count": op.retry_count,
                }
                for op in failed_ops
            ],
            "recommendations": self._generate_recommendations(failed_ops),
        }

        return report

    def _generate_recommendations(self, failed_ops: List[DeletionOperation]) -> List[str]:
        """根據失敗操作生成建議"""
        recommendations = []

        vector_failures = [op for op in failed_ops if op.operation_type == "vector"]
        if vector_failures:
            recommendations.append(
                f"警告: {len(vector_failures)} 個文件的向量刪除失敗。 " "建議手動檢查 Qdrant 集合中的殘留數據。"
            )

        kg_failures = [op for op in failed_ops if op.operation_type in ["kg_entity", "kg_relation"]]
        if kg_failures:
            recommendations.append(
                f"警告: {len(kg_failures)} 個知識圖譜操作失敗。 " "建議手動清理 ArangoDB 中的 entities 和 relations 集合。"
            )

        file_failures = [op for op in failed_ops if op.operation_type == "file"]
        if file_failures:
            recommendations.append(f"警告: {len(file_failures)} 個實體文件刪除失敗。 " "建議手動檢查 S3/本地存儲中的殘留文件。")

        if not recommendations:
            recommendations.append("所有刪除操作均已成功完成。")

        return recommendations
