# 代碼功能說明: 任務工作區整合服務
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11 15:44:36 (UTC+8)

"""任務工作區整合服務 - 整合 TaskWorkspaceService 和 FileMetadataService

提供統一的文件創建、讀取、查找接口，確保所有新文件創建在任務工作區下。
"""

from pathlib import Path
from typing import Optional
from uuid import uuid4

import structlog

from services.api.models.file_metadata import FileMetadata, FileMetadataCreate
from services.api.services.file_metadata_service import FileMetadataService, get_metadata_service
from services.api.services.task_workspace_service import (
    TaskWorkspaceService,
    get_task_workspace_service,
)

logger = structlog.get_logger(__name__)


class WorkspaceIntegration:
    """任務工作區整合服務

    提供統一的文件創建、讀取、查找接口，確保所有新文件創建在任務工作區下。
    """

    def __init__(
        self,
        task_workspace_service: Optional[TaskWorkspaceService] = None,
        file_metadata_service: Optional[FileMetadataService] = None,
    ):
        """
        初始化任務工作區整合服務

        Args:
            task_workspace_service: 任務工作區服務（可選，如果不提供則自動創建）
            file_metadata_service: 文件元數據服務（可選，如果不提供則自動創建）
        """
        self.task_workspace_service = task_workspace_service or get_task_workspace_service()
        self.file_metadata_service = file_metadata_service or get_metadata_service()
        self.logger = logger

    def ensure_workspace_exists(self, task_id: str, user_id: str) -> dict:
        """
        確保任務工作區存在（如果不存在則創建）

        Args:
            task_id: 任務 ID
            user_id: 用戶 ID

        Returns:
            工作區信息
        """
        return self.task_workspace_service.ensure_workspace_exists(task_id, user_id)

    def generate_file_path(self, task_id: str, file_id: str, file_extension: str) -> str:
        """
        生成文件路徑

        Args:
            task_id: 任務 ID
            file_id: 文件 ID
            file_extension: 文件擴展名（不含點號，如 "md", "xlsx", "pdf"）

        Returns:
            文件路徑（相對於項目根目錄）
        """
        workspace_path = self.task_workspace_service.get_workspace_path(task_id)
        file_path = workspace_path / f"{file_id}.{file_extension}"
        return str(file_path)

    def create_file(
        self,
        task_id: str,
        user_id: str,
        file_name: str,
        content: str,
        file_format: str = "markdown",
        file_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> FileMetadata:
        """
        創建文件（在任務工作區下）

        Args:
            task_id: 任務 ID
            user_id: 用戶 ID
            file_name: 文件名
            content: 文件內容（字符串）
            file_format: 文件格式（markdown, excel, pdf）
            file_id: 文件 ID（可選，如果不提供則自動生成）
            tenant_id: 租戶 ID（可選）

        Returns:
            文件元數據
        """
        # 1. 確保任務工作區存在
        workspace_info = self.ensure_workspace_exists(task_id, user_id)
        folder_id = workspace_info["folder_key"]  # {task_id}_workspace

        # 2. 生成文件 ID
        if file_id is None:
            file_id = str(uuid4())

        # 3. 確定文件擴展名和 MIME 類型
        file_extension_map = {
            "markdown": ("md", "text/markdown"),
            "excel": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "pdf": ("pdf", "application/pdf"),
        }
        if file_format not in file_extension_map:
            raise ValueError(f"Unsupported file format: {file_format}")

        file_extension, mime_type = file_extension_map[file_format]

        # 4. 生成文件路徑
        file_path = self.generate_file_path(task_id, file_id, file_extension)

        # 5. 保存文件到文件系統
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        file_path_obj.write_text(content, encoding="utf-8")

        # 6. 計算文件大小
        file_size = len(content.encode("utf-8"))

        # 7. 創建文件元數據
        metadata_create = FileMetadataCreate(
            file_id=file_id,
            filename=file_name,
            file_type=mime_type,
            file_size=file_size,
            user_id=user_id,
            task_id=task_id,
            folder_id=folder_id,
            storage_path=file_path,
            status="uploaded",
        )

        file_metadata = self.file_metadata_service.create(metadata_create)

        self.logger.info(
            "文件創建成功",
            file_id=file_id,
            task_id=task_id,
            file_path=file_path,
            folder_id=folder_id,
        )

        return file_metadata

    def create_file_from_path(
        self,
        task_id: str,
        user_id: str,
        file_name: str,
        source_file_path: str,
        file_format: str = "pdf",
        file_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> FileMetadata:
        """
        從現有文件路徑創建文件元數據（用於轉換類 Agent）

        Args:
            task_id: 任務 ID
            user_id: 用戶 ID
            file_name: 文件名
            source_file_path: 源文件路徑（已存在的文件）
            file_format: 文件格式（markdown, excel, pdf）
            file_id: 文件 ID（可選，如果不提供則自動生成）
            tenant_id: 租戶 ID（可選）

        Returns:
            文件元數據
        """
        # 1. 確保任務工作區存在
        workspace_info = self.ensure_workspace_exists(task_id, user_id)
        folder_id = workspace_info["folder_key"]  # {task_id}_workspace

        # 2. 生成文件 ID
        if file_id is None:
            file_id = str(uuid4())

        # 3. 確定文件擴展名和 MIME 類型
        file_extension_map = {
            "markdown": ("md", "text/markdown"),
            "excel": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "pdf": ("pdf", "application/pdf"),
        }
        if file_format not in file_extension_map:
            raise ValueError(f"Unsupported file format: {file_format}")

        file_extension, mime_type = file_extension_map[file_format]

        # 4. 驗證源文件存在
        source_path = Path(source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")

        # 5. 計算文件大小
        file_size = source_path.stat().st_size

        # 6. 創建文件元數據（使用源文件路徑作為 storage_path）
        metadata_create = FileMetadataCreate(
            file_id=file_id,
            filename=file_name,
            file_type=mime_type,
            file_size=file_size,
            user_id=user_id,
            task_id=task_id,
            folder_id=folder_id,
            storage_path=source_file_path,
            status="uploaded",
        )

        file_metadata = self.file_metadata_service.create(metadata_create)

        self.logger.info(
            "文件元數據創建成功",
            file_id=file_id,
            task_id=task_id,
            file_path=source_file_path,
            folder_id=folder_id,
        )

        return file_metadata

    def get_file_content(self, file_id: str, task_id: Optional[str] = None) -> Optional[str]:
        """
        獲取文件內容

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則用於驗證）

        Returns:
            文件內容字符串，如果失敗返回 None
        """
        # 1. 獲取文件元數據
        file_metadata = self.file_metadata_service.get(file_id)
        if file_metadata is None:
            self.logger.warning("文件元數據不存在", file_id=file_id)
            return None

        # 2. 驗證 task_id（如果提供）
        if task_id is not None and file_metadata.task_id != task_id:
            self.logger.warning(
                "任務 ID 不匹配",
                file_id=file_id,
                expected_task_id=task_id,
                actual_task_id=file_metadata.task_id,
            )
            return None

        # 3. 讀取文件內容
        if file_metadata.storage_path is None:
            self.logger.warning("文件存儲路徑為空", file_id=file_id)
            return None

        file_path = Path(file_metadata.storage_path)
        if not file_path.exists():
            self.logger.warning("文件不存在", file_id=file_id, file_path=str(file_path))
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            return content
        except Exception as e:
            self.logger.error("讀取文件失敗", file_id=file_id, file_path=str(file_path), error=str(e))
            return None

    def find_file_by_task(
        self, task_id: str, file_name: Optional[str] = None
    ) -> Optional[FileMetadata]:
        """
        在任務工作區中查找文件

        Args:
            task_id: 任務 ID
            file_name: 文件名（可選，如果提供則按文件名查找）

        Returns:
            文件元數據，如果不存在返回 None
        """
        # 使用 FileMetadataService 的 list 方法查詢
        files = self.file_metadata_service.list(task_id=task_id, limit=1000)

        if file_name is None:
            # 如果沒有指定文件名，返回第一個文件（如果存在）
            return files[0] if files else None

        # 按文件名查找
        for file_metadata in files:
            if file_metadata.filename == file_name:
                return file_metadata

        return None

    def delete_file(self, file_id: str, task_id: Optional[str] = None) -> bool:
        """
        刪除文件（軟刪除或物理刪除）

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則用於驗證）

        Returns:
            是否成功刪除
        """
        # 1. 獲取文件元數據
        file_metadata = self.file_metadata_service.get(file_id)
        if file_metadata is None:
            self.logger.warning("文件元數據不存在", file_id=file_id)
            return False

        # 2. 驗證 task_id（如果提供）
        if task_id is not None and file_metadata.task_id != task_id:
            self.logger.warning(
                "任務 ID 不匹配",
                file_id=file_id,
                expected_task_id=task_id,
                actual_task_id=file_metadata.task_id,
            )
            return False

        # 3. 刪除文件系統中的文件
        if file_metadata.storage_path:
            file_path = Path(file_metadata.storage_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    self.logger.info("文件已刪除", file_id=file_id, file_path=str(file_path))
                except Exception as e:
                    self.logger.error(
                        "刪除文件失敗", file_id=file_id, file_path=str(file_path), error=str(e)
                    )

        # 4. 刪除文件元數據（軟刪除：更新狀態為 deleted）
        # 或者物理刪除：直接刪除記錄
        # 這裡使用物理刪除
        deleted = self.file_metadata_service.delete(file_id)
        if deleted:
            self.logger.info("文件元數據已刪除", file_id=file_id)
        else:
            self.logger.warning("刪除文件元數據失敗", file_id=file_id)

        return deleted
