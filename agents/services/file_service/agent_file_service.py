# 代碼功能說明: Agent File Service Agent 產出物文件服務
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent File Service - 實現 Agent 產出物（HTML/PDF）的存儲和訪問"""

import logging
import os
from typing import Optional, List
from pathlib import Path

from .models import AgentFileInfo, FileType
from storage.file_storage import FileStorage, LocalFileStorage

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
            storage: 文件存儲接口（可選，默認使用本地存儲）
            base_url: 文件訪問基礎 URL
        """
        self._storage = storage or LocalFileStorage(
            storage_path=os.getenv("AGENT_FILES_STORAGE_PATH", "./datasets/agent_files")
        )
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

            # 保存文件
            file_id, saved_path = self._storage.save_file(
                file_content, filename, file_id=file_id
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

    def get_agent_file(
        self, agent_id: str, task_id: str, file_id: str
    ) -> Optional[AgentFileInfo]:
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
            file_path = self._storage.get_file_path(file_id)
            if not file_path:
                return None

            # 讀取文件獲取大小
            file_content = self._storage.read_file(file_id)
            if file_content is None:
                return None

            # 從文件路徑推斷文件名
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

    def list_agent_files(
        self, agent_id: str, task_id: Optional[str] = None
    ) -> List[AgentFileInfo]:
        """
        列出 Agent 的文件

        Args:
            agent_id: Agent ID
            task_id: 任務 ID（可選）

        Returns:
            文件信息列表
        """
        # 簡單實現：列出特定路徑下的文件
        # 後續可以擴展為數據庫查詢
        files: List[AgentFileInfo] = []
        # 檢查是否為 LocalFileStorage（有 storage_path 屬性）
        if not hasattr(self._storage, "storage_path"):
            # 如果不是本地存儲，返回空列表（後續可以擴展為數據庫查詢）
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
                        file_url=self._generate_file_url(
                            agent_id, task_id or "unknown", file_id
                        ),
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
