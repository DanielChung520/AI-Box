# 代碼功能說明: Excel Structured Patch 生成器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel Structured Patch 生成器

實現 Excel Structured Patch 的生成功能。
"""

import logging
from typing import Any, Dict, List

from agents.builtin.xls_editor.models import (
    ExcelEditIntent,
    StructuredPatch,
    StructuredPatchOperation,
)
from agents.core.editing_v2.error_handler import EditingError
from agents.core.editing_v2.excel_parser import ExcelParser
from agents.core.editing_v2.excel_target_locator import ExcelTargetLocator

logger = logging.getLogger(__name__)


class ExcelPatchGenerator:
    """Excel Structured Patch 生成器

    提供 Excel Structured Patch 的生成功能。
    """

    def __init__(self, parser: ExcelParser):
        """
        初始化 Patch 生成器

        Args:
            parser: Excel 解析器實例
        """
        self.parser = parser
        self.target_locator = ExcelTargetLocator(parser)

    def generate_patch(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> StructuredPatch:
        """
        生成 Structured Patch

        Args:
            edit_intent: Excel 編輯意圖
            target_info: 目標信息

        Returns:
            Structured Patch 對象
        """
        operations: List[StructuredPatchOperation] = []

        action_mode = edit_intent.action.mode

        if action_mode == "update":
            operations.extend(self._generate_update_operations(edit_intent, target_info))
        elif action_mode == "insert":
            operations.extend(self._generate_insert_operations(edit_intent, target_info))
        elif action_mode == "delete":
            operations.extend(self._generate_delete_operations(edit_intent, target_info))
        elif action_mode == "insert_row":
            operations.append(self._generate_insert_row_operation(edit_intent, target_info))
        elif action_mode == "delete_row":
            operations.append(self._generate_delete_row_operation(edit_intent, target_info))
        elif action_mode == "insert_column":
            operations.append(self._generate_insert_column_operation(edit_intent, target_info))
        elif action_mode == "delete_column":
            operations.append(self._generate_delete_column_operation(edit_intent, target_info))
        else:
            raise EditingError(
                code="INVALID_FORMAT",
                message=f"不支持的操作模式: {action_mode}",
            )

        return StructuredPatch(operations=operations)

    def _generate_update_operations(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> List[StructuredPatchOperation]:
        """生成更新操作"""
        operations: List[StructuredPatchOperation] = []
        worksheet = target_info.get("worksheet")
        action = edit_intent.action
        content = action.content or {}

        if target_info.get("type") == "cell":
            cell_address = target_info.get("cell")
            old_value = target_info.get("value")
            new_value = content.get("values", [None])[0] if content.get("values") else None

            target = f"{worksheet}!{cell_address}"
            operations.append(
                StructuredPatchOperation(
                    op="update",
                    target=target,
                    old_value=old_value,
                    new_value=new_value,
                )
            )
        elif target_info.get("type") == "range":
            old_values = target_info.get("values", [])
            new_values = content.get("values", [])

            # 為範圍中的每個單元格生成操作
            if new_values:
                # 簡化實現：假設範圍是矩形
                for i, row in enumerate(new_values):
                    for j, value in enumerate(row):
                        # 計算單元格地址（簡化實現）
                        cell_col = chr(ord("A") + j)
                        cell_row = i + 1
                        cell_address = f"{cell_col}{cell_row}"
                        target = f"{worksheet}!{cell_address}"

                        old_value = (
                            old_values[i][j]
                            if i < len(old_values) and j < len(old_values[i])
                            else None
                        )

                        operations.append(
                            StructuredPatchOperation(
                                op="update",
                                target=target,
                                old_value=old_value,
                                new_value=value,
                            )
                        )

        return operations

    def _generate_insert_operations(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> List[StructuredPatchOperation]:
        """生成插入操作"""
        operations: List[StructuredPatchOperation] = []
        worksheet = target_info.get("worksheet")
        action = edit_intent.action
        content = action.content or {}
        new_values = content.get("values", [])

        if target_info.get("type") == "cell":
            cell_address = target_info.get("cell")
            new_value = new_values[0] if new_values else None

            target = f"{worksheet}!{cell_address}"
            operations.append(
                StructuredPatchOperation(
                    op="insert",
                    target=target,
                    old_value=None,
                    new_value=new_value,
                )
            )

        return operations

    def _generate_delete_operations(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> List[StructuredPatchOperation]:
        """生成刪除操作"""
        operations: List[StructuredPatchOperation] = []
        worksheet = target_info.get("worksheet")

        if target_info.get("type") == "cell":
            cell_address = target_info.get("cell")
            old_value = target_info.get("value")

            target = f"{worksheet}!{cell_address}"
            operations.append(
                StructuredPatchOperation(
                    op="delete",
                    target=target,
                    old_value=old_value,
                    new_value=None,
                )
            )

        return operations

    def _generate_insert_row_operation(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> StructuredPatchOperation:
        """生成插入行操作"""
        worksheet = target_info.get("worksheet")
        row = target_info.get("row")

        target = f"{worksheet}!{row}"
        return StructuredPatchOperation(
            op="insert_row",
            target=target,
            old_value=None,
            new_value=None,
        )

    def _generate_delete_row_operation(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> StructuredPatchOperation:
        """生成刪除行操作"""
        worksheet = target_info.get("worksheet")
        row = target_info.get("row")

        target = f"{worksheet}!{row}"
        return StructuredPatchOperation(
            op="delete_row",
            target=target,
            old_value=None,
            new_value=None,
        )

    def _generate_insert_column_operation(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> StructuredPatchOperation:
        """生成插入列操作"""
        worksheet = target_info.get("worksheet")
        column = target_info.get("column")

        target = f"{worksheet}!{column}"
        return StructuredPatchOperation(
            op="insert_column",
            target=target,
            old_value=None,
            new_value=None,
        )

    def _generate_delete_column_operation(
        self, edit_intent: ExcelEditIntent, target_info: Dict[str, Any]
    ) -> StructuredPatchOperation:
        """生成刪除列操作"""
        worksheet = target_info.get("worksheet")
        column = target_info.get("column")

        target = f"{worksheet}!{column}"
        return StructuredPatchOperation(
            op="delete_column",
            target=target,
            old_value=None,
            new_value=None,
        )
