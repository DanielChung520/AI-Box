# 代碼功能說明: 文件存儲模組
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件存儲模組 - 提供本地和雲存儲接口"""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class FileStorage(ABC):
    """文件存儲抽象基類"""

    @abstractmethod
    def save_file(
        self, file_content: bytes, filename: str, file_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        保存文件

        Args:
            file_content: 文件內容
            filename: 原始文件名
            file_id: 文件 ID（可選，如果不提供則自動生成）

        Returns:
            (file_id, file_path)
        """
        pass

    @abstractmethod
    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        獲取文件路徑

        Args:
            file_id: 文件 ID

        Returns:
            文件路徑，如果不存在則返回 None
        """
        pass

    @abstractmethod
    def read_file(self, file_id: str) -> Optional[bytes]:
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
    def file_exists(self, file_id: str) -> bool:
        """
        檢查文件是否存在

        Args:
            file_id: 文件 ID

        Returns:
            文件是否存在
        """
        pass

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
                from services.api.services.encryption_service import (
                    get_encryption_service,
                )

                self._encryption_service = get_encryption_service()
                self.logger.info("文件加密已啟用")
            except Exception as e:
                self.logger.warning("無法初始化加密服務，將禁用加密", error=str(e))
                self.enable_encryption = False

    def _get_file_path(self, file_id: str, filename: Optional[str] = None) -> Path:
        """
        獲取文件路徑

        Args:
            file_id: 文件 ID
            filename: 文件名（可選）

        Returns:
            文件路徑
        """
        # 使用文件 ID 的前兩個字符作為子目錄，避免單一目錄文件過多
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
        self, file_content: bytes, filename: str, file_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        保存文件到本地文件系統

        Args:
            file_content: 文件內容
            filename: 原始文件名
            file_id: 文件 ID（可選，如果不提供則自動生成）

        Returns:
            (file_id, file_path)
        """
        if file_id is None:
            file_id = self.generate_file_id()

        file_path = self._get_file_path(file_id, filename)

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
                encrypted=self.enable_encryption
                and self._encryption_service is not None,
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

    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        獲取文件路徑

        Args:
            file_id: 文件 ID

        Returns:
            文件路徑，如果不存在則返回 None
        """
        # 嘗試查找文件（可能有多種擴展名）
        subdir = file_id[:2]
        subdir_path = self.storage_path / subdir

        if not subdir_path.exists():
            return None

        # 查找以 file_id 開頭的文件
        for file_path in subdir_path.iterdir():
            if file_path.stem == file_id:
                return str(file_path)

        return None

    def read_file(self, file_id: str) -> Optional[bytes]:
        """
        讀取文件內容

        Args:
            file_id: 文件 ID

        Returns:
            文件內容，如果不存在則返回 None
        """
        file_path = self.get_file_path(file_id)
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
                        decrypted_content = self._encryption_service.decrypt(
                            encrypted_content
                        )
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

    def delete_file(self, file_id: str) -> bool:
        """
        刪除文件

        Args:
            file_id: 文件 ID

        Returns:
            是否成功刪除
        """
        file_path = self.get_file_path(file_id)
        if file_path is None:
            return False

        try:
            os.remove(file_path)
            self.logger.info("文件刪除成功", file_id=file_id, file_path=file_path)
            return True
        except Exception as e:
            self.logger.error("文件刪除失敗", file_id=file_id, error=str(e))
            return False

    def file_exists(self, file_id: str) -> bool:
        """
        檢查文件是否存在

        Args:
            file_id: 文件 ID

        Returns:
            文件是否存在
        """
        return self.get_file_path(file_id) is not None


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


def create_storage_from_config(config: dict) -> FileStorage:
    """
    從配置創建文件存儲實例

    Args:
        config: 配置文件中的 file_upload 區塊

    Returns:
        FileStorage 實例
    """
    storage_backend = config.get("storage_backend", "local")
    storage_path = config.get("storage_path", "./data/datasets/files")
    enable_encryption = config.get("encryption", {}).get("enabled", False)

    if storage_backend == "local":
        return LocalFileStorage(
            storage_path=storage_path, enable_encryption=enable_encryption
        )
    elif storage_backend == "s3":
        raise NotImplementedError("S3 存儲尚未實現")
    elif storage_backend == "oss":
        raise NotImplementedError("OSS 存儲尚未實現")
    else:
        raise ValueError(f"不支持的存儲後端: {storage_backend}")
