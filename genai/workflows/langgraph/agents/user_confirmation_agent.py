from __future__ import annotations
# 代碼功能說明: UserConfirmationAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""UserConfirmationAgent實現 - 負責任戶交互和指令確認LangGraph節點"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class UserConfirmationResult:
    """用戶確認結果"""
    confirmation_required: bool
    confirmation_message: str
    confirmation_options: List[Dict[str, str]] = field(default_factory=list)
    timeout_seconds: int = 300
    reasoning: str = ""


class UserConfirmationAgent(BaseAgentNode):
    """用戶確認Agent - 在執行敏感操作或高風險任務前請求用戶授權"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        處理用戶確認請求
        """
        try:
            confirmation_needed = self._check_confirmation_needed(state)

            if not confirmation_needed:
                return NodeResult.success(
                    data={"confirmation": {"skipped": True}},
                    next_layer="task_orchestration",
                )

            # 生成確認請求
            confirmation_result = self._generate_confirmation_request(state)

            # 更新狀態
            state.user_confirmation = confirmation_result

            # 記錄觀察
            state.add_observation(
                "user_confirmation_required",
                {
                    "confirmation_required": confirmation_result.confirmation_required,
                    "timeout_seconds": confirmation_result.timeout_seconds,
                    "options_count": len(confirmation_result.confirmation_options),
                },
                0.5,
            )

            logger.info(f"User confirmation requested for user {state.user_id}")

            # 用戶確認是終止狀態
            return NodeResult.success(
                data={
                    "user_confirmation": {
                        "confirmation_required": confirmation_result.confirmation_required,
                        "confirmation_message": confirmation_result.confirmation_message,
                        "confirmation_options": confirmation_result.confirmation_options,
                        "timeout_seconds": confirmation_result.timeout_seconds,
                        "reasoning": confirmation_result.reasoning,
                    },
                    "confirmation_summary": self._create_confirmation_summary(confirmation_result),
                },
                next_layer=None,
            )

        except Exception as e:
            logger.error(f"UserConfirmationAgent execution error: {e}")
            return NodeResult.failure(f"User confirmation error: {e}")

    def _check_confirmation_needed(self, state: AIBoxState) -> bool:
        """檢查是否需要用戶確認"""
        policy_result = getattr(state, "policy_verification", None)
        if policy_result and getattr(policy_result, "requires_confirmation", False):
            return True
        return False

    def _generate_confirmation_request(self, state: AIBoxState) -> UserConfirmationResult:
        """生成確認請求"""
        return UserConfirmationResult(
            confirmation_required=True,
            confirmation_message="執行此操作可能涉及敏感數據，您確定要繼續嗎？",
            confirmation_options=[
                {"label": "是", "value": "approve"},
                {"label": "否", "value": "reject"},
            ],
            reasoning="Required by security policy.",
        )

    def _create_confirmation_summary(
        self, confirmation_result: UserConfirmationResult,
    ) -> Dict[str, Any]:
        return {
            "required": confirmation_result.confirmation_required,
            "options": len(confirmation_result.confirmation_options),
        }


def create_user_confirmation_agent_config() -> NodeConfig:
    return NodeConfig(
        name="UserConfirmationAgent",
        description="用戶確認Agent - 在執行敏感操作或高風險任務前請求用戶授權",
        max_retries=1,
        timeout=15.0,
        required_inputs=["user_id"],
        optional_inputs=["policy_verification", "messages"],
        output_keys=["user_confirmation", "confirmation_summary"],
    )


def create_user_confirmation_agent() -> UserConfirmationAgent:
    config = create_user_confirmation_agent_config()
    return UserConfirmationAgent(config)
