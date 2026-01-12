# 代碼功能說明: Capability Adapter 數據庫適配器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 數據庫適配器

實現數據庫操作的適配器，限制表白名單，記錄審計日誌。
"""

import logging
from typing import Any, Dict, List, Optional

from agents.services.capability_adapter.adapter import CapabilityAdapter
from agents.services.capability_adapter.models import AdapterResult, ValidationResult

logger = logging.getLogger(__name__)


class DatabaseAdapter(CapabilityAdapter):
    """數據庫操作適配器"""

    def __init__(self, allowed_tables: Optional[List[str]] = None):
        """
        初始化數據庫操作適配器

        Args:
            allowed_tables: 允許的表名列表（白名單），如果不提供則從配置文件加載
        """
        if allowed_tables is None:
            from agents.services.capability_adapter.config_loader import (
                CapabilityAdapterConfigLoader,
            )

            config_loader = CapabilityAdapterConfigLoader()
            allowed_tables = config_loader.get_database_adapter_tables()

        super().__init__(allowed_scopes=allowed_tables or [])
        self.allowed_tables = allowed_tables or []

    def validate(self, params: Dict[str, Any]) -> ValidationResult:
        """
        驗證參數

        Args:
            params: 參數字典，應包含 "table" 或 "collection" 字段

        Returns:
            ValidationResult 對象
        """
        table_name = params.get("table") or params.get("collection")

        if not table_name:
            return ValidationResult(valid=False, reason="table or collection is required")

        # 檢查表名是否在白名單中
        if not self.check_scope(table_name):
            return ValidationResult(valid=False, reason=f"Table not in allowed list: {table_name}")

        return ValidationResult(valid=True)

    async def execute(self, capability: str, params: Dict[str, Any]) -> AdapterResult:
        """
        執行數據庫操作

        支持的能力：
        - query: 查詢數據
        - update: 更新數據
        - insert: 插入數據
        - delete: 刪除數據

        Args:
            capability: 能力名稱
            params: 參數字典

        Returns:
            AdapterResult 對象
        """
        # 驗證參數
        validation = self.validate(params)
        if not validation.valid:
            return AdapterResult(success=False, error=validation.reason)

        table_name = params.get("table") or params.get("collection")

        try:
            if capability == "query":
                return await self._query(table_name, params)
            elif capability == "update":
                return await self._update(table_name, params)
            elif capability == "insert":
                return await self._insert(table_name, params)
            elif capability == "delete":
                return await self._delete(table_name, params)
            else:
                return AdapterResult(success=False, error=f"Unsupported capability: {capability}")
        except Exception as e:
            logger.error(f"Database operation failed: {e}", exc_info=True)
            return AdapterResult(success=False, error=str(e))

    async def _query(self, table_name: str, params: Dict[str, Any]) -> AdapterResult:
        """查詢數據"""
        # 簡化實現：實際應該調用數據庫客戶端
        logger.info(f"Querying table: {table_name}")
        audit_log = self.create_audit_log(
            "query", {"table": table_name, "params": params}, AdapterResult(success=True)
        )
        return AdapterResult(
            success=True, result={"table": table_name, "rows": []}, audit_log=audit_log
        )

    async def _update(self, table_name: str, params: Dict[str, Any]) -> AdapterResult:
        """更新數據"""
        # 簡化實現：實際應該調用數據庫客戶端
        logger.info(f"Updating table: {table_name}")
        audit_log = self.create_audit_log(
            "update", {"table": table_name, "params": params}, AdapterResult(success=True)
        )
        return AdapterResult(
            success=True, result={"table": table_name, "rows_updated": 0}, audit_log=audit_log
        )

    async def _insert(self, table_name: str, params: Dict[str, Any]) -> AdapterResult:
        """插入數據"""
        # 簡化實現：實際應該調用數據庫客戶端
        logger.info(f"Inserting into table: {table_name}")
        audit_log = self.create_audit_log(
            "insert", {"table": table_name, "params": params}, AdapterResult(success=True)
        )
        return AdapterResult(
            success=True, result={"table": table_name, "rows_inserted": 0}, audit_log=audit_log
        )

    async def _delete(self, table_name: str, params: Dict[str, Any]) -> AdapterResult:
        """刪除數據"""
        # 簡化實現：實際應該調用數據庫客戶端
        logger.info(f"Deleting from table: {table_name}")
        audit_log = self.create_audit_log(
            "delete", {"table": table_name, "params": params}, AdapterResult(success=True)
        )
        return AdapterResult(
            success=True, result={"table": table_name, "rows_deleted": 0}, audit_log=audit_log
        )
