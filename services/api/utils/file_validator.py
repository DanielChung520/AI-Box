# 代碼功能說明: 文件驗證工具
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""文件驗證工具 - 提供 MIME 類型、擴展名、大小和內容驗證"""

import mimetypes
import os
from pathlib import Path
from typing import List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

# 支持的文件格式映射
ALLOWED_MIME_TYPES = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/msword": [".doc"],  # .doc
    "text/plain": [".txt"],
    "text/markdown": [".md"],
    "text/csv": [".csv"],
    "application/json": [".json"],
    "text/html": [".html"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "application/vnd.ms-excel": [".xls"],  # .xls
    # 圖像格式
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/gif": [".gif"],
    "image/bmp": [".bmp"],
    "image/webp": [".webp"],
    "image/svg+xml": [".svg"],
}

# 擴展名到 MIME 類型的映射
EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    # 圖像格式
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

# 允許的擴展名列表
ALLOWED_EXTENSIONS = list(EXTENSION_TO_MIME.keys())

# 文件簽名（魔數）驗證 - 用於驗證文件實際類型
FILE_SIGNATURES = {
    b"%PDF": [".pdf"],  # PDF 文件
    b"PK\x03\x04": [".docx", ".xlsx"],  # ZIP-based formats (DOCX, XLSX)
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": [".doc", ".xls"],  # OLE2 (DOC, XLS)
    # 圖像格式簽名
    b"\x89PNG\r\n\x1a\n": [".png"],  # PNG 文件
    b"\xff\xd8\xff": [".jpg", ".jpeg"],  # JPEG 文件
    b"GIF87a": [".gif"],  # GIF 87a 格式
    b"GIF89a": [".gif"],  # GIF 89a 格式
    b"BM": [".bmp"],  # BMP 文件
    b"RIFF": [".webp"],  # WebP 文件（需要進一步檢查）
    b"<svg": [".svg"],  # SVG 文件（XML 格式）
    b"<?xml": [".svg"],  # SVG 文件（XML 格式，可能以 <?xml 開頭）
}


class FileValidationError(Exception):
    """文件驗證錯誤"""

    pass


def validate_file_signature(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """驗證文件簽名（魔數）以確認文件實際類型。

    Args:
        file_content: 文件內容（字節）
        filename: 文件名

    Returns:
        (是否有效, 錯誤消息)
    """
    if len(file_content) < 4:
        return True, None  # 文件太小，跳過簽名驗證

    ext = Path(filename).suffix.lower()

    # 檢查 PDF
    if ext == ".pdf":
        if not file_content.startswith(b"%PDF"):
            return False, "PDF 文件簽名驗證失敗，文件可能損壞"

    # 檢查 ZIP-based 格式 (DOCX, XLSX)
    if ext in [".docx", ".xlsx"]:
        if not file_content.startswith(b"PK\x03\x04"):
            return False, f"{ext[1:].upper()} 文件簽名驗證失敗，文件可能損壞"

    # 檢查 OLE2 格式 (DOC, XLS)
    if ext in [".doc", ".xls"]:
        if not file_content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            return False, f"{ext[1:].upper()} 文件簽名驗證失敗，文件可能損壞"

    # 檢查圖像格式
    if ext in [".png"]:
        if not file_content.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "PNG 文件簽名驗證失敗，文件可能損壞"

    if ext in [".jpg", ".jpeg"]:
        if not file_content.startswith(b"\xff\xd8\xff"):
            return False, "JPEG 文件簽名驗證失敗，文件可能損壞"

    if ext == ".gif":
        # GIF 可以是 GIF87a 或 GIF89a
        if not (file_content.startswith(b"GIF87a") or file_content.startswith(b"GIF89a")):
            return False, "GIF 文件簽名驗證失敗，文件可能損壞"

    if ext == ".bmp":
        if not file_content.startswith(b"BM"):
            return False, "BMP 文件簽名驗證失敗，文件可能損壞"

    if ext == ".webp":
        # WebP 文件以 RIFF 開頭，但需要進一步檢查 WEBP 標識
        if not (file_content.startswith(b"RIFF") and b"WEBP" in file_content[:12]):
            return False, "WebP 文件簽名驗證失敗，文件可能損壞"

    if ext == ".svg":
        # SVG 是 XML 格式，可能以 <svg 或 <?xml 開頭
        header_str = file_content[:100].decode("utf-8", errors="ignore").strip()
        if not (header_str.startswith("<svg") or header_str.startswith("<?xml")):
            # 對於 SVG，如果無法解析為文本，可能是二進制文件，跳過嚴格驗證
            pass  # SVG 驗證較寬鬆，因為可能是壓縮的 SVGZ

    return True, None


class FileValidator:
    """文件驗證器"""

    def __init__(
        self,
        allowed_extensions: Optional[List[str]] = None,
        max_file_size: int = 52428800,  # 50MB (符合計劃要求)
    ):
        """
        初始化文件驗證器

        Args:
            allowed_extensions: 允許的文件擴展名列表，默認為所有支持的格式
            max_file_size: 最大文件大小（字節），默認 50MB
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
                    f"文件大小超過限制: {self._format_size(file_size)} > {self._format_size(self.max_file_size)}",
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
                if mime_type:
                    # 檢查 MIME 類型是否在允許列表中
                    if mime_type not in ALLOWED_MIME_TYPES:
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

                    # 驗證文件簽名
                    if filename:
                        is_valid, error_msg = validate_file_signature(header, filename)
                        if not is_valid:
                            return False, error_msg or "文件內容驗證失敗"
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
                f"文件大小超過限制: {self._format_size(file_size)} > {self._format_size(self.max_file_size)}",
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
                if ext not in self.allowed_extensions:
                    return False, f"不支持的文件類型: {mime_type}"

        # 文件內容驗證（檢查文件簽名）
        is_valid, error_msg = validate_file_signature(file_content, filename)
        if not is_valid:
            return False, error_msg or "文件內容驗證失敗"

        # 文件名清理和驗證
        sanitized_filename = self.sanitize_filename(filename)
        if sanitized_filename != filename:
            return False, f"文件名包含非法字符，已清理為: {sanitized_filename}"

        # 路徑驗證（防止路徑遍歷攻擊）
        if not self.validate_path(filename):
            return False, "文件名包含路徑遍歷字符"

        # 檢查文件名長度
        if len(filename) > 255:
            return False, "文件名過長"

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

    def sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除危險字符

        Args:
            filename: 原始文件名

        Returns:
            清理後的文件名
        """
        # 移除路徑分隔符和路徑遍歷字符
        filename = filename.replace("..", "")
        filename = filename.replace("/", "_")
        filename = filename.replace("\\", "_")
        filename = filename.replace(":", "_")

        # 移除控制字符（保留換行、回車、製表符）
        filename = "".join(c for c in filename if ord(c) >= 32 or c in ["\n", "\r", "\t"])

        # 移除前導和尾隨空格、點號
        filename = filename.strip(" .")

        # 限制文件名長度
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            max_name_len = 255 - len(ext)
            filename = name[:max_name_len] + ext

        return filename

    def validate_path(self, filename: str) -> bool:
        """
        驗證文件名路徑，防止路徑遍歷攻擊

        Args:
            filename: 文件名

        Returns:
            是否安全
        """
        # 檢查路徑遍歷字符
        if ".." in filename:
            return False

        # 檢查絕對路徑
        if os.path.isabs(filename):
            return False

        # 檢查路徑分隔符
        if "/" in filename or "\\" in filename:
            return False

        # 檢查 Windows 保留字符
        reserved_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in reserved_chars:
            if char in filename:
                return False

        return True

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小。

        Args:
            size: 文件大小（字節）

        Returns:
            格式化後的大小字符串
        """
        size_float: float = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"


