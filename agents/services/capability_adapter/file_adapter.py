# 代碼功能說明: Capability Adapter 文件操作適配器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 文件操作適配器

實現文件操作的適配器，限制文件路徑白名單，記錄審計日誌。
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.services.capability_adapter.adapter import CapabilityAdapter
from agents.services.capability_adapter.models import AdapterResult, ValidationResult

logger = logging.getLogger(__name__)


class FileAdapter(CapabilityAdapter):
    """文件操作適配器"""

    def __init__(self, allowed_paths: Optional[List[str]] = None):
        """
        初始化文件操作適配器

        Args:
            allowed_paths: 允許的文件路徑列表（白名單），如果不提供則從配置文件加載
        """
        if allowed_paths is None:
            from agents.services.capability_adapter.config_loader import (
                CapabilityAdapterConfigLoader,
            )

            config_loader = CapabilityAdapterConfigLoader()
            allowed_paths = config_loader.get_file_adapter_paths()

        super().__init__(allowed_scopes=allowed_paths or [])
        self.allowed_paths = allowed_paths or []

    def validate(self, params: Dict[str, Any]) -> ValidationResult:
        """
        驗證參數

        Args:
            params: 參數字典，應包含 "file_path" 字段

        Returns:
            ValidationResult 對象
        """
        if "file_path" not in params:
            return ValidationResult(valid=False, reason="file_path is required")

        file_path = params["file_path"]

        # 檢查路徑是否在白名單中
        if not self.check_scope(file_path):
            return ValidationResult(
                valid=False, reason=f"File path not in allowed list: {file_path}"
            )

        # 檢查路徑是否安全（防止路徑遍歷攻擊）
        try:
            resolved_path = Path(file_path).resolve()
            # 檢查是否在允許的目錄下
            if self.allowed_paths:
                allowed = False
                for allowed_path in self.allowed_paths:
                    allowed_resolved = Path(allowed_path).resolve()
                    try:
                        resolved_path.relative_to(allowed_resolved)
                        allowed = True
                        break
                    except ValueError:
                        continue

                if not allowed:
                    return ValidationResult(
                        valid=False, reason=f"File path not in allowed directory: {file_path}"
                    )
        except Exception as e:
            return ValidationResult(valid=False, reason=f"Invalid file path: {e}")

        return ValidationResult(valid=True)

    async def execute(self, capability: str, params: Dict[str, Any]) -> AdapterResult:
        """
        執行文件操作

        支持的能力：
        - read_file: 讀取文件
        - write_file: 寫入文件
        - delete_file: 刪除文件
        - list_files: 列出文件

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

        file_path = params["file_path"]

        try:
            if capability == "read_file":
                return await self._read_file(file_path)
            elif capability == "write_file":
                content = params.get("content", "")
                return await self._write_file(file_path, content)
            elif capability == "delete_file":
                return await self._delete_file(file_path)
            elif capability == "list_files":
                directory = params.get("directory", file_path)
                return await self._list_files(directory)
            else:
                return AdapterResult(success=False, error=f"Unsupported capability: {capability}")
        except Exception as e:
            logger.error(f"File operation failed: {e}", exc_info=True)
            return AdapterResult(success=False, error=str(e))

    async def _read_file(self, file_path: str) -> AdapterResult:
        """讀取文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            audit_log = self.create_audit_log(
                "read_file", {"file_path": file_path}, AdapterResult(success=True)
            )

            return AdapterResult(
                success=True,
                result={"content": content, "file_path": file_path},
                audit_log=audit_log,
            )
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    async def _write_file(self, file_path: str, content: str) -> AdapterResult:
        """寫入文件"""
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            audit_log = self.create_audit_log(
                "write_file",
                {"file_path": file_path, "content_length": len(content)},
                AdapterResult(success=True),
            )

            return AdapterResult(
                success=True,
                result={"file_path": file_path, "bytes_written": len(content.encode("utf-8"))},
                audit_log=audit_log,
            )
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    async def _delete_file(self, file_path: str) -> AdapterResult:
        """刪除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)

                audit_log = self.create_audit_log(
                    "delete_file", {"file_path": file_path}, AdapterResult(success=True)
                )

                return AdapterResult(
                    success=True, result={"file_path": file_path}, audit_log=audit_log
                )
            else:
                return AdapterResult(success=False, error=f"File not found: {file_path}")
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    async def _list_files(self, directory: str) -> AdapterResult:
        """列出文件"""
        try:
            files = []
            if os.path.isdir(directory):
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path):
                        files.append(item)

            audit_log = self.create_audit_log(
                "list_files", {"directory": directory}, AdapterResult(success=True)
            )

            return AdapterResult(
                success=True, result={"files": files, "directory": directory}, audit_log=audit_log
            )
        except Exception as e:
            return AdapterResult(success=False, error=str(e))
