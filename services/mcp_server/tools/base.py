# 代碼功能說明: MCP Server 工具基類
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 工具基類模組"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """工具基類"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
    ):
        """
        初始化工具

        Args:
            name: 工具名稱
            description: 工具描述
            input_schema: 輸入 Schema（JSON Schema 格式）
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行工具

        Args:
            arguments: 工具參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        pass

    def validate_input(self, arguments: Dict[str, Any]) -> bool:
        """
        驗證輸入參數（簡單實現，可擴展）

        Args:
            arguments: 工具參數

        Returns:
            bool: 是否有效
        """
        # 簡單驗證：檢查必需字段
        if "properties" in self.input_schema:
            required = self.input_schema.get("required", [])
            for field in required:
                if field not in arguments:
                    logger.warning(f"Missing required field: {field}")
                    return False
        return True

    def get_info(self) -> Dict[str, Any]:
        """
        獲取工具信息

        Returns:
            Dict[str, Any]: 工具信息
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
