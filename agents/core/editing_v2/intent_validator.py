# 代碼功能說明: Intent DSL 驗證器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Intent DSL 驗證器

實現 Intent DSL 的 JSON Schema 驗證、格式驗證和解析功能。
"""

from typing import Any, Dict

import jsonschema

from agents.builtin.document_editing_v2.models import (
    Action,
    Constraints,
    DocumentContext,
    EditIntent,
    TargetSelector,
)
from agents.core.editing_v2.error_handler import EditingError, ErrorHandler
from agents.core.editing_v2.schemas import (
    ANCHOR_SELECTOR_SCHEMA,
    BLOCK_SELECTOR_SCHEMA,
    CONSTRAINTS_SCHEMA,
    DOCUMENT_CONTEXT_SCHEMA,
    HEADING_SELECTOR_SCHEMA,
    INTENT_DSL_SCHEMA,
)


class IntentValidator:
    """Intent DSL 驗證器

    提供 Intent DSL 的驗證和解析功能。
    """

    def __init__(self):
        """初始化驗證器"""
        self.error_handler = ErrorHandler()

    def validate_intent_dsl(self, intent_data: Dict[str, Any]) -> None:
        """
        驗證 Intent DSL

        Args:
            intent_data: Intent DSL 數據

        Raises:
            EditingError: 驗證失敗時拋出
        """
        try:
            # JSON Schema 驗證
            jsonschema.validate(instance=intent_data, schema=INTENT_DSL_SCHEMA)

            # Intent Type 與 Action Mode 兼容性檢查
            intent_type = intent_data.get("intent_type")
            action_mode = intent_data.get("action", {}).get("mode")
            if intent_type != action_mode:
                raise ValueError(f"Intent type '{intent_type}' 與 action mode '{action_mode}' 不兼容")

            # Target Selector 格式驗證
            target_selector = intent_data.get("target_selector", {})
            selector_type = target_selector.get("type")
            selector_data = target_selector.get("selector", {})

            if selector_type == "heading":
                jsonschema.validate(instance=selector_data, schema=HEADING_SELECTOR_SCHEMA)
            elif selector_type == "anchor":
                jsonschema.validate(instance=selector_data, schema=ANCHOR_SELECTOR_SCHEMA)
            elif selector_type == "block":
                jsonschema.validate(instance=selector_data, schema=BLOCK_SELECTOR_SCHEMA)
            else:
                raise ValueError(f"不支持的選擇器類型: {selector_type}")

            # Constraints 格式驗證（如果提供）
            constraints = intent_data.get("constraints")
            if constraints:
                jsonschema.validate(instance=constraints, schema=CONSTRAINTS_SCHEMA)

        except jsonschema.ValidationError as e:
            raise self.error_handler.handle_validation_error(e, field=e.path[0] if e.path else None)
        except ValueError as e:
            raise self.error_handler.handle_validation_error(e)

    def validate_document_context(self, context_data: Dict[str, Any]) -> None:
        """
        驗證 DocumentContext

        Args:
            context_data: DocumentContext 數據

        Raises:
            EditingError: 驗證失敗時拋出
        """
        try:
            jsonschema.validate(instance=context_data, schema=DOCUMENT_CONTEXT_SCHEMA)
        except jsonschema.ValidationError as e:
            raise self.error_handler.handle_validation_error(e, field=e.path[0] if e.path else None)

    def parse_intent(self, intent_data: Dict[str, Any]) -> EditIntent:
        """
        解析 Intent DSL 為內部數據結構

        Args:
            intent_data: Intent DSL 數據

        Returns:
            EditIntent 對象

        Raises:
            EditingError: 解析失敗時拋出
        """
        try:
            # 先驗證
            self.validate_intent_dsl(intent_data)

            # 解析為 Pydantic 模型
            target_selector = TargetSelector(
                type=intent_data["target_selector"]["type"],
                selector=intent_data["target_selector"]["selector"],
            )

            action_data = intent_data["action"]
            action = Action(
                mode=action_data["mode"],
                content=action_data.get("content"),
                position=action_data.get("position"),
            )

            constraints = None
            if "constraints" in intent_data and intent_data["constraints"]:
                constraints_data = intent_data["constraints"]
                constraints = Constraints(
                    max_tokens=constraints_data.get("max_tokens"),
                    style_guide=constraints_data.get("style_guide"),
                    no_external_reference=constraints_data.get("no_external_reference"),
                )

            return EditIntent(
                intent_id=intent_data["intent_id"],
                intent_type=intent_data["intent_type"],
                target_selector=target_selector,
                action=action,
                constraints=constraints,
            )
        except EditingError:
            raise
        except Exception as e:
            raise self.error_handler.handle_validation_error(e)

    def parse_document_context(self, context_data: Dict[str, Any]) -> DocumentContext:
        """
        解析 DocumentContext

        Args:
            context_data: DocumentContext 數據

        Returns:
            DocumentContext 對象

        Raises:
            EditingError: 解析失敗時拋出
        """
        try:
            # 先驗證
            self.validate_document_context(context_data)

            # 解析為 Pydantic 模型
            return DocumentContext(
                doc_id=context_data["doc_id"],
                version_id=context_data.get("version_id"),
                file_path=context_data["file_path"],
                task_id=context_data["task_id"],
                user_id=context_data["user_id"],
                tenant_id=context_data.get("tenant_id"),
            )
        except EditingError:
            raise
        except Exception as e:
            raise self.error_handler.handle_validation_error(e)
