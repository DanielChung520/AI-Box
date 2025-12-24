# 代碼功能說明: System Config Agent 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""System Config Agent 實現

系統設置代理，通過自然語言進行系統配置管理。
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.task_analyzer.models import ConfigIntent
from services.api.core.log.log_service import LogService, get_log_service
from services.api.models.config import ConfigCreate, ConfigUpdate
from services.api.services.config_store_service import ConfigStoreService, get_config_store_service

from .inspection_service import ConfigInspectionService
from .models import ComplianceCheckResult, ConfigOperationResult
from .preview_service import ConfigPreviewService
from .rollback_service import ConfigRollbackService

logger = logging.getLogger(__name__)


class SystemConfigAgent(AgentServiceProtocol):
    """System Config Agent - 系統設置代理

    通過自然語言進行系統配置管理，支持配置查詢、設置、驗證等功能。
    """

    def __init__(self):
        """初始化 System Config Agent"""
        self._config_service: ConfigStoreService = get_config_store_service()
        self._log_service: LogService = get_log_service()
        self._preview_service = ConfigPreviewService()
        self._rollback_service = ConfigRollbackService()
        self._inspection_service = ConfigInspectionService()
        self._logger = logger

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        處理系統配置相關的任務

        Args:
            request: Agent 服務請求，包含：
                - intent: 已解析的配置意圖（ConfigIntent，由 Orchestrator 解析）
                - admin_user_id: 管理員用戶 ID
                - context: 上下文信息（包含原始指令、任務 ID、audit_context 等）

        Returns:
            AgentServiceResponse: 包含配置查詢結果或設置確認
        """
        try:
            # 解析請求數據
            task_data = request.task_data
            intent_data = task_data.get("intent")
            if not intent_data:
                raise ValueError(
                    "ConfigIntent is required. Orchestrator should parse intent and pass it to System Config Agent."
                )

            # 從字典或對象創建 ConfigIntent
            if isinstance(intent_data, dict):
                intent = ConfigIntent(**intent_data)
            else:
                intent = intent_data

            admin_user_id = task_data.get("admin_user_id")
            if not admin_user_id:
                raise ValueError("admin_user_id is required")

            context = task_data.get("context", {})
            trace_id = context.get("trace_id")  # 由 Orchestrator 提供的 trace_id

            # 如果需要澄清，直接返回澄清問題
            if intent.clarification_needed:
                return AgentServiceResponse(
                    task_id=request.task_id,
                    status="clarification_needed",
                    result={
                        "clarification_needed": True,
                        "clarification_question": intent.clarification_question,
                        "missing_slots": intent.missing_slots,
                    },
                    error=None,  # type: ignore[call-arg]  # error 有默認值
                    metadata=request.metadata,  # type: ignore[call-arg]  # metadata 有默認值
                )

            # 1. 權限驗證（二次確認，主要權限檢查已在 Orchestrator 層完成）
            await self._verify_permission(admin_user_id, intent)

            # 2. 執行操作
            if intent.action == "query":
                result = await self._handle_query(intent)
            elif intent.action == "create":
                result = await self._handle_create(intent, admin_user_id, trace_id)
            elif intent.action == "update":
                # 配置更新需要預覽確認（使用 ConfigPreviewService）
                result = await self._handle_update_with_preview(intent, admin_user_id, trace_id)
            elif intent.action == "delete":
                result = await self._handle_delete(intent, admin_user_id, trace_id)
            elif intent.action == "list":
                result = await self._handle_list(intent)
            elif intent.action == "rollback":
                result = await self._handle_rollback(intent, admin_user_id, trace_id)
            elif intent.action == "inspect":
                result = await self._handle_inspection(intent, admin_user_id, trace_id)
            else:
                result = ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action=intent.action,
                    scope=intent.scope,
                    level=intent.level,
                    success=False,
                    error=f"Unsupported action: {intent.action}",
                )

            # 3. 構建響應
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result=result.model_dump() if isinstance(result, ConfigOperationResult) else result,
                error=None,  # type: ignore[call-arg]  # error 有默認值
                metadata=request.metadata,  # type: ignore[call-arg]  # metadata 有默認值
            )

        except Exception as e:
            self._logger.error(f"System Config Agent execution failed: {e}", exc_info=True)
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,  # type: ignore[call-arg]  # result 有默認值
                error=str(e),
                metadata=request.metadata,  # type: ignore[call-arg]  # metadata 有默認值
            )

    async def _handle_query(self, intent: ConfigIntent) -> ConfigOperationResult:
        """處理配置查詢"""
        try:
            if intent.level == "system":
                config = self._config_service.get_config(intent.scope, tenant_id=None, user_id=None)
            elif intent.level == "tenant":
                if not intent.tenant_id:
                    return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                        action="query",
                        scope=intent.scope,
                        level=intent.level,
                        success=False,
                        error="tenant_id is required for tenant-level query",
                    )
                config = self._config_service.get_config(
                    intent.scope, tenant_id=intent.tenant_id, user_id=None
                )
            elif intent.level == "user":
                if not intent.tenant_id or not intent.user_id:
                    return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                        action="query",
                        scope=intent.scope,
                        level=intent.level,
                        success=False,
                        error="tenant_id and user_id are required for user-level query",
                    )
                config = self._config_service.get_config(
                    intent.scope, tenant_id=intent.tenant_id, user_id=intent.user_id
                )
            else:
                # 有效配置查詢（合併後）
                if not intent.tenant_id:
                    return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                        action="query",
                        scope=intent.scope,
                        level="effective",
                        success=False,
                        error="tenant_id is required for effective config query",
                    )
                effective_config = self._config_service.get_effective_config(
                    intent.scope, tenant_id=intent.tenant_id, user_id=intent.user_id
                )
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="query",
                    scope=intent.scope,
                    level="effective",
                    success=True,
                    config=effective_config.config,
                    message=f"Effective config for scope: {intent.scope}",
                )

            config_dict = None
            if config:
                config_dict = {
                    "id": config.id,
                    "scope": config.scope,
                    "level": intent.level,
                    "config_data": config.config_data,
                    "metadata": config.metadata,
                    "is_active": config.is_active,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="query",
                scope=intent.scope,
                level=intent.level,
                success=True,
                config=config_dict,
                message=f"Config query completed for scope: {intent.scope}, level: {intent.level}",
            )

        except Exception as e:
            self._logger.error(f"Config query failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="query",
                scope=intent.scope,
                level=intent.level or "unknown",
                success=False,
                error=str(e),
            )

    async def _handle_create(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置創建"""
        try:
            if not intent.config_data:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="create",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error="config_data is required for create operation",
                )

            # 創建 ConfigCreate 對象
            config_create = ConfigCreate(
                scope=intent.scope,
                config_data=intent.config_data,
                tenant_id=intent.tenant_id if intent.level == "tenant" else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )

            # 保存配置
            config_id = self._config_service.save_config(
                config_create,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )

            # 記錄審計日誌
            if trace_id:
                await self._log_service.log_audit(
                    trace_id=trace_id,
                    actor=admin_user_id,
                    action="create_config",
                    content={
                        "scope": intent.scope,
                        "level": intent.level or "system",
                        "config_data": intent.config_data,
                        "config_id": config_id,
                    },
                    level=intent.level or "system",
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                )

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="create",
                scope=intent.scope,
                level=intent.level or "system",
                success=True,
                config={"id": config_id, "config_data": intent.config_data},
                message=f"Config created successfully: {config_id}",
                audit_log_id=trace_id,
            )

        except Exception as e:
            self._logger.error(f"Config create failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="create",
                scope=intent.scope,
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_update_with_preview(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置更新（含預覽機制）"""
        try:
            # 獲取當前配置
            current_config = self._config_service.get_config(
                intent.scope,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )

            # 生成預覽
            preview = await self._preview_service.generate_preview(intent, current_config)

            # 檢查是否需要確認（高風險操作需要確認）
            # 注意：這裡簡化實現，實際應該由 Orchestrator 處理確認流程
            if preview.confirmation_required and preview.risk_level == "high":
                # 返回預覽結果，等待確認
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="update",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    message="High risk operation requires confirmation",
                    impact_analysis=preview.impact_analysis,
                    config={"preview": preview.model_dump(), "requires_confirmation": True},
                )

            # 如果不需要確認或風險較低，直接執行更新
            return await self._handle_update(intent, admin_user_id, trace_id)

        except Exception as e:
            self._logger.error(f"Config update with preview failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="update",
                scope=intent.scope,
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_update(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置更新（實際執行）"""
        try:
            if not intent.config_data:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="update",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error="config_data is required for update operation",
                )

            # 確定配置 ID（通過獲取當前配置來確定）
            # 如果配置不存在，則根據規則生成 key
            def _generate_config_key(
                scope: str, tenant_id: Optional[str] = None, user_id: Optional[str] = None
            ) -> str:
                """生成 Config 的 _key"""
                if user_id:
                    return f"{tenant_id}_{user_id}_{scope}"
                elif tenant_id:
                    return f"{tenant_id}_{scope}"
                else:
                    return scope

            config_id = _generate_config_key(
                intent.scope,
                intent.tenant_id if intent.level in ["tenant", "user"] else None,
                intent.user_id if intent.level == "user" else None,
            )

            # 獲取當前配置（用於 before/after 對照）
            current_config = self._config_service.get_config(
                intent.scope,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )
            before_config = current_config.config_data if current_config else {}

            # 第二層深檢：配置合規性驗證
            compliance_result = await self._validate_config_compliance(intent, intent.config_data)
            if not compliance_result.valid:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="update",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error=f"Compliance check failed: {compliance_result.reason}",
                )

            # 創建 ConfigUpdate 對象
            config_update = ConfigUpdate(config_data=intent.config_data)

            # 更新配置
            updated_config = self._config_service.update_config(
                config_id,
                config_update,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )
            after_config = updated_config.config_data

            # 計算變更內容
            changes = self._calculate_changes(before_config, after_config)

            # 生成 rollback_id
            rollback_id = f"rb-{uuid.uuid4().hex[:8]}"

            # 構建 AQL 查詢記錄
            collection_name = (
                "system_configs"
                if intent.level == "system"
                else "tenant_configs" if intent.level == "tenant" else "user_configs"
            )
            aql_query = f"""
UPDATE {{_key: '{config_id}'}}
WITH {{config_data: {json.dumps(after_config, ensure_ascii=False)}}}
IN {collection_name}
RETURN NEW
"""

            # 記錄審計日誌
            if trace_id:
                await self._log_service.log_audit(
                    trace_id=trace_id,
                    actor=admin_user_id,
                    action="update_config",
                    content={
                        "scope": intent.scope,
                        "level": intent.level or "system",
                        "before": before_config,
                        "after": after_config,
                        "changes": changes,
                        "aql_query": aql_query,
                        "rollback_id": rollback_id,
                        "compliance_check": {
                            "passed": True,
                            "convergence_violations": compliance_result.convergence_violations,
                            "business_rule_violations": compliance_result.business_rule_violations,
                        },
                    },
                    level=intent.level or "system",
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                )

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="update",
                scope=intent.scope,
                level=intent.level or "system",
                success=True,
                config={"id": config_id, "config_data": after_config},
                changes=changes,
                message=f"Config updated successfully: {config_id}",
                audit_log_id=trace_id,
                rollback_id=rollback_id,
            )

        except Exception as e:
            self._logger.error(f"Config update failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="update",
                scope=intent.scope,
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_delete(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置刪除"""
        try:
            # 確定配置 ID（通過獲取當前配置來確定）
            # 如果配置不存在，則根據規則生成 key
            def _generate_config_key(
                scope: str, tenant_id: Optional[str] = None, user_id: Optional[str] = None
            ) -> str:
                """生成 Config 的 _key"""
                if user_id:
                    return f"{tenant_id}_{user_id}_{scope}"
                elif tenant_id:
                    return f"{tenant_id}_{scope}"
                else:
                    return scope

            config_id = _generate_config_key(
                intent.scope,
                intent.tenant_id if intent.level in ["tenant", "user"] else None,
                intent.user_id if intent.level == "user" else None,
            )

            # 獲取當前配置（用於審計）
            current_config = self._config_service.get_config(
                intent.scope,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                user_id=intent.user_id if intent.level == "user" else None,
            )

            if not current_config:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="delete",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error=f"Config not found: {config_id}",
                )

            # 執行軟刪除
            deleted = self._config_service.delete_config(
                config_id,
                tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                hard_delete=False,  # 默認軟刪除
            )

            if not deleted:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="delete",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error=f"Failed to delete config: {config_id}",
                )

            # 記錄審計日誌
            if trace_id:
                await self._log_service.log_audit(
                    trace_id=trace_id,
                    actor=admin_user_id,
                    action="delete_config",
                    content={
                        "scope": intent.scope,
                        "level": intent.level or "system",
                        "config_id": config_id,
                        "deleted_config": current_config.config_data,
                    },
                    level=intent.level or "system",
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                )

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="delete",
                scope=intent.scope,
                level=intent.level or "system",
                success=True,
                message=f"Config deleted successfully: {config_id}",
                audit_log_id=trace_id,
            )

        except Exception as e:
            self._logger.error(f"Config delete failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="delete",
                scope=intent.scope,
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_list(self, intent: ConfigIntent) -> ConfigOperationResult:
        """處理配置列表查詢"""
        try:
            # 基礎實現：查詢單個配置（後續可以擴展為真正的列表查詢）
            # TODO: 實現完整的配置列表查詢（需要數據庫查詢支持）
            if intent.scope:
                # 如果指定了 scope，查詢該 scope 的配置
                config = self._config_service.get_config(
                    intent.scope,
                    tenant_id=intent.tenant_id if intent.level in ["tenant", "user"] else None,
                    user_id=intent.user_id if intent.level == "user" else None,
                )
                configs = [config] if config else []
            else:
                # 如果未指定 scope，返回空列表（需要後續實現完整查詢）
                configs = []

            config_list = []
            for config in configs:
                if config:
                    config_list.append(
                        {
                            "id": config.id,
                            "scope": config.scope,
                            "level": intent.level or "system",
                            "config_data": config.config_data,
                            "is_active": config.is_active,
                        }
                    )

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="list",
                scope=intent.scope or "all",
                level=intent.level or "system",
                success=True,
                config={"configs": config_list, "count": len(config_list)},
                message=f"Found {len(config_list)} config(s)",
            )

        except Exception as e:
            self._logger.error(f"Config list failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="list",
                scope=intent.scope or "all",
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_rollback(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置回滾"""
        try:
            # 從 intent.config_data 中獲取 rollback_id
            # 如果沒有提供 rollback_id，嘗試從 intent.scope 或其他字段獲取
            rollback_id = intent.config_data.get("rollback_id") if intent.config_data else None
            if not rollback_id:
                # 如果沒有明確的 rollback_id，嘗試使用最近一次變更的 trace_id
                recent_changes = await self._rollback_service.get_recent_changes(
                    scope=intent.scope,
                    level=intent.level,
                    tenant_id=intent.tenant_id,
                    limit=1,
                )
                if recent_changes and len(recent_changes) > 0:
                    rollback_id = recent_changes[0].get("trace_id") or recent_changes[0].get(
                        "rollback_id"
                    )
                else:
                    return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                        action="rollback",
                        scope=intent.scope,
                        level=intent.level or "system",
                        success=False,
                        error="rollback_id is required for rollback operation",
                    )

            # 執行回滾
            rollback_result = await self._rollback_service.rollback_config(
                rollback_id=rollback_id,
                admin_user_id=admin_user_id,
                scope=intent.scope,
                level=intent.level,
                tenant_id=intent.tenant_id,
            )

            if not rollback_result.success:
                return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                    action="rollback",
                    scope=intent.scope,
                    level=intent.level or "system",
                    success=False,
                    error=rollback_result.message,
                )

            # 記錄審計日誌
            if trace_id:
                await self._log_service.log_audit(
                    trace_id=trace_id,
                    actor=admin_user_id,
                    action="rollback_config",
                    content={
                        "scope": intent.scope,
                        "level": intent.level or "system",
                        "original_rollback_id": rollback_id,
                        "new_rollback_id": rollback_result.rollback_id,
                        "restored_config": rollback_result.restored_config,
                    },
                    level=intent.level or "system",
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                )

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="rollback",
                scope=intent.scope,
                level=intent.level or "system",
                success=True,
                config=rollback_result.restored_config,
                message=rollback_result.message,
                rollback_id=rollback_result.rollback_id,
            )

        except Exception as e:
            self._logger.error(f"Config rollback failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="rollback",
                scope=intent.scope,
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _handle_inspection(
        self, intent: ConfigIntent, admin_user_id: str, trace_id: Optional[str] = None
    ) -> ConfigOperationResult:
        """處理配置巡檢"""
        try:
            # 執行巡檢
            issues = await self._inspection_service.inspect_all_configs(
                scope=intent.scope,
                tenant_id=intent.tenant_id,
            )

            # 為每個問題生成修復建議
            issues_with_suggestions = []
            for issue in issues:
                suggestion = await self._inspection_service.suggest_fix(issue)
                issues_with_suggestions.append(
                    {
                        "issue": issue.model_dump(),
                        "suggestion": suggestion.model_dump(),
                    }
                )

            # 記錄審計日誌
            if trace_id:
                await self._log_service.log_audit(
                    trace_id=trace_id,
                    actor=admin_user_id,
                    action="inspect_configs",
                    content={
                        "scope": intent.scope,
                        "level": intent.level or "system",
                        "tenant_id": intent.tenant_id,
                        "issues_count": len(issues),
                        "issues": [issue.model_dump() for issue in issues],
                    },
                    level=intent.level or "system",
                    tenant_id=intent.tenant_id,
                    user_id=intent.user_id,
                )

            # 構建結果
            if issues:
                message = f"發現 {len(issues)} 個配置問題"
            else:
                message = "配置巡檢完成，未發現問題"

            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="inspect",
                scope=intent.scope or "all",
                level=intent.level or "system",
                success=True,
                message=message,
                config={
                    "issues_count": len(issues),
                    "issues": issues_with_suggestions,
                },
            )

        except Exception as e:
            self._logger.error(f"Config inspection failed: {e}", exc_info=True)
            return ConfigOperationResult(  # type: ignore[call-arg]  # 字段都有默認值
                action="inspect",
                scope=intent.scope or "all",
                level=intent.level or "system",
                success=False,
                error=str(e),
            )

    async def _validate_config_compliance(
        self, intent: ConfigIntent, new_config_data: Dict[str, Any]
    ) -> ComplianceCheckResult:
        """
        驗證配置合規性（第二層深檢）

        Args:
            intent: 配置操作意圖
            new_config_data: 新的配置數據

        Returns:
            ComplianceCheckResult: 合規性檢查結果
        """
        violations = []
        convergence_violations = []
        business_rule_violations = []

        # 1. 檢查收斂規則（僅對 tenant 級配置）
        if intent.level == "tenant":
            convergence_result = await self._check_convergence_rules(intent, new_config_data)
            if not convergence_result.valid:
                convergence_violations.extend(convergence_result.convergence_violations)
                violations.extend(convergence_result.convergence_violations)

        # 2. 檢查業務規則
        business_result = await self._check_business_rules(intent, new_config_data)
        if not business_result.valid:
            business_rule_violations.extend(business_result.business_rule_violations)
            violations.extend(business_result.business_rule_violations)

        valid = len(violations) == 0
        reason = "; ".join(violations) if violations else None

        return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
            valid=valid,
            reason=reason,
            convergence_violations=convergence_violations,
            business_rule_violations=business_rule_violations,
        )

    async def _check_convergence_rules(
        self, intent: ConfigIntent, tenant_config_data: Dict[str, Any]
    ) -> ComplianceCheckResult:
        """
        檢查收斂規則（tenant 配置不能擴權）

        Args:
            intent: 配置操作意圖
            tenant_config_data: 租戶配置數據

        Returns:
            ComplianceCheckResult: 檢查結果
        """
        violations = []

        try:
            # 獲取 system 配置
            system_config = self._config_service.get_config(intent.scope, tenant_id=None)
            if not system_config:
                # 如果沒有 system 配置，無法驗證收斂規則
                return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
                    valid=True,
                    reason="No system config found, skipping convergence check",
                )

            system_data = system_config.config_data

            # 使用 ConfigStoreService 的驗證方法
            # 注意：這裡需要訪問私有方法，但我們可以實現自己的驗證邏輯
            def _normalize_provider(value: str) -> str:
                """標準化 provider 名稱"""
                return str(value).strip().lower()

            def _pattern_is_subset_of_any(pattern: str, supersets: list) -> bool:
                """判斷 pattern 是否不會擴權"""
                p = str(pattern).strip().lower()
                if not p:
                    return False
                for s in supersets:
                    sp = str(s).strip().lower()
                    if not sp:
                        continue
                    if sp == "*":
                        return True
                    if sp.endswith("*"):
                        if p.startswith(sp[:-1]):
                            return True
                    else:
                        if p == sp:
                            return True
                return False

            # 檢查 allowed_providers
            sys_providers = set(
                _normalize_provider(p) for p in system_data.get("allowed_providers", [])
            )
            tenant_providers = set(
                _normalize_provider(p) for p in tenant_config_data.get("allowed_providers", [])
            )
            if tenant_providers - sys_providers:
                diff = tenant_providers - sys_providers
                violations.append(
                    f"Tenant allowed_providers contains providers not in system config: {', '.join(diff)}"
                )

            # 檢查 allowed_models
            sys_models = system_data.get("allowed_models", {})
            tenant_models = tenant_config_data.get("allowed_models", {})
            if isinstance(sys_models, dict) and isinstance(tenant_models, dict):
                for prov, patterns in tenant_models.items():
                    prov_key = _normalize_provider(prov)
                    sys_patterns = sys_models.get(prov_key, [])
                    tenant_patterns_list = patterns if isinstance(patterns, list) else []
                    for pattern in tenant_patterns_list:
                        if not _pattern_is_subset_of_any(str(pattern), sys_patterns):
                            violations.append(
                                f"Tenant model pattern '{pattern}' for provider '{prov}' is not allowed by system config"
                            )

            valid = len(violations) == 0
            reason = "; ".join(violations) if violations else None

            return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
                valid=valid,
                reason=reason,
                convergence_violations=violations,
            )

        except Exception as e:
            self._logger.error(f"Convergence rule check failed: {e}", exc_info=True)
            return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
                valid=False,
                reason=f"Error checking convergence rules: {str(e)}",
                convergence_violations=[f"Check error: {str(e)}"],
            )

    async def _check_business_rules(
        self, intent: ConfigIntent, config_data: Dict[str, Any]
    ) -> ComplianceCheckResult:
        """
        檢查業務規則

        Args:
            intent: 配置操作意圖
            config_data: 配置數據

        Returns:
            ComplianceCheckResult: 檢查結果
        """
        violations = []

        try:
            # 1. 檢查限流值合理性
            if "rate_limit" in config_data:
                rate_limit = config_data.get("rate_limit")
                if isinstance(rate_limit, (int, float)):
                    if rate_limit < 0:
                        violations.append("rate_limit cannot be negative")
                    elif rate_limit > 1000000:  # 最大限流值
                        violations.append("rate_limit exceeds maximum allowed value (1000000)")

            # 2. 檢查模型可用性（基礎檢查）
            if "default_model" in config_data:
                default_model = config_data.get("default_model")
                if not default_model or not isinstance(default_model, str):
                    violations.append("default_model must be a non-empty string")

            # 3. 檢查 allowed_models 結構
            if "allowed_models" in config_data:
                allowed_models = config_data.get("allowed_models")
                if not isinstance(allowed_models, dict):
                    violations.append("allowed_models must be a dictionary")

            # 4. 檢查 allowed_providers 結構
            if "allowed_providers" in config_data:
                allowed_providers = config_data.get("allowed_providers")
                if not isinstance(allowed_providers, list):
                    violations.append("allowed_providers must be a list")

            valid = len(violations) == 0
            reason = "; ".join(violations) if violations else None

            return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
                valid=valid,
                reason=reason,
                business_rule_violations=violations,
            )

        except Exception as e:
            self._logger.error(f"Business rule check failed: {e}", exc_info=True)
            return ComplianceCheckResult(  # type: ignore[call-arg]  # 字段都有默認值
                valid=False,
                reason=f"Error checking business rules: {str(e)}",
                business_rule_violations=[f"Check error: {str(e)}"],
            )

    async def _verify_permission(self, user_id: str, intent: ConfigIntent) -> None:
        """
        驗證用戶權限（二次確認）

        Args:
            user_id: 用戶 ID
            intent: 配置操作意圖

        Raises:
            PermissionError: 如果權限不足

        注意：主要權限檢查已在 Orchestrator 層通過 Security Agent 完成
        這裡做二次確認，確保權限驗證的完整性
        """
        # TODO: 集成 RBAC Service 獲取用戶角色
        # 目前使用簡化實現，後續可以集成完整的 RBAC 服務

        # 簡化實現：根據操作類型和級別進行基礎權限檢查
        # 實際應該從 RBAC Service 獲取用戶角色

        # 1. 系統級配置：需要 system_admin 權限
        if intent.level == "system":
            if intent.action in ["create", "update", "delete"]:
                # 系統級配置的修改操作需要系統管理員權限
                # 這裡只是示例，實際應該檢查用戶角色
                # if user_role != "system_admin":
                #     raise PermissionError("只有系統管理員可以操作系統級配置")
                pass

        # 2. 租戶級配置：需要 tenant_admin 或 system_admin 權限
        elif intent.level == "tenant":
            if intent.action in ["create", "update", "delete"]:
                # 租戶管理員只能操作自己租戶的配置
                # 這裡只是示例，實際應該檢查用戶角色和租戶歸屬
                # if user_role == "tenant_admin":
                #     user_tenant = await self._get_user_tenant(user_id)
                #     if intent.tenant_id != user_tenant:
                #         raise PermissionError("無權操作其他租戶的配置")
                pass

        # 3. 查詢操作：所有用戶都可以查詢（如果權限允許）
        elif intent.action == "query":
            # 查詢操作通常允許所有有權限的用戶
            pass

        # 4. 危險操作：需要額外確認（由 Orchestrator 層處理）
        if intent.action in ["delete"] and intent.level == "system":
            # 系統級配置刪除需要二次確認（由 Orchestrator 層處理）
            pass

    def _calculate_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """計算變更內容"""
        changes = {}
        all_keys = set(before.keys()) | set(after.keys())
        for key in all_keys:
            before_val = before.get(key)
            after_val = after.get(key)
            if before_val != after_val:
                changes[key] = {"old": before_val, "new": after_val}
        return changes

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        try:
            # 檢查 ConfigStoreService 和 LogService 是否可用
            # 簡單測試：嘗試獲取一個不存在的配置（應該返回 None，不拋出異常）
            self._config_service.get_config("health_check_scope", tenant_id=None, user_id=None)
            return AgentServiceStatus.AVAILABLE
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        return {
            "name": "System Config Agent",
            "description": "系統設置代理，通過自然語言進行系統配置管理",
            "capabilities": [
                "config_query",  # 配置查詢
                "config_create",  # 配置創建
                "config_update",  # 配置更新
                "config_delete",  # 配置刪除
                "config_list",  # 配置列表（待實現）
                "config_rollback",  # 配置回滾（待實現）
            ],
            "ai_enabled": False,  # 意圖解析由 Orchestrator 完成
            "version": "1.0.0",
        }
