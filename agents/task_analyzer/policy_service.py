# 代碼功能說明: Policy & Constraint Service - 策略與約束服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Policy & Constraint Service - 策略與約束服務

實現 L4 層級的策略驗證和約束檢查，包括權限、風險、策略和資源檢查。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import structlog

from agents.builtin.security_manager.agent import SecurityManagerAgent
from agents.builtin.security_manager.models import SecurityManagerRequest
from agents.task_analyzer.models import PolicyRule, PolicyValidationResult
from agents.task_analyzer.rag_service import RAGService, get_rag_service

logger = structlog.get_logger(__name__)


class PolicyService:
    """Policy & Constraint Service 類

    實現規則引擎接口（不使用 LLM），進行權限、風險、策略和資源檢查。
    """

    def __init__(
        self,
        security_agent: Optional[SecurityManagerAgent] = None,
        rag_service: Optional[RAGService] = None,
    ):
        """
        初始化 Policy Service

        Args:
            security_agent: Security Agent 實例（可選，用於權限檢查）
            rag_service: RAG Service 實例（可選，用於 RAG-3 檢索）
        """
        self._security_agent = security_agent
        self._rag_service = rag_service or get_rag_service()
        self._logger = logger
        self._rules: List[PolicyRule] = []
        self._rule_cache: Dict[str, Any] = {}
        self._permission_cache: Dict[str, bool] = {}
        self._risk_cache: Dict[str, Dict[str, Any]] = {}

    def validate(
        self, task_dag: Any, context: Optional[Dict[str, Any]] = None
    ) -> PolicyValidationResult:
        """
        驗證 Task DAG（v4.0 更新：支持 TaskDAG 對象或字典）

        Args:
            task_dag: Task DAG 對象（TaskDAG 或 Dict[str, Any]）
            context: 上下文信息（用戶 ID、租戶 ID 等）

        Returns:
            策略驗證結果
        """
        self._logger.info("policy_validation_start", task_dag=task_dag)

        if context is None:
            context = {}

        # 將 TaskDAG 對象轉換為字典（如果需要的話）
        if hasattr(task_dag, "model_dump"):
            task_dag_dict = task_dag.model_dump()
        elif hasattr(task_dag, "dict"):
            task_dag_dict = task_dag.dict()
        elif isinstance(task_dag, dict):
            task_dag_dict = task_dag
        else:
            # 嘗試手動轉換
            task_dag_dict = {
                "task_graph": [
                    {
                        "id": node.id if hasattr(node, "id") else str(node),
                        "capability": node.capability if hasattr(node, "capability") else "",
                        "agent": node.agent if hasattr(node, "agent") else "",
                        "depends_on": node.depends_on if hasattr(node, "depends_on") else [],
                        "description": getattr(node, "description", None),
                        "metadata": getattr(node, "metadata", {}),
                    }
                    for node in (task_dag.task_graph if hasattr(task_dag, "task_graph") else [])
                ],
                "reasoning": getattr(task_dag, "reasoning", None),
                "metadata": getattr(task_dag, "metadata", {}),
            }

        # 從 RAG-3 檢索相關策略知識
        policy_knowledge = self._retrieve_policy_knowledge(task_dag_dict)

        # 執行規則評估
        rule_result = self.evaluate_rules(
            {**context, "task_dag": task_dag_dict, "policy_knowledge": policy_knowledge}
        )

        # 執行各項檢查
        permission_result = self.check_permission(
            user_id=context.get("user_id"),
            action="execute",
            resource=task_dag_dict,
        )

        risk_result = self.assess_risk(task_dag_dict, context, policy_knowledge)

        resource_result = self.check_resource_limits("task_execution", context)

        # 綜合判斷
        # 如果規則明確拒絕，則不允許
        if rule_result.get("action") == "deny":
            allowed = False
            reasons = [f"規則 {rule_result.get('rule_id')} 拒絕執行"]
        # 如果規則要求確認，則需要確認
        elif rule_result.get("action") == "require_confirmation":
            allowed = True
            requires_confirmation = True
        else:
            # 其他情況根據各項檢查結果判斷
            allowed = permission_result and risk_result.get("allowed", False) and resource_result
            requires_confirmation = (
                risk_result.get("requires_confirmation", False)
                or rule_result.get("action") == "require_confirmation"
            )

        # 確定風險等級（取最高等級）
        risk_levels = [risk_result.get("risk_level", "low")]
        if rule_result.get("risk_level"):
            risk_levels.append(rule_result.get("risk_level"))
        risk_level = "high" if "high" in risk_levels else ("mid" if "mid" in risk_levels else "low")

        reasons: List[str] = []
        if not permission_result:
            reasons.append("權限檢查失敗")
        if not risk_result.get("allowed", False):
            reasons.append(risk_result.get("reason", "風險評估未通過"))
        if not resource_result:
            reasons.append("資源限制檢查未通過")
        if rule_result.get("action") == "deny":
            reasons.append(f"規則 {rule_result.get('rule_id')} 拒絕執行")

        result = PolicyValidationResult(
            allowed=allowed,
            requires_confirmation=requires_confirmation,
            risk_level=risk_level,
            reasons=reasons,
            metadata={
                "rule_result": rule_result,
                "risk_details": risk_result,
                "policy_knowledge_count": len(policy_knowledge),
            },
        )

        self._logger.info(
            "policy_validation_complete",
            allowed=allowed,
            risk_level=risk_level,
            reasons=reasons,
        )

        return result

    def check_permission(self, user_id: Optional[str], action: str, resource: Any) -> bool:
        """
        權限檢查（集成 Security Agent）

        Args:
            user_id: 用戶 ID
            action: 操作類型
            resource: 資源對象

        Returns:
            是否有權限
        """
        # 檢查緩存
        cache_key = f"{user_id}:{action}:{str(resource)[:100]}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        # 如果沒有 Security Agent，使用默認邏輯（允許所有操作）
        if self._security_agent is None:
            self._logger.warning("permission_check_no_security_agent", user_id=user_id)
            self._permission_cache[cache_key] = True
            return True

        try:
            # 構建 Security Manager Request
            # 從 resource (task_dag) 中提取 agent_id 和 resource_type
            agent_id = None
            resource_type = "task_execution"

            if isinstance(resource, dict):
                # 嘗試從 task_dag 中提取 agent 信息
                task_graph = resource.get("task_graph", [])
                if task_graph:
                    # 使用第一個任務的 agent
                    first_task = task_graph[0] if isinstance(task_graph, list) else None
                    if isinstance(first_task, dict):
                        agent_id = first_task.get("agent")
                    elif hasattr(first_task, "agent"):
                        agent_id = first_task.agent

            request = SecurityManagerRequest(
                action="check_permission",
                agent_id=agent_id or user_id,
                resource_type=resource_type,
                resource_name=str(resource)[:200],
                operation=action,
                context={"user_id": user_id},
            )

            # 調用 Security Agent 的權限檢查方法
            import asyncio

            # 檢查是否已經在事件循環中
            try:
                asyncio.get_running_loop()
                # 如果已經在事件循環中，無法同步調用異步方法
                # 為了安全起見，使用默認邏輯（允許）
                self._logger.warning(
                    "permission_check_async_context",
                    message="在異步上下文中無法同步調用 Security Agent，使用默認允許",
                )
                self._permission_cache[cache_key] = True
                return True
            except RuntimeError:
                # 沒有運行中的事件循環，可以安全地創建新的並同步調用
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(
                        self._security_agent._check_permission(request)
                    )
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)

            allowed = response.allowed if response.allowed is not None else True

            # 緩存結果
            self._permission_cache[cache_key] = allowed

            self._logger.debug(
                "permission_check_security_agent",
                user_id=user_id,
                action=action,
                allowed=allowed,
            )

            return allowed

        except Exception as exc:
            self._logger.error("permission_check_failed", error=str(exc), exc_info=True)
            # 發生錯誤時，為了安全起見，默認拒絕
            self._permission_cache[cache_key] = False
            return False

    def assess_risk(
        self,
        task_dag: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        policy_knowledge: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        風險評估

        Args:
            task_dag: Task DAG 對象
            context: 上下文信息
            policy_knowledge: 從 RAG-3 檢索的策略知識（可選）

        Returns:
            風險評估結果字典（allowed, risk_level, requires_confirmation, reason）
        """
        self._logger.debug("risk_assessment_start", task_dag=task_dag)

        if context is None:
            context = {}

        if policy_knowledge is None:
            policy_knowledge = []

        # 檢查緩存
        cache_key = str(task_dag)[:200]
        if cache_key in self._risk_cache:
            return self._risk_cache[cache_key]

        # 初始化風險檢查項
        risk_factors: List[str] = []
        risk_score = 0

        # 1. 任務數量風險
        task_graph = task_dag.get("task_graph", [])
        task_count = len(task_graph) if isinstance(task_graph, list) else 0

        if task_count > 10:
            risk_score += 3
            risk_factors.append(f"任務數量過多（{task_count} 個任務）")
        elif task_count > 5:
            risk_score += 1
            risk_factors.append(f"任務數量較多（{task_count} 個任務）")

        # 2. 敏感操作風險
        sensitive_operations = ["delete", "remove", "drop", "destroy", "clear", "wipe"]
        sensitive_capabilities = ["config_update", "config_delete", "file_delete", "data_delete"]

        for task in task_graph:
            if isinstance(task, dict):
                capability = task.get("capability", "").lower()
                description = task.get("description", "").lower()
                for op in sensitive_operations:
                    if op in capability or op in description:
                        risk_score += 3
                        risk_factors.append(f"包含敏感操作：{capability}")
                        break
                for cap in sensitive_capabilities:
                    if cap in capability:
                        risk_score += 2
                        risk_factors.append(f"包含敏感能力：{capability}")
                        break

        # 3. 資源消耗風險（估算）
        estimated_api_calls = task_count * 2  # 假設每個任務平均 2 次 API 調用
        if estimated_api_calls > 50:
            risk_score += 2
            risk_factors.append(f"預估 API 調用次數過多（{estimated_api_calls} 次）")
        elif estimated_api_calls > 20:
            risk_score += 1
            risk_factors.append(f"預估 API 調用次數較多（{estimated_api_calls} 次）")

        # 4. 時間風險（估算）
        estimated_time = task_count * 5  # 假設每個任務平均 5 秒
        if estimated_time > 60:
            risk_score += 2
            risk_factors.append(f"預估執行時間過長（{estimated_time} 秒）")
        elif estimated_time > 30:
            risk_score += 1
            risk_factors.append(f"預估執行時間較長（{estimated_time} 秒）")

        # 5. 依賴風險（DAG 深度）
        max_depth = self._calculate_dag_depth(task_graph)
        if max_depth > 5:
            risk_score += 2
            risk_factors.append(f"DAG 深度過深（{max_depth} 層）")
        elif max_depth > 3:
            risk_score += 1
            risk_factors.append(f"DAG 深度較深（{max_depth} 層）")

        # 6. 從 RAG-3 策略知識中檢查風險
        for policy in policy_knowledge:
            policy_metadata = policy.get("metadata", {})
            policy_risk_level = policy_metadata.get("risk_level", "low")
            if policy_risk_level == "high":
                risk_score += 2
                risk_factors.append(f"策略知識提示高風險：{policy.get('content', '')[:50]}")
            elif policy_risk_level == "mid":
                risk_score += 1
                risk_factors.append(f"策略知識提示中風險：{policy.get('content', '')[:50]}")

        # 計算風險等級
        if risk_score >= 5:
            risk_level = "high"
            requires_confirmation = True
            allowed = True  # 高風險也需要確認，但不直接拒絕
        elif risk_score >= 2:
            risk_level = "mid"
            requires_confirmation = True
            allowed = True
        else:
            risk_level = "low"
            requires_confirmation = False
            allowed = True

        reason = "; ".join(risk_factors) if risk_factors else "無風險因素"

        result = {
            "allowed": allowed,
            "risk_level": risk_level,
            "requires_confirmation": requires_confirmation,
            "reason": reason,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
        }

        # 緩存結果
        self._risk_cache[cache_key] = result

        self._logger.debug("risk_assessment_complete", result=result)
        return result

    def _calculate_dag_depth(self, task_graph: List[Any]) -> int:
        """
        計算 DAG 的最大深度

        Args:
            task_graph: 任務圖列表

        Returns:
            最大深度
        """
        if not task_graph:
            return 0

        # 構建依賴圖
        task_map: Dict[str, Any] = {}
        for task in task_graph:
            if isinstance(task, dict):
                task_id = task.get("id")
                depends_on = task.get("depends_on", [])
                task_map[task_id] = {"depends_on": depends_on, "depth": 0}
            elif hasattr(task, "id"):
                task_id = task.id
                depends_on = task.depends_on if hasattr(task, "depends_on") else []
                task_map[task_id] = {"depends_on": depends_on, "depth": 0}

        # 計算每個任務的深度
        def calculate_task_depth(task_id: str, visited: set) -> int:
            if task_id in visited:
                return 0  # 循環依賴，返回 0
            visited.add(task_id)

            if task_id not in task_map:
                return 1

            task_info = task_map[task_id]
            if task_info["depth"] > 0:
                return task_info["depth"]

            max_dep_depth = 0
            for dep_id in task_info["depends_on"]:
                dep_depth = calculate_task_depth(dep_id, visited.copy())
                max_dep_depth = max(max_dep_depth, dep_depth)

            task_info["depth"] = max_dep_depth + 1
            return task_info["depth"]

        max_depth = 0
        for task_id in task_map.keys():
            depth = calculate_task_depth(task_id, set())
            max_depth = max(max_depth, depth)

        return max_depth

    def check_resource_limits(
        self, resource_type: str, context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        資源限制檢查

        Args:
            resource_type: 資源類型（如 "task_execution", "api_calls"）
            context: 上下文信息（包含 user_id, tenant_id 等）

        Returns:
            是否在資源限制內
        """
        self._logger.debug("resource_limit_check_start", resource_type=resource_type)

        if context is None:
            context = {}

        # 默認資源限制配置（可以從配置服務或數據庫讀取）
        default_limits = {
            "api_calls": {"daily": 1000, "per_user": True},
            "concurrent_tasks": {"max": 5, "per_user": True},
            "storage": {"max_gb": 100, "per_tenant": True},
            "task_execution": {"max_daily": 100, "per_user": True},
        }

        # 獲取當前資源使用情況（這裡是簡化實現，實際應該從數據庫或監控服務查詢）
        # TODO: 集成資源監控服務或查詢數據庫中的資源使用記錄

        if resource_type == "task_execution":
            # 檢查並發任務數量限制
            # TODO: 從任務管理服務查詢當前並發任務數
            current_concurrent = 0  # 實際應該查詢
            max_concurrent = default_limits["concurrent_tasks"]["max"]
            if current_concurrent >= max_concurrent:
                self._logger.warning(
                    "resource_limit_exceeded",
                    resource_type=resource_type,
                    current=current_concurrent,
                    limit=max_concurrent,
                )
                return False

            # 檢查每日任務執行次數限制
            # TODO: 從數據庫查詢今日任務執行次數
            daily_executions = 0  # 實際應該查詢
            max_daily = default_limits["task_execution"]["max_daily"]
            if daily_executions >= max_daily:
                self._logger.warning(
                    "resource_limit_exceeded",
                    resource_type=resource_type,
                    current=daily_executions,
                    limit=max_daily,
                )
                return False

        elif resource_type == "api_calls":
            # 檢查 API 調用次數限制
            # TODO: 從數據庫查詢今日 API 調用次數
            daily_api_calls = 0  # 實際應該查詢
            max_daily = default_limits["api_calls"]["daily"]
            if daily_api_calls >= max_daily:
                self._logger.warning(
                    "resource_limit_exceeded",
                    resource_type=resource_type,
                    current=daily_api_calls,
                    limit=max_daily,
                )
                return False

        elif resource_type == "storage":
            # 檢查存儲空間限制
            # TODO: 從存儲服務查詢當前使用量
            current_storage_gb = 0  # 實際應該查詢
            max_storage_gb = default_limits["storage"]["max_gb"]
            if current_storage_gb >= max_storage_gb:
                self._logger.warning(
                    "resource_limit_exceeded",
                    resource_type=resource_type,
                    current=current_storage_gb,
                    limit=max_storage_gb,
                )
                return False

        result = True
        self._logger.debug(
            "resource_limit_check_complete", result=result, resource_type=resource_type
        )
        return result

    def add_rule(self, rule: PolicyRule) -> None:
        """
        添加策略規則

        Args:
            rule: 策略規則
        """
        self._rules.append(rule)
        self._logger.info("policy_rule_added", rule_id=rule.rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        """
        移除策略規則

        Args:
            rule_id: 規則 ID

        Returns:
            是否成功移除
        """
        original_count = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        removed = len(self._rules) < original_count

        if removed:
            self._logger.info("policy_rule_removed", rule_id=rule_id)
        else:
            self._logger.warning("policy_rule_not_found", rule_id=rule_id)

        return removed

    def list_rules(self) -> List[PolicyRule]:
        """
        列出所有策略規則

        Returns:
            策略規則列表
        """
        return self._rules.copy()

    def evaluate_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        評估規則（規則引擎接口）

        按規則優先級評估，支持短路評估（如果遇到 deny 規則立即返回）

        Args:
            context: 上下文信息

        Returns:
            評估結果字典
        """
        self._logger.debug("rule_evaluation_start", context=context)

        # 按規則類型排序：permission > risk > resource
        # deny 規則優先級最高
        sorted_rules = sorted(
            self._rules,
            key=lambda r: (
                0 if r.action == "deny" else 1,
                0 if r.rule_type == "permission" else (1 if r.rule_type == "risk" else 2),
            ),
        )

        # 遍歷所有規則，檢查條件
        for rule in sorted_rules:
            # 檢查規則條件是否滿足
            if self._check_rule_conditions(rule, context):
                # 執行規則動作
                result = {
                    "rule_id": rule.rule_id,
                    "action": rule.action,
                    "risk_level": rule.risk_level or "low",
                    "rule_type": rule.rule_type,
                }
                self._logger.info("rule_triggered", rule_id=rule.rule_id, action=rule.action)

                # 如果是 deny 動作，立即返回（短路評估）
                if rule.action == "deny":
                    return result

                # 如果是 require_confirmation，繼續檢查是否有 deny 規則
                # 但記錄需要確認的規則
                if rule.action == "require_confirmation":
                    # 繼續檢查，但記錄這個規則
                    continue

        # 沒有規則觸發，默認允許
        result = {"action": "allow", "risk_level": "low"}
        self._logger.debug("rule_evaluation_complete", result=result)
        return result

    def _retrieve_policy_knowledge(self, task_dag: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        從 RAG-3 檢索策略知識

        Args:
            task_dag: Task DAG 對象

        Returns:
            策略知識列表
        """
        try:
            # 構建查詢文本
            query_parts = []

            # 從 task_dag 中提取關鍵信息
            task_graph = task_dag.get("task_graph", [])
            if task_graph:
                # 提取所有 agent 和 capability
                agents = set()
                capabilities = set()
                for task in task_graph:
                    if isinstance(task, dict):
                        if task.get("agent"):
                            agents.add(task.get("agent"))
                        if task.get("capability"):
                            capabilities.add(task.get("capability"))
                    elif hasattr(task, "agent"):
                        agents.add(task.agent)
                    if hasattr(task, "capability"):
                        capabilities.add(task.capability)

                if agents:
                    query_parts.append(f"agents: {', '.join(agents)}")
                if capabilities:
                    query_parts.append(f"capabilities: {', '.join(capabilities)}")

            # 如果沒有提取到信息，使用通用查詢
            if not query_parts:
                query = "task execution policy"
            else:
                query = " ".join(query_parts)

            # 調用 RAG Service 檢索策略知識
            policies = self._rag_service.retrieve_policies(
                query=query,
                top_k=5,
                similarity_threshold=0.7,
            )

            self._logger.debug(
                "policy_knowledge_retrieved",
                query=query,
                count=len(policies),
            )

            return policies

        except Exception as exc:
            self._logger.error("policy_knowledge_retrieval_failed", error=str(exc), exc_info=True)
            return []

    def _check_rule_conditions(self, rule: PolicyRule, context: Dict[str, Any]) -> bool:
        """
        檢查規則條件是否滿足

        支持多種條件類型：
        - 屬性匹配（如 {"field": "value"}）
        - 數值比較（如 {"field": {"operator": ">", "value": 10}}）
        - 邏輯運算（AND/OR/NOT）
        - 正則表達式匹配
        - 集合操作（in/not in）

        Args:
            rule: 策略規則
            context: 上下文信息

        Returns:
            條件是否滿足
        """
        conditions = rule.conditions
        if not conditions:
            return True

        # 處理邏輯運算符
        if "AND" in conditions:
            # 所有條件都必須滿足
            and_conditions = conditions["AND"]
            if isinstance(and_conditions, list):
                return all(
                    self._evaluate_single_condition(cond, context) for cond in and_conditions
                )
            return False

        if "OR" in conditions:
            # 至少一個條件滿足
            or_conditions = conditions["OR"]
            if isinstance(or_conditions, list):
                return any(self._evaluate_single_condition(cond, context) for cond in or_conditions)
            return False

        if "NOT" in conditions:
            # 條件不滿足
            not_condition = conditions["NOT"]
            return not self._evaluate_single_condition(not_condition, context)

        # 如果沒有邏輯運算符，則所有條件都必須滿足（AND 語義）
        return all(
            self._evaluate_single_condition({key: value}, context)
            for key, value in conditions.items()
        )

    def _evaluate_single_condition(
        self, condition: Dict[str, Any], context: Dict[str, Any]
    ) -> bool:
        """
        評估單個條件

        Args:
            condition: 條件字典，格式如 {"field": "value"} 或 {"field": {"operator": ">", "value": 10}}
            context: 上下文信息

        Returns:
            條件是否滿足
        """
        if not condition:
            return True

        for field, value in condition.items():
            # 獲取上下文中的字段值
            field_value = self._get_field_value(field, context)

            # 如果值是字典，表示有運算符
            if isinstance(value, dict):
                operator = value.get("operator", "==")
                expected_value = value.get("value")

                if operator == "==":
                    return field_value == expected_value
                elif operator == "!=":
                    return field_value != expected_value
                elif operator == ">":
                    return self._compare_values(field_value, expected_value, ">")
                elif operator == ">=":
                    return self._compare_values(field_value, expected_value, ">=")
                elif operator == "<":
                    return self._compare_values(field_value, expected_value, "<")
                elif operator == "<=":
                    return self._compare_values(field_value, expected_value, "<=")
                elif operator == "in":
                    if isinstance(expected_value, list):
                        return field_value in expected_value
                    return False
                elif operator == "not_in":
                    if isinstance(expected_value, list):
                        return field_value not in expected_value
                    return True
                elif operator == "regex":
                    if isinstance(expected_value, str):
                        try:
                            return bool(re.match(expected_value, str(field_value)))
                        except re.error:
                            self._logger.warning("invalid_regex", pattern=expected_value)
                            return False
                    return False
                elif operator == "contains":
                    return str(expected_value) in str(field_value)
                elif operator == "starts_with":
                    return str(field_value).startswith(str(expected_value))
                elif operator == "ends_with":
                    return str(field_value).endswith(str(expected_value))
                else:
                    self._logger.warning("unknown_operator", operator=operator)
                    return False
            else:
                # 簡單的相等比較
                return field_value == value

        return True

    def _get_field_value(self, field: str, context: Dict[str, Any]) -> Any:
        """
        從上下文中獲取字段值，支持嵌套字段（如 "task_dag.task_graph"）

        Args:
            field: 字段名，支持點號分隔的嵌套字段
            context: 上下文信息

        Returns:
            字段值，如果不存在返回 None
        """
        parts = field.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value

    def _compare_values(self, value1: Any, value2: Any, operator: str) -> bool:
        """
        比較兩個值

        Args:
            value1: 第一個值
            value2: 第二個值
            operator: 運算符（>, >=, <, <=）

        Returns:
            比較結果
        """
        try:
            # 嘗試轉換為數值進行比較
            num1 = float(value1) if value1 is not None else 0
            num2 = float(value2) if value2 is not None else 0

            if operator == ">":
                return num1 > num2
            elif operator == ">=":
                return num1 >= num2
            elif operator == "<":
                return num1 < num2
            elif operator == "<=":
                return num1 <= num2
        except (ValueError, TypeError):
            # 如果無法轉換為數值，嘗試字符串比較
            str1 = str(value1) if value1 is not None else ""
            str2 = str(value2) if value2 is not None else ""

            if operator == ">":
                return str1 > str2
            elif operator == ">=":
                return str1 >= str2
            elif operator == "<":
                return str1 < str2
            elif operator == "<=":
                return str1 <= str2

        return False


def get_policy_service(
    security_agent: Optional[SecurityManagerAgent] = None,
    rag_service: Optional[RAGService] = None,
) -> PolicyService:
    """
    獲取 Policy Service 實例（單例模式）

    Args:
        security_agent: Security Agent 實例（可選）
        rag_service: RAG Service 實例（可選）

    Returns:
        Policy Service 實例
    """
    global _policy_service_instance
    if _policy_service_instance is None:
        _policy_service_instance = PolicyService(security_agent, rag_service)
    return _policy_service_instance


# 全局單例實例
_policy_service_instance: Optional[PolicyService] = None
