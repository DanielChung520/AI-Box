# 代碼功能說明: Intent Validator 測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Intent Validator 單元測試

測試 Intent DSL 驗證和解析功能。
"""

import pytest

from agents.core.editing_v2.error_handler import EditingError, EditingErrorCode
from agents.core.editing_v2.intent_validator import IntentValidator


@pytest.fixture
def intent_validator():
    """創建 IntentValidator 實例"""
    return IntentValidator()


@pytest.fixture
def valid_intent_dsl():
    """合法的 Intent DSL 示例"""
    return {
        "intent_id": "intent-123",
        "intent_type": "update",
        "target_selector": {
            "type": "heading",
            "selector": {
                "text": "標題",
                "level": 1,
                "occurrence": 1,
            },
        },
        "action": {
            "mode": "update",
            "content": "新標題",
            "position": "inside",
        },
        "constraints": {
            "max_tokens": 100,
            "style_guide": "enterprise-tech-v1",
            "no_external_reference": True,
        },
    }


@pytest.fixture
def valid_document_context():
    """合法的 DocumentContext 示例"""
    return {
        "doc_id": "doc-123",
        "version_id": "v1",
        "file_path": "data/tasks/task-123/workspace/file.md",
        "task_id": "task-123",
        "user_id": "user-456",
        "tenant_id": "tenant-789",
    }


class TestIntentValidator:
    """Intent Validator 測試類"""

    def test_validate_valid_intent_dsl(self, intent_validator, valid_intent_dsl):
        """測試合法的 Intent DSL 驗證"""
        # 不應該拋出異常
        intent_validator.validate_intent_dsl(valid_intent_dsl)

    def test_validate_intent_dsl_missing_required_field(self, intent_validator, valid_intent_dsl):
        """測試缺少必需字段的 Intent DSL"""
        invalid_intent = valid_intent_dsl.copy()
        del invalid_intent["intent_id"]

        with pytest.raises(EditingError) as exc_info:
            intent_validator.validate_intent_dsl(invalid_intent)

        assert exc_info.value.code == EditingErrorCode.VALIDATION_FAILED

    def test_validate_intent_dsl_invalid_intent_type(self, intent_validator, valid_intent_dsl):
        """測試無效的 Intent Type"""
        invalid_intent = valid_intent_dsl.copy()
        invalid_intent["intent_type"] = "invalid_type"

        with pytest.raises(EditingError) as exc_info:
            intent_validator.validate_intent_dsl(invalid_intent)

        assert exc_info.value.code == EditingErrorCode.VALIDATION_FAILED

    def test_validate_intent_dsl_incompatible_intent_and_action(
        self, intent_validator, valid_intent_dsl
    ):
        """測試 Intent Type 與 Action Mode 不兼容"""
        invalid_intent = valid_intent_dsl.copy()
        invalid_intent["intent_type"] = "update"
        invalid_intent["action"]["mode"] = "insert"

        with pytest.raises(EditingError) as exc_info:
            intent_validator.validate_intent_dsl(invalid_intent)

        assert exc_info.value.code == EditingErrorCode.VALIDATION_FAILED

    def test_validate_intent_dsl_heading_selector(self, intent_validator, valid_intent_dsl):
        """測試 Heading Selector 驗證"""
        intent = valid_intent_dsl.copy()
        intent["target_selector"] = {
            "type": "heading",
            "selector": {
                "text": "標題",
                "level": 1,
            },
        }

        # 應該通過驗證
        intent_validator.validate_intent_dsl(intent)

    def test_validate_intent_dsl_anchor_selector(self, intent_validator, valid_intent_dsl):
        """測試 Anchor Selector 驗證"""
        intent = valid_intent_dsl.copy()
        intent["target_selector"] = {
            "type": "anchor",
            "selector": {
                "anchor_id": "anchor-123",
            },
        }

        # 應該通過驗證
        intent_validator.validate_intent_dsl(intent)

    def test_validate_intent_dsl_block_selector(self, intent_validator, valid_intent_dsl):
        """測試 Block Selector 驗證"""
        intent = valid_intent_dsl.copy()
        intent["target_selector"] = {
            "type": "block",
            "selector": {
                "block_id": "block-123",
            },
        }

        # 應該通過驗證
        intent_validator.validate_intent_dsl(intent)

    def test_validate_intent_dsl_invalid_selector_type(self, intent_validator, valid_intent_dsl):
        """測試無效的 Selector Type"""
        invalid_intent = valid_intent_dsl.copy()
        invalid_intent["target_selector"]["type"] = "invalid_type"

        with pytest.raises(EditingError) as exc_info:
            intent_validator.validate_intent_dsl(invalid_intent)

        assert exc_info.value.code == EditingErrorCode.VALIDATION_FAILED

    def test_parse_intent(self, intent_validator, valid_intent_dsl):
        """測試 Intent DSL 解析為 Pydantic 模型"""
        edit_intent = intent_validator.parse_intent(valid_intent_dsl)

        assert edit_intent.intent_id == "intent-123"
        assert edit_intent.intent_type == "update"
        assert edit_intent.target_selector.type == "heading"
        assert edit_intent.action.mode == "update"
        assert edit_intent.constraints is not None
        assert edit_intent.constraints.max_tokens == 100

    def test_parse_document_context(self, intent_validator, valid_document_context):
        """測試 DocumentContext 解析"""
        context = intent_validator.parse_document_context(valid_document_context)

        assert context.doc_id == "doc-123"
        assert context.version_id == "v1"
        assert context.file_path == "data/tasks/task-123/workspace/file.md"
        assert context.task_id == "task-123"
        assert context.user_id == "user-456"
        assert context.tenant_id == "tenant-789"

    def test_validate_document_context_missing_field(
        self, intent_validator, valid_document_context
    ):
        """測試缺少必需字段的 DocumentContext"""
        invalid_context = valid_document_context.copy()
        del invalid_context["doc_id"]

        with pytest.raises(EditingError) as exc_info:
            intent_validator.validate_document_context(invalid_context)

        assert exc_info.value.code == EditingErrorCode.VALIDATION_FAILED
