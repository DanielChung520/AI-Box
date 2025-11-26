# 代碼功能說明: 解析器基類
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""解析器基類 - 定義統一接口和錯誤處理"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class BaseParser(ABC):
    """解析器抽象基類"""

    def __init__(self):
        self.logger = logger.bind(parser=self.__class__.__name__)

    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析文件

        Args:
            file_path: 文件路徑

        Returns:
            解析結果，包含 text 和 metadata
        """
        pass

    @abstractmethod
    def parse_from_bytes(self, file_content: bytes, **kwargs) -> Dict[str, Any]:
        """
        從字節內容解析

        Args:
            file_content: 文件內容（字節）
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        pass

    def can_parse(self, file_path: str) -> bool:
        """
        檢查是否可以解析此文件

        Args:
            file_path: 文件路徑

        Returns:
            是否可以解析
        """
        return True

    def get_supported_extensions(self) -> list:
        """
        獲取支持的文件擴展名列表

        Returns:
            擴展名列表
        """
        return []
