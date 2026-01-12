# 代碼功能說明: 錯誤處理模組
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""錯誤處理模組

定義錯誤碼、錯誤處理邏輯和錯誤響應格式。
"""

from typing import Any, Dict, List, Optional


class EditingErrorCode:
    """編輯錯誤碼

    定義所有編輯相關的錯誤碼。
    """

    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    VERSION_NOT_FOUND = "VERSION_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    TARGET_AMBIGUOUS = "TARGET_AMBIGUOUS"
    PATCH_GENERATION_FAILED = "PATCH_GENERATION_FAILED"
    CONTEXT_ASSEMBLY_FAILED = "CONTEXT_ASSEMBLY_FAILED"
    LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    INVALID_INTENT = "INVALID_INTENT"
    INVALID_SELECTOR = "INVALID_SELECTOR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EditingError(Exception):
    """編輯錯誤基類"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[Dict[str, str]]] = None,
    ):
        """
        初始化編輯錯誤

        Args:
            code: 錯誤碼
            message: 錯誤消息
            details: 錯誤詳情
            suggestions: 修正建議
        """
        self.code = code
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式

        Returns:
            錯誤字典
        """
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
        }


class ErrorHandler:
    """錯誤處理器

    提供錯誤處理和錯誤響應生成功能。
    """

    @staticmethod
    def handle_validation_error(error: Exception, field: Optional[str] = None) -> EditingError:
        """
        處理驗證錯誤

        Args:
            error: 驗證異常
            field: 字段名稱

        Returns:
            編輯錯誤
        """
        return EditingError(
            code=EditingErrorCode.VALIDATION_FAILED,
            message=f"驗證失敗: {str(error)}",
            details={"field": field, "error": str(error)},
            suggestions=[{"action": "檢查輸入格式", "example": "確保所有必需字段都已提供"}],
        )

    @staticmethod
    def handle_target_not_found(selector_type: str, selector_value: Any) -> EditingError:
        """
        處理目標未找到錯誤

        Args:
            selector_type: 選擇器類型
            selector_value: 選擇器值

        Returns:
            編輯錯誤
        """
        return EditingError(
            code=EditingErrorCode.TARGET_NOT_FOUND,
            message=f"未找到目標: {selector_type}={selector_value}",
            details={"selector_type": selector_type, "selector_value": str(selector_value)},
            suggestions=[{"action": "檢查選擇器值", "example": "確保目標存在於文檔中"}],
        )

    @staticmethod
    def handle_target_ambiguous(
        selector_type: str, selector_value: Any, candidates: List[Dict[str, Any]]
    ) -> EditingError:
        """
        處理目標模糊錯誤

        Args:
            selector_type: 選擇器類型
            selector_value: 選擇器值
            candidates: 候選列表

        Returns:
            編輯錯誤
        """
        return EditingError(
            code=EditingErrorCode.TARGET_AMBIGUOUS,
            message=f"目標模糊: {selector_type}={selector_value}，找到 {len(candidates)} 個匹配",
            details={
                "selector_type": selector_type,
                "selector_value": str(selector_value),
                "candidates": candidates,
            },
            suggestions=[
                {
                    "action": "使用更精確的選擇器",
                    "example": "添加 level 或 occurrence 參數來精確定位",
                }
            ],
        )

    @staticmethod
    def handle_internal_error(error: Exception) -> EditingError:
        """
        處理內部錯誤

        Args:
            error: 異常

        Returns:
            編輯錯誤
        """
        return EditingError(
            code=EditingErrorCode.INTERNAL_ERROR,
            message=f"內部錯誤: {str(error)}",
            details={"error_type": type(error).__name__, "error_message": str(error)},
            suggestions=[{"action": "聯繫系統管理員", "example": "報告此錯誤"}],
        )
