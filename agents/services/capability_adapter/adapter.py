# 代碼功能說明: Capability Adapter 基類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 基類

定義適配器的標準接口，所有適配器都應該繼承此基類。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from agents.services.capability_adapter.models import AdapterResult, ValidationResult

logger = logging.getLogger(__name__)


class CapabilityAdapter(ABC):
    """Capability Adapter 基類

    定義適配器的標準接口，所有適配器都應該繼承此基類。
    """

    def __init__(self, allowed_scopes: list[str] | None = None):
        """
        初始化適配器

        Args:
            allowed_scopes: 允許的作用域列表（白名單）
        """
        self.allowed_scopes = allowed_scopes or []

    @abstractmethod
    async def execute(self, capability: str, params: Dict[str, Any]) -> AdapterResult:
        """
        執行能力操作

        Args:
            capability: 能力名稱（如 "read_file", "write_file"）
            params: 參數字典

        Returns:
            AdapterResult 對象
        """
        raise NotImplementedError

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> ValidationResult:
        """
        驗證參數

        Args:
            params: 參數字典

        Returns:
            ValidationResult 對象
        """
        raise NotImplementedError

    def check_scope(self, scope: str) -> bool:
        """
        檢查作用域是否在白名單中

        Args:
            scope: 作用域（如文件路徑、數據庫表名、API端點）

        Returns:
            是否允許
        """
        if not self.allowed_scopes:
            # 如果沒有設置白名單，允許所有作用域（開發階段）
            logger.warning("No allowed_scopes configured, allowing all scopes")
            return True

        return scope in self.allowed_scopes

    def create_audit_log(
        self, capability: str, params: Dict[str, Any], result: AdapterResult
    ) -> Dict[str, Any]:
        """
        創建審計日誌

        Args:
            capability: 能力名稱
            params: 參數字典
            result: 執行結果

        Returns:
            審計日誌字典
        """
        return {
            "capability": capability,
            "params": params,
            "success": result.success,
            "error": result.error,
            "timestamp": None,  # 實際實現中應該使用 datetime.utcnow()
        }
