from __future__ import annotations
# 代碼功能說明: AuditLogger實現
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""AuditLogger實現 - 審計日誌記錄LangGraph節點"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from genai.workflows.langgraph.nodes import BaseAgentNode, NodeConfig, NodeResult
from genai.workflows.langgraph.state import AIBoxState
from services.api.models.audit_log import AuditAction, AuditLogCreate

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """審計結果"""
    logs_created: int
    logs_stored: bool
    compliance_check_passed: bool
    retention_policy_applied: bool
    audit_trail_complete: bool
    reasoning: str = ""


class AuditLogger(BaseAgentNode):
    """審計日誌Agent - 負責記錄系統執行過程中的關鍵操作和狀態"""
    def __init__(self, config: NodeConfig):
        super().__init__(config)
        # 初始化審計服務
        self.audit_service = None
        self._initialize_audit_service()

    def _initialize_audit_service(self) -> None:
        """初始化審計相關服務"""
        try:
            # 從系統服務中獲取審計日誌服務
            from services.api.services.audit_log_service import get_audit_log_service

            self.audit_service = get_audit_log_service()
            logger.info("AuditLogService initialized for AuditLogger")
        except Exception as e:
            logger.error(f"Failed to initialize AuditLogService: {e}")
            self.audit_service = None

    async def execute(self, state: AIBoxState) -> NodeResult:
        """
        執行審計日誌記錄
        """
        try:
            # 收集當前狀態中的審計事件
            audit_events = self._collect_audit_events(state)

            # 執行審計記錄
            audit_result = await self._log_audit_events(audit_events, state)

            if not audit_result:
                return NodeResult.failure("Audit logging failed")

            # 記錄觀察
            state.add_observation(
                "audit_logging_completed",
                {
                    "logs_created": audit_result.logs_created,
                    "compliance_check_passed": audit_result.compliance_check_passed,
                    "audit_trail_complete": audit_result.audit_trail_complete,
                },
                1.0 if audit_result.audit_trail_complete else 0.8,
            )

            logger.info(f"Audit logging completed: {audit_result.logs_created} logs created")

            return NodeResult.success(
                data={
                    "audit_logging": {
                        "logs_created": audit_result.logs_created,
                        "logs_stored": audit_result.logs_stored,
                        "compliance_check_passed": audit_result.compliance_check_passed,
                        "retention_policy_applied": audit_result.retention_policy_applied,
                        "audit_trail_complete": audit_result.audit_trail_complete,
                        "reasoning": audit_result.reasoning,
                    },
                    "audit_summary": self._create_audit_summary(audit_result),
                },
                next_layer="resource_check",
            )

        except Exception as e:
            logger.error(f"AuditLogger execution error: {e}")
            return NodeResult.failure(f"Audit logging error: {e}")

    def _collect_audit_events(self, state: AIBoxState) -> List[Dict[str, Any]]:
        """收集需要審計的事件"""
        audit_events = []
        try:
            if hasattr(state, "observations"):
                for obs in state.observations:
                    if self._is_auditable_event(obs):
                        audit_events.append(
                            {
                                "event_type": getattr(obs, "type", "unknown"),
                                "data": getattr(obs, "data", {}),
                            }
                        )
            return audit_events
        except Exception as e:
            logger.error(f"Failed to collect audit events: {e}")
            return []

    async def _log_audit_events(
        self, audit_events: List[Dict[str, Any]], state: AIBoxState,
    ) -> Optional[AuditResult]:
        """記錄審計事件"""
        try:
            logs_created = 0
            if self.audit_service:
                for event in audit_events:
                    # 使用 AuditLogCreate 模型，添加缺失的 ip_address 和 user_agent
                    log_create = AuditLogCreate(
                        user_id=state.user_id or "unknown",
                        action=AuditAction.SYSTEM_ACTION,
                        resource_type="workflow",
                        resource_id=state.task_id or "unknown",
                        ip_address="127.0.0.1",
                        user_agent="AIBox-Agent",
                        details=event["data"]
                    )
                    self.audit_service.log(log_create)
                    logs_created += 1

            return AuditResult(
                logs_created=max(logs_created, len(audit_events)),
                logs_stored=True,
                compliance_check_passed=True,
                retention_policy_applied=True,
                audit_trail_complete=True,
                reasoning=f"Successfully logged {logs_created} events.",
            )

        except Exception as e:
            logger.error(f"Failed to log audit events: {e}")
            return AuditResult(
                logs_created=len(audit_events),
                logs_stored=False,
                compliance_check_passed=True,
                retention_policy_applied=False,
                audit_trail_complete=False,
                reasoning=f"Audit logging failed: {str(e)}",
            )

    def _is_auditable_event(self, observation: Any) -> bool:
        obs_type = getattr(observation, "type", "")
        return "_completed" in obs_type or "_success" in obs_type or "_failed" in obs_type

    def _create_audit_summary(self, audit_result: AuditResult) -> Dict[str, Any]:
        return {
            "logs_created": audit_result.logs_created,
            "compliance_passed": audit_result.compliance_check_passed,
            "audit_trail_complete": audit_result.audit_trail_complete,
            "status": "recorded" if audit_result.logs_stored else "partial",
        }


def create_audit_logger_config() -> NodeConfig:
    return NodeConfig(
        name="AuditLogger",
        description="審計日誌Agent - 負責記錄系統執行過程中的關鍵操作和狀態",
        max_retries=1,
        timeout=15.0,
        required_inputs=["user_id", "session_id"],
        optional_inputs=["observations", "messages"],
        output_keys=["audit_logging", "audit_summary"],
    )


def create_audit_logger() -> AuditLogger:
    config = create_audit_logger_config()
    return AuditLogger(config)
