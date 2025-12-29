# 代碼功能說明: Agent File Service Agent 產出物文件服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""Agent File Service - 實現 Agent 產出物（HTML/PDF）的存儲和訪問"""

import logging
from pathlib import Path
from typing import List, Optional

from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section

from .models import AgentFileInfo, FileType

logger = logging.getLogger(__name__)


class AgentFileService:
    """Agent 產出物文件服務"""

    def __init__(
        self,
        storage: Optional[FileStorage] = None,
        base_url: str = "http://localhost:8000/api/v1/files",
    ):
        """
        初始化 Agent 文件服務

        Args:
            storage: 文件存儲接口（可選，默認從配置創建，支持 S3/SeaweedFS）
            base_url: 文件訪問基礎 URL
        """
        if storage is None:
            # 從配置創建存儲實例（支持 S3/SeaweedFS）
            config = get_config_section("file_upload", default={}) or {}
            storage = create_storage_from_config(config, service_type="ai_box")
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._logger = logger

    def upload_agent_output(
        self,
        file_content: bytes,
        filename: str,
        agent_id: str,
        task_id: str,
        file_type: Optional[FileType] = None,
        metadata: Optional[dict] = None,
    ) -> AgentFileInfo:
        """
        上傳 Agent 產出物

        Args:
            file_content: 文件內容
            filename: 文件名
            agent_id: Agent ID
            task_id: 任務 ID
            file_type: 文件類型（可選，自動從文件名推斷）
            metadata: 額外元數據

        Returns:
            Agent 文件信息
        """
        try:
            # 確定文件類型
            if file_type is None:
                file_type = self._infer_file_type(filename)

            # 生成文件 ID
            file_id = self._generate_file_id(agent_id, task_id, filename)

            # 保存文件（傳遞 task_id 以便文件存儲在任務工作區）
            file_id, saved_path = self._storage.save_file(
                file_content, filename, file_id=file_id, task_id=task_id
            )

            # 如果保存路徑不包含組織化結構，需要手動組織
            # 這裡暫時使用保存後的路徑，後續可以擴展 FileStorage 支持組織化路徑

            # 生成文件訪問 URL
            file_url = self._generate_file_url(agent_id, task_id, file_id)

            # 創建文件信息
            file_info = AgentFileInfo(
                file_id=file_id,
                agent_id=agent_id,
                task_id=task_id,
                file_type=file_type,
                filename=filename,
                file_path=saved_path,
                file_url=file_url,
                file_size=len(file_content),
                metadata=metadata or {},
            )

            self._logger.info(
                f"Uploaded agent output file: {file_id} "
                f"(agent: {agent_id}, task: {task_id}, type: {file_type.value})"
            )

            return file_info

        except Exception as e:
            self._logger.error(f"Failed to upload agent output: {e}")
            raise

    def get_agent_file(self, agent_id: str, task_id: str, file_id: str) -> Optional[AgentFileInfo]:
        """
        獲取 Agent 文件信息

        Args:
            agent_id: Agent ID
            task_id: 任務 ID
            file_id: 文件 ID

        Returns:
            文件信息，如果不存在則返回 None
        """
        try:
            # 使用 task_id 獲取文件路徑（支持任務工作區）
            file_path = self._storage.get_file_path(file_id, task_id=task_id)
            if not file_path:
                return None

            # 讀取文件獲取大小（使用 task_id 和 file_path）
            file_content = self._storage.read_file(
                file_id, task_id=task_id, metadata_storage_path=file_path
            )
            if file_content is None:
                return None

            # 從文件路徑推斷文件名（支持 S3 URI）
            if file_path.startswith("s3://"):
                # S3 URI 格式：s3://bucket/key，從 key 中提取文件名
                filename = file_path.split("/")[-1]
            else:
                filename = Path(file_path).name
            file_type = self._infer_file_type(filename)

            # 生成文件 URL
            file_url = self._generate_file_url(agent_id, task_id, file_id)

            return AgentFileInfo(
                file_id=file_id,
                agent_id=agent_id,
                task_id=task_id,
                file_type=file_type,
                filename=filename,
                file_path=file_path,
                file_url=file_url,
                file_size=len(file_content),
            )

        except Exception as e:
            self._logger.error(f"Failed to get agent file: {e}")
            return None

    def list_agent_files(self, agent_id: str, task_id: Optional[str] = None) -> List[AgentFileInfo]:
        """
        列出 Agent 的文件

        Args:
            agent_id: Agent ID
            task_id: 任務 ID（可選）

        Returns:
            文件信息列表

        注意：
        - 對於 S3/SeaweedFS 存儲，需要通過 S3 API 列出文件（需要實現）
        - 目前僅支持 LocalFileStorage 的文件列表
        - 後續可以擴展為數據庫查詢或 S3 list_objects
        """
        files: List[AgentFileInfo] = []
        # 檢查是否為 LocalFileStorage（有 storage_path 屬性）
        if not hasattr(self._storage, "storage_path"):
            # 如果不是本地存儲，返回空列表
            # TODO: 實現 S3 list_objects 支持
            self._logger.warning(
                "list_agent_files not supported for S3 storage yet, "
                "consider using database query or S3 list_objects"
            )
            return files
        base_path = Path(self._storage.storage_path) / agent_id

        if task_id:
            base_path = base_path / task_id

        if base_path.exists():
            for file_path in base_path.rglob("*"):
                if file_path.is_file():
                    file_id = file_path.stem
                    filename = file_path.name
                    file_type = self._infer_file_type(filename)

                    file_info = AgentFileInfo(
                        file_id=file_id,
                        agent_id=agent_id,
                        task_id=task_id or "unknown",
                        file_type=file_type,
                        filename=filename,
                        file_path=str(file_path),
                        file_url=self._generate_file_url(agent_id, task_id or "unknown", file_id),
                        file_size=file_path.stat().st_size,
                    )
                    files.append(file_info)

        return files

    def _infer_file_type(self, filename: str) -> FileType:
        """
        從文件名推斷文件類型

        Args:
            filename: 文件名

        Returns:
            文件類型
        """
        ext = Path(filename).suffix.lower()
        type_mapping = {
            ".html": FileType.HTML,
            ".pdf": FileType.PDF,
            ".png": FileType.PNG,
            ".svg": FileType.SVG,
            ".json": FileType.JSON,
            ".csv": FileType.CSV,
        }
        return type_mapping.get(ext, FileType.OTHER)

    def _generate_file_id(self, agent_id: str, task_id: str, filename: str) -> str:
        """
        生成文件 ID（包含 agent_id 和 task_id 信息）

        Args:
            agent_id: Agent ID
            task_id: 任務 ID
            filename: 文件名

        Returns:
            文件 ID
        """
        import uuid

        # 使用 UUID 生成唯一文件 ID，但保持與 agent_id 和 task_id 的關聯
        file_id = str(uuid.uuid4())
        return file_id

    def _get_agent_file_path(self, agent_id: str, task_id: str, filename: str) -> str:
        """
        獲取 Agent 文件的組織化路徑

        Args:
            agent_id: Agent ID
            task_id: 任務 ID
            filename: 文件名

        Returns:
            文件路徑字符串
        """
        return f"{agent_id}/{task_id}/{filename}"

    def _generate_file_url(self, agent_id: str, task_id: str, file_id: str) -> str:
        """
        生成文件訪問 URL

        Args:
            agent_id: Agent ID
            task_id: 任務 ID
            file_id: 文件 ID

        Returns:
            文件 URL
        """
        return f"{self._base_url}/{agent_id}/{task_id}/{file_id}"


# 全局 Agent File Service 實例
_global_file_service: Optional[AgentFileService] = None


def get_agent_file_service() -> AgentFileService:
    """
    獲取全局 Agent File Service 實例

    Returns:
        Agent File Service 實例
    """
    global _global_file_service
    if _global_file_service is None:
        _global_file_service = AgentFileService()
    return _global_file_service