def create_validator_from_config(config: dict) -> FileValidator:
    """
    從配置創建文件驗證器

    Args:
        config: 配置文件中的 file_upload 或 file_processing 區塊
               支持兩種格式：
               - 舊格式：{"allowed_extensions": [...], "max_file_size": ...}
               - 新格式：{"supported_file_types": [...], "max_file_size": ...}

    Returns:
        FileValidator 實例
    """
    # 支持新舊兩種配置格式
    if "allowed_extensions" in config:
        # 舊格式：直接使用 allowed_extensions
        allowed_extensions = config.get("allowed_extensions", ALLOWED_EXTENSIONS)
    elif "supported_file_types" in config:
        # 新格式：從 supported_file_types 轉換為 allowed_extensions
        supported_types = config.get("supported_file_types", [])
        # 將 MIME 類型轉換為擴展名列表
        allowed_extensions = []
        for mime_type in supported_types:
            if mime_type in ALLOWED_MIME_TYPES:
                allowed_extensions.extend(ALLOWED_MIME_TYPES[mime_type])
        # 去重並排序
        allowed_extensions = sorted(list(set(allowed_extensions)))
        if not allowed_extensions:
            allowed_extensions = ALLOWED_EXTENSIONS  # 如果轉換失敗，使用默認值
    else:
        # 如果都沒有，使用默認值
        allowed_extensions = ALLOWED_EXTENSIONS
    
    max_file_size = config.get("max_file_size", 104857600)  # 默認 100MB（與文檔一致）

    return FileValidator(allowed_extensions=allowed_extensions, max_file_size=max_file_size)
