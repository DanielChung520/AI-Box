# 代碼功能說明: 文件掃描服務
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:20 (UTC+8)

"""文件掃描服務 - 實現文件內容掃描（病毒掃描、惡意代碼檢測）"""

import re
from typing import Optional, Tuple, List
import structlog

logger = structlog.get_logger(__name__)

# 惡意文件簽名模式（基礎實現）
MALICIOUS_PATTERNS = [
    # 可執行文件簽名
    b"MZ\x90\x00",  # PE executable (Windows)
    b"\x7fELF",  # ELF executable (Linux)
    b"#!/bin/",  # Shell script
    b"#!/usr/bin/",  # Shell script
    # 常見惡意代碼模式
    b"eval(",  # JavaScript eval
    b"exec(",  # Python exec
    b"<script",  # Script tags
    b"javascript:",  # JavaScript protocol
]


class FileScanner:
    """文件掃描服務"""

    def __init__(self):
        """初始化文件掃描服務"""
        self.logger = logger
        self.malicious_patterns = MALICIOUS_PATTERNS

    def scan_file(
        self, file_content: bytes, filename: str, file_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        掃描文件內容，檢測惡意代碼

        Args:
            file_content: 文件內容（字節）
            filename: 文件名
            file_type: 文件類型（MIME類型，可選）

        Returns:
            (是否安全, 錯誤消息)
        """
        # 檢查文件大小（避免掃描過大文件）
        max_scan_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_scan_size:
            self.logger.warning(
                "文件過大，跳過深度掃描",
                filename=filename,
                file_size=len(file_content),
            )
            # 只檢查文件頭部
            content_to_scan = file_content[:1024]
        else:
            content_to_scan = file_content

        # 檢查惡意模式
        for pattern in self.malicious_patterns:
            if pattern in content_to_scan:
                # 對於某些模式，需要更嚴格的檢查
                if self._is_false_positive(pattern, content_to_scan, file_type):
                    continue

                self.logger.warning(
                    "檢測到可疑內容",
                    filename=filename,
                    pattern=pattern.hex(),
                )
                return False, f"文件包含可疑內容，可能包含惡意代碼: {filename}"

        # 檢查文件名中的可疑字符
        if self._has_suspicious_filename(filename):
            return False, f"文件名包含可疑字符: {filename}"

        return True, None

    def _is_false_positive(
        self, pattern: bytes, content: bytes, file_type: Optional[str]
    ) -> bool:
        """
        檢查是否為誤報

        Args:
            pattern: 檢測到的模式
            content: 文件內容
            file_type: 文件類型

        Returns:
            bool: 是否為誤報
        """
        # 對於某些文件類型，某些模式是正常的
        if file_type:
            # HTML文件可能包含 <script> 標籤，這是正常的
            if file_type == "text/html" and pattern == b"<script":
                return True

            # JavaScript文件可能包含 eval，需要更嚴格的檢查
            if file_type in ["application/javascript", "text/javascript"]:
                if pattern == b"eval(":
                    # 檢查是否在註釋中
                    return False  # 暫時不允許

        return False

    def _has_suspicious_filename(self, filename: str) -> bool:
        """
        檢查文件名是否包含可疑字符

        Args:
            filename: 文件名

        Returns:
            bool: 是否可疑
        """
        # 檢查路徑遍歷字符
        suspicious_chars = ["../", "..\\", "/", "\\"]
        for char in suspicious_chars:
            if char in filename:
                return True

        # 檢查控制字符
        if any(ord(c) < 32 for c in filename if c not in ["\n", "\r", "\t"]):
            return True

        return False

    def scan_for_virus(
        self, file_content: bytes, filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        病毒掃描（基礎實現）

        注意：這是一個基礎實現，生產環境應使用專業的病毒掃描庫（如 ClamAV）

        Args:
            file_content: 文件內容
            filename: 文件名

        Returns:
            (是否安全, 錯誤消息)
        """
        # TODO: 集成專業的病毒掃描庫（如 ClamAV）
        # 當前實現僅進行基礎檢查
        return self.scan_file(file_content, filename)


# 全局服務實例（懶加載）
_file_scanner: Optional[FileScanner] = None


def get_file_scanner() -> FileScanner:
    """獲取文件掃描服務實例（單例模式）"""
    global _file_scanner
    if _file_scanner is None:
        _file_scanner = FileScanner()
    return _file_scanner
