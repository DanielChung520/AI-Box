# 代碼功能說明: Error Handler 測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Error Handler 單元測試

測試錯誤處理功能。
"""

import pytest

from agents.core.editing_v2.error_handler import EditingError, EditingErrorCode, ErrorHandler


@pytest.fixture
def error_handler():
    """創建 ErrorHandler 實例"""
    return ErrorHandler()


class TestErrorHandler:
    """Error Handler 測試類"""

    def test_handle_validation_error(self, error_handler):
        """測試驗證錯誤處理"""
        error = ValueError("驗證失敗")
        editing_error = error_handler.handle_validation_error(error, field="intent_id")

        assert isinstance(editing_error, EditingError)
        assert editing_error.code == EditingErrorCode.VALIDATION_FAILED
        assert "驗證失敗" in editing_error.message
        assert editing_error.details.get("field") == "intent_id"

    def test_handle_target_not_found(self, error_handler):
        """測試目標未找到錯誤處理"""
        editing_error = error_handler.handle_target_not_found("heading", "標題")

        assert isinstance(editing_error, EditingError)
        assert editing_error.code == EditingErrorCode.TARGET_NOT_FOUND
        assert "未找到目標" in editing_error.message
        assert editing_error.details["selector_type"] == "heading"

    def test_handle_target_ambiguous(self, error_handler):
        """測試目標模糊錯誤處理"""
        candidates = [
            {"block_id": "block-1", "content": "標題一"},
            {"block_id": "block-2", "content": "標題一"},
        ]
        editing_error = error_handler.handle_target_ambiguous("heading", "標題", candidates)

        assert isinstance(editing_error, EditingError)
        assert editing_error.code == EditingErrorCode.TARGET_AMBIGUOUS
        assert "目標模糊" in editing_error.message
        assert len(editing_error.details["candidates"]) == 2

    def test_handle_internal_error(self, error_handler):
        """測試內部錯誤處理"""
        error = RuntimeError("內部錯誤")
        editing_error = error_handler.handle_internal_error(error)

        assert isinstance(editing_error, EditingError)
        assert editing_error.code == EditingErrorCode.INTERNAL_ERROR
        assert "內部錯誤" in editing_error.message

    def test_editing_error_to_dict(self):
        """測試 EditingError 轉換為字典"""
        error = EditingError(
            code=EditingErrorCode.VALIDATION_FAILED,
            message="驗證失敗",
            details={"field": "intent_id"},
            suggestions=[{"action": "檢查輸入", "example": "確保所有字段都已提供"}],
        )

        error_dict = error.to_dict()

        assert error_dict["code"] == EditingErrorCode.VALIDATION_FAILED
        assert error_dict["message"] == "驗證失敗"
        assert "details" in error_dict
        assert "suggestions" in error_dict
