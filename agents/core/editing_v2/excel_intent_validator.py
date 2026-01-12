# 代碼功能說明: Excel Intent DSL 驗證器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel Intent DSL 驗證器

實現 Excel Intent DSL 的驗證和解析功能。
"""

from typing import Any, Dict

import jsonschema

from agents.builtin.xls_editor.models import (
    ExcelAction,
    ExcelConstraints,
    ExcelEditIntent,
    ExcelTargetSelector,
)
from agents.core.editing_v2.error_handler import ErrorHandler

# Excel Intent DSL JSON Schema
EXCEL_INTENT_DSL_SCHEMA = {
    "type": "object",
    "properties": {
        "intent_id": {"type": "string"},
        "intent_type": {
            "type": "string",
            "enum": [
                "insert",
                "update",
                "delete",
                "move",
                "replace",
                "insert_row",
                "delete_row",
                "insert_column",
                "delete_column",
            ],
        },
        "target_selector": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["worksheet", "range", "cell", "row", "column"],
                },
                "selector": {"type": "object"},
            },
            "required": ["type", "selector"],
        },
        "action": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": [
                        "insert",
                        "update",
                        "delete",
                        "move",
                        "replace",
                        "insert_row",
                        "delete_row",
                        "insert_column",
                        "delete_column",
                    ],
                },
                "content": {"type": "object"},
                "position": {
                    "type": "string",
                    "enum": ["before", "after", "inside", "start", "end"],
                },
            },
            "required": ["mode"],
        },
        "constraints": {
            "type": "object",
            "properties": {
                "max_cells": {"type": "integer"},
                "preserve_formulas": {"type": "boolean"},
                "preserve_styles": {"type": "boolean"},
                "no_external_reference": {"type": "boolean"},
            },
        },
    },
    "required": ["intent_id", "intent_type", "target_selector", "action"],
}

# Excel Target Selector Schemas
WORKSHEET_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "worksheet": {"type": "string"},
    },
    "required": ["worksheet"],
}

RANGE_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "worksheet": {"type": "string"},
        "range": {"type": "string"},
    },
    "required": ["worksheet", "range"],
}

CELL_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "worksheet": {"type": "string"},
        "cell": {"type": "string"},
    },
    "required": ["worksheet", "cell"],
}

ROW_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "worksheet": {"type": "string"},
        "row": {"type": "integer"},
    },
    "required": ["worksheet", "row"],
}

COLUMN_SELECTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "worksheet": {"type": "string"},
        "column": {"type": "string"},
    },
    "required": ["worksheet", "column"],
}


class ExcelIntentValidator:
    """Excel Intent DSL 驗證器

    提供 Excel Intent DSL 的驗證和解析功能。
    """

    def __init__(self):
        """初始化驗證器"""
        self.error_handler = ErrorHandler()

    def validate_intent_dsl(self, intent_data: Dict[str, Any]) -> None:
        """
        驗證 Excel Intent DSL

        Args:
            intent_data: Intent DSL 數據

        Raises:
            EditingError: 驗證失敗時拋出
        """
        try:
            # JSON Schema 驗證
            jsonschema.validate(instance=intent_data, schema=EXCEL_INTENT_DSL_SCHEMA)

            # Intent Type 與 Action Mode 兼容性檢查
            intent_type = intent_data.get("intent_type")
            action_mode = intent_data.get("action", {}).get("mode")
            if intent_type != action_mode:
                raise ValueError(f"Intent type '{intent_type}' 與 action mode '{action_mode}' 不兼容")

            # Target Selector 格式驗證
            target_selector = intent_data.get("target_selector", {})
            selector_type = target_selector.get("type")
            selector_data = target_selector.get("selector", {})

            if selector_type == "worksheet":
                jsonschema.validate(instance=selector_data, schema=WORKSHEET_SELECTOR_SCHEMA)
            elif selector_type == "range":
                jsonschema.validate(instance=selector_data, schema=RANGE_SELECTOR_SCHEMA)
            elif selector_type == "cell":
                jsonschema.validate(instance=selector_data, schema=CELL_SELECTOR_SCHEMA)
            elif selector_type == "row":
                jsonschema.validate(instance=selector_data, schema=ROW_SELECTOR_SCHEMA)
            elif selector_type == "column":
                jsonschema.validate(instance=selector_data, schema=COLUMN_SELECTOR_SCHEMA)
            else:
                raise ValueError(f"不支持的選擇器類型: {selector_type}")

        except jsonschema.ValidationError as e:
            raise self.error_handler.handle_validation_error(e, field=e.path[0] if e.path else None)
        except ValueError as e:
            raise self.error_handler.handle_validation_error(e)

    def parse_intent(self, intent_data: Dict[str, Any]) -> ExcelEditIntent:
        """
        解析 Excel Intent DSL

        Args:
            intent_data: Intent DSL 數據

        Returns:
            ExcelEditIntent 對象

        Raises:
            EditingError: 解析失敗時拋出
        """
        try:
            # 驗證 Intent DSL
            self.validate_intent_dsl(intent_data)

            # 解析 Target Selector
            target_selector_data = intent_data.get("target_selector", {})
            target_selector = ExcelTargetSelector(
                type=target_selector_data.get("type"),
                selector=target_selector_data.get("selector", {}),
            )

            # 解析 Action
            action_data = intent_data.get("action", {})
            action = ExcelAction(
                mode=action_data.get("mode"),
                content=action_data.get("content"),
                position=action_data.get("position"),
            )

            # 解析 Constraints（可選）
            constraints_data = intent_data.get("constraints")
            constraints = None
            if constraints_data:
                constraints = ExcelConstraints(
                    max_cells=constraints_data.get("max_cells"),
                    preserve_formulas=constraints_data.get("preserve_formulas"),
                    preserve_styles=constraints_data.get("preserve_styles"),
                    no_external_reference=constraints_data.get("no_external_reference"),
                )

            # 構建 ExcelEditIntent
            return ExcelEditIntent(
                intent_id=intent_data.get("intent_id"),
                intent_type=intent_data.get("intent_type"),
                target_selector=target_selector,
                action=action,
                constraints=constraints,
            )

        except Exception as e:
            raise self.error_handler.handle_validation_error(e)

    def parse_document_context(self, context_data: Dict[str, Any]) -> Any:
        """
        解析 DocumentContext（使用統一的模型）

        Args:
            context_data: DocumentContext 數據

        Returns:
            DocumentContext 對象
        """
        from agents.builtin.document_editing_v2.models import DocumentContext

        try:
            return DocumentContext(**context_data)
        except Exception as e:
            raise self.error_handler.handle_validation_error(e)
