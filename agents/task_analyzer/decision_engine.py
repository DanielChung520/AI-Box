# 代碼功能說明: 工作流決策引擎
# 創建日期: 2025-11-26 22:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""實現工作流模式選擇決策邏輯。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

from agents.task_analyzer.models import (
    CapabilityMatch,
    DecisionResult,
    PolicyValidationResult,
    RouterDecision,
    TaskClassificationResult,
    TaskDAG,
    TaskType,
    WorkflowStrategy,
    WorkflowType,
)
from agents.task_analyzer.policy_service import get_policy_service

logger = logging.getLogger(__name__)


class DecisionEngine:
    """工作流決策引擎。"""

    def __init__(self):
        """初始化決策引擎。"""
        # 複雜度閾值
        self.complexity_threshold_hybrid = 70
        self.step_count_threshold_hybrid = 10

        # 成本門檻（避免頻繁切換）
        self.cost_threshold_switch = 100.0  # 美元

        # 冷卻時間（秒）
        self.cooldown_seconds = 60

    def _is_file_editing_task(self, query: str) -> bool:
        """
        判斷是否為文件編輯任務

        Args:
            query: 用戶查詢文本

        Returns:
            是否為文件編輯任務
        """
        if not query:
            return False

        file_editing_keywords = [
            # 明確的編輯動詞
            "編輯",
            "修改",
            "更新",
            "刪除",
            "添加",
            "替換",
            "重寫",
            "格式化",
            # 產生/創建動詞
            "產生",
            "創建",
            "寫",
            "生成",
            "建立",
            "製作",
            # 文件相關名詞
            "文件",
            "檔案",
            "文檔",
            "document",
            "file",
            # 英文關鍵詞
            "edit",
            "create",
            "generate",
            "write",
            "make",
            "build",
            "update",
            "modify",
            "delete",
            "add",
            "replace",
            "rewrite",
            "format",
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in file_editing_keywords)

    def _select_agent_by_file_extension(self, query: str) -> Optional[str]:
        """
        根據文件擴展名和操作類型選擇具體的 Agent（方案1：精確匹配）

        Args:
            query: 用戶查詢文本

        Returns:
            建議的 Agent ID，如果無法確定則返回 None
        """
        if not query:
            return None

        query_lower = query.lower()

        # 檢查文件擴展名
        file_extensions = {
            ".md": "md-editor",
            ".markdown": "md-editor",
            ".xlsx": "xls-editor",
            ".xls": "xls-editor",
            ".pdf": None,  # PDF 需要根據操作類型判斷
        }

        # 檢查轉換操作
        # 擴展的轉換關鍵詞列表（包含更多表達轉換意圖的詞彙）
        conversion_keywords = [
            "轉換",
            "轉為",
            "轉成",
            "轉",
            "convert",
            "to",
            "生成",
            "產生",
            "生成為",
            "產生為",  # 生成/產生 + 目標格式
            "版本",
            "version",  # 版本（如 "PDF 版本"）
            "導出",
            "export",  # 導出為某格式
            "輸出",
            "output",  # 輸出為某格式
        ]
        is_conversion = any(keyword in query_lower for keyword in conversion_keywords)

        # 檢查文件擴展名（優先檢查轉換操作，因為轉換操作更明確）
        # 先檢查轉換操作（明確的轉換關鍵詞）
        # 注意：檢查順序很重要！應該先檢查更具體的轉換（pdf -> md），再檢查通用轉換（md -> pdf）
        # 因為 "將 document.pdf 轉換為 Markdown" 同時包含 "pdf" 和 "markdown"，如果先檢查 md -> pdf 會錯誤匹配
        if is_conversion:
            # 先檢查 pdf -> md（更具體的轉換，優先檢查）
            if ".pdf" in query_lower and ("markdown" in query_lower or ".md" in query_lower):
                logger.debug(
                    f"File extension match: pdf-to-md conversion detected in query: {query[:100]}"
                )
                return "pdf-to-md"
            # 檢查 xlsx/xls -> pdf
            if (".xlsx" in query_lower or ".xls" in query_lower) and "pdf" in query_lower:
                logger.debug(
                    f"File extension match: xls-to-pdf conversion detected in query: {query[:100]}"
                )
                return "xls-to-pdf"
            # 最後檢查 md -> pdf（放在最後，避免與 pdf -> md 衝突）
            if (".md" in query_lower or "markdown" in query_lower) and "pdf" in query_lower:
                logger.debug(
                    f"File extension match: md-to-pdf conversion detected in query: {query[:100]}"
                )
                return "md-to-pdf"

        # 檢查隱式轉換操作（沒有明確轉換關鍵詞，但同時包含源文件格式和目標格式）
        # 例如："生成 README.md 的 PDF 版本" - 包含 .md 和 PDF，但沒有明確的轉換關鍵詞
        # 注意：檢查順序很重要！應該先檢查更具體的轉換（pdf -> md），再檢查通用轉換（md -> pdf）
        # 檢查 pdf -> md（隱式，優先檢查）
        if ".pdf" in query_lower and ("markdown" in query_lower or ".md" in query_lower):
            editing_keywords = [
                "編輯",
                "修改",
                "更新",
                "刪除",
                "添加",
                "插入",
                "設置",
                "edit",
                "modify",
                "update",
            ]
            has_editing_keyword = any(keyword in query_lower for keyword in editing_keywords)
            if not has_editing_keyword:
                logger.debug(
                    f"File extension match: pdf-to-md implicit conversion detected in query: {query[:100]}"
                )
                return "pdf-to-md"
        # 檢查 xlsx/xls -> pdf（隱式）
        if (".xlsx" in query_lower or ".xls" in query_lower) and "pdf" in query_lower:
            editing_keywords = [
                "編輯",
                "修改",
                "更新",
                "刪除",
                "添加",
                "插入",
                "設置",
                "edit",
                "modify",
                "update",
            ]
            has_editing_keyword = any(keyword in query_lower for keyword in editing_keywords)
            if not has_editing_keyword:
                logger.debug(
                    f"File extension match: xls-to-pdf implicit conversion detected in query: {query[:100]}"
                )
                return "xls-to-pdf"
        # 檢查 md -> pdf（隱式，放在最後）
        if (".md" in query_lower or "markdown" in query_lower) and "pdf" in query_lower:
            editing_keywords = [
                "編輯",
                "修改",
                "更新",
                "刪除",
                "添加",
                "插入",
                "設置",
                "edit",
                "modify",
                "update",
            ]
            has_editing_keyword = any(keyword in query_lower for keyword in editing_keywords)
            if not has_editing_keyword:
                logger.debug(
                    f"File extension match: md-to-pdf implicit conversion detected in query: {query[:100]}"
                )
                return "md-to-pdf"

        # 檢查編輯操作（非轉換）
        for ext, agent_id in file_extensions.items():
            if ext in query_lower and agent_id:
                # 編輯操作
                logger.debug(
                    f"File extension match: {ext} -> {agent_id} for editing operation in query: {query[:100]}"
                )
                return agent_id

        logger.debug(f"File extension match: No match found for query: {query[:100]}")
        return None

    def decide_strategy(
        self,
        classification: TaskClassificationResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowStrategy:
        """
        決策工作流策略。

        Args:
            classification: 任務分類結果
            context: 上下文信息

        Returns:
            工作流策略
        """
        context = context or {}
        task_type = classification.task_type
        complexity_score = context.get("complexity_score", 0)
        step_count = context.get("step_count", 0)
        failure_history = context.get("failure_history", [])
        requires_observability = context.get("requires_observability", False)
        requires_long_horizon = context.get("requires_long_horizon", False)

        # 決策邏輯
        mode: Literal["single", "hybrid"] = "single"
        primary = WorkflowType.LANGCHAIN
        fallback: list[WorkflowType] = []
        reasoning_parts = []

        # 規則 1: 複雜度 ≥70 分 → 混合模式
        if complexity_score >= self.complexity_threshold_hybrid:
            mode = "hybrid"
            primary = WorkflowType.AUTOGEN
            fallback = [WorkflowType.LANGCHAIN]
            reasoning_parts.append(
                f"複雜度分數 {complexity_score} ≥ {self.complexity_threshold_hybrid}，使用混合模式"
            )

        # 規則 2: 步驟數 >10 → 混合模式
        elif step_count > self.step_count_threshold_hybrid:
            mode = "hybrid"
            primary = WorkflowType.AUTOGEN
            fallback = [WorkflowType.LANGCHAIN]
            reasoning_parts.append(
                f"步驟數 {step_count} > {self.step_count_threshold_hybrid}，使用混合模式"
            )

        # 規則 3: 需要可觀測性 → LangGraph 作為主要模式
        elif requires_observability:
            if mode == "hybrid":
                primary = WorkflowType.LANGCHAIN
                fallback = [WorkflowType.AUTOGEN]
            else:
                primary = WorkflowType.LANGCHAIN
            reasoning_parts.append("需要狀態可觀測性，優先使用 LangGraph")

        # 規則 4: 需要長程規劃 → AutoGen 作為主要模式
        elif requires_long_horizon:
            if mode == "hybrid":
                primary = WorkflowType.AUTOGEN
                fallback = [WorkflowType.LANGCHAIN]
            else:
                primary = WorkflowType.AUTOGEN
            reasoning_parts.append("需要長程規劃能力，優先使用 AutoGen")

        # 規則 5: 失敗歷史 → 觸發 fallback
        if failure_history:
            if not fallback:
                # 根據任務類型選擇 fallback
                if task_type == TaskType.PLANNING:
                    fallback = [WorkflowType.LANGCHAIN]
                else:
                    fallback = [WorkflowType.AUTOGEN]
            reasoning_parts.append(f"檢測到 {len(failure_history)} 次失敗歷史，啟用備用模式")

        # 根據任務類型調整策略
        if mode == "single":
            primary, fallback = self._adjust_for_task_type(task_type)
            reasoning_parts.append(f"根據任務類型 {task_type.value} 選擇 {primary.value} 工作流")

        # 構建切換條件
        switch_conditions = {
            "error_rate_threshold": 0.3,
            "cost_threshold": self.cost_threshold_switch,
            "cooldown_seconds": self.cooldown_seconds,
            "max_switches": 5,
        }

        # 合併推理
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "使用默認策略"

        strategy = WorkflowStrategy(
            mode=mode,
            primary=primary,
            fallback=fallback,
            switch_conditions=switch_conditions,
            reasoning=reasoning,
        )

        logger.info(
            f"Decided strategy: mode={mode}, primary={primary.value}, "
            f"fallback={[f.value for f in fallback]}"
        )

        return strategy

    def _adjust_for_task_type(self, task_type: TaskType) -> tuple[WorkflowType, list[WorkflowType]]:
        """
        根據任務類型調整工作流選擇。

        Args:
            task_type: 任務類型

        Returns:
            (主要工作流, 備用工作流列表)
        """
        mapping = {
            TaskType.QUERY: (WorkflowType.LANGCHAIN, [WorkflowType.CREWAI]),
            TaskType.EXECUTION: (
                WorkflowType.LANGCHAIN,
                [WorkflowType.AUTOGEN, WorkflowType.CREWAI],
            ),
            TaskType.REVIEW: (WorkflowType.LANGCHAIN, [WorkflowType.CREWAI]),
            TaskType.PLANNING: (
                WorkflowType.AUTOGEN,
                [WorkflowType.CREWAI, WorkflowType.LANGCHAIN],
            ),
            TaskType.COMPLEX: (
                WorkflowType.AUTOGEN,
                [WorkflowType.LANGCHAIN, WorkflowType.CREWAI],
            ),
        }

        return mapping.get(task_type, (WorkflowType.LANGCHAIN, []))

    def check_cost_threshold(self, current_cost: float) -> bool:
        """
        檢查成本是否超過閾值。

        Args:
            current_cost: 當前成本

        Returns:
            是否超過閾值
        """
        return current_cost > self.cost_threshold_switch

    def is_cooldown_active(self, last_switch_time: Optional[float], current_time: float) -> bool:
        """
        檢查是否在冷卻時間內。

        Args:
            last_switch_time: 上次切換時間戳
            current_time: 當前時間戳

        Returns:
            是否在冷卻時間內
        """
        if last_switch_time is None:
            return False
        return (current_time - last_switch_time) < self.cooldown_seconds

    def decide(
        self,
        router_decision: RouterDecision,
        agent_candidates: list[CapabilityMatch],
        tool_candidates: list[CapabilityMatch],
        model_candidates: list[CapabilityMatch],
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionResult:
        """
        綜合決策：選擇 Agent、Tool、Model

        Args:
            router_decision: Router 決策
            agent_candidates: Agent 候選列表
            tool_candidates: Tool 候選列表
            model_candidates: Model 候選列表
            context: 上下文信息

        Returns:
            決策結果
        """
        context = context or {}
        reasoning_parts = []

        # 檢查是否為文件編輯任務
        user_query = context.get("task", "") or context.get("query", "") if context else ""
        is_file_editing = self._is_file_editing_task(user_query)

        # 檢查是否為知識庫查詢任務（從 context 中獲取 Knowledge Signal）
        is_knowledge_query = False
        knowledge_signal_dict = context.get("knowledge_signal") if context else None
        if knowledge_signal_dict and knowledge_signal_dict.get("is_knowledge_event"):
            is_knowledge_query = True
            logger.info(
                f"Decision Engine: Knowledge query detected from Knowledge Signal: "
                f"is_knowledge_event=True, knowledge_type={knowledge_signal_dict.get('knowledge_type')}"
            )
            # 如果 Knowledge Signal 標記為知識事件，強制設置 needs_agent=True
            if not router_decision.needs_agent:
                router_decision.needs_agent = True
                logger.info(
                    f"Decision Engine: Forcing needs_agent=True for knowledge query "
                    f"(query: {user_query[:100]}...)"
                )

        # 注意：任務類型修正已在 analyzer.py 中處理（修正 RouterDecision.intent_type）
        # 這裡不需要再次修正，因為 RouterDecision 沒有 task_type 字段

        # 修改時間：2026-01-27 - 優先使用 context 中用戶明確選擇的 agent_id（最高優先級）
        user_selected_agent_id = context.get("agent_id") if context else None

        # 根據文件擴展名選擇具體的 Agent（方案2：精確匹配，僅在用戶未選擇時使用）
        file_extension_agent_id = self._select_agent_by_file_extension(user_query)

        # 優先級：用戶選擇 > 文件擴展名匹配
        specific_agent_id = user_selected_agent_id or file_extension_agent_id

        if user_selected_agent_id:
            logger.info(
                f"Decision Engine: User explicitly selected agent: {user_selected_agent_id} "
                f"for query: {user_query[:100]}..."
            )
        if specific_agent_id:
            logger.info(
                f"Decision Engine: File extension match found agent: {specific_agent_id} "
                f"for query: {user_query[:100]}..."
            )
            # 如果文件擴展名匹配到特定 Agent，但該 Agent 不在候選列表中
            # 嘗試從 Registry 直接查找該 Agent 並添加到候選列表
            candidate_ids_before = (
                [a.candidate_id for a in agent_candidates] if agent_candidates else []
            )
            if specific_agent_id not in candidate_ids_before:
                logger.warning(
                    f"Decision Engine: File extension matched {specific_agent_id} but it's not in candidates "
                    f"(current candidates: {candidate_ids_before}). Attempting to find it directly from registry..."
                )
                try:
                    from agents.services.registry.registry import get_agent_registry

                    registry = get_agent_registry()
                    if registry:
                        agent_info = registry.get_agent_info(specific_agent_id)
                        logger.info(
                            f"Decision Engine: Registry lookup for {specific_agent_id}: "
                            f"found={agent_info is not None}, "
                            f"status={agent_info.status.value if agent_info else 'N/A'}"
                        )
                        if agent_info and agent_info.status.value == "online":
                            # 創建一個 CapabilityMatch 對象並添加到候選列表
                            from agents.task_analyzer.models import CapabilityMatch

                            matched_agent = CapabilityMatch(
                                candidate_id=specific_agent_id,
                                candidate_type="agent",
                                capability_match=1.0,  # 文件擴展名匹配 = 完美匹配
                                cost_score=0.7,
                                latency_score=0.7,
                                success_history=0.9,  # 文件擴展名匹配的 Agent 應該有較高的成功歷史
                                stability=0.9,
                                total_score=0.95,  # 非常高的評分，確保優先選擇（提高到 0.95）
                                metadata={
                                    "agent_type": agent_info.agent_type,
                                    "capabilities": agent_info.capabilities,
                                    "load": agent_info.load if hasattr(agent_info, "load") else 0,
                                    "file_extension_match": True,  # 標記為文件擴展名匹配
                                },
                            )
                            agent_candidates.insert(0, matched_agent)  # 插入到列表開頭，優先考慮
                            logger.info(
                                f"Decision Engine: ✅ Added {specific_agent_id} to candidates from registry "
                                f"(file extension match, score: {matched_agent.total_score:.2f})"
                            )
                        else:
                            logger.warning(
                                f"Decision Engine: Agent {specific_agent_id} found in registry but "
                                f"status is {agent_info.status.value if agent_info else 'not found'} "
                                f"(expected: online)"
                            )
                    else:
                        logger.warning(
                            f"Decision Engine: Registry is None, cannot lookup {specific_agent_id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Decision Engine: Failed to find {specific_agent_id} from registry: {e}",
                        exc_info=True,
                    )
            else:
                logger.info(
                    f"Decision Engine: File extension matched {specific_agent_id} and it's already in candidates"
                )
        else:
            logger.info(
                f"Decision Engine: No file extension match for query: {user_query[:100]}..."
            )

        # 1. Rule Filter（硬性規則過濾）
        # 過濾掉已棄用的 document-editing-agent
        # 注意：如果文件擴展名匹配到特定 Agent，不要過濾掉它
        agent_candidates = [
            a for a in agent_candidates if a.candidate_id != "document-editing-agent"
        ]
        logger.debug(
            f"Decision Engine: Filtered out document-editing-agent, remaining candidates: "
            f"{[a.candidate_id for a in agent_candidates]}"
        )

        # 風險等級過濾
        # 注意：如果文件擴展名匹配到特定 Agent，跳過風險等級過濾（因為它是精確匹配）
        max_risk_level = router_decision.risk_level
        if specific_agent_id:
            # 對於文件擴展名匹配的 Agent，跳過風險等級過濾
            agent_candidates = [
                a
                for a in agent_candidates
                if a.candidate_id == specific_agent_id or self._check_risk_level(a, max_risk_level)
            ]
        else:
            agent_candidates = [
                a for a in agent_candidates if self._check_risk_level(a, max_risk_level)
            ]
        tool_candidates = [t for t in tool_candidates if self._check_risk_level(t, max_risk_level)]
        model_candidates = [
            m for m in model_candidates if self._check_risk_level(m, max_risk_level)
        ]

        # 成本限制
        # 注意：如果文件擴展名匹配到特定 Agent，跳過成本過濾（因為它是精確匹配）
        max_cost = context.get("max_cost", "medium")
        if specific_agent_id:
            # 對於文件擴展名匹配的 Agent，跳過成本過濾
            agent_candidates = [
                a
                for a in agent_candidates
                if a.candidate_id == specific_agent_id or self._check_cost_constraint(a, max_cost)
            ]
        else:
            agent_candidates = [
                a for a in agent_candidates if self._check_cost_constraint(a, max_cost)
            ]
        tool_candidates = [t for t in tool_candidates if self._check_cost_constraint(t, max_cost)]
        model_candidates = [m for m in model_candidates if self._check_cost_constraint(m, max_cost)]

        # 2. 選擇 Agent
        chosen_agent = None

        # ============================================
        # 新增：檢查用戶選擇的 Agent 是否有知識庫權限
        # 修改時間：2026-02-03
        # 設計目標：
        # 1. 如果用戶選擇的 Agent 有知識庫權限，優先使用該 Agent
        # 2. Agent 內部調用 KA-Agent 檢索，保持統一的檢索入口
        # 3. 未來若檢索升級，只需修改 KA-Agent，其他 Agent 無需調整
        # ============================================
        if is_knowledge_query and user_selected_agent_id:
            try:
                from agents.services.registry.registry import get_agent_registry

                registry = get_agent_registry()
                if registry:
                    user_agent_info = registry.get_agent_info(user_selected_agent_id)
                    if user_agent_info:
                        # 檢查是否有 MM-Agent 知識庫權限
                        has_mm_knowledge = "mm_agent_knowledge" in user_agent_info.capabilities

                        if has_mm_knowledge:
                            # 用戶選擇的 Agent 有權限，直接使用該 Agent
                            chosen_agent = user_selected_agent_id
                            reasoning_parts.append(
                                f"知識庫查詢任務，用戶選擇的 Agent '{user_selected_agent_id}' "
                                f"有 MM-Agent 知識庫權限，優先使用該 Agent"
                            )
                            logger.info(
                                f"Decision Engine: User selected agent {user_selected_agent_id} has "
                                f"mm_agent_knowledge capability, using it for knowledge query"
                            )

                            # 標記為使用授權 Agent（供後續調用 KA-Agent 時使用）
                            context["knowledge_via_authorized_agent"] = True
                            context["authorized_agent_id"] = user_selected_agent_id
                        else:
                            logger.info(
                                f"Decision Engine: User selected agent {user_selected_agent_id} does NOT have "
                                f"mm_agent_knowledge capability, falling back to KA-Agent"
                            )
                    else:
                        logger.warning(
                            f"Decision Engine: Agent {user_selected_agent_id} not found in registry"
                        )
            except Exception as e:
                logger.warning(
                    f"Decision Engine: Failed to check agent capabilities: {e}",
                    exc_info=True,
                )

        # 方案1（優先）：若是知識庫查詢任務，優先選擇 KA-Agent
        # 即使用戶當前在 MM-Agent 等任務中，問「專業知識」「知識庫」時也應走 KA-Agent 檢索
        # 注意：僅在用戶選擇的 Agent 無權限時才走此邏輯
        if not chosen_agent and is_knowledge_query and agent_candidates:
            # 優先查找 ka-agent
            ka_agent = next((a for a in agent_candidates if a.candidate_id == "ka-agent"), None)
            if ka_agent:
                chosen_agent = "ka-agent"
                reasoning_parts.append(
                    f"知識庫查詢任務，選擇 KA-Agent: {chosen_agent} (評分: {ka_agent.total_score:.2f})"
                )
                logger.info(
                    f"Decision Engine: Knowledge query detected, selected KA-Agent: {chosen_agent} "
                    f"(score: {ka_agent.total_score:.2f})"
                )
            else:
                # 如果沒有找到 ka-agent，查找知識服務類型的 Agent
                knowledge_service_agents = [
                    a
                    for a in agent_candidates
                    if a.metadata.get("agent_type") == "knowledge_service"
                ]
                if knowledge_service_agents:
                    best_knowledge_agent = max(
                        knowledge_service_agents, key=lambda x: x.total_score
                    )
                    chosen_agent = best_knowledge_agent.candidate_id
                    reasoning_parts.append(
                        f"知識庫查詢任務，選擇知識服務 Agent: {chosen_agent} "
                        f"(評分: {best_knowledge_agent.total_score:.2f})"
                    )
                    logger.info(
                        f"Decision Engine: Knowledge query detected, selected knowledge service agent: "
                        f"{chosen_agent} (score: {best_knowledge_agent.total_score:.2f})"
                    )

        # 方案2：根據用戶選擇或文件擴展名精確匹配（僅在未因知識查詢選中 Agent 時）
        if not chosen_agent and specific_agent_id:
            # 記錄所有候選 Agent ID（用於調試）
            candidate_ids = [a.candidate_id for a in agent_candidates] if agent_candidates else []
            logger.info(
                f"Decision Engine: File extension match found {specific_agent_id}, "
                f"Agent candidates: {candidate_ids}"
            )

            matched_agent = (
                next((a for a in agent_candidates if a.candidate_id == specific_agent_id), None)
                if agent_candidates
                else None
            )

            if matched_agent:
                chosen_agent = specific_agent_id
                reasoning_parts.append(
                    f"根據文件擴展名/用戶選擇: {chosen_agent} (評分: {matched_agent.total_score:.2f})"
                )
                logger.info(
                    f"Decision Engine: File extension match - selected {chosen_agent} "
                    f"(score: {matched_agent.total_score:.2f})"
                )
            else:
                logger.warning(
                    f"Decision Engine: File extension match found {specific_agent_id}, "
                    f"but it's not in agent_candidates! Available: {candidate_ids}. "
                    f"This may indicate the agent is not properly registered or loaded."
                )

        # 方案3：如果是文件編輯任務，選擇評分最高的 Agent（document-editing-agent 已被過濾）
        if not chosen_agent and router_decision.needs_agent and agent_candidates:
            # 選擇評分最高的 Agent
            best_agent = max(agent_candidates, key=lambda x: x.total_score)
            if best_agent.total_score >= 0.5:  # 最低可接受評分
                chosen_agent = best_agent.candidate_id
                reasoning_parts.append(
                    f"選擇 Agent: {chosen_agent} (評分: {best_agent.total_score:.2f})"
                )
                logger.info(
                    f"Decision Engine: Selected agent: {chosen_agent} (score: {best_agent.total_score:.2f})"
                )
            else:
                logger.info(
                    f"Decision Engine: No agent selected (best score {best_agent.total_score:.2f} < 0.5)"
                )
                reasoning_parts.append(
                    f"Agent 評分過低 ({best_agent.total_score:.2f})，不使用 Agent"
                )
        elif not chosen_agent:
            logger.debug(
                f"Decision Engine: No agent selection - needs_agent={router_decision.needs_agent}, "
                f"is_file_editing={is_file_editing}, is_knowledge_query={is_knowledge_query}, "
                f"candidates_count={len(agent_candidates)}"
            )

        # 3. 選擇 Tool
        chosen_tools = []

        # 修改時間：2026-02-03 - 根據 Knowledge Signal 的 internal_only 字段調整 Tool 選擇
        # 如果是知識查詢，且 internal_only=True，則不選擇外部搜尋工具（優先內部知識庫）
        # 如果是知識查詢，且 internal_only=False，則可以選擇外部搜尋工具（fallback）
        is_internal_only = True  # 默認：優先內部知識庫
        if knowledge_signal_dict:
            is_internal_only = knowledge_signal_dict.get("internal_only", True)
            logger.info(f"Decision Engine: Knowledge Signal internal_only={is_internal_only}")

        if router_decision.needs_tools and tool_candidates:
            logger.info(f"Decision Engine: Selecting tools from {len(tool_candidates)} candidates")

            # 如果是內部優先模式（internal_only=True），過濾掉外部搜尋工具
            if is_internal_only:
                original_tool_count = len(tool_candidates)
                tool_candidates = [
                    t
                    for t in tool_candidates
                    if t.candidate_id not in ["web_search", "google_search", "bing_search"]
                ]
                if len(tool_candidates) < original_tool_count:
                    logger.info(
                        f"Decision Engine: Filtered out external search tools "
                        f"(internal_only=True, {original_tool_count - len(tool_candidates)} tools removed)"
                    )

            # 選擇評分最高的工具（可以選擇多個）
            sorted_tools = sorted(tool_candidates, key=lambda x: x.total_score, reverse=True)

            # 修改時間：2026-01-06 - 添加詳細日誌追蹤 document_editing 工具的選擇過程
            document_editing_candidate = next(
                (t for t in sorted_tools if t.candidate_id in ["document_editing", "file_editing"]),
                None,
            )
            if document_editing_candidate:
                logger.info(
                    "decision_engine_document_editing_candidate_found",
                    extra={
                        "tool_name": document_editing_candidate.candidate_id,
                        "total_score": document_editing_candidate.total_score,
                        "rank": sorted_tools.index(document_editing_candidate) + 1,
                        "total_candidates": len(sorted_tools),
                        "top_5_tools": [(t.candidate_id, t.total_score) for t in sorted_tools[:5]],
                        "note": f"document_editing tool candidate found with score {document_editing_candidate.total_score:.2f}, rank {sorted_tools.index(document_editing_candidate) + 1}/{len(sorted_tools)}",
                    },
                )
            else:
                logger.info(
                    "decision_engine_document_editing_candidate_not_found",
                    extra={
                        "top_5_tools": [(t.candidate_id, t.total_score) for t in sorted_tools[:5]],
                        "router_needs_tools": router_decision.needs_tools,
                        "router_intent_type": router_decision.intent_type,
                        "note": "document_editing tool not in candidates - check Capability Matcher logs",
                    },
                )

            logger.debug(
                f"Decision Engine: Top tool candidates: {[(t.candidate_id, t.total_score) for t in sorted_tools[:5]]}"
            )
            for tool in sorted_tools[:3]:  # 最多選擇 3 個工具
                if tool.total_score >= 0.5:  # 最低可接受評分
                    chosen_tools.append(tool.candidate_id)
                    reasoning_parts.append(
                        f"選擇 Tool: {tool.candidate_id} (評分: {tool.total_score:.2f})"
                    )
                    logger.info(
                        f"Decision Engine: Selected tool: {tool.candidate_id} (score: {tool.total_score:.2f})"
                    )

                    # 修改時間：2026-01-06 - 特別標記 document_editing 工具的選擇
                    if tool.candidate_id in ["document_editing", "file_editing"]:
                        logger.info(
                            "decision_engine_document_editing_tool_selected",
                            extra={
                                "tool_name": tool.candidate_id,
                                "total_score": tool.total_score,
                                "note": "✅ document_editing tool SELECTED by Decision Engine - file creation should be triggered",
                            },
                        )

            if not chosen_tools:
                logger.info("Decision Engine: No tools selected (all scores < 0.5)")
                # 修改時間：2026-01-06 - 如果沒有選擇工具，檢查 document_editing 是否因為評分太低
                if document_editing_candidate:
                    logger.warning(
                        "decision_engine_document_editing_not_selected_score_too_low",
                        extra={
                            "tool_name": document_editing_candidate.candidate_id,
                            "total_score": document_editing_candidate.total_score,
                            "threshold": 0.5,
                            "note": f"❌ document_editing tool NOT selected - score {document_editing_candidate.total_score:.2f} < threshold 0.5",
                        },
                    )
        else:
            logger.debug(
                f"Decision Engine: No tool selection - needs_tools={router_decision.needs_tools}, candidates_count={len(tool_candidates)}"
            )
            # 修改時間：2026-01-06 - 如果沒有工具候選，記錄詳細信息
            if not router_decision.needs_tools:
                logger.info(
                    "decision_engine_no_tool_selection_router_needs_tools_false",
                    extra={
                        "router_needs_tools": router_decision.needs_tools,
                        "router_intent_type": router_decision.intent_type,
                        "note": "❌ No tool selection - Router LLM set needs_tools=false, check Router LLM logs",
                    },
                )
            elif not tool_candidates:
                logger.info(
                    "decision_engine_no_tool_selection_no_candidates",
                    extra={
                        "router_needs_tools": router_decision.needs_tools,
                        "router_intent_type": router_decision.intent_type,
                        "note": "❌ No tool selection - No tool candidates from Capability Matcher, check Capability Matcher logs",
                    },
                )

        # 4. 選擇 Model
        chosen_model = None
        if model_candidates:
            best_model = max(model_candidates, key=lambda x: x.total_score)
            chosen_model = best_model.candidate_id
            reasoning_parts.append(
                f"選擇 Model: {chosen_model} (評分: {best_model.total_score:.2f})"
            )

        # 5. 計算總評分
        scores = []
        if chosen_agent:
            agent_match = next(
                (a for a in agent_candidates if a.candidate_id == chosen_agent), None
            )
            if agent_match:
                scores.append(agent_match.total_score)
        if chosen_tools:
            tool_scores = [
                next((t for t in tool_candidates if t.candidate_id == tool_id), None).total_score
                for tool_id in chosen_tools
                if next((t for t in tool_candidates if t.candidate_id == tool_id), None)
            ]
            if tool_scores:
                scores.append(sum(tool_scores) / len(tool_scores))
        if chosen_model:
            model_match = next(
                (m for m in model_candidates if m.candidate_id == chosen_model), None
            )
            if model_match:
                scores.append(model_match.total_score)

        overall_score = sum(scores) / len(scores) if scores else 0.5

        # 6. Fallback 檢查
        fallback_used = False
        if overall_score < 0.5:  # 最低可接受評分
            fallback_used = True
            reasoning_parts.append("評分過低，使用 Fallback 模式")
            # Fallback: 不使用 Agent，只使用基礎模型
            chosen_agent = None
            chosen_tools = []

        # 7. 構建決策結果
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "使用默認決策"

        result = DecisionResult(
            router_result=router_decision,
            chosen_agent=chosen_agent,
            chosen_tools=chosen_tools,
            chosen_model=chosen_model,
            score=overall_score,
            fallback_used=fallback_used,
            reasoning=reasoning,
        )

        logger.info(
            f"Decision made: agent={chosen_agent}, tools={chosen_tools}, "
            f"model={chosen_model}, score={overall_score:.2f}"
        )

        return result

    def _check_risk_level(self, candidate: CapabilityMatch, max_risk_level: str) -> bool:
        """
        檢查候選的風險等級

        Args:
            candidate: 候選匹配結果
            max_risk_level: 最大允許風險等級

        Returns:
            是否符合風險要求
        """
        # 簡化實現：從 metadata 中獲取風險等級（如果有的話）
        candidate_risk = candidate.metadata.get("risk_level", "low")

        risk_levels = {"low": 0, "mid": 1, "high": 2}
        return risk_levels.get(candidate_risk, 0) <= risk_levels.get(max_risk_level, 2)

    def _check_cost_constraint(self, candidate: CapabilityMatch, max_cost: str) -> bool:
        """
        檢查候選的成本約束

        Args:
            candidate: 候選匹配結果
            max_cost: 最大允許成本（low/medium/high）

        Returns:
            是否符合成本要求
        """
        # 簡化實現：根據 cost_score 判斷
        if max_cost == "low":
            return candidate.cost_score >= 0.7
        elif max_cost == "medium":
            return candidate.cost_score >= 0.5
        else:  # high
            return True  # 不限制

    def validate_dag(self, task_dag: TaskDAG) -> tuple[bool, List[str]]:
        """
        驗證 Task DAG 的合法性

        Args:
            task_dag: Task DAG 對象

        Returns:
            (是否有效, 錯誤信息列表)
        """
        errors: List[str] = []

        # 1. 檢查 task_graph 是否為空
        if not task_dag.task_graph:
            errors.append("Task DAG 為空")
            return False, errors

        # 2. 檢查任務 ID 唯一性
        task_ids = set()
        for task_node in task_dag.task_graph:
            if task_node.id in task_ids:
                errors.append(f"任務 ID 重複: {task_node.id}")
            task_ids.add(task_node.id)

        # 3. 檢查依賴關係
        for task_node in task_dag.task_graph:
            # 檢查依賴的任務是否存在
            for dep_id in task_node.depends_on:
                if dep_id not in task_ids:
                    errors.append(f"任務 {task_node.id} 依賴的任務 {dep_id} 不存在")

        # 4. 檢查循環依賴（簡單檢查）
        # 構建依賴圖
        dependency_graph: Dict[str, List[str]] = {}
        for task_node in task_dag.task_graph:
            dependency_graph[task_node.id] = task_node.depends_on

        # 使用 DFS 檢測循環
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node_id: str) -> bool:
            """檢測從 node_id 開始是否有循環"""
            visited.add(node_id)
            rec_stack.add(node_id)

            for dep_id in dependency_graph.get(node_id, []):
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    # 找到循環
                    errors.append(f"檢測到循環依賴: {node_id} -> {dep_id}")
                    return True

            rec_stack.remove(node_id)
            return False

        # 檢查所有節點
        for task_node in task_dag.task_graph:
            if task_node.id not in visited:
                has_cycle(task_node.id)

        # 5. 檢查 Capability 和 Agent 是否為空
        for task_node in task_dag.task_graph:
            if not task_node.capability:
                errors.append(f"任務 {task_node.id} 的 capability 為空")
            if not task_node.agent:
                errors.append(f"任務 {task_node.id} 的 agent 為空")

        is_valid = len(errors) == 0
        return is_valid, errors

    def decide_with_dag(
        self,
        router_decision: RouterDecision,
        task_dag: TaskDAG,
        context: Optional[Dict[str, Any]] = None,
    ) -> DecisionResult:
        """
        使用 Task DAG 進行決策（擴展版本）

        Args:
            router_decision: Router 決策
            task_dag: Task DAG
            context: 上下文信息

        Returns:
            決策結果
        """
        context = context or {}

        # 1. 驗證 DAG
        is_valid, errors = self.validate_dag(task_dag)
        if not is_valid:
            logger.warning(
                f"decision_engine_dag_validation_failed: {errors}",
            )
            return DecisionResult(
                router_result=router_decision,
                chosen_agent=None,
                chosen_tools=[],
                chosen_model=None,
                score=0.0,
                fallback_used=True,
                reasoning=f"DAG 驗證失敗: {'; '.join(errors)}",
            )

        # 2. L4 層級：策略驗證
        policy_service = get_policy_service()
        task_dag_dict = (
            task_dag.model_dump() if hasattr(task_dag, "model_dump") else task_dag.dict()
        )
        policy_result: PolicyValidationResult = policy_service.validate(task_dag_dict, context)

        # 如果策略驗證不通過，拒絕執行
        if not policy_result.allowed:
            logger.warning(
                f"decision_engine_policy_validation_failed: {policy_result.reasons}",
            )
            return DecisionResult(
                router_result=router_decision,
                chosen_agent=None,
                chosen_tools=[],
                chosen_model=None,
                score=0.0,
                fallback_used=True,
                reasoning=f"策略驗證失敗: {'; '.join(policy_result.reasons)}",
            )

        # 如果策略驗證要求確認，記錄日誌
        if policy_result.requires_confirmation:
            logger.info(
                f"decision_engine_policy_requires_confirmation: risk_level={policy_result.risk_level}, reasons={policy_result.reasons}",
            )

        # 3. 從 DAG 中提取 Agent 和 Capability 信息
        # 選擇第一個任務的 Agent（可以根據實際需求調整策略）
        chosen_agent = None
        if task_dag.task_graph:
            chosen_agent = task_dag.task_graph[0].agent

        # 4. 構建決策理由
        reasoning_parts = []
        reasoning_parts.append(f"使用 Task DAG 規劃，共 {len(task_dag.task_graph)} 個任務")
        if task_dag.reasoning:
            reasoning_parts.append(f"規劃理由: {task_dag.reasoning}")
        if policy_result.risk_level != "low":
            reasoning_parts.append(f"風險等級: {policy_result.risk_level}")
        if policy_result.requires_confirmation:
            reasoning_parts.append("需要用戶確認")

        # 5. 構建決策結果
        reasoning = "；".join(reasoning_parts) if reasoning_parts else "使用 Task DAG 規劃"

        result = DecisionResult(
            router_result=router_decision,
            chosen_agent=chosen_agent,
            chosen_tools=[],  # DAG 模式下，工具由 DAG 中的任務定義
            chosen_model=None,  # 可以根據需要選擇模型
            score=0.8,  # DAG 模式下的默認評分
            fallback_used=False,
            reasoning=reasoning,
        )

        logger.info(
            f"Decision made with DAG: agent={chosen_agent}, task_count={len(task_dag.task_graph)}, risk_level={policy_result.risk_level}",
        )

        return result
