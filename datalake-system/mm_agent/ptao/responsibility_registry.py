# 代碼功能說明: P-T-A-O 職責分派 Registry
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""
職責分派 Registry - Dict 容器

提供職責類型到 handler 函數的映射。
取代 _execute_responsibility() 中的 if/elif 分支邏輯。

特性：
- 動態註冊 handler
- 友善查詢（未知類型返回 None，不拋出異常）
- 簡單的 Dict 容器實作
"""

from typing import Dict, Callable, Optional, List


class ResponsibilityRegistry:
    """
    職責分派 Registry

    管理職責類型到 handler 函數的映射。
    提供簡單、可擴展的職責派遣容器。

    支援的 7 種預設類型（但不自動建立）：
    - query_part
    - query_stock
    - query_stock_history
    - analyze_shortage
    - generate_purchase_order
    - analyze_existing_result
    - clarification_needed
    """

    def __init__(self):
        """初始化空 registry"""
        self._handlers: Dict[str, Callable] = {}

    def register(self, responsibility_type: str, handler: Callable) -> None:
        """
        註冊 handler

        Args:
            responsibility_type: 職責類型
            handler: 可呼叫的 handler 函數

        Returns:
            無
        """
        if not isinstance(responsibility_type, str):
            raise TypeError(f"職責類型必須是字符串，但獲得: {type(responsibility_type)}")

        if not callable(handler):
            raise TypeError(f"Handler 必須是可呼叫的，但獲得: {type(handler)}")

        self._handlers[responsibility_type] = handler

    def get_handler(self, responsibility_type: str) -> Optional[Callable]:
        """
        取得 handler

        Args:
            responsibility_type: 職責類型

        Returns:
            Handler 函數，如果找不到返回 None
        """
        return self._handlers.get(responsibility_type, None)

    def has_handler(self, responsibility_type: str) -> bool:
        """
        檢查是否已註冊 handler

        Args:
            responsibility_type: 職責類型

        Returns:
            已註冊返回 True，未註冊返回 False
        """
        return responsibility_type in self._handlers

    def list_types(self) -> List[str]:
        """
        列出所有已註冊的職責類型

        Returns:
            職責類型列表
        """
        return list(self._handlers.keys())

    def get_all_handlers(self) -> Dict[str, Callable]:
        """
        取得所有 handler 的副本

        Returns:
            責任類型到 handler 的字典（副本）
        """
        return dict(self._handlers)
