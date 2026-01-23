# 代碼功能說明: Soft Delete 功能測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""Soft Delete 功能測試"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest


class TestUserTaskSoftDelete:
    """UserTask Soft Delete 測試"""

    @pytest.fixture
    def mock_arangodb_client(self):
        """創建模擬 ArangoDB 客戶端"""
        client = Mock()
        client.db = Mock()
        return client

    @pytest.fixture
    def mock_collection(self, mock_arangodb_client):
        """創建模擬 collection"""
        collection = Mock()
        mock_arangodb_client.db.collection.return_value = collection
        return collection

    @pytest.fixture
    def user_task_service(self, mock_arangodb_client):
        """創建 UserTaskService 實例"""
        from services.api.services.user_task_service import UserTaskService

        return UserTaskService(client=mock_arangodb_client)

    def test_soft_delete_success(self, user_task_service, mock_collection):
        """測試軟刪除成功"""
        # 準備測試數據
        task_id = "test_task_123"
        user_id = "user_456"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "task_status": "activate",
        }
        mock_collection.get.return_value = mock_doc

        # 執行軟刪除
        result = user_task_service.soft_delete(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is True
        assert result["task_id"] == task_id
        assert result["task_status"] == "trash"
        assert result["deleted_at"] is not None
        assert result["permanent_delete_at"] is not None

        # 驗證文檔被更新
        mock_collection.update.assert_called_once()
        updated_doc = mock_collection.update.call_args[0][0]
        assert updated_doc["task_status"] == "trash"
        assert updated_doc["deleted_at"] is not None
        assert updated_doc["permanent_delete_at"] is not None

    def test_soft_delete_task_not_found(self, user_task_service, mock_collection):
        """測試軟刪除任務不存在"""
        task_id = "nonexistent_task"
        user_id = "user_456"

        mock_collection.get.return_value = None

        # 執行軟刪除
        result = user_task_service.soft_delete(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is False
        assert result["error"] == "Task not found"

    def test_soft_delete_wrong_user(self, user_task_service, mock_collection):
        """測試軟刪除權限錯誤"""
        task_id = "test_task_123"
        user_id = "wrong_user"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": "actual_user",
            "title": "Test Task",
        }
        mock_collection.get.return_value = mock_doc

        # 執行軟刪除
        result = user_task_service.soft_delete(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is False
        assert "not found or access denied" in result["error"]

    def test_restore_success(self, user_task_service, mock_collection):
        """測試恢復成功"""
        task_id = "test_task_123"
        user_id = "user_456"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "task_status": "trash",
            "deleted_at": datetime.utcnow().isoformat(),
            "permanent_delete_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }
        mock_collection.get.return_value = mock_doc

        # 執行恢復
        result = user_task_service.restore(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is True
        assert result["task_status"] == "activate"
        assert result["deleted_at"] is None
        assert result["permanent_delete_at"] is None

        # 驗證文檔被更新
        mock_collection.update.assert_called_once()
        updated_doc = mock_collection.update.call_args[0][0]
        assert updated_doc["task_status"] == "activate"
        assert updated_doc["deleted_at"] is None

    def test_restore_not_in_trash(self, user_task_service, mock_collection):
        """測試恢復不在 Trash 中的任務"""
        task_id = "test_task_123"
        user_id = "user_456"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "task_status": "activate",  # 不在 Trash 中
        }
        mock_collection.get.return_value = mock_doc

        # 執行恢復
        result = user_task_service.restore(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is False
        assert "not in trash" in result["error"]

    def test_permanent_delete_success(self, user_task_service, mock_collection):
        """測試永久刪除成功"""
        task_id = "test_task_123"
        user_id = "user_456"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "task_status": "trash",
        }
        mock_collection.get.return_value = mock_doc

        # 執行永久刪除
        result = user_task_service.permanent_delete(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is True
        assert result["task_id"] == task_id

        # 驗證文檔被刪除（使用 doc_key 格式）
        doc_key = f"{user_id}_{task_id}"
        mock_collection.delete.assert_called_once_with(doc_key)

    def test_permanent_delete_not_in_trash(self, user_task_service, mock_collection):
        """測試永久刪除不在 Trash 中的任務"""
        task_id = "test_task_123"
        user_id = "user_456"

        mock_doc = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "task_status": "activate",  # 不在 Trash 中
        }
        mock_collection.get.return_value = mock_doc

        # 執行永久刪除
        result = user_task_service.permanent_delete(user_id=user_id, task_id=task_id)

        # 驗證結果
        assert result["success"] is False
        assert "not in trash" in result["error"]


class TestTaskDeletionJob:
    """任務刪除 Job 測試"""

    def test_execute_task_deletion_with_soft_delete(self):
        """測試帶 Soft Delete 的任務刪除"""
        from datetime import datetime

        from services.api.tasks.task_deletion import execute_task_deletion

        # 準備測試數據
        task_id = "test_task_123"
        user_id = "user_456"

        # 創建模擬客戶端
        mock_client = Mock()
        mock_client.db = Mock()
        mock_client.db.collection.return_value.get.return_value = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "deleted_at": None,  # 未標記為 Soft Delete
        }

        # 模擬其他服務
        with (
            patch("services.api.tasks.task_deletion.ArangoDBClient") as mock_arangodb,
            patch("services.api.tasks.task_deletion.UserTaskService") as mock_service,
            patch("services.api.tasks.task_deletion.FileMetadataService") as mock_file_service,
            patch(
                "services.api.tasks.task_deletion.get_qdrant_vector_store_service"
            ) as mock_vector_service,
            patch(
                "services.api.tasks.task_deletion.get_folder_metadata_service"
            ) as mock_folder_service,
            patch("services.api.tasks.task_deletion.create_storage_from_config") as mock_storage,
            patch("services.api.tasks.task_deletion.DeletionRollbackManager") as mock_rollback,
        ):
            # 設置模擬返回值
            mock_arangodb.return_value = mock_client
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.soft_delete.return_value = {
                "success": True,
                "task_id": task_id,
                "deleted_at": datetime.utcnow().isoformat(),
                "permanent_delete_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            }
            mock_file_service.return_value.list.return_value = []
            mock_folder_service.return_value.list.return_value = []
            mock_rollback_instance = Mock()
            mock_rollback_instance.complete.return_value = Mock()
            mock_rollback_instance.get_success_count.return_value = 0
            mock_rollback_instance.get_failed_count.return_value = 0
            mock_rollback.return_value = mock_rollback_instance

            # 執行測試
            result = execute_task_deletion(task_id=task_id, user_id=user_id)

            # 驗證 Soft Delete 被調用
            mock_service_instance.soft_delete.assert_called_once_with(
                user_id=user_id,
                task_id=task_id,
            )

    def test_execute_task_deletion_skip_soft_delete(self):
        """測試跳過 Soft Delete 的任務刪除"""
        from services.api.tasks.task_deletion import execute_task_deletion

        # 準備測試數據
        task_id = "test_task_123"
        user_id = "user_456"

        # 創建模擬客戶端
        mock_client = Mock()
        mock_client.db = Mock()
        mock_client.db.collection.return_value.get.return_value = {
            "_key": task_id,
            "task_id": task_id,
            "user_id": user_id,
            "title": "Test Task",
            "deleted_at": datetime.utcnow().isoformat(),  # 已經 Soft Delete
        }

        # 模擬其他服務
        with (
            patch("services.api.tasks.task_deletion.ArangoDBClient") as mock_arangodb,
            patch("services.api.tasks.task_deletion.UserTaskService") as mock_service,
            patch("services.api.tasks.task_deletion.FileMetadataService") as mock_file_service,
            patch(
                "services.api.tasks.task_deletion.get_qdrant_vector_store_service"
            ) as mock_vector_service,
            patch(
                "services.api.tasks.task_deletion.get_folder_metadata_service"
            ) as mock_folder_service,
            patch("services.api.tasks.task_deletion.create_storage_from_config") as mock_storage,
            patch("services.api.tasks.task_deletion.DeletionRollbackManager") as mock_rollback,
        ):
            # 設置模擬返回值
            mock_arangodb.return_value = mock_client
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            mock_file_service.return_value.list.return_value = []
            mock_folder_service.return_value.list.return_value = []
            mock_rollback_instance = Mock()
            mock_rollback_instance.complete.return_value = Mock()
            mock_rollback_instance.get_success_count.return_value = 0
            mock_rollback_instance.get_failed_count.return_value = 0
            mock_rollback.return_value = mock_rollback_instance

            # 執行測試（skip_soft_delete=True）
            result = execute_task_deletion(
                task_id=task_id,
                user_id=user_id,
                skip_soft_delete=True,
            )

            # 驗證 Soft Delete 沒有被調用
            mock_service_instance.soft_delete.assert_not_called()


class TestSoftDeleteModel:
    """Soft Delete 模型測試"""

    def test_user_task_model_with_deleted_at(self):
        """測試 UserTask 模型包含 deleted_at 字段"""
        from services.api.models.user_task import UserTask

        # 創建測試數據
        now = datetime.utcnow()
        task_data = {
            "task_id": "test_123",
            "user_id": "user_456",
            "title": "Test Task",
            "status": "pending",
            "task_status": "trash",
            "deleted_at": now,
            "permanent_delete_at": now + timedelta(days=7),
            "created_at": now,
            "updated_at": now,
        }

        # 創建 UserTask 實例
        task = UserTask(**task_data)

        # 驗證字段值
        assert task.task_status == "trash"
        assert task.deleted_at == now
        assert task.permanent_delete_at == now + timedelta(days=7)

    def test_user_task_update_with_deleted_at(self):
        """測試 UserTaskUpdate 模型包含 deleted_at 字段"""
        from services.api.models.user_task import UserTaskUpdate

        # 創建測試數據
        now = datetime.utcnow()
        update_data = {
            "task_status": "activate",
            "deleted_at": None,
            "permanent_delete_at": None,
        }

        # 創建 UserTaskUpdate 實例
        update = UserTaskUpdate(**update_data)

        # 驗證字段值
        assert update.task_status == "activate"
        assert update.deleted_at is None
        assert update.permanent_delete_at is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
