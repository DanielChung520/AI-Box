# 代碼功能說明: 文件存儲模組
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""文件存儲模組 - 提供本地和雲存儲接口"""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import structlog

if TYPE_CHECKING:
    from storage.s3_storage import SeaweedFSService

logger = structlog.get_logger(__name__)


class FileStorage(ABC):
    """文件存儲抽象基類"""

    @abstractmethod
    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        保存文件

        Args:
            file_content: 文件內容
            filename: 原始文件名
            file_id: 文件 ID（可選，如果不提供則自動生成）
            task_id: 任務 ID（可選，如果提供則文件存儲在任務工作區）

        Returns:
            (file_id, file_path)
        """
        pass

    @abstractmethod
    def get_file_path(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        獲取文件路徑

        Args:
            file_id: 文件 ID

        Returns:
            文件路徑，如果不存在則返回 None
        """
        pass

    @abstractmethod
    def read_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        讀取文件內容

        Args:
            file_id: 文件 ID

        Returns:
            文件內容，如果不存在則返回 None
        """
        pass

    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """
        刪除文件

        Args:
            file_id: 文件 ID

        Returns:
            是否成功刪除
        """
        pass

    @abstractmethod
    def file_exists(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> bool:
        """
        檢查文件是否存在

        Args:
            file_id: 文件 ID

        Returns:
            文件是否存在
        """
        pass

    def move_file(
        self,
        file_id: str,
        old_task_id: Optional[str],
        new_task_id: str,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        移動文件到新的任務工作區（更新存儲路徑）

        預設實現：直接返回新路徑，不移動實體文件（由 S3 等雲存儲處理）

        Args:
            file_id: 文件 ID
            old_task_id: 舊任務 ID
            new_task_id: 新任務 ID
            metadata_storage_path: 元數據中記錄的存儲路徑

        Returns:
            新的存儲路徑，如果移動失敗則返回 None
        """
        new_path = self._get_file_path(file_id, None, new_task_id)
        logger.info(
            "File storage path calculated for move",
            file_id=file_id,
            old_task_id=old_task_id,
            new_task_id=new_task_id,
            new_path=str(new_path),
        )
        return str(new_path)

    @staticmethod
    def generate_file_id() -> str:
        """
        生成文件 ID

        Returns:
            文件 ID（UUID）
        """
        return str(uuid.uuid4())


class LocalFileStorage(FileStorage):
    """本地文件系統存儲"""

    def __init__(
        self,
        storage_path: str = "./data/datasets/files",
        enable_encryption: bool = False,
    ):
        """
        初始化本地文件存儲

        Args:
            storage_path: 存儲路徑
            enable_encryption: 是否啟用文件加密（默認 False）
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.enable_encryption = enable_encryption
        self.logger = logger.bind(
            storage_path=str(self.storage_path), encryption_enabled=enable_encryption
        )

        # 如果啟用加密，初始化加密服務
        self._encryption_service = None
        if self.enable_encryption:
            try:
                from services.api.services.encryption_service import get_encryption_service

                self._encryption_service = get_encryption_service()
                self.logger.info("文件加密已啟用")
            except Exception as e:
                self.logger.warning("無法初始化加密服務，將禁用加密", error=str(e))
                self.enable_encryption = False

    def _get_file_path(
        self,
        file_id: str,
        filename: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Path:
        """
        獲取文件路徑

        Args:
            file_id: 文件 ID
            filename: 文件名（可選）
            task_id: 任務 ID（可選，如果提供則使用任務工作區路徑）

        Returns:
            文件路徑
        """
        # 修改時間：2025-01-27 - 支持按 task_id 組織文件
        if task_id:
            # 如果提供了 task_id，文件存儲在任務工作區
            # 路徑結構：data/tasks/{task_id}/workspace/{file_id}.{ext}
            from services.api.services.task_workspace_service import get_task_workspace_service

            workspace_service = get_task_workspace_service()
            workspace_path = workspace_service.get_workspace_path(task_id)
            workspace_path.mkdir(parents=True, exist_ok=True)

            if filename:
                # 保留原始擴展名
                ext = Path(filename).suffix
                return workspace_path / f"{file_id}{ext}"
            else:
                return workspace_path / file_id
        else:
            # 舊的邏輯：使用文件 ID 的前兩個字符作為子目錄（向後兼容）
            # 注意：新邏輯要求所有文件必須有 task_id，此處保留用於遷移期間
            subdir = file_id[:2]
            subdir_path = self.storage_path / subdir
            subdir_path.mkdir(parents=True, exist_ok=True)

            if filename:
                # 保留原始擴展名
                ext = Path(filename).suffix
                return subdir_path / f"{file_id}{ext}"
            else:
                return subdir_path / file_id

    def save_file(
        self,
        file_content: bytes,
        filename: str,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        保存文件到本地文件系統

        Args:
            file_content: 文件內容
            filename: 原始文件名
            file_id: 文件 ID（可選，如果不提供則自動生成）
            task_id: 任務 ID（可選，如果提供則文件存儲在任務工作區）

        Returns:
            (file_id, file_path)
        """
        if file_id is None:
            file_id = self.generate_file_id()

        file_path = self._get_file_path(file_id, filename, task_id)

        try:
            # 確保目錄存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 如果啟用加密，先加密文件內容
            content_to_write = file_content
            if self.enable_encryption and self._encryption_service:
                try:
                    content_to_write = self._encryption_service.encrypt(file_content)
                    self.logger.debug(
                        "文件已加密",
                        file_id=file_id,
                        original_size=len(file_content),
                        encrypted_size=len(content_to_write),
                    )
                except Exception as e:
                    self.logger.error(
                        "文件加密失敗，將保存未加密文件",
                        file_id=file_id,
                        error=str(e),
                    )
                    # 加密失敗時，保存未加密文件（可選：也可以拋出異常）
                    content_to_write = file_content

            # 寫入文件
            with open(file_path, "wb") as f:
                f.write(content_to_write)

            self.logger.info(
                "文件保存成功",
                file_id=file_id,
                filename=filename,
                file_path=str(file_path),
                file_size=len(file_content),
                encrypted=self.enable_encryption and self._encryption_service is not None,
            )

            return file_id, str(file_path)

        except Exception as e:
            self.logger.error(
                "文件保存失敗",
                file_id=file_id,
                filename=filename,
                error=str(e),
            )
            raise

    def get_file_path(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        獲取文件路徑

        修改時間：2025-01-27 - 改進文件查找邏輯，支持多種路徑查找方式

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            文件路徑，如果不存在則返回 None

        查找順序：
        1. 優先使用 metadata_storage_path（如果提供且文件存在）
        2. 如果提供了 task_id，在任務工作區中查找
        3. 否則在舊的目錄結構中查找（向後兼容）
        """
        # 修改時間：2025-01-27 - 優先使用 metadata 中的 storage_path
        if metadata_storage_path and os.path.exists(metadata_storage_path):
            return metadata_storage_path

        # 修改時間：2025-01-27 - 如果提供了 task_id，在任務工作區中查找
        if task_id:
            try:
                from services.api.services.task_workspace_service import get_task_workspace_service

                workspace_service = get_task_workspace_service()
                workspace_path = workspace_service.get_workspace_path(task_id)

                if workspace_path.exists():
                    # 查找以 file_id 開頭的文件
                    for file_path in workspace_path.iterdir():
                        if file_path.is_file() and file_path.stem == file_id:
                            return str(file_path)
            except Exception as e:
                logger.warning(
                    "Failed to get file path from workspace",
                    file_id=file_id,
                    task_id=task_id,
                    error=str(e),
                )

        # 修改時間：2025-01-27 - 向後兼容：在舊的目錄結構中查找
        subdir = file_id[:2]
        subdir_path = self.storage_path / subdir

        if subdir_path.exists():
            # 查找以 file_id 開頭的文件
            for file_path in subdir_path.iterdir():
                if file_path.is_file() and file_path.stem == file_id:
                    return str(file_path)

        return None

    def read_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        讀取文件內容

        修改時間：2025-01-27 - 支持使用 metadata_storage_path

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            文件內容，如果不存在則返回 None
        """
        file_path = self.get_file_path(file_id, task_id, metadata_storage_path)
        if file_path is None:
            return None

        try:
            with open(file_path, "rb") as f:
                encrypted_content = f.read()

            # 如果啟用加密，嘗試解密文件內容
            if self.enable_encryption and self._encryption_service:
                try:
                    # 檢查是否已加密
                    if self._encryption_service.is_encrypted(encrypted_content):
                        decrypted_content = self._encryption_service.decrypt(encrypted_content)
                        self.logger.debug(
                            "文件已解密",
                            file_id=file_id,
                            encrypted_size=len(encrypted_content),
                            decrypted_size=len(decrypted_content),
                        )
                        return decrypted_content
                    else:
                        # 文件未加密，直接返回
                        self.logger.debug("文件未加密，直接返回", file_id=file_id)
                        return encrypted_content
                except Exception as e:
                    self.logger.error(
                        "文件解密失敗",
                        file_id=file_id,
                        error=str(e),
                        exc_info=True,
                    )
                    # 解密失敗時，返回 None（可選：也可以返回原始內容）
                    return None

            # 未啟用加密，直接返回
            return encrypted_content
        except Exception as e:
            self.logger.error("文件讀取失敗", file_id=file_id, error=str(e))
            return None

    def delete_file(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> bool:
        """
        刪除文件

        修改時間：2025-01-27 - 支持使用 metadata_storage_path

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            是否成功刪除
        """
        file_path = self.get_file_path(file_id, task_id, metadata_storage_path)
        if file_path is None:
            return False

        try:
            os.remove(file_path)
            self.logger.info("文件刪除成功", file_id=file_id, file_path=file_path)
            return True
        except Exception as e:
            self.logger.error("文件刪除失敗", file_id=file_id, error=str(e))
            return False

    def file_exists(
        self,
        file_id: str,
        task_id: Optional[str] = None,
        metadata_storage_path: Optional[str] = None,
    ) -> bool:
        """
        檢查文件是否存在

        修改時間：2025-01-27 - 支持使用 metadata_storage_path

        Args:
            file_id: 文件 ID
            task_id: 任務 ID（可選，如果提供則在任務工作區中查找）
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            文件是否存在
        """
        return self.get_file_path(file_id, task_id, metadata_storage_path) is not None

    def move_file(
        self,
        file_id: str,
        old_task_id: Optional[str],
        new_task_id: str,
        metadata_storage_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        移動文件到新的任務工作區

        修改時間：2026-01-21 - 實現本地文件移動

        Args:
            file_id: 文件 ID
            old_task_id: 舊任務 ID
            new_task_id: 新任務 ID
            metadata_storage_path: 元數據中記錄的存儲路徑（優先使用）

        Returns:
            新的存儲路徑，如果移動失敗則返回 None
        """
        old_path = self.get_file_path(file_id, old_task_id, metadata_storage_path)
        if old_path is None:
            self.logger.warning("File not found for move", file_id=file_id, old_task_id=old_task_id)
            return None

        new_path = self._get_file_path(file_id, None, new_task_id)

        try:
            if old_path != str(new_path):
                new_path.parent.mkdir(parents=True, exist_ok=True)
                if old_path.exists():
                    import shutil

                    shutil.move(str(old_path), str(new_path))
                    self.logger.info(
                        "File moved successfully",
                        file_id=file_id,
                        old_path=str(old_path),
                        new_path=str(new_path),
                    )
                else:
                    self.logger.warning(
                        "File does not exist, cannot move",
                        file_id=file_id,
                        old_path=str(old_path),
                    )
                    return None
            return str(new_path)
        except Exception as e:
            self.logger.error(
                "Failed to move file",
                file_id=file_id,
                old_path=str(old_path),
                new_path=str(new_path),
                error=str(e),
            )
            return None


# 預留雲存儲接口（未來擴展）
class S3FileStorage(FileStorage):
    """S3 雲存儲（預留接口）"""

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        初始化 S3 文件存儲

        Args:
            bucket_name: S3 存儲桶名稱
            region: AWS 區域
        """
        self.bucket_name = bucket_name
        self.region = region
        raise NotImplementedError("S3 存儲尚未實現")


class OSSFileStorage(FileStorage):
    """阿里雲 OSS 存儲（預留接口）"""

    def __init__(self, bucket_name: str, endpoint: str):
        """
        初始化 OSS 文件存儲

        Args:
            bucket_name: OSS 存儲桶名稱
            endpoint: OSS 端點
        """
        self.bucket_name = bucket_name
        self.endpoint = endpoint
        raise NotImplementedError("OSS 存儲尚未實現")


def _get_s3_config(
    config: dict, service_type: Optional[str] = None
) -> Optional[Tuple[str, str, str, bool, "SeaweedFSService"]]:
    """
    獲取 S3 配置

    Args:
        config: 配置文件
        service_type: 服務類型（"ai_box" 或 "datalake"）

    Returns:
        如果配置可用，返回 (endpoint, access_key, secret_key, use_ssl, service_type_enum)
        否則返回 None
    """
    from storage.s3_storage import SeaweedFSService

    # 確定服務類型
    if service_type is None:
        service_type = config.get("service_type", "ai_box")

    # 根據服務類型選擇配置
    if service_type == "ai_box" or service_type == SeaweedFSService.AI_BOX:
        endpoint = (
            config.get("ai_box_seaweedfs_s3_endpoint")
            or os.getenv("AI_BOX_SEAWEEDFS_S3_ENDPOINT")
            or "http://seaweedfs-ai-box-filer:8333"
        )
        access_key = (
            config.get("ai_box_seaweedfs_s3_access_key")
            or os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY")
            or ""
        )
        secret_key = (
            config.get("ai_box_seaweedfs_s3_secret_key")
            or os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY")
            or ""
        )
        use_ssl = (
            config.get("ai_box_seaweedfs_use_ssl", False)
            or os.getenv("AI_BOX_SEAWEEDFS_USE_SSL", "false").lower() == "true"
        )
        seaweedfs_service = SeaweedFSService.AI_BOX
    elif service_type == "datalake" or service_type == SeaweedFSService.DATALAKE:
        endpoint = (
            config.get("datalake_seaweedfs_s3_endpoint")
            or os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT")
            or "http://seaweedfs-datalake-filer:8333"
        )
        access_key = (
            config.get("datalake_seaweedfs_s3_access_key")
            or os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY")
            or ""
        )
        secret_key = (
            config.get("datalake_seaweedfs_s3_secret_key")
            or os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY")
            or ""
        )
        use_ssl = (
            config.get("datalake_seaweedfs_use_ssl", False)
            or os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"
        )
        seaweedfs_service = SeaweedFSService.DATALAKE
    else:
        return None

    # 檢查配置是否完整（endpoint 必須有，access_key 和 secret_key 必須都有）
    if not endpoint:
        return None
    if not access_key or not secret_key:
        return None

    return (endpoint, access_key, secret_key, use_ssl, seaweedfs_service)


def create_storage_from_config(
    config: Optional[dict] = None, service_type: Optional[str] = None
) -> FileStorage:
    """
    從配置創建文件存儲實例

    Args:
        config: 配置文件中的 file_upload 區塊（如果為 None，使用默認配置）
        service_type: SeaweedFS 服務類型（"ai_box" 或 "datalake"），僅在 storage_backend="s3" 時使用

    Returns:
        FileStorage 實例

    配置優先級：
    - 如果明確指定 storage_backend，使用指定值
    - 否則，生產環境（ENV=production）優先使用 S3，開發環境使用 Local
    - 如果 S3 配置可用，優先使用 S3
    - 否則回退到 Local
    """
    # 修改時間：2025-12-09 - 處理 config 為 None 的情況
    # 修改時間：2025-01-27 - 添加 S3 存儲支持和雙服務選擇
    # 修改時間：2025-01-27 - 實現配置優先級：S3 > Local（生產環境使用 S3）
    if config is None:
        config = {}

    storage_backend = config.get("storage_backend")
    storage_path = config.get("storage_path", "./data/datasets/files")
    encryption_config = config.get("encryption", {}) if config.get("encryption") else {}
    enable_encryption = (
        encryption_config.get("enabled", False) if isinstance(encryption_config, dict) else False
    )

    # 如果明確指定了 storage_backend，使用指定值
    if storage_backend == "local":
        return LocalFileStorage(storage_path=storage_path, enable_encryption=enable_encryption)
    elif storage_backend == "s3":
        # 導入 S3FileStorage（延遲導入避免循環依賴）
        from storage.s3_storage import S3FileStorage

        # 獲取 S3 配置
        s3_config = _get_s3_config(config, service_type)
        if s3_config is None:
            raise ValueError("SeaweedFS S3 配置不完整或服務類型不支持")

        endpoint, access_key, secret_key, use_ssl, seaweedfs_service = s3_config

        # 創建 S3FileStorage 實例
        return S3FileStorage(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            use_ssl=use_ssl,
            service_type=seaweedfs_service,
        )
    elif storage_backend == "oss":
        raise NotImplementedError("OSS 存儲尚未實現")
    else:
        # 如果未明確指定 storage_backend，根據環境和配置自動選擇
        # 優先級：S3 > Local（生產環境使用 S3）
        env = os.getenv("ENV", "development").lower()

        # 檢查 S3 配置是否可用
        s3_config = _get_s3_config(config, service_type)

        # 生產環境優先使用 S3，如果 S3 配置可用
        if env == "production" and s3_config is not None:
            from storage.s3_storage import S3FileStorage

            endpoint, access_key, secret_key, use_ssl, seaweedfs_service = s3_config
            return S3FileStorage(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                use_ssl=use_ssl,
                service_type=seaweedfs_service,
            )
        elif s3_config is not None:
            # 開發環境：如果 S3 配置可用，也可以使用 S3
            from storage.s3_storage import S3FileStorage

            endpoint, access_key, secret_key, use_ssl, seaweedfs_service = s3_config
            return S3FileStorage(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                use_ssl=use_ssl,
                service_type=seaweedfs_service,
            )
        else:
            # 默認使用 LocalFileStorage（S3 配置不可用時）
            return LocalFileStorage(storage_path=storage_path, enable_encryption=enable_encryption)
