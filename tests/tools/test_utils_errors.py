# 代碼功能說明: 工具錯誤定義測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具錯誤定義測試"""

from __future__ import annotations

import pytest

from tools.utils.errors import (
    ToolConfigurationError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
)


class TestToolError:
    """工具錯誤基類測試"""

    def test_tool_error_is_exception(self):
        """測試 ToolError 是 Exception 的子類"""
        assert issubclass(ToolError, Exception)

    def test_tool_error_can_be_raised(self):
        """測試可以拋出 ToolError"""
        with pytest.raises(ToolError):
            raise ToolError("Test error")


class TestToolExecutionError:
    """工具執行錯誤測試"""

    def test_tool_execution_error_creation(self):
        """測試創建工具執行錯誤"""
        error = ToolExecutionError("Execution failed", tool_name="test_tool")

        assert str(error) == "Execution failed"
        assert error.message == "Execution failed"
        assert error.tool_name == "test_tool"

    def test_tool_execution_error_without_tool_name(self):
        """測試沒有工具名稱的執行錯誤"""
        error = ToolExecutionError("Execution failed")

        assert str(error) == "Execution failed"
        assert error.message == "Execution failed"
        assert error.tool_name is None

    def test_tool_execution_error_can_be_raised(self):
        """測試可以拋出 ToolExecutionError"""
        with pytest.raises(ToolExecutionError) as exc_info:
            raise ToolExecutionError("Execution failed", tool_name="test_tool")

        assert exc_info.value.tool_name == "test_tool"


class TestToolValidationError:
    """工具驗證錯誤測試"""

    def test_tool_validation_error_creation(self):
        """測試創建工具驗證錯誤"""
        error = ToolValidationError("Validation failed", field="test_field")

        assert str(error) == "Validation failed"
        assert error.message == "Validation failed"
        assert error.field == "test_field"

    def test_tool_validation_error_without_field(self):
        """測試沒有字段的驗證錯誤"""
        error = ToolValidationError("Validation failed")

        assert str(error) == "Validation failed"
        assert error.message == "Validation failed"
        assert error.field is None

    def test_tool_validation_error_can_be_raised(self):
        """測試可以拋出 ToolValidationError"""
        with pytest.raises(ToolValidationError) as exc_info:
            raise ToolValidationError("Validation failed", field="test_field")

        assert exc_info.value.field == "test_field"


class TestToolNotFoundError:
    """工具未找到錯誤測試"""

    def test_tool_not_found_error_creation(self):
        """測試創建工具未找到錯誤"""
        error = ToolNotFoundError("test_tool")

        assert "test_tool" in str(error)
        assert error.tool_name == "test_tool"

    def test_tool_not_found_error_message(self):
        """測試工具未找到錯誤消息"""
        error = ToolNotFoundError("test_tool")

        assert str(error) == "Tool 'test_tool' not found"

    def test_tool_not_found_error_can_be_raised(self):
        """測試可以拋出 ToolNotFoundError"""
        with pytest.raises(ToolNotFoundError) as exc_info:
            raise ToolNotFoundError("test_tool")

        assert exc_info.value.tool_name == "test_tool"


class TestToolConfigurationError:
    """工具配置錯誤測試"""

    def test_tool_configuration_error_creation(self):
        """測試創建工具配置錯誤"""
        error = ToolConfigurationError("Configuration failed", tool_name="test_tool")

        assert str(error) == "Configuration failed"
        assert error.message == "Configuration failed"
        assert error.tool_name == "test_tool"

    def test_tool_configuration_error_without_tool_name(self):
        """測試沒有工具名稱的配置錯誤"""
        error = ToolConfigurationError("Configuration failed")

        assert str(error) == "Configuration failed"
        assert error.message == "Configuration failed"
        assert error.tool_name is None

    def test_tool_configuration_error_can_be_raised(self):
        """測試可以拋出 ToolConfigurationError"""
        with pytest.raises(ToolConfigurationError) as exc_info:
            raise ToolConfigurationError("Configuration failed", tool_name="test_tool")

        assert exc_info.value.tool_name == "test_tool"


class TestErrorInheritance:
    """錯誤繼承關係測試"""

    def test_all_errors_inherit_from_tool_error(self):
        """測試所有錯誤都繼承自 ToolError"""
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(ToolValidationError, ToolError)
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolConfigurationError, ToolError)

    def test_all_errors_are_exceptions(self):
        """測試所有錯誤都是 Exception 的子類"""
        assert issubclass(ToolError, Exception)
        assert issubclass(ToolExecutionError, Exception)
        assert issubclass(ToolValidationError, Exception)
        assert issubclass(ToolNotFoundError, Exception)
        assert issubclass(ToolConfigurationError, Exception)
