# 代碼功能說明: KA-Agent 錯誤處理和用戶反饋機制
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28 11:00 UTC+8

from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel


class ErrorType(str, Enum):
    """錯誤類型分類"""

    # 權限相關
    PERMISSION_DENIED = "permission_denied"
    INSUFFICIENT_PRIVILEGES = "insufficient_privileges"

    # 參數相關
    MISSING_REQUIRED_PARAMETER = "missing_required_parameter"
    INVALID_PARAMETER = "invalid_parameter"
    PARAMETER_OUT_OF_RANGE = "parameter_out_of_range"

    # 指令相關
    AMBIGUOUS_INSTRUCTION = "ambiguous_instruction"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    CONFLICTING_PARAMETERS = "conflicting_parameters"

    # 資源相關
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"

    # 系統相關
    SYSTEM_ERROR = "system_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"

    # 數據相關
    DATA_VALIDATION_FAILED = "data_validation_failed"
    DATA_FORMAT_ERROR = "data_format_error"


class FeedbackAction(str, Enum):
    """建議的用戶操作"""

    PROVIDE_PARAMETER = "provide_parameter"
    CLARIFY_INSTRUCTION = "clarify_instruction"
    CHECK_PERMISSION = "check_permission"
    RETRY_LATER = "retry_later"
    CONTACT_ADMIN = "contact_admin"
    MODIFY_REQUEST = "modify_request"
    NONE = "none"


class UserFeedback(BaseModel):
    """用戶反饋結構"""

    error_type: ErrorType
    user_message: str  # 用戶友好的錯誤消息
    technical_details: Optional[str] = None  # 技術細節（可選）
    suggested_action: FeedbackAction  # 建議的操作
    clarifying_questions: List[str] = []  # 回問問題列表
    example_usage: Optional[str] = None  # 使用範例（可選）
    metadata: Dict[str, Any] = {}  # 額外元數據


