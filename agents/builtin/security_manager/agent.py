# 代碼功能說明: Security Manager Agent 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Security Manager Agent 實現

AI 驱动的安全管理服务，提供智能风险评估、权限检查和安全审计功能。
"""

import json
import logging
from typing import Any, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from agents.services.registry.registry import get_agent_registry
from agents.services.resource_controller import ResourceType, get_resource_controller
from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import get_client

from .models import (
    ConfigRiskAssessmentResult,
    PermissionCheckResult,
    RiskAssessmentResult,
    RiskLevel,
    SecurityCheckResult,
    SecurityManagerRequest,
    SecurityManagerResponse,
)

logger = logging.getLogger(__name__)


class SecurityManagerAgent(AgentServiceProtocol):
    """Security Manager Agent - 安全管理员

    AI 驱动的安全管理服务，提供：
    - 智能风险评估
    - 权限检查和验证
    - 安全审计和分析
    """

    def __init__(self):
        """初始化 Security Manager Agent"""
        self._registry = get_agent_registry()
        self._resource_controller = get_resource_controller()
        self._llm_client = None  # 延迟初始化
        self._logger = logger

    def _get_llm_client(self):
        """获取 LLM 客户端（延迟初始化）"""
        if self._llm_client is None:
            try:
                self._llm_client = get_client(LLMProvider.OLLAMA)
            except Exception as e:
                self._logger.warning(f"Failed to initialize Ollama client: {e}")
                try:
                    self._llm_client = get_client(LLMProvider.QWEN)
                except Exception:
                    self._logger.error("No LLM client available")
        return self._llm_client

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        执行安全管理任务

        Args:
            request: Agent 服务请求

        Returns:
            Agent 服务响应
        """
        try:
            # 解析请求数据
            task_data = request.task_data
            action = task_data.get("action", "check_permission")
            security_request = SecurityManagerRequest(**task_data)

            # 根据操作类型执行相应功能
            if action == "assess":
                result = await self._assess_risk(security_request)
            elif action == "check_permission":
                result = await self._check_permission(security_request)
            elif action == "audit":
                result = await self._audit_security(security_request)
            elif action == "analyze":
                result = await self._analyze_security(security_request)
            else:
                result = SecurityManagerResponse(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}",
                    allowed=None,  # type: ignore[call-arg]  # allowed 有默認值
                    risk_assessment=None,  # type: ignore[call-arg]  # risk_assessment 有默認值
                    audit_result=None,  # type: ignore[call-arg]  # audit_result 有默認值
                    analysis=None,  # type: ignore[call-arg]  # analysis 有默認值
                    message=None,  # type: ignore[call-arg]  # message 有默認值
                )

            # 构建响应
            return AgentServiceResponse(
                task_id=request.task_id,
                status="completed" if result.success else "failed",
                result={
                    "success": result.success,
                    "action": result.action,
                    "allowed": result.allowed,
                    "risk_assessment": (
                        result.risk_assessment.model_dump() if result.risk_assessment else None
                    ),
                    "audit_result": result.audit_result,
                    "analysis": result.analysis,
                    "message": result.message,
                    "error": result.error,
                },
                error=None,  # type: ignore[call-arg]  # error 有默認值
                metadata=request.metadata,
            )

        except Exception as e:
            self._logger.error(f"Security Manager execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,  # type: ignore[call-arg]  # result 有默認值
                error=str(e),
                metadata=request.metadata,
            )

    async def _assess_risk(self, request: SecurityManagerRequest) -> SecurityManagerResponse:
        """
        AI 驱动的风险评估

        Args:
            request: 安全管理请求

        Returns:
            安全管理响应
        """
        try:
            # 基础风险评估
            risk_factors = []
            risk_score = 0.0

            # 检查 Agent 是否存在
            if request.agent_id:
                agent_info = self._registry.get_agent_info(request.agent_id)
                if not agent_info:
                    risk_factors.append("Agent not found")
                    risk_score += 0.3

                # 检查是否为外部 Agent
                if agent_info and not agent_info.endpoints.is_internal:
                    risk_factors.append("External agent access")
                    risk_score += 0.2

            # 使用 AI 进行智能风险评估
            if self._get_llm_client():
                ai_assessment = await self._ai_assess_risk(request, risk_factors)
                risk_score = ai_assessment.get("score", risk_score)
                risk_factors.extend(ai_assessment.get("factors", []))
                recommendations = ai_assessment.get("recommendations", [])
            else:
                recommendations = self._generate_basic_recommendations(risk_score)

            # 确定风险等级
            if risk_score >= 0.8:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            risk_assessment = RiskAssessmentResult(
                risk_level=risk_level,
                score=risk_score,
                details=None,  # type: ignore[call-arg]  # details 有默認值
                factors=risk_factors,
                recommendations=recommendations,
            )

            return SecurityManagerResponse(
                success=True,
                action="assess",
                risk_assessment=risk_assessment,
                message=f"Risk assessment completed: {risk_level.value}",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Risk assessment failed: {e}")
            return SecurityManagerResponse(
                success=False,
                action="assess",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _check_permission(self, request: SecurityManagerRequest) -> SecurityManagerResponse:
        """
        检查权限

        Args:
            request: 安全管理请求

        Returns:
            安全管理响应
        """
        try:
            if not request.agent_id or not request.resource_type:
                return SecurityManagerResponse(
                    success=False,
                    action="check_permission",
                    error="agent_id and resource_type are required",
                )  # type: ignore[call-arg]  # 其他參數都是 Optional

            # 使用资源访问控制器检查权限
            resource_type = ResourceType(request.resource_type)
            allowed = self._resource_controller.check_access(
                request.agent_id,
                resource_type,
                request.resource_name or "",
            )

            # 如果允许访问，进行风险评估
            risk_assessment = None
            if allowed and self._get_llm_client():
                risk_assessment_result = await self._assess_risk(request)
                risk_assessment = risk_assessment_result.risk_assessment

            return SecurityManagerResponse(
                success=True,
                action="check_permission",
                allowed=allowed,
                risk_assessment=risk_assessment,
                message=f"Permission check: {'allowed' if allowed else 'denied'}",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Permission check failed: {e}")
            return SecurityManagerResponse(
                success=False,
                action="check_permission",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _audit_security(self, request: SecurityManagerRequest) -> SecurityManagerResponse:
        """
        安全审计

        Args:
            request: 安全管理请求

        Returns:
            安全管理响应
        """
        try:
            # 获取所有 Agent
            all_agents = self._registry.list_agents()

            # 基础审计
            audit_result: Dict[str, Any] = {
                "total_agents": len(all_agents),
                "internal_agents": 0,
                "external_agents": 0,
                "security_issues": [],
            }

            for agent in all_agents:
                if agent.endpoints.is_internal:
                    audit_result["internal_agents"] += 1
                else:
                    audit_result["external_agents"] += 1

                    # 检查外部 Agent 的安全配置
                    if not agent.permissions.api_key:
                        audit_result["security_issues"].append(
                            f"External agent '{agent.agent_id}' has no API key"
                        )
                    if not agent.permissions.ip_whitelist:
                        audit_result["security_issues"].append(
                            f"External agent '{agent.agent_id}' has no IP whitelist"
                        )

            # 使用 AI 进行深度审计分析
            if self._get_llm_client():
                ai_audit = await self._ai_audit_security(all_agents, audit_result)
                audit_result.update(ai_audit)

            return SecurityManagerResponse(
                success=True,
                action="audit",
                audit_result=audit_result,
                message="Security audit completed",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Security audit failed: {e}")
            return SecurityManagerResponse(
                success=False,
                action="audit",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _analyze_security(self, request: SecurityManagerRequest) -> SecurityManagerResponse:
        """
        安全分析

        Args:
            request: 安全管理请求

        Returns:
            安全管理响应
        """
        try:
            # 基础分析
            analysis: Dict[str, Any] = {
                "permission_distribution": {},
                "risk_summary": {},
            }

            # 使用 AI 进行深度分析
            if self._get_llm_client():
                ai_analysis = await self._ai_analyze_security(request, analysis)
                analysis.update(ai_analysis)

            return SecurityManagerResponse(
                success=True,
                action="analyze",
                analysis=analysis,
                message="Security analysis completed",
            )  # type: ignore[call-arg]  # 其他參數都是 Optional

        except Exception as e:
            self._logger.error(f"Security analysis failed: {e}")
            return SecurityManagerResponse(
                success=False,
                action="analyze",
                error=str(e),  # type: ignore[call-arg]  # 其他參數都是 Optional,
            )

    async def _ai_assess_risk(
        self, request: SecurityManagerRequest, existing_factors: list
    ) -> Dict[str, Any]:
        """
        使用 AI 进行风险评估

        Args:
            request: 安全管理请求
            existing_factors: 已有的风险因素

        Returns:
            AI 风险评估结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {
                    "score": 0.5,
                    "factors": existing_factors,
                    "recommendations": [],
                }

            prompt = f"""你是一个安全专家。评估以下操作的安全风险。

操作信息：
- Agent ID: {request.agent_id or 'N/A'}
- Resource Type: {request.resource_type or 'N/A'}
- Resource Name: {request.resource_name or 'N/A'}
- Operation: {request.operation or 'N/A'}

已有风险因素：{existing_factors}

请返回风险评估结果（JSON 格式）：
{{"score": 0.0-1.0, "factors": ["factor1", ...], "recommendations": ["rec1", ...]}}"""

            response = await llm_client.generate(prompt, max_tokens=500)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                result = json.loads(result_text)
                return {
                    "score": result.get("score", 0.5),
                    "factors": result.get("factors", existing_factors),
                    "recommendations": result.get("recommendations", []),
                }
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {
                    "score": 0.5,
                    "factors": existing_factors,
                    "recommendations": [],
                }

        except Exception as e:
            self._logger.error(f"AI risk assessment failed: {e}")
            return {"score": 0.5, "factors": existing_factors, "recommendations": []}

    async def _ai_audit_security(self, agents: list, base_audit: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 AI 进行安全审计

        Args:
            agents: Agent 列表
            base_audit: 基础审计结果

        Returns:
            AI 审计结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {}

            prompt = f"""你是一个安全审计专家。分析以下 Agent 注册表的安全状态。

审计统计：
{json.dumps(base_audit, ensure_ascii=False, indent=2)}

请返回审计结果（JSON 格式），包含：
- security_recommendations: 安全建议列表
- risk_areas: 风险区域列表
- compliance_status: 合规状态

{{"security_recommendations": [...], "risk_areas": [...], "compliance_status": "..."}}"""

            response = await llm_client.generate(prompt, max_tokens=1000)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {}

        except Exception as e:
            self._logger.error(f"AI audit failed: {e}")
            return {}

    async def _ai_analyze_security(
        self, request: SecurityManagerRequest, base_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 AI 进行安全分析

        Args:
            request: 安全管理请求
            base_analysis: 基础分析结果

        Returns:
            AI 分析结果
        """
        try:
            llm_client = self._get_llm_client()
            if not llm_client:
                return {}

            prompt = f"""你是一个安全分析专家。分析以下安全配置。

分析请求：
{json.dumps(request.model_dump(), ensure_ascii=False, indent=2)}

基础分析：
{json.dumps(base_analysis, ensure_ascii=False, indent=2)}

请返回分析结果（JSON 格式），包含 insights 和 recommendations。"""

            response = await llm_client.generate(prompt, max_tokens=1000)
            result_text = response.get("text", "") or response.get("content", "")

            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                self._logger.warning("Failed to parse LLM response")
                return {}

        except Exception as e:
            self._logger.error(f"AI analysis failed: {e}")
            return {}

    def _generate_basic_recommendations(self, risk_score: float) -> list:
        """
        生成基础安全建议

        Args:
            risk_score: 风险分数

        Returns:
            建议列表
        """
        recommendations = []
        if risk_score >= 0.6:
            recommendations.append("建议启用额外的安全验证")
            recommendations.append("建议限制资源访问范围")
        if risk_score >= 0.4:
            recommendations.append("建议定期审查权限配置")
        return recommendations

    async def health_check(self) -> AgentServiceStatus:
        """
        健康检查

        Returns:
            服务状态
        """
        try:
            # 检查 Registry 和 Resource Controller 是否可用
            self._registry.list_agents()  # 檢查是否可用
            return AgentServiceStatus.AVAILABLE
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        获取服务能力

        Returns:
            服务能力描述
        """
        return {
            "name": "Security Manager Agent",
            "description": "AI 驱动的安全管理服务",
            "capabilities": [
                "risk_assessment",  # 风险评估
                "permission_check",  # 权限检查
                "security_audit",  # 安全审计
                "security_analysis",  # 安全分析
            ],
            "ai_enabled": True,
            "version": "1.0.0",
        }

    async def verify_access(
        self,
        admin_id: str,
        intent: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> SecurityCheckResult:
        """
        驗證用戶權限並評估操作風險

        這是符合 Security-Agent-規格書的標準接口，供 Orchestrator 調用。

        Args:
            admin_id: 管理員用戶 ID
            intent: ConfigIntent（包含 action、level、scope 等）
            context: 額外上下文（IP、User Agent、trace_id 等）

        Returns:
            SecurityCheckResult: 安全檢查結果
        """
        from datetime import datetime

        try:
            # 1. 獲取用戶角色（簡化實現，實際應該從 RBAC Service 獲取）
            # TODO: 集成 RBAC Service
            user_role = "tenant_admin"  # 暫時使用默認角色

            # 2. 權限檢查
            permission_check = await self._check_permission_for_config(admin_id, intent, user_role)
            if not permission_check.allowed:
                audit_context = {
                    "admin_id": admin_id,
                    "admin_role": user_role,
                    "intent": intent,
                    "ip": context.get("ip") if context else None,
                    "user_agent": context.get("user_agent") if context else None,
                }
                return SecurityCheckResult(
                    allowed=False,
                    reason=permission_check.reason,
                    audit_context=audit_context,
                )

            # 3. 風險評估
            risk_assessment = await self._assess_config_risk(intent, user_role)

            # 4. 構建審計上下文
            audit_context = {
                "admin_id": admin_id,
                "admin_role": user_role,
                "intent": intent,
                "risk_level": risk_assessment.risk_level,
                "ip": context.get("ip") if context else None,
                "user_agent": context.get("user_agent") if context else None,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 5. 記錄安全日誌（使用 LogService）
            trace_id = context.get("trace_id") if context else None
            if trace_id:
                try:
                    from services.api.core.log import get_log_service

                    log_service = get_log_service()
                    await log_service.log_security(
                        trace_id=trace_id,
                        actor=admin_id,
                        action="check_permission",
                        content={
                            "intent": intent,
                            "permission_check": {
                                "allowed": permission_check.allowed,
                                "user_role": user_role,
                                "reason": permission_check.reason,
                            },
                            "risk_assessment": {
                                "risk_level": risk_assessment.risk_level,
                                "requires_double_check": risk_assessment.requires_double_check,
                            },
                            "audit_context": audit_context,
                        },
                    )
                except Exception as e:
                    self._logger.warning(f"Failed to log security event: {e}")

            return SecurityCheckResult(
                allowed=True,
                reason=None,
                requires_double_check=risk_assessment.requires_double_check,
                risk_level=risk_assessment.risk_level,
                audit_context=audit_context,
            )

        except Exception as e:
            self._logger.error(f"verify_access failed: {e}", exc_info=True)
            return SecurityCheckResult(
                allowed=False,
                reason=f"Security check failed: {str(e)}",
                audit_context={
                    "admin_id": admin_id,
                    "intent": intent,
                    "error": str(e),
                },
            )

    async def _check_permission_for_config(
        self, admin_id: str, intent: Dict[str, Any], user_role: str
    ) -> PermissionCheckResult:
        """
        檢查用戶權限（針對配置操作）

        Args:
            admin_id: 管理員用戶 ID
            intent: ConfigIntent
            user_role: 用戶角色

        Returns:
            PermissionCheckResult: 權限檢查結果
        """
        action = intent.get("action")
        level = intent.get("level")

        # 1. 系統級配置：只有 system_admin 可以操作
        if level == "system":
            if user_role != "system_admin":
                return PermissionCheckResult(
                    allowed=False,
                    reason="Security Error: 權限不足，僅系統管理員可修改全域配置",
                )

        # 2. 租戶級配置：tenant_admin 只能操作自己的租戶
        elif level == "tenant":
            if user_role == "tenant_admin":
                # TODO: 獲取用戶所屬租戶（需要集成 RBAC Service）
                # user_tenant = await self._rbac_service.get_user_tenant(admin_id)
                # if tenant_id != user_tenant:
                #     return PermissionCheckResult(
                #         allowed=False,
                #         reason=f"Security Error: 無權操作其他租戶的配置（您的租戶：{user_tenant}）",
                #     )
                pass
            elif user_role != "system_admin":
                return PermissionCheckResult(
                    allowed=False,
                    reason="Security Error: 無權操作租戶級配置",
                )

        # 3. 用戶級配置：檢查用戶是否有權限操作目標用戶
        elif level == "user":
            if user_role == "tenant_admin":
                # TODO: 租戶管理員可以操作自己租戶下的用戶
                # user_tenant = await self._rbac_service.get_user_tenant(admin_id)
                # target_user_tenant = await self._rbac_service.get_user_tenant(intent.get("user_id"))
                # if user_tenant != target_user_tenant:
                #     return PermissionCheckResult(
                #         allowed=False,
                #         reason="Security Error: 無權操作其他租戶的用戶配置",
                #     )
                pass
            elif user_role not in ["system_admin", "user"]:
                return PermissionCheckResult(
                    allowed=False,
                    reason="Security Error: 無權操作用戶級配置",
                )

        # 4. 操作級別權限檢查
        if action == "delete" and user_role not in ["system_admin", "tenant_admin"]:
            return PermissionCheckResult(
                allowed=False,
                reason="Security Error: 無權執行刪除操作",
            )

        return PermissionCheckResult(allowed=True, reason=None)

    async def _assess_config_risk(
        self, intent: Dict[str, Any], user_role: str
    ) -> ConfigRiskAssessmentResult:
        """
        評估配置操作風險

        Args:
            intent: ConfigIntent
            user_role: 用戶角色

        Returns:
            ConfigRiskAssessmentResult: 風險評估結果
        """
        action = intent.get("action")
        level = intent.get("level")

        # 高風險操作：需要二次確認
        is_high_risk = (action in ["delete", "update"] and level == "system") or action == "delete"

        # 中風險操作：可選確認
        is_medium_risk = (action == "update" and level == "tenant") or action == "create"

        if is_high_risk:
            return ConfigRiskAssessmentResult(
                risk_level="high",
                requires_double_check=True,
            )
        elif is_medium_risk:
            return ConfigRiskAssessmentResult(
                risk_level="medium",
                requires_double_check=False,  # 可選，由 Orchestrator 決定
            )
        else:
            return ConfigRiskAssessmentResult(
                risk_level="low",
                requires_double_check=False,
            )
