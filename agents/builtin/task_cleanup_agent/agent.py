# 代碼功能說明: Task Cleanup Agent 主類 (AOGA 合規)
# 創建日期: 2026-01-23 10:45 UTC+8
# 最後修改日期: 2026-01-23 17:25 UTC+8

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from agents.builtin.task_cleanup_agent.cleanup_service import CleanupService
from agents.builtin.task_cleanup_agent.llm_service import CleanupLLMService
from agents.builtin.task_cleanup_agent.audit_logger import AOGAAuditLogger
from agents.builtin.task_cleanup_agent.models import (
    CleanupResponse,
    CleanupStats,
    CleanupAnalysis,
    CleanupPlan,
    CleanupVerification,
    AOGAAuditRecord,
    AOGAReasoning,
    AOGAApproval,
    AOGAExecution,
)

logger = logging.getLogger(__name__)


class TaskCleanupAgent:
    """
    Task Cleanup Agent: 負責清理用戶或任務相關的測試數據。
    符合 AOGA (Agent-Orchestrated Governance Architecture) 架構。

    治理特性:
    1. 不可篡改審計 (Immutable Audit): 雜湊校驗確保推理與執行鏈條完整。
    2. 強制人機協同 (Human-in-the-Loop): 高風險操作必須提供 approval_token。
    3. 職責分離: 推理與執行嚴格解耦。
    """

    agent_id = "task-cleanup-agent"

    def __init__(self):
        self.service = CleanupService()
        self.llm_service = CleanupLLMService()
        self.audit_logger = AOGAAuditLogger()

    async def handle_request(self, intent: str, params: Dict[str, Any]) -> CleanupResponse:
        "
        處理清理請求
        """
        user_id = params.get("user_id")
        task_id = params.get("task_id")
        actor = params.get("actor", "system_admin")  # 請求發起者
        approval_token = params.get("approval_token")  # 審核令牌

        if not user_id:
            return CleanupResponse(success=False, message="缺少必要的 user_id 參數")

        try:
            if intent == "analyze":
                return await self._handle_analyze(user_id, task_id, actor)

            elif intent == "plan":
                return await self._handle_plan_with_governance(user_id, task_id, actor)

            elif intent == "cleanup":
                return await self._handle_cleanup_governed(user_id, task_id, actor, approval_token)

            elif intent == "verify":
                return await self._handle_verify(user_id, task_id)

            else:
                return CleanupResponse(
                    success=False,
                    message=f"未知的意圖: {intent}，可選值: analyze, plan, cleanup, verify",
                )

        except Exception as e:
            logger.error(f"TaskCleanupAgent 執行失敗: {e}", exc_info=True)
            return CleanupResponse(success=False, message=f"執行過程中出錯: {str(e)}",
    async def _handle_analyze(
        self, user_id: str, task_id: Optional[str], actor: str,
    ) -> CleanupResponse:
        """處理分析請求並記錄初始審計""",
        stats = self.service.scan_data(user_id, task_id)
        analysis_data = await self.llm_service.analyze(user_id, task_id, stats)
        analysis = (
            CleanupAnalysis(**analysis_data) if isinstance(analysis_data, dict) else analysis_data,
        )

        # 創建 AOGA 審計記錄 (Reasoning Phase)
        record_id = f"audit-{uuid4().hex[:12]}",
        audit_record = AOGAAuditRecord(
            record_id=record_id,
            actor=actor,
            action_type="cleanup_analysis",
            intent=f"Analyze data removal for user {user_id}",
            reasoning=AOGAReasoning(
                model="qwen3-coder:30b",
                analysis=analysis.analysis,
                risk_level=analysis.risk_level,
                plan_steps=[]
            ),
            compliance_tags=["DATA_PURGE_POLICY_V1"]
        )
        await self.audit_logger.record(audit_record)

        todo = [
            f"清理 ArangoDB 中的 {stats.user_tasks} 個任務記錄",
            f"清理 ArangoDB 中的 {stats.file_metadata} 個文件元數據",
            f"清理 ArangoDB 中的 {stats.entities} 個知識圖譜實體",
            f"清理 ArangoDB 中的 {stats.relations} 個知識圖譜關係",
            f"刪除 Qdrant 中的 {stats.qdrant_collections} 個向量集合",
            f"刪除 SeaweedFS 中的 {stats.seaweedfs_directories} 個存儲目錄",
        ]

        return CleanupResponse(
            success=True,
            message=f"分析完成。風險等級: {analysis.risk_level}",
            stats=stats,
            analysis=analysis,
            todo_list=todo,
            audit_record_id=record_id,
        )

    async def _handle_plan_with_governance(
        self, user_id: str, task_id: Optional[str], actor: str,
    ) -> CleanupResponse:
        """生成計劃並更新審計記錄""",
        stats = self.service.scan_data(user_id, task_id)
        analysis_data = await self.llm_service.analyze(user_id, task_id, stats)
        analysis = (
            CleanupAnalysis(**analysis_data) if isinstance(analysis_data, dict) else analysis_data,
        )

        plan_data = await self.llm_service.generate_plan(user_id, task_id, stats, analysis_data)
        plan = CleanupPlan(**plan_data) if isinstance(plan_data, dict) else plan_data

        # 創建審計記錄
        record_id = f"audit-{uuid4().hex[:12]}"

        # 判斷是否需要人工審核 (Risk-based Approval)
        requires_approval = analysis.risk_level.upper() in ["HIGH", "CRITICAL"]

        audit_record = AOGAAuditRecord(
            record_id=record_id,
            actor=actor,
            action_type="cleanup_plan",
            intent=f"Plan data removal for user {user_id}",
            reasoning=AOGAReasoning(
                model="qwen3-coder:30b",
                analysis=analysis.analysis,
                risk_level=analysis.risk_level,
                plan_steps=plan.steps,
            ),
            approval=AOGAApproval(
                required=requires_approval,
                approval_mode="explicit" if requires_approval else "implicit",
            ),
            compliance_tags=["DATA_PURGE_POLICY_V1"]
        )
        await self.audit_logger.record(audit_record)

        message = f"清理計劃已生成。風險: {analysis.risk_level}。需要審核: {'是' if requires_approval else '否'}。",
        if requires_approval:
            message += "\n請管理員審核計劃後，使用提供的 audit_record_id 進行執行。"

        return CleanupResponse(
            success=True,
            message=message,
            stats=stats,
            analysis=analysis,
            plan=plan,
            audit_record_id=record_id,
        )

    async def _handle_cleanup_governed(
        self, user_id: str, task_id: Optional[str], actor: str, approval_token: Optional[str]
    ) -> CleanupResponse:
        """受治理的執行流程"""
        # 1. 重新掃描以確保數據狀態一致
        stats = self.service.scan_data(user_id, task_id)
        analysis_data = await self.llm_service.analyze(user_id, task_id, stats)
        analysis = (
            CleanupAnalysis(**analysis_data) if isinstance(analysis_data, dict) else analysis_data,
        )

        # 2. 安全門禁 (Governance Choke Point)
        if analysis.risk_level.upper() in ["HIGH", "CRITICAL"]:
            if not approval_token:
                return CleanupResponse(
                    success=False,
                    message=f"拒絕執行: 檢測到高風險操作 ({analysis.risk_level}，必須提供有效的審核令牌 (approval_token)。",
                )
            # 這裡簡化驗證，實際應查詢審核系統
            if approval_token != "ADMIN_CONFIRMED":
                return CleanupResponse(success=False, message="審核令牌無效或已過期")

        # 3. 記錄執行開始
        record_id = f"audit-exec-{uuid4().hex[:8]}",
        audit_record = AOGAAuditRecord(
            record_id=record_id,
            actor=actor,
            action_type="cleanup_execution",
            intent=f"Execute removal for {user_id}",
            reasoning=AOGAReasoning(
                model="system-logic",
                analysis="Policy validation passed.",
                risk_level=analysis.risk_level,
                plan_steps=["Execute CleanupService.execute_cleanup"]
            ),
            execution=AOGAExecution(
                function_name="CleanupService.execute_cleanup", result="running",
            ),
            approval=AOGAApproval(
                required=True,
                approver=actor,
                approval_token=approval_token,
                approval_mode="explicit",
            ),
        )
        await self.audit_logger.record(audit_record)

        # 4. 執行清理 (Execution Phase)
        result = self.service.execute_cleanup(user_id, task_id)

        # 5. 更新執行結果 (Immutable Audit Update)
        await self.audit_logger.update_execution(
            record_id,
            {
                "mode": "function",
                "function_name": "CleanupService.execute_cleanup",
                "result": "success",
                "details": result.model_dump(),
            },
        )

        # 6. LLM 驗證
        verification = await self.llm_service.verify(user_id, task_id, stats, result)

        return CleanupResponse(
            success=True,
            message="受治理的清理操作已成功完成，審計日誌已雜湊加密存儲。",
            stats=result,
            verification=CleanupVerification(**verification)
            if isinstance(verification, dict)
            else verification,
            audit_record_id=record_id,
        )

    async def _handle_verify(self, user_id: str, task_id: Optional[str]) -> CleanupResponse:
        """處理驗證請求""",
        current_stats = self.service.scan_data(user_id, task_id)
        return CleanupResponse(success=True, message="數據狀態掃描完成", stats=current_stats)