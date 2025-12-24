# 代碼功能說明: Agent Orchestrator 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Agent Orchestrator - 實現 Agent 協調、調度、任務分發和結果聚合

使用 AgentRegistry 管理 Agent，支持內部/外部 Agent 統一調度。
"""

import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.services.protocol.base import AgentServiceRequest, AgentServiceResponse
from agents.services.registry.discovery import AgentDiscovery

# AgentStatus 已移至 agents.services.registry.models
from agents.services.registry.models import (
    AgentStatus,  # type: ignore[attr-defined]  # 從 registry.models 導入
)
from agents.services.registry.registry import get_agent_registry

from .models import AgentRegistryInfo, TaskRequest, TaskResult, TaskStatus, ValidationResult

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 協調器

    使用 AgentRegistry 管理 Agent，支持內部/外部 Agent 統一調度。
    """

    def __init__(self, registry: Optional[Any] = None):
        """
        初始化 Agent 協調器

        Args:
            registry: AgentRegistry 實例（可選，默認使用全局實例）
        """
        self._registry = registry or get_agent_registry()
        self._discovery = AgentDiscovery(registry=self._registry)
        self._tasks: Dict[str, TaskRequest] = {}
        self._task_results: Dict[str, TaskResult] = {}
        self._task_queue: deque = deque()
        self._agent_loads: Dict[str, int] = {}  # Agent 負載計數（從 Registry 獲取）
        # ⭐ 日誌查詢功能：集成 Task Analyzer 和 LogService（懶加載以避免循環導入）
        self._task_analyzer: Optional[Any] = None
        self._log_service: Optional[Any] = None
        # ⭐ 配置元數據機制：集成 DefinitionLoader（懶加載以避免循環導入）
        self._definition_loader: Optional[Any] = None
        # ⭐ Security Agent：集成 Security Manager Agent（懶加載以避免循環導入）
        self._security_agent: Optional[Any] = None
        # ⭐ Task Tracker：任務追蹤器
        from agents.services.orchestrator.task_tracker import TaskTracker

        self._task_tracker = TaskTracker()

    def get_agent(self, agent_id: str) -> Optional[AgentRegistryInfo]:
        """
        獲取 Agent 信息（從 Registry）

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，如果不存在則返回 None
        """
        return self._registry.get_agent_info(agent_id)

    def list_agents(
        self,
        agent_type: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[AgentRegistryInfo]:
        """
        列出 Agent（從 Registry）

        Args:
            agent_type: Agent 類型過濾器
            status: Agent 狀態過濾器

        Returns:
            Agent 列表
        """
        return self._discovery.discover_agents(agent_type=agent_type, status=status)

    def discover_agents(
        self,
        required_capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
    ) -> List[AgentRegistryInfo]:
        """
        發現可用的 Agent（從 Registry）

        Args:
            required_capabilities: 需要的能力列表
            agent_type: Agent 類型過濾器

        Returns:
            匹配的 Agent 列表
        """
        return self._discovery.discover_agents(
            required_capabilities=required_capabilities,
            agent_type=agent_type,
            status=AgentStatus.ONLINE,  # 使用 ONLINE 狀態（對應原來的 IDLE）
        )

    def submit_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        required_agents: Optional[List[str]] = None,
        priority: int = 0,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        提交任務

        Args:
            task_type: 任務類型
            task_data: 任務數據
            required_agents: 需要的Agent列表
            priority: 優先級
            timeout: 超時時間（秒）
            metadata: 元數據

        Returns:
            任務ID
        """
        task_id = str(uuid.uuid4())

        task_request = TaskRequest(
            task_id=task_id,
            task_type=task_type,
            task_data=task_data,
            required_agents=required_agents,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {},
        )

        self._tasks[task_id] = task_request
        self._task_queue.append((priority, task_id))

        logger.info(f"Submitted task: {task_id} (type: {task_type})")

        # 嘗試立即分配任務
        self._try_assign_tasks()

        return task_id

    def _try_assign_tasks(self):
        """嘗試分配任務"""
        # 按優先級排序任務隊列
        self._task_queue = deque(sorted(self._task_queue, key=lambda x: x[0], reverse=True))

        for priority, task_id in list(self._task_queue):
            task_request = self._tasks.get(task_id)
            if not task_request:
                continue

            # 檢查任務是否已經分配
            if task_id in self._task_results:
                result = self._task_results[task_id]
                if result.status in [TaskStatus.ASSIGNED, TaskStatus.RUNNING]:
                    continue

            # 尋找合適的 Agent
            agent = self._select_agent(task_request)

            if agent:
                # 分配任務
                self._assign_task(task_id, agent.agent_id)
                self._task_queue.remove((priority, task_id))

    def _select_agent(self, task_request: TaskRequest) -> Optional[AgentRegistryInfo]:
        """
        選擇合適的 Agent（優先選擇內部 Agent）

        Args:
            task_request: 任務請求

        Returns:
            選中的 Agent，如果沒有合適的則返回 None
        """
        # 如果指定了需要的 Agent
        if task_request.required_agents:
            for agent_id in task_request.required_agents:
                agent_info = self._registry.get_agent_info(agent_id)
                if agent_info and agent_info.status == AgentStatus.ONLINE:
                    return agent_info
            return None

        # 根據任務類型選擇 Agent
        agent_type_mapping = {
            "planning": "planning",
            "execution": "execution",
            "review": "review",
        }

        preferred_type = agent_type_mapping.get(task_request.task_type)

        # 發現可用的 Agent
        available_agents = self.discover_agents(agent_type=preferred_type)

        if not available_agents:
            return None

        # 優先選擇內部 Agent（性能更好）
        internal_agents = [agent for agent in available_agents if agent.endpoints.is_internal]
        if internal_agents:
            available_agents = internal_agents

        # 選擇負載最低的 Agent（從 Registry 獲取負載信息）
        selected_agent = min(
            available_agents,
            key=lambda a: self._agent_loads.get(a.agent_id, a.load),
        )

        return selected_agent

    def _assign_task(self, task_id: str, agent_id: str) -> bool:
        """
        分配任務給 Agent 並執行

        Args:
            task_id: 任務ID
            agent_id: Agent ID

        Returns:
            是否成功分配
        """
        try:
            task_request = self._tasks.get(task_id)
            agent_info = self._registry.get_agent_info(agent_id)

            if not task_request or not agent_info:
                return False

            # 更新任務狀態
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.ASSIGNED,
                agent_id=agent_id,
                started_at=datetime.now(),
                result=None,
                error=None,
                completed_at=None,
            )
            self._task_results[task_id] = task_result

            # 更新負載計數
            self._agent_loads[agent_id] = self._agent_loads.get(agent_id, 0) + 1

            logger.info(f"Assigned task {task_id} to agent {agent_id}")

            # 異步執行任務（這裡先標記為已分配，實際執行由調用方處理）
            # 或者可以在這裡直接執行任務
            return True
        except Exception as e:
            logger.error(f"Failed to assign task '{task_id}' to agent '{agent_id}': {e}")
            return False

    async def execute_task(
        self,
        task_id: str,
        agent_id: Optional[str] = None,
    ) -> Optional[TaskResult]:
        """
        執行任務（使用 AgentServiceProtocol 接口）

        Args:
            task_id: 任務ID
            agent_id: Agent ID（可選，如果不提供則自動選擇）

        Returns:
            任務結果，如果失敗則返回 None
        """
        try:
            task_request = self._tasks.get(task_id)
            if not task_request:
                logger.error(f"Task not found: {task_id}")
                return None

            # 如果未指定 Agent，自動選擇
            if not agent_id:
                agent_info = self._select_agent(task_request)
                if not agent_info:
                    logger.error(f"No available agent for task {task_id}")
                    return None
                agent_id = agent_info.agent_id
            else:
                agent_info = self._registry.get_agent_info(agent_id)
                if not agent_info:
                    logger.error(f"Agent not found: {agent_id}")
                    return None

            # 獲取 Agent 實例或客戶端
            agent = self._registry.get_agent(agent_id)
            if not agent:
                logger.error(f"Failed to get agent instance: {agent_id}")
                return None

            # 構建 AgentServiceRequest
            service_request = AgentServiceRequest(
                task_id=task_id,
                task_type=task_request.task_type,
                task_data=task_request.task_data,
                context=task_request.metadata.get("context"),
                metadata=task_request.metadata,
            )

            # 執行任務
            task_result = self._task_results.get(task_id)
            if task_result:
                task_result.status = TaskStatus.RUNNING

            logger.info(f"Executing task {task_id} on agent {agent_id}")
            service_response: AgentServiceResponse = await agent.execute(service_request)

            # 更新任務結果
            if task_result:
                if service_response.status == "completed":
                    task_result.status = TaskStatus.COMPLETED
                    task_result.result = service_response.result
                else:
                    task_result.status = TaskStatus.FAILED
                    task_result.error = service_response.error
                task_result.completed_at = datetime.now()
            else:
                # 創建新的任務結果
                task_result = TaskResult(
                    task_id=task_id,
                    status=(
                        TaskStatus.COMPLETED
                        if service_response.status == "completed"
                        else TaskStatus.FAILED
                    ),
                    agent_id=agent_id,
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    result=service_response.result,
                    error=service_response.error,
                )
                self._task_results[task_id] = task_result

            # 更新負載計數
            self._agent_loads[agent_id] = max(0, self._agent_loads.get(agent_id, 0) - 1)

            logger.info(f"Task {task_id} completed with status: {service_response.status}")
            return task_result

        except Exception as e:
            logger.error(f"Failed to execute task '{task_id}': {e}")
            task_result = self._task_results.get(task_id)
            if task_result:
                task_result.status = TaskStatus.FAILED
                task_result.error = str(e)
                task_result.completed_at = datetime.now()
            return None

    def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        完成任務

        Args:
            task_id: 任務ID
            result: 任務結果
            error: 錯誤信息

        Returns:
            是否成功完成
        """
        try:
            task_result = self._task_results.get(task_id)
            if not task_result:
                logger.warning(f"Task result not found: {task_id}")
                return False

            # 更新任務狀態
            if error:
                task_result.status = TaskStatus.FAILED
                task_result.error = error
            else:
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result

            task_result.completed_at = datetime.now()

            # 更新負載計數（Agent 狀態由 Registry 管理）
            if task_result.agent_id:
                self._agent_loads[task_result.agent_id] = max(
                    0, self._agent_loads.get(task_result.agent_id, 0) - 1
                )

            logger.info(f"Completed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete task '{task_id}': {e}")
            return False

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        獲取任務結果

        Args:
            task_id: 任務ID

        Returns:
            任務結果，如果不存在則返回 None
        """
        return self._task_results.get(task_id)

    def aggregate_results(
        self,
        task_ids: List[str],
    ) -> Dict[str, Any]:
        """
        聚合多個任務的結果

        Args:
            task_ids: 任務ID列表

        Returns:
            聚合結果
        """
        results = []
        errors = []

        for task_id in task_ids:
            task_result = self._task_results.get(task_id)
            if task_result:
                if task_result.status == TaskStatus.COMPLETED:
                    results.append(task_result.result)
                elif task_result.status == TaskStatus.FAILED:
                    errors.append(
                        {
                            "task_id": task_id,
                            "error": task_result.error,
                        }
                    )

        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }

    def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> bool:
        """
        更新 Agent 狀態（通過 Registry）

        Args:
            agent_id: Agent ID
            status: 新狀態

        Returns:
            是否成功更新

        注意：Agent 狀態應由 Registry 管理，此方法僅為向後兼容保留。
        """
        agent_info = self._registry.get_agent_info(agent_id)
        if agent_info:
            # Agent 狀態由 Registry 管理，這裡僅記錄日誌
            logger.debug(f"Agent {agent_id} status update requested: {status.value}")
            # 實際狀態更新應通過 Registry 的心跳機制完成
            return True
        return False

    def _get_task_analyzer(self) -> Any:
        """獲取 Task Analyzer 實例（懶加載，避免循環導入）"""
        if self._task_analyzer is None:
            from agents.task_analyzer.analyzer import TaskAnalyzer

            self._task_analyzer = TaskAnalyzer()
        return self._task_analyzer

    def _get_log_service(self) -> Any:
        """獲取 LogService 實例（懶加載，避免循環導入）"""
        if self._log_service is None:
            from services.api.core.log import get_log_service

            self._log_service = get_log_service()
        return self._log_service

    def _get_definition_loader(self) -> Any:
        """獲取 DefinitionLoader 實例（懶加載，避免循環導入）"""
        if self._definition_loader is None:
            try:
                from services.api.core.config import get_definition_loader

                self._definition_loader = get_definition_loader()
            except ImportError as e:
                logger.warning(f"Failed to import DefinitionLoader: {e}")
                # 如果 DefinitionLoader 不存在，返回 None，預檢會失敗並返回錯誤
                return None
        return self._definition_loader

    def _get_security_agent(self) -> Any:
        """獲取 Security Agent 實例（懶加載，避免循環導入）"""
        if self._security_agent is None:
            try:
                from agents.builtin import get_builtin_agent

                self._security_agent = get_builtin_agent("security_manager")
                if self._security_agent is None:
                    logger.warning("Security Manager Agent not found, initializing new instance")
                    from agents.builtin.security_manager.agent import SecurityManagerAgent

                    self._security_agent = SecurityManagerAgent()
            except ImportError as e:
                logger.warning(f"Failed to import Security Agent: {e}")
                return None
        return self._security_agent

    async def process_natural_language_request(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        specified_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        處理自然語言請求（完整流程）

        完整流程包括：
        1. 生成 trace_id 並記錄任務開始日誌
        2. 使用 Task Analyzer 解析自然語言意圖
        3. 處理澄清響應（如果需要）
        4. 第一層預檢（配置操作時）
        5. Security Agent 權限檢查
        6. 創建任務記錄
        7. 分發任務給目標 Agent
        8. 結果修飾
        9. 記錄任務完成日誌

        ⭐ 日誌查詢功能設計說明：
        當 Task Analyzer 識別為 LOG_QUERY 類型時，直接調用 LogService 執行查詢，
        不路由到 Agent。這是因為：
        1. 日誌查詢是查詢操作，不是業務邏輯執行，不需要 Agent
        2. 減少架構複雜度（避免重複解析和額外的 Agent 調用）
        3. 性能更好（減少一層調用開銷）
        4. 符合 Function/Tool 模式的設計原則

        Args:
            instruction: 自然語言指令
            context: 上下文信息（可選）
            user_id: 用戶 ID（可選）
            session_id: 會話 ID（可選）
            specified_agent_id: 前端指定的 Agent ID（可選）

        Returns:
            處理結果字典，包含：
            - status: 狀態（"completed", "failed", "clarification_needed", "validation_failed", "permission_denied", "confirmation_required"）
            - result: 結果數據（如果成功）
            - error: 錯誤信息（如果失敗）
            - clarification_question: 澄清問題（如果需要澄清）
            - trace_id: 追蹤 ID（用於後續查詢）
        """

        # 0. 生成 trace_id（用於串聯整個請求的生命週期）
        trace_id = str(uuid.uuid4())

        try:
            log_service = self._get_log_service()

            # 記錄任務開始
            await log_service.log_task(
                trace_id=trace_id,
                actor=user_id or "unknown",
                action="task_start",
                content={
                    "instruction": instruction,
                    "context": context,
                    "specified_agent_id": specified_agent_id,
                },
            )

            # 1. 使用 Task Analyzer 解析自然語言意圖
            from agents.task_analyzer.models import ConfigIntent, TaskAnalysisRequest, TaskType

            task_analyzer = self._get_task_analyzer()
            analysis_result = await task_analyzer.analyze(
                TaskAnalysisRequest(
                    task=instruction,
                    context=context,
                    user_id=user_id,
                    session_id=session_id,
                )
            )

            # 記錄任務路由決策
            await log_service.log_task(
                trace_id=trace_id,
                actor=user_id or "unknown",
                action="task_routing",
                content={
                    "intent": analysis_result.analysis_details.get("intent"),
                    "suggested_agents": analysis_result.suggested_agents,
                    "workflow_type": analysis_result.workflow_type.value,
                    "confidence": analysis_result.confidence,
                },
            )

            # 2. 如果是日誌查詢，直接處理（不路由到 Agent）
            if analysis_result.task_type == TaskType.LOG_QUERY:
                return await self._handle_log_query(analysis_result, user_id, trace_id)

            # 3. 檢查是否需要澄清（配置操作時）
            intent = analysis_result.get_intent()
            if isinstance(intent, ConfigIntent):
                clarification_needed = analysis_result.analysis_details.get(
                    "clarification_needed", False
                )
                if clarification_needed:
                    clarification_question = analysis_result.analysis_details.get(
                        "clarification_question"
                    )
                    missing_slots = analysis_result.analysis_details.get("missing_slots", [])
                    return {
                        "status": "clarification_needed",
                        "result": {
                            "clarification_question": clarification_question,
                            "missing_slots": missing_slots,
                        },
                        "trace_id": trace_id,
                    }

                # 4. 第一層預檢：格式與邊界驗證（配置操作時）
                if analysis_result.suggested_agents:
                    target_agent_id = analysis_result.suggested_agents[0]
                    # 將 ConfigIntent 轉換為字典格式用於預檢
                    if hasattr(intent, "dict"):
                        intent_dict: Dict[str, Any] = intent.dict()
                    elif isinstance(intent, dict):
                        intent_dict = intent
                    else:
                        intent_dict = {}
                    pre_check_result = await self._pre_check_config_intent(
                        intent=intent_dict,
                        agent_id=target_agent_id,
                    )

                    if not pre_check_result.valid:
                        # 記錄預檢失敗日誌
                        await log_service.log_task(
                            trace_id=trace_id,
                            actor=user_id or "unknown",
                            action="pre_check_failed",
                            content={
                                "reason": pre_check_result.reason,
                                "intent": intent_dict,
                            },
                        )
                        return {
                            "status": "validation_failed",
                            "result": {"error": pre_check_result.reason},
                            "trace_id": trace_id,
                        }

                    # 5. 權限檢查（通過 Security Agent）
                    if user_id:
                        # 確保 intent_dict 是字典類型
                        security_intent_dict: Dict[str, Any] = intent_dict
                        security_result = await self._check_permission(
                            user_id=user_id,
                            intent=security_intent_dict,
                            target_agents=analysis_result.suggested_agents,
                            context={**(context or {}), "trace_id": trace_id},
                        )

                        # 記錄權限檢查結果
                        await log_service.log_task(
                            trace_id=trace_id,
                            actor=user_id or "unknown",
                            action="permission_check",
                            content={
                                "security_result": {
                                    "allowed": security_result.allowed,
                                    "risk_level": security_result.risk_level,
                                    "requires_double_check": security_result.requires_double_check,
                                },
                            },
                        )

                        if not security_result.allowed:
                            return {
                                "status": "permission_denied",
                                "result": {"error": security_result.reason},
                                "trace_id": trace_id,
                            }

                        # 6. 二次確認流程（高風險操作需要二次確認）
                        if security_result.requires_double_check:
                            confirmation_message = self._generate_confirmation_message(
                                intent, security_result.risk_level
                            )
                            return {
                                "status": "confirmation_required",
                                "result": {
                                    "confirmation_message": confirmation_message,
                                    "audit_context": security_result.audit_context,
                                },
                                "trace_id": trace_id,
                            }

            # 7. 創建任務記錄（使用 Task Tracker）
            if analysis_result.suggested_agents:
                target_agent_id = (
                    specified_agent_id
                    if specified_agent_id
                    else analysis_result.suggested_agents[0]
                )
                intent_dict = intent.dict() if hasattr(intent, "dict") else intent

                task_id = self._task_tracker.create_task(
                    instruction=instruction,
                    target_agent_id=target_agent_id,
                    user_id=user_id or "unknown",
                    intent=intent_dict,
                )

                # 更新任務狀態為 running
                self._task_tracker.update_task_status(task_id, TaskStatus.RUNNING)

                # 8. 對於其他任務類型，暫時返回未實現（後續任務中會完善任務分發和結果修飾）
                # TODO: 任務 4.3 將完善結果修飾和任務分發
                return {
                    "status": "task_created",
                    "result": {
                        "task_id": task_id,
                        "target_agent_id": target_agent_id,
                        "message": "Task created successfully, execution will be handled separately",
                    },
                    "trace_id": trace_id,
                }
            else:
                return {
                    "status": "not_implemented",
                    "error": f"Task type {analysis_result.task_type.value} has no suggested agents.",
                    "trace_id": trace_id,
                }

        except Exception as e:
            logger.error(f"Failed to process natural language request: {e}", exc_info=True)
            log_service = self._get_log_service()
            await log_service.log_task(
                trace_id=trace_id,
                actor=user_id or "unknown",
                action="task_failed",
                content={"error": str(e), "instruction": instruction},
            )
            return {
                "status": "failed",
                "error": str(e),
                "trace_id": trace_id,
            }

    async def _handle_log_query(
        self, analysis_result: Any, user_id: Optional[str], trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        處理日誌查詢請求

        ⭐ 這是日誌查詢的核心處理邏輯，直接調用 LogService，不經過 Agent

        Args:
            analysis_result: Task Analyzer 的分析結果
            user_id: 用戶 ID

        Returns:
            查詢結果字典
        """
        try:
            from agents.task_analyzer.models import LogQueryIntent

            log_service = self._get_log_service()
            intent = analysis_result.get_intent()

            if not isinstance(intent, LogQueryIntent):
                return {
                    "status": "failed",
                    "error": "Failed to extract log query intent",
                }

            # 根據日誌類型調用對應的查詢方法
            logs = []
            if intent.trace_id:
                # 根據 trace_id 查詢
                logs = await log_service.get_logs_by_trace_id(intent.trace_id)
            elif intent.log_type == "AUDIT":
                # 查詢審計日誌
                logs = await log_service.get_audit_logs(
                    actor=intent.actor,
                    level=intent.level,
                    tenant_id=intent.tenant_id,
                    start_time=intent.start_time,
                    end_time=intent.end_time,
                    limit=intent.limit,
                )
            elif intent.log_type == "SECURITY":
                # 查詢安全日誌
                logs = await log_service.get_security_logs(
                    actor=intent.actor,
                    action=None,  # 可以從 intent 中提取
                    start_time=intent.start_time,
                    end_time=intent.end_time,
                    limit=intent.limit,
                )
            elif intent.log_type == "TASK":
                # TASK 日誌目前沒有專門的查詢方法，可以通過 trace_id 或時間範圍查詢
                # 這裡可以擴展 LogService 添加 get_task_logs 方法
                return {
                    "status": "failed",
                    "error": "TASK log query by time range is not yet implemented. Please use trace_id query.",
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Unsupported log type: {intent.log_type}",
                }

            # 格式化結果（可以使用 LLM 將結果轉換為自然語言）
            formatted_result = await self._format_log_query_result(logs, intent)

            return {
                "status": "completed",
                "result": {
                    "logs": logs,
                    "formatted_response": formatted_result,
                    "count": len(logs),
                    "query_intent": intent.dict(),
                },
            }

        except Exception as e:
            logger.error(f"Failed to handle log query: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _format_log_query_result(self, logs: List[Dict[str, Any]], intent: Any) -> str:
        """
        格式化日誌查詢結果為自然語言

        Args:
            logs: 查詢到的日誌列表
            intent: 查詢意圖

        Returns:
            格式化後的自然語言描述
        """
        if not logs:
            return f"未找到符合條件的{intent.log_type or '日誌'}記錄。"

        # 簡單格式化（可以擴展使用 LLM 生成更友好的描述）
        log_type_name = {
            "TASK": "任務日誌",
            "AUDIT": "審計日誌",
            "SECURITY": "安全日誌",
        }.get(intent.log_type, "日誌")

        result = f"找到 {len(logs)} 條{log_type_name}記錄：\n\n"
        for i, log in enumerate(logs[:10], 1):  # 只顯示前 10 條
            timestamp = log.get("timestamp", "")
            action = log.get("action", "")
            actor = log.get("actor", "")
            result += f"{i}. [{timestamp}] {actor} - {action}\n"

        if len(logs) > 10:
            result += f"\n... 還有 {len(logs) - 10} 條記錄未顯示"

        return result

    async def _format_result(
        self,
        agent_result: Dict[str, Any],
        original_instruction: str,
        intent: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        使用 LLM 將技術性結果轉換為友好的自然語言

        Args:
            agent_result: Agent 執行的原始結果（技術性數據）
            original_instruction: 原始指令
            intent: 結構化意圖（可選）

        Returns:
            格式化後的自然語言描述
        """
        try:
            # 1. 獲取 LLM Router 和客戶端
            from agents.task_analyzer.llm_router import LLMRouter
            from llm.clients.factory import LLMClientFactory

            llm_router = LLMRouter()

            # 2. 路由選擇合適的 LLM（用於結果格式化）
            # 結果格式化通常不需要高性能模型，可以使用較快的模型
            from agents.task_analyzer.models import TaskClassificationResult, TaskType

            # 創建一個簡單的分類結果用於路由
            classification = TaskClassificationResult(
                task_type=TaskType.EXECUTION,
                confidence=0.8,
                reasoning="result_formatting",
            )
            routing_result = llm_router.route(
                task_classification=classification,
                task="result_formatting",
            )

            # 3. 獲取 LLM 客戶端
            llm_client = LLMClientFactory.create_client(routing_result.provider, use_cache=True)

            # 4. 構建 System Prompt
            system_prompt = """你是一個友好的 AI 助手。你的任務是將技術性的執行結果轉換為清晰、友好的自然語言響應。

請遵循以下原則：
1. 使用簡潔明瞭的語言
2. 避免使用技術術語，如果必須使用，請簡單解釋
3. 突出顯示重要信息
4. 如果結果包含錯誤，請友好地解釋問題
5. 如果操作成功，請確認操作已完成並簡要說明結果

請只返回轉換後的自然語言描述，不要包含額外的格式標記。"""

            # 5. 構建用戶 Prompt
            user_prompt = f"""原始指令：{original_instruction}

執行結果：
{self._format_result_for_llm(agent_result)}

請將上述技術性結果轉換為友好的自然語言響應。"""

            # 6. 調用 LLM 生成格式化結果
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await llm_client.chat(messages, max_tokens=500)

            # 7. 提取格式化後的文本
            formatted_text = response.get("content") or response.get("text") or ""
            if not formatted_text:
                # 如果 LLM 調用失敗，返回簡單的格式化結果
                return self._format_result_simple(agent_result, original_instruction)

            return formatted_text

        except Exception as e:
            logger.warning(f"Failed to format result with LLM: {e}, using simple formatting")
            # 如果 LLM 調用失敗，使用簡單格式化
            return self._format_result_simple(agent_result, original_instruction)

    def _format_result_for_llm(self, result: Dict[str, Any]) -> str:
        """
        將結果格式化為 LLM 可以理解的文本

        Args:
            result: 結果字典

        Returns:
            格式化後的文本
        """
        import json

        # 將結果轉換為 JSON 字符串，便於 LLM 理解
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            return str(result)

    def _format_result_simple(self, agent_result: Dict[str, Any], original_instruction: str) -> str:
        """
        簡單格式化結果（LLM 調用失敗時的備用方案）

        Args:
            agent_result: Agent 執行的原始結果
            original_instruction: 原始指令

        Returns:
            簡單格式化後的文本
        """
        if not agent_result:
            return f"執行指令「{original_instruction}」完成，但沒有返回結果。"

        # 檢查結果中是否有成功/失敗標記
        status = agent_result.get("status", "unknown")
        if status == "success" or status == "completed":
            return f"✅ 已成功執行指令「{original_instruction}」。"
        elif status == "failed" or status == "error":
            error = agent_result.get("error", "未知錯誤")
            return f"❌ 執行指令「{original_instruction}」時發生錯誤：{error}"
        else:
            # 簡單展示結果
            return f"執行指令「{original_instruction}」完成。結果：{str(agent_result)[:200]}"

    async def _get_config_definition(self, scope: str) -> Optional[Dict[str, Any]]:
        """
        獲取配置定義（只從內存緩存讀取）

        JSON 文件是唯一數據源，啟動時已加載到內存緩存。
        不再從 ArangoDB 讀取備用，避免讀到舊數據。

        Args:
            scope: 配置範圍

        Returns:
            配置定義（如果存在）

        注意：
        - JSON 文件是唯一數據源
        - 啟動時應該已經加載所有定義到內存
        - 如果內存緩存沒有，說明 JSON 文件缺失（系統配置錯誤）
        """
        definition_loader = self._get_definition_loader()
        if definition_loader is None:
            logger.error("DefinitionLoader is not available")
            return None

        definition = definition_loader.get_definition(scope)

        if not definition:
            logger.error(
                f"配置定義缺失: {scope}，請檢查 JSON 文件是否存在",
                extra={"scope": scope},
            )

        return definition

    async def _pre_check_config_intent(
        self,
        intent: Dict[str, Any],
        agent_id: str,
    ) -> ValidationResult:
        """
        第一層預檢：格式與邊界驗證

        快速止損：
        - 檢查型別是否正確
        - 檢查數值是否在 min/max 內
        - 檢查選項是否在 options 列表中

        詳細說明請參考：[ConfigMetadata-配置元數據機制規格書.md](../docs/Agent%20Platform/Tools/ConfigMetadata-配置元數據機制規格書.md)

        Args:
            intent: ConfigIntent（字典格式）
            agent_id: 目標 Agent ID

        Returns:
            ValidationResult: 驗證結果
        """
        from agents.task_analyzer.models import ConfigIntent

        # 將 intent 轉換為 ConfigIntent 對象（如果是字典）
        if isinstance(intent, dict):
            try:
                config_intent = ConfigIntent(**intent)
            except Exception as e:
                logger.error(f"Failed to parse ConfigIntent: {e}")
                return ValidationResult(
                    valid=False, reason=f"Invalid ConfigIntent format: {str(e)}"
                )
        elif isinstance(intent, ConfigIntent):
            config_intent = intent
        else:
            return ValidationResult(valid=False, reason=f"Invalid intent type: {type(intent)}")

        # 1. 獲取配置定義（從內存緩存，JSON 文件是唯一數據源）
        scope = config_intent.scope
        if not scope:
            return ValidationResult(valid=False, reason="scope is required")

        definition = await self._get_config_definition(scope)
        if not definition:
            return ValidationResult(
                valid=False,
                reason=f"Config definition not found for scope: {scope}。請檢查 JSON 文件是否存在。",
            )

        # 2. 驗證每個配置字段
        config_data = config_intent.config_data
        if config_data:
            for field_name, field_value in config_data.items():
                fields = definition.get("fields", {})
                if field_name not in fields:
                    return ValidationResult(valid=False, reason=f"未知的配置字段：{field_name}")

                field_def = fields[field_name]
                validation_result = self._validate_field(field_name, field_value, field_def)

                if not validation_result.valid:
                    return validation_result

        return ValidationResult(valid=True, reason=None)

    def _validate_field(
        self,
        field_name: str,
        field_value: Any,
        field_def: Dict[str, Any],
    ) -> ValidationResult:
        """
        驗證單個字段

        Args:
            field_name: 字段名稱
            field_value: 字段值
            field_def: 字段定義（從配置定義 JSON 中讀取）

        Returns:
            ValidationResult: 驗證結果
        """

        # 1. 類型檢查
        expected_type = field_def.get("type")
        if expected_type and not self._check_type(field_value, expected_type):
            return ValidationResult(
                valid=False,
                reason=f"{field_name} 的類型錯誤：期望 {expected_type}，實際 {type(field_value).__name__}",
            )

        # 2. 數值邊界檢查
        if expected_type in ["integer", "number"]:
            if "min" in field_def and field_value < field_def["min"]:
                description = field_def.get("description", "")
                error_msg = (
                    f"設置失敗：{field_name} ({field_value}) 小於系統定義下限 ({field_def['min']})。"
                    f"{description} 合法範圍：{field_def.get('min', 'N/A')}-{field_def.get('max', 'N/A')}"
                )
                return ValidationResult(valid=False, reason=error_msg)

            if "max" in field_def and field_value > field_def["max"]:
                description = field_def.get("description", "")
                error_msg = (
                    f"設置失敗：{field_name} ({field_value}) 超出系統定義上限 ({field_def['max']})。"
                    f"{description} 合法範圍：{field_def.get('min', 'N/A')}-{field_def.get('max', 'N/A')}"
                )
                return ValidationResult(valid=False, reason=error_msg)

        # 3. 枚舉值檢查
        if "options" in field_def:
            options = field_def["options"]
            if isinstance(field_value, list):
                # 數組類型：檢查每個元素
                invalid_values = [v for v in field_value if v not in options]
                if invalid_values:
                    return ValidationResult(
                        valid=False,
                        reason=f"{field_name} 包含無效值：{invalid_values}。允許的值：{options}",
                    )
            else:
                # 單值類型：檢查值本身
                if field_value not in options:
                    return ValidationResult(
                        valid=False,
                        reason=f"{field_name} ({field_value}) 不在允許列表中。允許的值：{options}",
                    )

        return ValidationResult(valid=True, reason=None)

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        檢查類型是否匹配

        Args:
            value: 值
            expected_type: 期望的類型（字符串，如 "integer", "number", "string", "boolean", "array", "object"）

        Returns:
            是否匹配
        """
        type_map = {
            "integer": int,
            "number": (int, float),
            "string": str,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True  # 未知類型，跳過檢查

        if isinstance(expected, tuple):
            return isinstance(value, expected)
        # 使用 type: ignore 因為 expected 是 type 或 tuple，mypy 會抱怨
        return isinstance(value, expected)  # type: ignore[arg-type]

    async def _check_permission(
        self,
        user_id: str,
        intent: Dict[str, Any],
        target_agents: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        權限檢查（通過 Security Agent）

        ⭐ 關鍵判斷：安全過濾
        - 檢查該管理員是否擁有對應層級和租戶的修改權限
        - 例如：租戶級操作時，檢查是否擁有該租戶的權限

        詳細說明請參考：[Security-Agent-規格書.md](../docs/Agent%20Platform/Security-Agent-規格書.md)

        Args:
            user_id: 用戶 ID
            intent: ConfigIntent（字典格式）
            target_agents: 目標 Agent 列表
            context: 上下文信息（包含 trace_id 等）

        Returns:
            SecurityCheckResult: 安全檢查結果
        """
        from agents.builtin.security_manager.models import SecurityCheckResult

        security_agent = self._get_security_agent()
        if security_agent is None:
            logger.warning("Security Agent is not available, allowing access by default")
            # 如果 Security Agent 不可用，返回允許（開發環境的寬鬆策略）
            return SecurityCheckResult(
                allowed=True,
                reason="Security Agent not available",
                requires_double_check=False,
                risk_level="low",
                audit_context={},
            )

        try:
            # 調用 Security Agent 進行權限檢查
            security_result = await security_agent.verify_access(
                admin_id=user_id,
                intent=intent,
                context=context or {},
            )
            return security_result
        except Exception as e:
            logger.error(f"Security check failed: {e}", exc_info=True)
            # 安全檢查失敗時，拒絕訪問（安全優先）
            return SecurityCheckResult(
                allowed=False,
                reason=f"Security check failed: {str(e)}",
                requires_double_check=False,
                risk_level="high",
                audit_context={"error": str(e)},
            )

    def _generate_confirmation_message(self, intent: Any, risk_level: str) -> str:
        """
        生成二次確認消息

        Args:
            intent: ConfigIntent 對象或字典
            risk_level: 風險級別（low/medium/high）

        Returns:
            確認消息字符串
        """
        # 將 intent 轉換為字典（如果還是對象）
        if hasattr(intent, "dict"):
            intent_dict = intent.dict()
        elif isinstance(intent, dict):
            intent_dict = intent
        else:
            intent_dict = {}

        action = intent_dict.get("action", "操作")
        scope = intent_dict.get("scope", "配置")
        level = intent_dict.get("level", "")

        action_names = {
            "update": "更新",
            "delete": "刪除",
            "create": "創建",
            "query": "查詢",
            "list": "列表",
            "rollback": "回滾",
        }

        level_names = {
            "system": "系統級",
            "tenant": "租戶級",
            "user": "用戶級",
        }

        action_name = action_names.get(action, action)
        level_name = level_names.get(level, level) if level else ""

        risk_messages = {
            "high": "這是一個高風險操作，可能對系統造成重大影響。",
            "medium": "這是一個中等風險操作，請確認操作正確。",
            "low": "請確認此操作。",
        }

        risk_message = risk_messages.get(risk_level, "請確認此操作。")

        message = "⚠️ 二次確認要求\n\n"
        message += f"操作：{action_name} {level_name} {scope} 配置\n"
        message += f"風險級別：{risk_level.upper()}\n\n"
        message += f"{risk_message}\n\n"
        message += "請確認是否繼續執行此操作？"

        return message
