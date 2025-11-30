# 代碼功能說明: 文件驗證工具
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件驗證工具 - 提供 MIME 類型、擴展名、大小和內容驗證"""

import os
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)

# 支持的文件格式映射
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        ".docx"
    ],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/csv": [".csv"],
    "application/json": [".json"],
    "text/html": [".html"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
}

# 擴展名到 MIME 類型的映射
EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# 允許的擴展名列表
ALLOWED_EXTENSIONS = list(EXTENSION_TO_MIME.keys())


class FileValidationError(Exception):
    """文件驗證錯誤"""

    pass


class FileValidator:
    """文件驗證器"""

    def __init__(
        self,
        allowed_extensions: Optional[List[str]] = None,
        max_file_size: int = 104857600,  # 100MB
    ):
        """
        初始化文件驗證器

        Args:
            allowed_extensions: 允許的文件擴展名列表，默認為所有支持的格式
            max_file_size: 最大文件大小（字節），默認 100MB
        """
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size
        self.logger = logger.bind(
            allowed_extensions=self.allowed_extensions,
            max_file_size=max_file_size,
        )

    def validate_file(
        self, file_path: str, filename: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證文件

        Args:
            file_path: 文件路徑
            filename: 文件名（可選，用於擴展名驗證）

        Returns:
            (是否有效, 錯誤消息)
        """
        try:
            # 驗證文件是否存在
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"

            # 驗證文件大小
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return (
                    False,
                    f"文件大小超過限制: {file_size} bytes > {self.max_file_size} bytes",
                )

            if file_size == 0:
                return False, "文件為空"

            # 驗證擴展名
            if filename:
                ext = Path(filename).suffix.lower()
                if ext not in self.allowed_extensions:
                    return False, f"不支持的文件擴展名: {ext}"

            # 驗證 MIME 類型
            if filename:
                mime_type, _ = mimetypes.guess_type(filename)
                if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                    # 檢查是否在允許的擴展名中
                    ext = Path(filename).suffix.lower()
                    if ext not in self.allowed_extensions:
                        return False, f"不支持的文件類型: {mime_type}"

            # 基本內容驗證（檢查文件是否可讀）
            try:
                with open(file_path, "rb") as f:
                    # 讀取前幾個字節進行基本驗證
                    header = f.read(1024)
                    if len(header) == 0:
                        return False, "文件無法讀取或為空"
            except IOError as e:
                return False, f"文件讀取錯誤: {str(e)}"

            return True, None

        except Exception as e:
            self.logger.error("文件驗證失敗", error=str(e), file_path=file_path)
            return False, f"文件驗證失敗: {str(e)}"

    def validate_upload_file(
        self, file_content: bytes, filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證上傳的文件

        Args:
            file_content: 文件內容（字節）
            filename: 文件名

        Returns:
            (是否有效, 錯誤消息)
        """
        # 驗證文件大小
        file_size = len(file_content)
        if file_size > self.max_file_size:
            return (
                False,
                f"文件大小超過限制: {file_size} bytes > {self.max_file_size} bytes",
            )

        if file_size == 0:
            return False, "文件為空"

        # 驗證擴展名
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            return False, f"不支持的文件擴展名: {ext}"

        # 驗證 MIME 類型
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            # 檢查 MIME 類型是否在允許列表中
            if mime_type not in ALLOWED_MIME_TYPES:
                # 如果 MIME 類型不在列表中，檢查擴展名是否允許
                if ext not in self.allowed_extensions:
                    return False, f"不支持的文件類型: {mime_type}"

        # 基本內容驗證（檢查文件頭）
        if len(file_content) > 0:
            # 檢查常見的惡意文件標識（簡單檢查）
            # 這裡可以擴展更複雜的驗證邏輯
            pass

        return True, None

    def get_file_type(self, filename: str) -> Optional[str]:
        """
        獲取文件類型（MIME 類型）

        Args:
            filename: 文件名

        Returns:
            MIME 類型，如果無法確定則返回 None
        """
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type

        # 如果無法通過 mimetypes 確定，使用擴展名映射
        ext = Path(filename).suffix.lower()
        return EXTENSION_TO_MIME.get(ext)

    def is_allowed_extension(self, extension: str) -> bool:
        """
        檢查擴展名是否允許

        Args:
            extension: 文件擴展名（包含點號，如 .pdf）

        Returns:
            是否允許
        """
        return extension.lower() in self.allowed_extensions


def create_validator_from_config(config: dict) -> FileValidator:
    """
    從配置創建文件驗證器

    Args:
        config: 配置文件中的 file_upload 區塊

    Returns:
        FileValidator 實例
    """
    allowed_extensions = config.get("allowed_extensions", ALLOWED_EXTENSIONS)
    max_file_size = config.get("max_file_size", 104857600)

    return FileValidator(
        allowed_extensions=allowed_extensions, max_file_size=max_file_size
    )
