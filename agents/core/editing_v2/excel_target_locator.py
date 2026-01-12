# 代碼功能說明: Excel Target Locator
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel Target Locator

實現 Excel 目標定位功能，支持工作表、範圍、單元格、行、列的定位。
"""

import logging
from typing import Any, Dict

from agents.builtin.xls_editor.models import ExcelTargetSelector
from agents.core.editing_v2.error_handler import EditingError, ErrorHandler
from agents.core.editing_v2.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class ExcelTargetLocator:
    """Excel 目標定位器

    提供 Excel 目標定位功能。
    """

    def __init__(self, parser: ExcelParser):
        """
        初始化目標定位器

        Args:
            parser: Excel 解析器實例
        """
        self.parser = parser
        self.error_handler = ErrorHandler()

    def locate(self, target_selector: ExcelTargetSelector) -> Dict[str, Any]:
        """
        定位目標

        Args:
            target_selector: 目標選擇器

        Returns:
            目標信息字典

        Raises:
            EditingError: 目標不存在時拋出
        """
        selector_type = target_selector.type
        selector_data = target_selector.selector

        if selector_type == "worksheet":
            return self._locate_worksheet(selector_data)
        elif selector_type == "range":
            return self._locate_range(selector_data)
        elif selector_type == "cell":
            return self._locate_cell(selector_data)
        elif selector_type == "row":
            return self._locate_row(selector_data)
        elif selector_type == "column":
            return self._locate_column(selector_data)
        else:
            raise EditingError(
                code="INVALID_FORMAT",
                message=f"不支持的選擇器類型: {selector_type}",
            )

    def _locate_worksheet(self, selector: Dict[str, Any]) -> Dict[str, Any]:
        """定位工作表"""
        worksheet_name = selector.get("worksheet")
        if worksheet_name is None:
            raise EditingError(
                code="VALIDATION_FAILED",
                message="Worksheet name is required",
            )

        worksheet = self.parser.get_worksheet(worksheet_name)
        if worksheet is None:
            raise self.error_handler.handle_target_not_found(
                f"Worksheet '{worksheet_name}' not found"
            )

        return {
            "type": "worksheet",
            "worksheet": worksheet_name,
            "worksheet_obj": worksheet,
        }

    def _locate_range(self, selector: Dict[str, Any]) -> Dict[str, Any]:
        """定位範圍"""
        worksheet_name = selector.get("worksheet")
        range_address = selector.get("range")

        if worksheet_name is None or range_address is None:
            raise EditingError(
                code="VALIDATION_FAILED",
                message="Worksheet name and range are required",
            )

        worksheet = self.parser.get_worksheet(worksheet_name)
        if worksheet is None:
            raise self.error_handler.handle_target_not_found(
                f"Worksheet '{worksheet_name}' not found"
            )

        # 驗證範圍是否存在
        try:
            values = self.parser.get_range_values(worksheet_name, range_address)
        except Exception:
            raise self.error_handler.handle_target_not_found(
                f"Range '{range_address}' not found in worksheet '{worksheet_name}'"
            )

        return {
            "type": "range",
            "worksheet": worksheet_name,
            "range": range_address,
            "values": values,
        }

    def _locate_cell(self, selector: Dict[str, Any]) -> Dict[str, Any]:
        """定位單元格"""
        worksheet_name = selector.get("worksheet")
        cell_address = selector.get("cell")

        if worksheet_name is None or cell_address is None:
            raise EditingError(
                code="VALIDATION_FAILED",
                message="Worksheet name and cell address are required",
            )

        worksheet = self.parser.get_worksheet(worksheet_name)
        if worksheet is None:
            raise self.error_handler.handle_target_not_found(
                f"Worksheet '{worksheet_name}' not found"
            )

        value = self.parser.get_cell_value(worksheet_name, cell_address)
        if value is None:
            # 單元格可能為空，但不一定不存在
            pass

        return {
            "type": "cell",
            "worksheet": worksheet_name,
            "cell": cell_address,
            "value": value,
        }

    def _locate_row(self, selector: Dict[str, Any]) -> Dict[str, Any]:
        """定位行"""
        worksheet_name = selector.get("worksheet")
        row_number = selector.get("row")

        if worksheet_name is None or row_number is None:
            raise EditingError(
                code="VALIDATION_FAILED",
                message="Worksheet name and row number are required",
            )

        worksheet = self.parser.get_worksheet(worksheet_name)
        if worksheet is None:
            raise self.error_handler.handle_target_not_found(
                f"Worksheet '{worksheet_name}' not found"
            )

        return {
            "type": "row",
            "worksheet": worksheet_name,
            "row": row_number,
        }

    def _locate_column(self, selector: Dict[str, Any]) -> Dict[str, Any]:
        """定位列"""
        worksheet_name = selector.get("worksheet")
        column_letter = selector.get("column")

        if worksheet_name is None or column_letter is None:
            raise EditingError(
                code="VALIDATION_FAILED",
                message="Worksheet name and column letter are required",
            )

        worksheet = self.parser.get_worksheet(worksheet_name)
        if worksheet is None:
            raise self.error_handler.handle_target_not_found(
                f"Worksheet '{worksheet_name}' not found"
            )

        return {
            "type": "column",
            "worksheet": worksheet_name,
            "column": column_letter,
        }
