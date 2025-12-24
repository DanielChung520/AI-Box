# 代碼功能說明: Config Inspection Service - 配置巡檢服務
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Config Inspection Service - 提供主動式配置巡檢功能"""

import logging
from typing import Any, Dict, List, Optional

from services.api.models.config import ConfigModel
from services.api.services.config_store_service import ConfigStoreService, get_config_store_service

from .models import FixSuggestion, InspectionIssue

logger = logging.getLogger(__name__)


class ConfigInspectionService:
    """配置巡檢服務 - 主動檢測配置問題"""

    def __init__(self):
        """初始化配置巡檢服務"""
        self._config_service: ConfigStoreService = get_config_store_service()
        self._logger = logger

    async def inspect_all_configs(
        self,
        scope: Optional[str] = None,
        tenant_id: Optional[str] = None,
        check_convergence: bool = True,
        check_consistency: bool = True,
        check_security: bool = True,
    ) -> List[InspectionIssue]:
        """
        巡檢所有配置，發現問題

        Args:
            scope: 配置範圍（如果指定，只檢查該範圍的配置）
            tenant_id: 租戶 ID（如果指定，只檢查該租戶的配置）
            check_convergence: 是否檢查收斂規則違反
            check_consistency: 是否檢查配置一致性
            check_security: 是否檢查安全策略違規

        Returns:
            List[InspectionIssue]: 發現的問題列表
        """
        issues: List[InspectionIssue] = []

        try:
            # 1. 檢查收斂規則違反
            if check_convergence:
                convergence_issues = await self._check_convergence_rules(scope, tenant_id)
                issues.extend(convergence_issues)

            # 2. 檢查配置不一致
            if check_consistency:
                consistency_issues = await self._check_consistency(scope, tenant_id)
                issues.extend(consistency_issues)

            # 3. 檢查安全策略違規
            if check_security:
                security_issues = await self._check_security_policies(scope, tenant_id)
                issues.extend(security_issues)

            return issues

        except Exception as e:
            self._logger.error(f"Config inspection failed: {e}", exc_info=True)
            # 返回一個錯誤類型的問題
            issues.append(
                InspectionIssue(
                    issue_type="system_error",
                    severity="high",
                    scope=scope or "all",
                    description=f"Inspection failed: {str(e)}",
                )
            )
            return issues

    async def suggest_fix(self, issue: InspectionIssue) -> FixSuggestion:
        """
        為問題生成修復建議

        Args:
            issue: 發現的問題

        Returns:
            FixSuggestion: 修復建議（包含自動修復方案）
        """
        try:
            if issue.issue_type == "convergence":
                return await self._suggest_convergence_fix(issue)
            elif issue.issue_type == "consistency":
                return await self._suggest_consistency_fix(issue)
            elif issue.issue_type == "security":
                return await self._suggest_security_fix(issue)
            else:
                return FixSuggestion(
                    issue_id=None,
                    auto_fixable=False,
                    fix_action="Manual review required",
                    fix_steps=["Review the issue description", "Apply appropriate fix"],
                )

        except Exception as e:
            self._logger.error(f"Failed to generate fix suggestion: {e}", exc_info=True)
            return FixSuggestion(
                issue_id=None,
                auto_fixable=False,
                fix_action="Error generating fix suggestion",
                fix_steps=["Contact administrator"],
            )

    async def _check_convergence_rules(
        self, scope: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> List[InspectionIssue]:
        """檢查收斂規則違反"""
        issues: List[InspectionIssue] = []

        try:
            # 獲取所有 tenant 配置（通過 AQL 查詢）
            if (
                self._config_service._client.db is None
                or self._config_service._client.db.aql is None
            ):
                self._logger.warning("ArangoDB client is not connected or AQL is not available")
                return issues

            # 構建 AQL 查詢
            aql = """
                FOR doc IN tenant_configs
                    FILTER doc.is_active == true
            """
            bind_vars: Dict[str, Any] = {}

            if scope:
                aql += " AND doc.scope == @scope"
                bind_vars["scope"] = scope

            if tenant_id:
                aql += " AND doc.tenant_id == @tenant_id"
                bind_vars["tenant_id"] = tenant_id

            aql += " RETURN doc"

            cursor = self._config_service._client.db.aql.execute(aql, bind_vars=bind_vars)
            tenant_configs = [doc for doc in cursor]

            # 對每個 tenant 配置檢查收斂規則
            for tenant_doc in tenant_configs:
                tenant_config = ConfigModel(
                    id=tenant_doc.get("_key"),
                    scope=tenant_doc.get("scope"),
                    tenant_id=tenant_doc.get("tenant_id"),
                    config_data=tenant_doc.get("config_data", {}),
                    is_active=tenant_doc.get("is_active", True),
                )

                # 獲取對應的 system 配置
                system_config = self._config_service.get_config(
                    tenant_config.scope, tenant_id=None, user_id=None
                )
                if not system_config:
                    continue

                system_data = system_config.config_data
                tenant_data = tenant_config.config_data

                # 檢查 allowed_providers
                sys_providers = set(
                    str(p).strip().lower() for p in system_data.get("allowed_providers", [])
                )
                tenant_providers = set(
                    str(p).strip().lower() for p in tenant_data.get("allowed_providers", [])
                )
                if tenant_providers - sys_providers:
                    diff = tenant_providers - sys_providers
                    issues.append(
                        InspectionIssue(
                            issue_type="convergence",
                            severity="high",
                            scope=tenant_config.scope,
                            level="tenant",
                            tenant_id=tenant_config.tenant_id,
                            description=f"Tenant {tenant_config.tenant_id} 的 allowed_providers 包含系統級不允許的提供商: {', '.join(diff)}",
                            affected_field="allowed_providers",
                            current_value=list(tenant_providers),
                            expected_value=list(sys_providers),
                            impact="可能導致 API 調用失敗",
                            details={"violated_providers": list(diff)},
                        )
                    )

                # 檢查 allowed_models
                sys_models = system_data.get("allowed_models", {})
                tenant_models = tenant_data.get("allowed_models", {})
                if isinstance(sys_models, dict) and isinstance(tenant_models, dict):
                    for prov, patterns in tenant_models.items():
                        prov_key = str(prov).strip().lower()
                        sys_patterns = sys_models.get(prov_key, [])
                        tenant_patterns_list = patterns if isinstance(patterns, list) else []

                        for pattern in tenant_patterns_list:
                            if not self._pattern_is_subset_of_any(str(pattern), sys_patterns):
                                issues.append(
                                    InspectionIssue(
                                        issue_type="convergence",
                                        severity="high",
                                        scope=tenant_config.scope,
                                        level="tenant",
                                        tenant_id=tenant_config.tenant_id,
                                        description=f"Tenant {tenant_config.tenant_id} 的模型模式 '{pattern}' (provider: {prov}) 不被系統級配置允許",
                                        affected_field=f"allowed_models.{prov}",
                                        current_value=pattern,
                                        expected_value=f"Must be subset of {sys_patterns}",
                                        impact="可能導致模型調用失敗",
                                        details={"provider": prov, "pattern": pattern},
                                    )
                                )

        except Exception as e:
            self._logger.error(f"Convergence rule check failed: {e}", exc_info=True)

        return issues

    async def _check_consistency(
        self, scope: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> List[InspectionIssue]:
        """檢查配置不一致"""
        issues: List[InspectionIssue] = []

        try:
            # 這裡可以實現配置一致性檢查邏輯
            # 例如：檢查配置字段的完整性、檢查必需的配置項是否存在等

            # 示例：檢查是否有配置缺少必需的字段
            if (
                self._config_service._client.db is None
                or self._config_service._client.db.aql is None
            ):
                self._logger.warning("ArangoDB client is not connected or AQL is not available")
                return issues

            # 檢查所有配置的完整性
            aql = """
                FOR doc IN system_configs
                    FILTER doc.is_active == true
            """
            bind_vars: Dict[str, Any] = {}

            if scope:
                aql += " AND doc.scope == @scope"
                bind_vars["scope"] = scope

            aql += " RETURN doc"

            cursor = self._config_service._client.db.aql.execute(aql, bind_vars=bind_vars)
            system_configs = [doc for doc in cursor]

            for doc in system_configs:
                config_data = doc.get("config_data", {})
                # 檢查 genai.policy 配置是否缺少必需字段
                if doc.get("scope") == "genai.policy":
                    if "allowed_providers" not in config_data or not config_data.get(
                        "allowed_providers"
                    ):
                        issues.append(
                            InspectionIssue(
                                issue_type="consistency",
                                severity="medium",
                                scope=doc.get("scope"),
                                level="system",
                                description=f"系統配置 {doc.get('scope')} 缺少必需字段 'allowed_providers'",
                                affected_field="allowed_providers",
                                current_value=None,
                                expected_value="非空列表",
                                impact="可能導致 LLM Router 無法正常工作",
                            )
                        )

        except Exception as e:
            self._logger.error(f"Consistency check failed: {e}", exc_info=True)

        return issues

    async def _check_security_policies(
        self, scope: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> List[InspectionIssue]:
        """檢查安全策略違規"""
        issues: List[InspectionIssue] = []

        try:
            # 這裡可以實現安全策略檢查邏輯
            # 例如：檢查 API Key 是否已加密、檢查敏感配置是否暴露等

            # 示例：檢查配置中是否包含明文敏感信息
            if (
                self._config_service._client.db is None
                or self._config_service._client.db.aql is None
            ):
                self._logger.warning("ArangoDB client is not connected or AQL is not available")
                return issues

            aql = """
                FOR doc IN tenant_configs
                    FILTER doc.is_active == true
            """
            bind_vars: Dict[str, Any] = {}

            if scope:
                aql += " AND doc.scope == @scope"
                bind_vars["scope"] = scope

            if tenant_id:
                aql += " AND doc.tenant_id == @tenant_id"
                bind_vars["tenant_id"] = tenant_id

            aql += " RETURN doc"

            cursor = self._config_service._client.db.aql.execute(aql, bind_vars=bind_vars)
            configs = [doc for doc in cursor]

            for doc in configs:
                config_data = doc.get("config_data", {})
                # 檢查是否包含明文 API Key（簡單檢查，實際應該檢查加密狀態）
                for key, value in config_data.items():
                    if "key" in key.lower() or "secret" in key.lower():
                        if isinstance(value, str) and len(value) > 20:
                            # 簡單檢查：如果看起來像 API Key，記錄警告
                            issues.append(
                                InspectionIssue(
                                    issue_type="security",
                                    severity="high",
                                    scope=doc.get("scope"),
                                    level="tenant",
                                    tenant_id=doc.get("tenant_id"),
                                    description=f"配置中包含可能的明文敏感信息字段: {key}",
                                    affected_field=key,
                                    impact="敏感信息可能暴露",
                                    details={"field": key},
                                )
                            )

        except Exception as e:
            self._logger.error(f"Security policy check failed: {e}", exc_info=True)

        return issues

    async def _suggest_convergence_fix(self, issue: InspectionIssue) -> FixSuggestion:
        """為收斂規則違反生成修復建議"""
        if issue.affected_field == "allowed_providers" and issue.tenant_id:
            # 自動修復：從 tenant 配置中移除不在 system 配置中的 providers
            # 計算應該保留的 providers（交集）
            if isinstance(issue.current_value, set):
                current_set = issue.current_value
            elif isinstance(issue.current_value, list):
                current_set = set(str(p).strip().lower() for p in issue.current_value)
            else:
                current_set = set()

            if isinstance(issue.expected_value, set):
                expected_set = issue.expected_value
            elif isinstance(issue.expected_value, list):
                expected_set = set(str(p).strip().lower() for p in issue.expected_value)
            else:
                expected_set = set()

            fixed_providers = list(current_set & expected_set)

            return FixSuggestion(
                issue_id=None,
                auto_fixable=True,
                fix_action=f"從 {issue.tenant_id} 的 allowed_providers 中移除不在系統級配置中的提供商",
                fix_steps=[
                    f"獲取租戶 {issue.tenant_id} 的當前配置",
                    "計算與系統級配置的交集",
                    "更新租戶配置的 allowed_providers 字段",
                    "保存配置變更",
                ],
                suggested_config={"allowed_providers": fixed_providers},
                risk_level="low",
                requires_confirmation=True,
            )

        return FixSuggestion(
            issue_id=None,
            auto_fixable=False,
            fix_action="需要手動審查和修復",
            fix_steps=["審查問題描述", "根據業務需求決定修復方案"],
            risk_level="medium",
        )

    async def _suggest_consistency_fix(self, issue: InspectionIssue) -> FixSuggestion:
        """為配置不一致生成修復建議"""
        if issue.affected_field and issue.expected_value:
            return FixSuggestion(
                issue_id=None,
                auto_fixable=True,
                fix_action=f"添加缺失的配置字段: {issue.affected_field}",
                fix_steps=[
                    "獲取當前配置",
                    f"設置 {issue.affected_field} 為: {issue.expected_value}",
                    "保存配置變更",
                ],
                suggested_config={issue.affected_field: issue.expected_value},
                risk_level="low",
                requires_confirmation=True,
            )

        return FixSuggestion(
            issue_id=None,
            auto_fixable=False,
            fix_action="需要手動審查和修復",
            fix_steps=["審查問題描述", "根據業務需求決定修復方案"],
        )

    async def _suggest_security_fix(self, issue: InspectionIssue) -> FixSuggestion:
        """為安全策略違規生成修復建議"""
        return FixSuggestion(
            issue_id=None,
            auto_fixable=False,
            fix_action="需要手動審查和修復敏感信息",
            fix_steps=[
                "審查配置中的敏感信息字段",
                "確認是否需要加密或移除",
                "應用適當的安全措施",
            ],
            risk_level="high",
            requires_confirmation=True,
        )

    def _pattern_is_subset_of_any(self, pattern: str, supersets: List[str]) -> bool:
        """判斷 pattern 是否不會擴權（是否被 system pattern 覆蓋）"""
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
                # system: gpt-* 覆蓋 tenant: gpt-4o / gpt-4* / gpt-4o-mini
                if p.startswith(sp[:-1]):
                    return True
            else:
                # system exact
                if p == sp:
                    return True
        return False
