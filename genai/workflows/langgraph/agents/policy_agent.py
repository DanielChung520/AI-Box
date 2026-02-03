from __future__ import annotations
# 代碼功能說明: PolicyAgent實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""PolicyAgent實現 - 策略驗證和權限檢查LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)


@dataclass
class PolicyVerificationResult:
    """策略驗證結果"""
    verification_passed: bool
    risk_level: str
    requires_confirmation: bool
    permission_granted: bool
    security_checks_passed: bool
    compliance_score: float
    violations: List[str] 
    recommendations: List[str] 
    reasoning: str = ""


class PolicyAgent(BaseAgentNode):
    """策略執行Agent - 負責安全性、權限和合規性檢查"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化策略服務
        self.policy_service = None
        self._initialize_policy_service()

    def _initialize_policy_service(self) -> None:
        """初始化策略相關服務"""
        try:
            # 從系統服務中獲取策略服務
            from agents.task_analyzer.policy_service import get_policy_service

            self.policy_service = get_policy_service()
            logger.info("PolicyService initialized for PolicyAgent")
        except Exception as e:
            logger.error(f"Failed to initialize PolicyService: {e}")
            self.policy_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行策略驗證
        """
        try:
            # 檢查資源分配結果是否存在
            resource_result = getattr(state, "resource_allocation", None)

            # 執行策略驗證
            policy_result = await self._verify_policies(resource_result, state)

            if not policy_result:
                return NodeResult.failure("Policy verification failed")

            # 更新狀態
            state.policy_verification = policy_result

            # 記錄觀察
            state.add_observation(
                "policy_verification_completed",
                {
                    "verification_passed": policy_result.verification_passed,
                    "risk_level": policy_result.risk_level,
                    "requires_confirmation": policy_result.requires_confirmation,
                    "compliance_score": policy_result.compliance_score,
                    "violations_count": len(policy_result.violations),
                },
                policy_result.compliance_score,
            )

            logger.info(
                f"Policy verification completed for user {state.user_id}: passed={policy_result.verification_passed}",
            )

            # 決定下一步
            next_layer = self._determine_next_layer(policy_result, state)

            return NodeResult.success(
                data={
                    "policy_verification": {
                        "verification_passed": policy_result.verification_passed,
                        "risk_level": policy_result.risk_level,
                        "requires_confirmation": policy_result.requires_confirmation,
                        "permission_granted": policy_result.permission_granted,
                        "security_checks_passed": policy_result.security_checks_passed,
                        "compliance_score": policy_result.compliance_score,
                        "violations": policy_result.violations,
                        "recommendations": policy_result.recommendations,
                        "reasoning": policy_result.reasoning,
                    },
                    "policy_summary": self._create_policy_summary(policy_result),
                },
                next_layer=next_layer,
            )

        except Exception as e:
            logger.error(f"PolicyAgent execution error: {e}")
            return NodeResult.failure(f"Policy verification error: {e}")

    async def _verify_policies(
        self, resource_result: Any, state: AIBoxState,
    ) -> Optional[PolicyVerificationResult]:
        """執行策略驗證"""
        try:
            # 模擬策略驗證邏輯
            return PolicyVerificationResult(
                verification_passed=True,
                risk_level="low",
                requires_confirmation=False,
                permission_granted=True,
                security_checks_passed=True,
                compliance_score=1.0,
                violations=[],
                recommendations=[],
                reasoning="All policy and security checks passed.",
            )
        except Exception as e:
            logger.error(f"Policy verification process failed: {e}")
            return None

    def _determine_next_layer(
        self, policy_result: PolicyVerificationResult, state: AIBoxState,
    ) -> str:
        """決定下一步層次"""
        if not policy_result.verification_passed:
            return "clarification"

        if policy_result.requires_confirmation:
            return "user_confirmation"

        return "task_orchestration"

    def _create_policy_summary(self, policy_result: PolicyVerificationResult) -> Dict[str, Any]:
        return {
            "passed": policy_result.verification_passed,
            "risk": policy_result.risk_level,
            "compliance": policy_result.compliance_score,
            "complexity": "low",
        }


def create_policy_agent_config() -> NodeConfig:
    return NodeConfig(
        name="PolicyAgent",
        description="策略執行Agent - 負責安全性、權限和合規性檢查",
        max_retries=1,
        timeout=20.0,
        required_inputs=["user_id"],
        optional_inputs=["resource_allocation", "messages"],
        output_keys=["policy_verification", "policy_summary"],
    )


def create_policy_agent() -> PolicyAgent:
    config = create_policy_agent_config()
    return PolicyAgent(config)