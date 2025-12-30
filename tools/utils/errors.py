# 代碼功能說明: 工具組錯誤定義
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具組錯誤定義

定義工具組相關的自定義異常類。
"""

from __future__ import annotations

from typing import Optional


class ToolError(Exception):
    """工具錯誤基類"""

    pass


class ToolExecutionError(ToolError):
    """工具執行錯誤"""

    def __init__(self, message: str, tool_name: Optional[str] = None) -> None:
        """
        初始化工具執行錯誤

        Args:
            message: 錯誤消息
            tool_name: 工具名稱（可選）
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.message = message


class ToolValidationError(ToolError):
    """工具驗證錯誤（輸入參數驗證失敗）"""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """
        初始化工具驗證錯誤

        Args:
            message: 錯誤消息
            field: 驗證失敗的字段（可選）
        """
        super().__init__(message)
        self.field = field
        self.message = message


class ToolNotFoundError(ToolError):
    """工具未找到錯誤"""

    def __init__(self, tool_name: str) -> None:
        """
        初始化工具未找到錯誤

        Args:
            tool_name: 工具名稱
        """
        super().__init__(f"Tool '{tool_name}' not found")
        self.tool_name = tool_name


class ToolConfigurationError(ToolError):
    """工具配置錯誤"""

    def __init__(self, message: str, tool_name: Optional[str] = None) -> None:
        """
        初始化工具配置錯誤

        Args:
            message: 錯誤消息
            tool_name: 工具名稱（可選）
        """
        super().__init__(message)
        self.tool_name = tool_name
        self.message = message