class KAAgentErrorHandler:
    """KA-Agent 錯誤處理器"""

    @staticmethod
    def permission_denied(
        user_id: str,
        action: str,
        resource: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> UserFeedback:
        """權限不足錯誤"""
        resource_desc = f"資源 '{resource}'" if resource else "此資源"

        user_message = (
            f"抱歉，您目前沒有執行「{action}」操作的權限。\n\n"
            f"原因：{reason if reason else '您的帳戶權限不足以訪問' + resource_desc}。"
        )

        clarifying_questions = [
            "您需要訪問哪些特定的知識資產？",
            "您是否需要申請更高的權限級別？",
        ]

        return UserFeedback(
            error_type=ErrorType.PERMISSION_DENIED,
            user_message=user_message,
            technical_details=f"user_id={user_id}, action={action}, resource={resource}",
            suggested_action=FeedbackAction.CHECK_PERMISSION,
            clarifying_questions=clarifying_questions,
            metadata={
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "reason": reason,
            },
        )

    @staticmethod
    def missing_parameter(parameter_name: str, context: Optional[str] = None) -> UserFeedback:
        """缺少必要參數"""
        context_desc = f"（{context}）" if context else ""

        user_message = (
            f"您的指令缺少必要的參數：**{parameter_name}** {context_desc}\n\n"
            f"請提供此參數以便我能正確執行您的請求。"
        )

        clarifying_questions = [f"請問您想要指定的「{parameter_name}」是什麼？"]

        return UserFeedback(
            error_type=ErrorType.MISSING_REQUIRED_PARAMETER,
            user_message=user_message,
            suggested_action=FeedbackAction.PROVIDE_PARAMETER,
            clarifying_questions=clarifying_questions,
            metadata={"parameter_name": parameter_name, "context": context},
        )

    @staticmethod
    def ambiguous_instruction(
        instruction: str,
        possible_interpretations: List[str],
        clarifying_questions: Optional[List[str]] = None,
    ) -> UserFeedback:
        """指令不清楚"""
        interpretations_text = "\n".join(
            f"{i + 1}. {interp}" for i, interp in enumerate(possible_interpretations)
        )

        user_message = (
            f"您的指令可能有多種理解方式，我不確定您具體想做什麼：\n\n"
            f"可能的理解：\n{interpretations_text}\n\n"
            f"請明確您的意圖，以便我能正確執行。"
        )

        if not clarifying_questions:
            clarifying_questions = [
                f"您是指「{interp}」嗎？" for interp in possible_interpretations[:2]
            ]

        return UserFeedback(
            error_type=ErrorType.AMBIGUOUS_INSTRUCTION,
            user_message=user_message,
            suggested_action=FeedbackAction.CLARIFY_INSTRUCTION,
            clarifying_questions=clarifying_questions,
            metadata={
                "original_instruction": instruction,
                "possible_interpretations": possible_interpretations,
            },
        )

    @staticmethod
    def resource_not_found(
        resource_type: str, resource_id: Optional[str] = None, search_criteria: Optional[str] = None
    ) -> UserFeedback:
        """資源不存在"""
        resource_desc = f"{resource_type}"
        if resource_id:
            resource_desc += f"（ID: {resource_id}）"

        user_message = (
            f"找不到您請求的 {resource_desc}。\n\n"
            f"可能的原因：\n"
            f"1. 資源不存在或已被刪除\n"
            f"2. 您沒有訪問此資源的權限\n"
            f"3. 資源 ID 或搜索條件有誤"
        )

        if search_criteria:
            user_message += f"\n\n搜索條件：{search_criteria}"

        clarifying_questions = [
            "請確認資源 ID 是否正確？",
            "您是否需要搜索類似的資源？",
        ]

        return UserFeedback(
            error_type=ErrorType.RESOURCE_NOT_FOUND,
            user_message=user_message,
            suggested_action=FeedbackAction.MODIFY_REQUEST,
            clarifying_questions=clarifying_questions,
            metadata={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "search_criteria": search_criteria,
            },
        )

    @staticmethod
    def invalid_parameter(
        parameter_name: str,
        provided_value: Any,
        expected_format: Optional[str] = None,
        valid_values: Optional[List[str]] = None,
    ) -> UserFeedback:
        """參數格式或值無效"""
        user_message = f"參數「{parameter_name}」的值無效：{provided_value}\n\n"

        if expected_format:
            user_message += f"期望的格式：{expected_format}\n"

        if valid_values:
            valid_values_text = "、".join([f"'{v}'" for v in valid_values[:5]])
            if len(valid_values) > 5:
                valid_values_text += f" 等 {len(valid_values)} 個選項"
            user_message += f"有效值：{valid_values_text}\n"

        example_usage = None
        if expected_format:
            example_usage = f"範例：{parameter_name}={expected_format}"

        return UserFeedback(
            error_type=ErrorType.INVALID_PARAMETER,
            user_message=user_message,
            suggested_action=FeedbackAction.MODIFY_REQUEST,
            example_usage=example_usage,
            metadata={
                "parameter_name": parameter_name,
                "provided_value": provided_value,
                "expected_format": expected_format,
                "valid_values": valid_values,
            },
        )

    @staticmethod
    def unsupported_operation(operation: str, supported_operations: Optional[List[str]] = None) -> UserFeedback:
        """不支持的操作"""
        user_message = f"抱歉，我目前不支持「{operation}」這個操作。\n\n"

        if supported_operations:
            supported_text = "、".join([f"「{op}」" for op in supported_operations[:5]])
            user_message += f"我目前支持的操作包括：{supported_text}"
            if len(supported_operations) > 5:
                user_message += f" 等 {len(supported_operations)} 種操作"

        clarifying_questions = ["您是否需要執行其他操作？", "我可以幫您查詢支持的操作列表嗎？"]

        return UserFeedback(
            error_type=ErrorType.UNSUPPORTED_OPERATION,
            user_message=user_message,
            suggested_action=FeedbackAction.MODIFY_REQUEST,
            clarifying_questions=clarifying_questions,
            metadata={"operation": operation, "supported_operations": supported_operations},
        )

    @staticmethod
    def system_error(
        error_message: str, error_type: Optional[str] = None, retry_possible: bool = True
    ) -> UserFeedback:
        """系統錯誤"""
        user_message = (
            "抱歉，系統在處理您的請求時遇到了問題。\n\n"
            "這可能是暫時性的系統故障，並非您的操作有誤。"
        )

        if retry_possible:
            user_message += "\n\n建議您稍後重試，或聯繫管理員協助。"
            suggested_action = FeedbackAction.RETRY_LATER
        else:
            user_message += "\n\n請聯繫系統管理員協助解決。"
            suggested_action = FeedbackAction.CONTACT_ADMIN

        return UserFeedback(
            error_type=ErrorType.SYSTEM_ERROR,
            user_message=user_message,
            technical_details=f"Error: {error_message}, Type: {error_type or 'Unknown'}",
            suggested_action=suggested_action,
            metadata={
                "original_error": error_message,
                "error_type": error_type,
                "retry_possible": retry_possible,
            },
        )

    @staticmethod
    def empty_result(query: str, search_scope: Optional[str] = None) -> UserFeedback:
        """查詢結果為空（不是錯誤，但需要用戶反饋）"""
        scope_desc = f"在「{search_scope}」範圍內" if search_scope else ""

        user_message = (
            f"我{scope_desc}沒有找到與「{query}」相關的知識資產或文件。\n\n"
            f"可能的原因：\n"
            f"1. 相關的知識資產尚未創建或上傳\n"
            f"2. 搜索範圍或條件可能需要調整\n"
            f"3. 您可能需要使用不同的關鍵詞"
        )

        clarifying_questions = [
            "您是否需要擴大搜索範圍？",
            "您可以提供更多關鍵詞或描述嗎？",
            "您是否需要查看所有可用的知識資產？",
        ]

        return UserFeedback(
            error_type=ErrorType.RESOURCE_NOT_FOUND,
            user_message=user_message,
            suggested_action=FeedbackAction.MODIFY_REQUEST,
            clarifying_questions=clarifying_questions,
            metadata={"query": query, "search_scope": search_scope},
        )

    @staticmethod
    def format_feedback_for_llm(feedback: UserFeedback) -> str:
        """格式化反饋消息供 LLM 使用（注入到上下文）"""
        parts = [
            f"[KA-Agent 反饋]\n",
            f"{feedback.user_message}\n",
        ]

        if feedback.clarifying_questions:
            parts.append("\n我需要了解：")
            for q in feedback.clarifying_questions:
                parts.append(f"- {q}")

        if feedback.example_usage:
            parts.append(f"\n範例：{feedback.example_usage}")

        if feedback.suggested_action != FeedbackAction.NONE:
            action_map = {
                FeedbackAction.PROVIDE_PARAMETER: "請提供缺少的參數",
                FeedbackAction.CLARIFY_INSTRUCTION: "請明確您的指令",
                FeedbackAction.CHECK_PERMISSION: "請檢查您的權限設置",
                FeedbackAction.RETRY_LATER: "請稍後重試",
                FeedbackAction.CONTACT_ADMIN: "請聯繫管理員",
                FeedbackAction.MODIFY_REQUEST: "請修改您的請求",
            }
            parts.append(f"\n建議：{action_map.get(feedback.suggested_action, '')}")

        return "\n".join(parts)
