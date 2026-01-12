# 代碼功能說明: Task Analyzer 核心邏輯實現（4 層漸進式路由架構）
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11 20:43

"""Task Analyzer 核心實現 - 整合任務分析、分類、路由和工作流選擇"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.task_analyzer.capability_matcher import CapabilityMatcher
from agents.task_analyzer.clarification import ClarificationService
from agents.task_analyzer.classifier import TaskClassifier
from agents.task_analyzer.decision_engine import DecisionEngine
from agents.task_analyzer.llm_router import LLMRouter
from agents.task_analyzer.models import (
    ConfigIntent,
    DecisionLog,
    DecisionResult,
    LLMProvider,
    LogQueryIntent,
    RouterDecision,
    RouterInput,
    TaskAnalysisRequest,
    TaskAnalysisResult,
    TaskClassificationResult,
    TaskType,
    WorkflowType,
)
from agents.task_analyzer.router_llm import RouterLLM
from agents.task_analyzer.routing_memory import RoutingMemoryService
from agents.task_analyzer.rule_override import RuleOverride
from agents.task_analyzer.workflow_selector import WorkflowSelector

logger = logging.getLogger(__name__)


class TaskAnalyzer:
    """Task Analyzer 核心類"""

    def __init__(self):
        """初始化 Task Analyzer"""
        self.classifier = TaskClassifier()
        self.workflow_selector = WorkflowSelector()
        self.llm_router = LLMRouter()
        # 新增組件
        self.router_llm = RouterLLM()
        self.rule_override = RuleOverride()
        self.capability_matcher = CapabilityMatcher()
        self.decision_engine = DecisionEngine()
        self.routing_memory = RoutingMemoryService()
        # 澄清服務
        self.clarification_service = ClarificationService()

    async def analyze(self, request: TaskAnalysisRequest) -> TaskAnalysisResult:
        """
        分析任務並返回分析結果

        Args:
            request: 任務分析請求

        Returns:
            任務分析結果
        """
        logger.info(f"Analyzing task: {request.task[:100]}...")

        # 生成任務ID
        task_id = str(uuid.uuid4())

        # ============================================
        # 前端指定Agent驗證（如果指定）
        # ============================================
        if request.specified_agent_id:
            validation_result = await self._validate_specified_agent(
                request.specified_agent_id, request.task, request.context
            )
            if not validation_result["valid"]:
                # 驗證失敗，返回錯誤結果
                logger.warning(f"Specified agent validation failed: {validation_result['error']}")
                return self._create_error_result(
                    task_id,
                    error_message=validation_result["error"],
                    suggested_agents=(
                        [request.specified_agent_id] if request.specified_agent_id else []
                    ),
                )

        # ============================================
        # Layer 0: Cheap Gating（快速過濾）
        # ============================================
        if self._is_simple_query(request.task):
            return await self._handle_simple_query(request, task_id)

        # ============================================
        # Layer 1: Fast Answer Layer（高級 LLM 直接回答）
        # ============================================
        direct_answer_result = await self._try_direct_answer(request, task_id)
        if direct_answer_result:
            logger.info(f"Layer 1: Direct answer returned for query: {request.task[:100]}...")
            return direct_answer_result  # 直接返回，不進入 Layer 2/3

        # ============================================
        # Layer 2: Semantic Intent Analysis（語義意圖分析）
        # ============================================
        # 步驟2: Router 前置 Recall（可選，提供 Context Bias）
        similar_decisions = []
        try:
            similar_decisions = await self.routing_memory.recall_similar_decisions(
                request.task, top_k=3, filters={"success": True}
            )
        except Exception as e:
            logger.warning(f"Failed to recall similar decisions: {e}")

        # 步驟3: Router LLM（意圖分類）
        router_input = RouterInput(
            user_query=request.task,
            session_context=request.context or {},
            system_constraints=self.rule_override.get_system_constraints(request.task),
        )

        logger.info(f"Layer 2: Calling Router LLM for query: {request.task[:100]}...")
        router_output = await self.router_llm.route(router_input, similar_decisions)

        # 修改時間：2026-01-06 - 添加詳細日誌追蹤 Router LLM 的語義分析結果
        # 修改時間：2026-01-06 - 修復：標準 logging 不支持關鍵字參數，使用 extra 字典
        logger.info(
            "router_llm_semantic_analysis_result",
            extra={
                "intent_type": router_output.intent_type,
                "needs_tools": router_output.needs_tools,
                "needs_agent": router_output.needs_agent,
                "complexity": router_output.complexity,
                "confidence": router_output.confidence,
                "determinism_required": router_output.determinism_required,
                "risk_level": router_output.risk_level,
                "user_query": request.task[:200],
                "note": "Router LLM semantic analysis - check if file generation intent detected (needs_tools=true, intent_type=execution)",
            },
        )

        logger.info(
            f"Layer 2: Router LLM output - intent_type={router_output.intent_type}, "
            f"needs_tools={router_output.needs_tools}, needs_agent={router_output.needs_agent}, "
            f"complexity={router_output.complexity}, confidence={router_output.confidence}"
        )

        # 步驟4: Rule Override（硬性規則覆蓋）
        router_output = self.rule_override.apply(router_output, request.task)
        logger.debug(
            f"Layer 2: After Rule Override - needs_tools={router_output.needs_tools}, needs_agent={router_output.needs_agent}"
        )

        # 步驟4.5: 文件編輯任務強制修正（確保 Router LLM 的判斷覆蓋 TaskClassifier）
        # 如果 Router LLM 識別為 execution 且包含文件編輯關鍵詞，強制設置 needs_agent=true
        # 同時，如果任務包含隱含編輯意圖關鍵詞，即使 intent_type 不是 execution，也應該修正為 execution
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
        ]
        # 隱含編輯意圖關鍵詞
        implicit_editing_keywords = [
            "幫我在文件中加入",
            "在文件裡添加",
            "在文件中添加",
            "把這個改成",
            "幫我整理一下這個文件",
            "優化這個代碼文件",
            "格式化整個文件",
            "在文件裡添加註釋",
            "幫我整理一下",
            "加入安裝說明",
            "添加註釋",
            "改成新的實現",
        ]
        task_lower = request.task.lower()
        is_file_editing = any(keyword in task_lower for keyword in file_editing_keywords)
        is_implicit_editing = any(keyword in task_lower for keyword in implicit_editing_keywords)

        logger.info(
            f"File editing detection: task='{request.task[:100]}...', "
            f"intent_type={router_output.intent_type}, "
            f"needs_agent={router_output.needs_agent}, "
            f"is_file_editing={is_file_editing}, "
            f"is_implicit_editing={is_implicit_editing}"
        )

        # 如果是文件編輯任務（明確或隱含），強制修正
        if (router_output.intent_type == "execution" and is_file_editing) or is_implicit_editing:
            # 如果是隱含編輯意圖但 intent_type 不是 execution，修正為 execution
            if is_implicit_editing and router_output.intent_type != "execution":
                logger.info(
                    f"Implicit file editing task detected, forcing intent_type=execution "
                    f"(query: {request.task[:100]}...)"
                )
                router_output = RouterDecision(
                    intent_type="execution",  # 強制設置為 execution
                    complexity=router_output.complexity,
                    needs_agent=True,  # 隱含編輯意圖也需要 agent
                    needs_tools=True,  # 隱含編輯意圖也需要工具
                    determinism_required=router_output.determinism_required,
                    risk_level=router_output.risk_level,
                    confidence=router_output.confidence,
                )
            elif router_output.intent_type == "execution" and is_file_editing:
                # 明確編輯意圖，但 needs_agent 可能是 False，需要強制設置為 True
                if not router_output.needs_agent:
                    logger.info(
                        f"File editing task detected, forcing needs_agent=true "
                        f"(query: {request.task[:100]}...)"
                    )
                    router_output = RouterDecision(
                        intent_type=router_output.intent_type,
                        complexity=router_output.complexity,
                        needs_agent=True,  # 強制設置為 True
                        needs_tools=router_output.needs_tools,
                        determinism_required=router_output.determinism_required,
                        risk_level=router_output.risk_level,
                        confidence=router_output.confidence,
                    )

        # ============================================
        # Layer 3: Decision Engine（完整決策引擎）
        # ============================================
        # 步驟5: Capability Matching（能力匹配）
        # 將查詢文本添加到 context 中，供 Capability Matcher 使用（特別是文件編輯任務檢測）
        enhanced_context = (request.context or {}).copy()
        enhanced_context["task"] = request.task
        enhanced_context["query"] = request.task
        # 使用增強後的 context 進行能力匹配
        agent_candidates = await self.capability_matcher.match_agents(
            router_output, enhanced_context
        )
        logger.info(
            f"Layer 3: Capability Matcher found {len(agent_candidates)} agent candidates: "
            f"{[c.candidate_id for c in agent_candidates[:5]]}"
        )
        tool_candidates = await self.capability_matcher.match_tools(router_output, enhanced_context)
        logger.info(
            f"Layer 3: Capability Matcher found {len(tool_candidates)} tool candidates: "
            f"{[c.candidate_id for c in tool_candidates[:5]]}"
        )
        model_candidates = await self.capability_matcher.match_models(
            router_output, request.context
        )
        logger.info(
            f"Layer 3: Capability Matcher found {len(model_candidates)} model candidates: "
            f"{[c.candidate_id for c in model_candidates[:5]]}"
        )

        # 步驟6: Decision Engine（綜合決策）
        logger.info(
            f"Layer 3: Calling Decision Engine with {len(agent_candidates)} agent candidates, "
            f"{len(tool_candidates)} tool candidates, {len(model_candidates)} model candidates"
        )
        decision_result = self.decision_engine.decide(
            router_output,
            agent_candidates,
            tool_candidates,
            model_candidates,
            enhanced_context,
        )
        logger.info(
            f"Layer 3: Decision Engine result - chosen_tools={decision_result.chosen_tools}, "
            f"chosen_agent={decision_result.chosen_agent}, chosen_model={decision_result.chosen_model}, "
            f"score={decision_result.score}, fallback_used={decision_result.fallback_used}"
        )

        # 步驟7: 傳統流程（向後兼容）
        # 任務分類
        classification = self.classifier.classify(
            request.task,
            request.context,
        )

        # 如果 Router LLM 識別為 execution，覆蓋 TaskClassifier 的結果
        # 優先信任 RouterLLM 的意圖識別結果，因為它更準確
        if router_output.intent_type == "execution":
            if classification.task_type != TaskType.EXECUTION:
                logger.info(
                    f"Overriding TaskClassifier result: {classification.task_type.value} -> execution "
                    f"(Router LLM intent_type=execution, query: {request.task[:100]}...)"
                )
                classification.task_type = TaskType.EXECUTION
                classification.confidence = max(classification.confidence, router_output.confidence)
                classification.reasoning = f"{classification.reasoning} (覆蓋：Router LLM 識別為 execution 意圖，置信度 {router_output.confidence:.2f})"

        # 工作流選擇
        workflow_selection = self.workflow_selector.select(
            classification,
            request.task,
            request.context,
        )

        # LLM 路由選擇（用於向後兼容）
        llm_routing = self.llm_router.route(
            classification,
            request.task,
            request.context,
        )

        # 判斷是否需要啟動 Agent（使用 Decision Engine 的結果）
        requires_agent = decision_result.chosen_agent is not None

        # 建議使用的 Agent 和工具列表（從 Decision Engine 獲取）
        suggested_agents = []
        if decision_result.chosen_agent:
            suggested_agents.append(decision_result.chosen_agent)
        suggested_tools = decision_result.chosen_tools

        # 提取意圖（保留原有邏輯）
        intent: Optional[Any] = None
        if classification.task_type == TaskType.LOG_QUERY:
            intent = self._extract_log_query_intent(request.task, request.context)
        elif self._is_config_operation(classification, request.task):
            intent = await self._extract_config_intent(
                request.task, classification, request.context
            )

        # 構建分析詳情
        analysis_details = {
            "classification": {
                "task_type": classification.task_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            },
            "workflow": {
                "workflow_type": workflow_selection.workflow_type.value,
                "confidence": workflow_selection.confidence,
                "reasoning": workflow_selection.reasoning,
                "config": workflow_selection.config,
            },
            "llm_routing": {
                "provider": llm_routing.provider.value,
                "model": llm_routing.model,
                "confidence": llm_routing.confidence,
                "reasoning": llm_routing.reasoning,
                "fallback_providers": [p.value for p in llm_routing.fallback_providers],
            },
            "router_decision": (
                router_output.model_dump()
                if hasattr(router_output, "model_dump")
                else router_output.dict()
                if hasattr(router_output, "dict")
                else router_output
            ),
            "decision_result": (
                decision_result.model_dump()
                if hasattr(decision_result, "model_dump")
                else decision_result.dict()
                if hasattr(decision_result, "dict")
                else decision_result
            ),
        }

        # 如果是混合模式，添加 strategy 信息
        if workflow_selection.workflow_type == WorkflowType.HYBRID and workflow_selection.strategy:
            strategy = workflow_selection.strategy
            analysis_details["workflow_strategy"] = {
                "mode": strategy.mode,
                "primary": strategy.primary.value,
                "fallback": [f.value for f in strategy.fallback],
                "switch_conditions": strategy.switch_conditions,
                "reasoning": strategy.reasoning,
            }

        # 計算整體置信度（取平均值）
        overall_confidence = (
            classification.confidence + workflow_selection.confidence + llm_routing.confidence
        ) / 3.0

        logger.info(
            f"Task analysis completed: task_id={task_id}, "
            f"type={classification.task_type.value}, "
            f"workflow={workflow_selection.workflow_type.value}, "
            f"llm={llm_routing.provider.value}, "
            f"requires_agent={requires_agent}"
        )

        # 將 intent 添加到 analysis_details 中
        if intent:
            analysis_details["intent"] = (
                intent.model_dump()
                if hasattr(intent, "model_dump")
                else intent.dict()
                if hasattr(intent, "dict")
                else intent
            )

            # 如果是 ConfigIntent，提取澄清信息並添加到分析詳情中
            if isinstance(intent, ConfigIntent):
                analysis_details["clarification_needed"] = intent.clarification_needed
                analysis_details["clarification_question"] = intent.clarification_question
                analysis_details["missing_slots"] = intent.missing_slots
                # 如果是配置操作，建議使用 System Config Agent
                if "system_config_agent" not in suggested_agents:
                    suggested_agents.insert(0, "system_config_agent")

        result = TaskAnalysisResult(
            task_id=task_id,
            task_type=classification.task_type,
            workflow_type=workflow_selection.workflow_type,
            llm_provider=llm_routing.provider,
            confidence=overall_confidence,
            requires_agent=requires_agent,
            analysis_details=analysis_details,
            suggested_agents=suggested_agents,
            router_decision=router_output,
            decision_result=decision_result,
            suggested_tools=suggested_tools,
        )

        # 步驟8: 異步記錄決策到 Routing Memory（不阻塞）
        try:
            decision_log = DecisionLog(
                decision_id=task_id,
                timestamp=datetime.utcnow(),
                query={"text": request.task},
                router_output=router_output,
                decision_engine=decision_result,
                execution_result=None,  # 執行結果在執行後更新
            )
            asyncio.create_task(self.routing_memory.record_decision(decision_log))
        except Exception as e:
            logger.warning(f"Failed to record decision to routing memory: {e}")

        return result

    def _is_simple_query(self, task: str) -> bool:
        """
        Layer 0: 判斷是否為簡單查詢（極簡單的情況，直接處理）

        Args:
            task: 任務描述

        Returns:
            是否為簡單查詢
        """
        # 簡單查詢的關鍵詞
        simple_keywords = ["你好", "hello", "hi", "謝謝", "thanks"]
        task_lower = task.lower().strip()

        # 檢查是否是簡單關鍵詞（完全匹配）
        if task_lower in simple_keywords:
            return True

        # 檢查長度（但必須排除需要工具的查詢）
        if len(task_lower) < 10:
            # 即使長度很短，如果包含工具指示詞，也不視為簡單查詢
            tool_indicators = [
                "股價",
                "股票",
                "天氣",
                "匯率",
                "時間",
                "時刻",
                "位置",
                "stock price",
                "weather",
                "exchange rate",
                "location",
                "time",
            ]
            if any(keyword in task_lower for keyword in tool_indicators):
                return False  # 需要工具，不是簡單查詢
            return True

        return False

    def _is_direct_answer_candidate(self, task: str) -> bool:
        """
        Layer 0: 判斷是否為 Direct Answer Candidate（可以用 LLM 直接回答的候選）

        Args:
            task: 任務描述

        Returns:
            是否為 Direct Answer Candidate
        """
        task_lower = task.lower().strip()

        # 定義工具指示詞（需要在多個地方使用）
        tool_indicators = [
            "股價",
            "股票",
            "天氣",
            "匯率",
            "時間",
            "時刻",
            "位置",
            "stock price",
            "weather",
            "exchange rate",
            "location",
            "time",
        ]

        # 定義動作關鍵詞（僅用於快速過濾明顯的系統行動，不應過度使用）
        # 修改時間：2026-01-06 - 移除文件生成關鍵詞檢查，改由 Router LLM 進行語義判斷
        action_keywords = ["幫我", "幫", "執行", "運行", "查詢", "獲取", "幫我查", "幫我找"]

        # 1. 檢查是否有明顯的副作用關鍵詞（需要系統行動）
        # 注意：這裡只檢查非常明顯的動作關鍵詞，文件生成等複雜意圖應由 Router LLM 語義分析判斷
        if any(keyword in task_lower for keyword in action_keywords):
            return False  # 需要系統行動，進入 Layer 2/3 進行語義分析

        # 2. 檢查是否涉及內部狀態/工具（需要工具）
        # 注意：這裡只檢查明確的工具需求（如時間、天氣），文件生成等應由 Router LLM 判斷
        if any(keyword in task_lower for keyword in tool_indicators):
            return False  # 需要工具，進入 Layer 2/3 進行語義分析

        # 3. 長度檢查（必須在工具檢查之後）
        if len(task_lower) < 10:
            return True

        # 4. Factoid / Definition 模式
        factoid_patterns = [
            r"什麼是\s*\w+",  # "什麼是 DevSecOps?"
            r"什麼叫\s*\w+",
            r"^[\w\s]+是哪家公司",  # "HCI 是哪家公司？"
            r"^[\w\s]+是什麼",
            r"^what is\s+\w+",
            r"^what are\s+\w+",
            r"^who is\s+\w+",
            r"^where is\s+\w+",
        ]
        if any(re.match(pattern, task_lower) for pattern in factoid_patterns):
            return True

        return True  # 默認：嘗試直接回答

    async def _try_direct_answer(
        self, request: TaskAnalysisRequest, task_id: str
    ) -> Optional[TaskAnalysisResult]:
        """
        Layer 1: Internal Knowledge / Embeddings / Retrieval（内部知识检索）

        优化策略（ChatGPT 优化流程）：
        1. 优先使用内部知识库检索（向量检索 + 知识图谱）
        2. 如果内部知识库可以回答 → 直接返回结果
        3. 如果内部知识库无法回答 → Fallback 到高级 LLM
        4. 如果 LLM 判断需要系统行动 → 进入 Layer 2/3

        Args:
            request: 任務分析請求
            task_id: 任務 ID

        Returns:
            如果能直接回答，返回結果；否則返回 None（進入 Layer 2/3）
        """
        # 先檢查是否為 Direct Answer Candidate
        is_direct_answer = self._is_direct_answer_candidate(request.task)
        logger.info(
            f"Layer 1: _is_direct_answer_candidate check - task='{request.task[:100]}...', result={is_direct_answer}"
        )
        if not is_direct_answer:
            logger.info(
                f"Layer 1: Not a direct answer candidate, entering Layer 2/3: {request.task[:100]}..."
            )
            return None  # 進入 Layer 2/3

        # ===== 步骤 1: 优先使用内部知识库检索 =====
        memory_result = None
        retrieval_context = None
        try:
            from services.api.services.chat_memory_service import get_chat_memory_service

            memory_service = get_chat_memory_service()
            user_id = request.context.get("user_id", "system") if request.context else "system"
            session_id = request.context.get("session_id", task_id) if request.context else task_id

            # 检索内部知识库（向量检索 + 知识图谱）
            memory_result = await memory_service.retrieve_for_prompt(
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                request_id=task_id,
                query=request.task,
                attachments=None,  # Layer 1 不处理附件
            )

            # 判断内部知识库是否足够回答
            # 如果检索到相关内容（memory_hit_count > 0 且相似度足够高），尝试直接回答
            if memory_result and memory_result.memory_hit_count > 0:
                logger.info(
                    f"Layer 1: Found {memory_result.memory_hit_count} relevant memories, "
                    f"attempting direct answer from internal knowledge"
                )

                # 使用检索到的内容构建回答
                # 这里可以进一步优化：使用小模型基于检索内容生成答案
                # 目前先 fallback 到 LLM，但将检索内容作为上下文
                retrieval_context = "\n".join(
                    [msg.get("content", "") for msg in memory_result.injection_messages]
                )

                # 如果检索内容足够丰富，可以尝试直接返回（简化版）
                # 这里我们仍然使用 LLM 来整合检索内容，但成本更低（因为有了上下文）
                # 未来可以进一步优化：使用小模型或规则引擎直接生成答案

        except Exception as e:
            logger.warning(
                f"Layer 1: Internal knowledge retrieval failed: {e}, falling back to LLM"
            )
            retrieval_context = None

        # ===== 步骤 2: Fallback 到高级 LLM（如果内部知识库无法回答） =====
        try:
            from llm.clients.factory import LLMClientFactory
            from services.api.models.llm_model import LLMProvider

            # 使用高級 LLM（優先 OpenAI，備選 Gemini）
            try:
                client = LLMClientFactory.create_client(LLMProvider.OPENAI, use_cache=True)
                model_name = "gpt-4o"
            except Exception:
                try:
                    client = LLMClientFactory.create_client(LLMProvider.GOOGLE, use_cache=True)
                    model_name = "gemini-1.5-pro"
                except Exception:
                    logger.warning("Failed to initialize high-end LLM, falling back to Layer 2/3")
                    return None

            # 構建 System Prompt（關鍵！）
            # 修改時間：2026-01-06 - 增強 System Prompt，明確說明文件生成需要系統行動
            system_prompt = """You are a helpful AI assistant.

Before answering, determine:
1. Does this question require real-time data or external tools?
2. Does this question require accessing internal system state?
3. Does this question require performing actions or operations?
4. Does this question require creating, generating, or editing files/documents?

If YES to any → Respond with ONLY: {"needs_system_action": true}
If NO → Answer the question directly and completely.

Examples:
- "什麼是 DevSecOps?" → Answer directly (provide definition and explanation)
- "台積電今天的股價" → {"needs_system_action": true} (requires real-time data)
- "幫我執行資料整合" → {"needs_system_action": true} (requires system operations)
- "幫我產生Data Agent文件" → {"needs_system_action": true} (requires file creation)
- "生成文件" → {"needs_system_action": true} (requires file creation)
- "幫我將說明做成文件" → {"needs_system_action": true} (requires file creation)
- "HCI 是哪家公司？" → Answer directly (provide company information)

Important:
- If you can answer the question using only your knowledge, answer it.
- If the user wants to CREATE, GENERATE, or EDIT files/documents, return {"needs_system_action": true}
- Only return {"needs_system_action": true} if you truly need external tools or system actions.

**Mermaid 圖表渲染要求**（如果回答中包含 Mermaid 圖表）：
- **版本要求**：使用 Mermaid 10.0 版本語法規範。
- **符號衝突處理**：節點標籤中包含特殊字符（如 `/`、`(`、`)`、`[`、`]`、`{`、`}`、`|`、`&`、`<`、`>` 等）時，必須使用雙引號包裹整個標籤文本。示例：`A["API/接口"]` 而不是 `A[API/接口]`。
- **段落換行**：節點標籤中的多行文本必須使用 `<br>` 標籤進行換行，不能使用 `\\n` 或直接換行。示例：`A["第一行<br>第二行"]`。
- **節點 ID 規範**：節點 ID 不能包含空格、特殊字符（如 `/`、`(`、`)` 等），建議使用下劃線或連字符：`api_gateway` 或 `api-gateway`。
- **引號轉義**：如果節點標籤中包含雙引號，需要使用轉義：`A["用戶說：\\"你好\\""]`。
- **避免保留字衝突**：避免使用 Mermaid 保留字（如 `style`、`classDef`、`click`、`link`、`class` 等）作為節點 ID 或類名。
- **語法檢查**：確保所有箭頭方向正確（`-->`、`<--`、`<-->`），確保子圖語法正確：`subgraph id["標籤"]`。"""

            # 如果有检索上下文，添加到消息中
            messages = [{"role": "system", "content": system_prompt}]
            if retrieval_context:
                messages.append(
                    {
                        "role": "system",
                        "content": f"以下是从内部知识库检索到的相关内容：\n{retrieval_context}\n\n请基于这些内容回答用户的问题。",
                    }
                )
            messages.append({"role": "user", "content": request.task})

            response = await client.chat(messages=messages, model=model_name)
            content = response.get("content", "")

            # 檢查是否需要系統行動
            if content.strip().startswith("{") and "needs_system_action" in content:
                try:
                    result_dict = json.loads(content.strip())
                    if result_dict.get("needs_system_action") is True:
                        logger.info("Layer 1: Needs system action, entering Layer 2/3")
                        return None  # 需要進入 Layer 2/3
                except (json.JSONDecodeError, KeyError):
                    pass

            # 直接回答成功
            from agents.task_analyzer.models import DecisionResult
            from agents.task_analyzer.models import LLMProvider as TaskLLMProvider
            from agents.task_analyzer.models import RouterDecision, TaskType, WorkflowType

            router_decision = RouterDecision(
                intent_type="conversation",
                complexity="low",
                needs_agent=False,
                needs_tools=False,
                determinism_required=False,
                risk_level="low",
                confidence=0.9,
            )

            decision_result = DecisionResult(
                router_result=router_decision,
                chosen_agent=None,
                chosen_tools=[],
                chosen_model=model_name,
                score=0.9,
                fallback_used=False,
                reasoning="Layer 1: Direct answer from internal knowledge + high-end LLM",
            )

            return TaskAnalysisResult(
                task_id=task_id,
                task_type=TaskType.QUERY,
                workflow_type=WorkflowType.LANGCHAIN,
                llm_provider=(
                    TaskLLMProvider.CHATGPT if "gpt" in model_name else TaskLLMProvider.GEMINI
                ),
                confidence=0.9,
                requires_agent=False,
                analysis_details={
                    "direct_answer": True,
                    "response": content,
                    "internal_knowledge_used": (
                        memory_result.memory_hit_count > 0 if memory_result is not None else False
                    ),
                    "layer": "layer_1_fast_answer",
                    "model": model_name,
                    "router_decision": (
                        router_decision.model_dump()
                        if hasattr(router_decision, "model_dump")
                        else (
                            router_decision.dict()
                            if hasattr(router_decision, "dict")
                            else router_decision
                        )
                    ),
                    "decision_result": (
                        decision_result.model_dump()
                        if hasattr(decision_result, "model_dump")
                        else (
                            decision_result.dict()
                            if hasattr(decision_result, "dict")
                            else decision_result
                        )
                    ),
                },
                suggested_agents=[],
                router_decision=router_decision,
                decision_result=decision_result,
                suggested_tools=[],
            )

        except Exception as e:
            logger.warning(f"Layer 1 failed, falling back to Layer 2/3: {e}")
            return None  # 失敗時進入 Layer 2/3

    async def _handle_simple_query(
        self, request: TaskAnalysisRequest, task_id: str
    ) -> TaskAnalysisResult:
        """
        處理簡單查詢（跳過 Router LLM）

        Args:
            request: 任務分析請求
            task_id: 任務 ID

        Returns:
            任務分析結果
        """
        from agents.task_analyzer.models import LLMProvider, RouterDecision, TaskType, WorkflowType

        # 使用默認配置
        router_decision = RouterDecision(
            intent_type="conversation",
            complexity="low",
            needs_agent=False,
            needs_tools=False,
            determinism_required=False,
            risk_level="low",
            confidence=1.0,
        )

        decision_result = DecisionResult(
            router_result=router_decision,
            chosen_agent=None,
            chosen_tools=[],
            chosen_model="ollama:llama2",
            score=1.0,
            fallback_used=False,
            reasoning="簡單查詢，使用默認配置",
        )

        return TaskAnalysisResult(
            task_id=task_id,
            task_type=TaskType.QUERY,
            workflow_type=WorkflowType.LANGCHAIN,
            llm_provider=LLMProvider.OLLAMA,
            confidence=1.0,
            requires_agent=False,
            analysis_details={
                "router_decision": (
                    router_decision.model_dump()
                    if hasattr(router_decision, "model_dump")
                    else (
                        router_decision.dict()
                        if hasattr(router_decision, "dict")
                        else router_decision
                    )
                ),
                "decision_result": (
                    decision_result.model_dump()
                    if hasattr(decision_result, "model_dump")
                    else (
                        decision_result.dict()
                        if hasattr(decision_result, "dict")
                        else decision_result
                    )
                ),
            },
            suggested_agents=[],
            router_decision=router_decision,
            decision_result=decision_result,
            suggested_tools=[],
        )

    def _should_use_agent(
        self,
        task_type: TaskType,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        判斷是否需要啟動 Agent

        Args:
            task_type: 任務類型
            task: 任務描述
            context: 上下文信息

        Returns:
            是否需要啟動 Agent
        """
        # 複雜任務、規劃任務、執行任務通常需要 Agent
        if task_type in [TaskType.COMPLEX, TaskType.PLANNING, TaskType.EXECUTION]:
            return True

        # 簡單查詢可能不需要 Agent
        if task_type == TaskType.QUERY:
            # 檢查任務複雜度
            complexity_keywords = [
                "多步驟",
                "多個",
                "綜合",
                "協作",
                "複雜",
                "multi-step",
                "multiple",
                "comprehensive",
                "collaborate",
                "complex",
            ]
            if any(keyword in task.lower() for keyword in complexity_keywords):
                return True
            return False

        # 審查任務通常需要 Agent
        if task_type == TaskType.REVIEW:
            return True

        # 默認需要 Agent
        return True

    def _suggest_agents(
        self,
        task_type: TaskType,
        workflow_type: Any,  # WorkflowType
    ) -> list[str]:
        """
        建議使用的 Agent 列表

        Args:
            task_type: 任務類型
            workflow_type: 工作流類型

        Returns:
            Agent 名稱列表
        """
        agents = []

        # 根據任務類型建議 Agent
        if task_type == TaskType.PLANNING:
            agents.append("planning_agent")
        if task_type == TaskType.EXECUTION:
            agents.append("execution_agent")
        if task_type == TaskType.REVIEW:
            agents.append("review_agent")

        # 複雜任務可能需要所有 Agent
        if task_type == TaskType.COMPLEX:
            agents.extend(["planning_agent", "execution_agent", "review_agent"])

        # 如果沒有特定建議，至少包含 orchestrator
        if not agents:
            agents.append("orchestrator")

        return agents

    def _extract_log_query_intent(
        self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> LogQueryIntent:
        """
        提取日誌查詢意圖

        從自然語言指令中提取日誌查詢參數（類型、時間範圍、執行者等）

        Args:
            task: 自然語言任務描述
            context: 上下文信息

        Returns:
            LogQueryIntent 對象
        """
        import re
        from datetime import datetime, timedelta

        task_lower = task.lower()

        # 識別日誌類型
        log_type = None
        if re.search(r"任務.*日誌|task.*log", task_lower):
            log_type = "TASK"
        elif re.search(r"審計.*日誌|audit.*log", task_lower):
            log_type = "AUDIT"
        elif re.search(r"安全.*日誌|security.*log", task_lower):
            log_type = "SECURITY"

        # 識別時間範圍
        start_time = None
        end_time = None

        # 昨天
        if re.search(r"昨天|yesterday", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=1)
        # 今天
        elif re.search(r"今天|today", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        # 最近 N 天/週/月
        elif match := re.search(r"最近\s*(\d+)\s*(天|週|月|day|week|month)", task_lower):
            days = int(match.group(1))
            unit = match.group(2)
            if unit in ["週", "week"]:
                days = days * 7
            elif unit in ["月", "month"]:
                days = days * 30
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
        # 上週/本月等
        elif re.search(r"上週|last.*week", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(weeks=1)
        elif re.search(r"本月|this.*month", task_lower):
            end_time = datetime.utcnow()
            start_time = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 識別執行者（actor）
        actor = None
        if match := re.search(r"(?:用戶|user|執行者|actor)\s*[:：]?\s*(\w+)", task_lower):
            actor = match.group(1)
        elif context and "user_id" in context:
            actor = context.get("user_id")

        # 識別租戶 ID
        tenant_id = None
        if match := re.search(r"(?:租戶|tenant)\s*[:：]?\s*(\w+)", task_lower):
            tenant_id = match.group(1)
        elif context and "tenant_id" in context:
            tenant_id = context.get("tenant_id")

        # 識別 trace_id
        trace_id = None
        if match := re.search(r"trace[_-]?id\s*[:：]?\s*([a-zA-Z0-9\-]+)", task_lower):
            trace_id = match.group(1)
        elif context and "trace_id" in context:
            trace_id = context.get("trace_id")

        # 識別限制數量
        limit = 100
        if match := re.search(r"(?:限制|limit|數量)\s*[:：]?\s*(\d+)", task_lower):
            limit = int(match.group(1))

        return LogQueryIntent(
            log_type=log_type,
            actor=actor,
            level=None,  # 日誌查詢的 level 是可選的
            tenant_id=tenant_id,
            user_id=context.get("user_id") if context else None,
            start_time=start_time,
            end_time=end_time,
            trace_id=trace_id,
            limit=limit,
        )

    def _is_config_operation(self, classification: TaskClassificationResult, task: str) -> bool:
        """
        判斷是否為配置操作

        Args:
            classification: 任務分類結果
            task: 任務描述

        Returns:
            是否為配置操作
        """
        config_keywords = [
            "配置",
            "設置",
            "系統設置",
            "config",
            "setting",
            "policy",
            "策略",
            "限流",
            "模型",
            "ontology",
            "知識架構",
        ]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in config_keywords)

    async def _extract_config_intent(
        self,
        instruction: str,
        classification: TaskClassificationResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConfigIntent:
        """
        提取配置操作意圖（使用 LLM）

        從自然語言指令中提取結構化的配置操作參數，生成 ConfigIntent 對象。

        Args:
            instruction: 自然語言指令
            classification: 任務分類結果
            context: 上下文信息

        Returns:
            ConfigIntent 對象
        """
        logger.info(f"Extracting config intent from instruction: {instruction[:100]}...")

        try:
            # 使用 LLM Router 選擇合適的模型
            llm_routing = self.llm_router.route(classification, instruction, context)

            # 獲取 LLM 客戶端
            from llm.clients.factory import LLMClientFactory
            from services.api.models.llm_model import LLMProvider as APILLMProvider

            # 將 llm_routing.provider (agents.task_analyzer.models.LLMProvider)
            # 轉換為 services.api.models.llm_model.LLMProvider
            provider_value = llm_routing.provider.value
            try:
                provider_enum = APILLMProvider(provider_value)
            except ValueError:
                # 如果轉換失敗，使用默認值
                provider_enum = APILLMProvider.OPENAI

            client = LLMClientFactory.create_client(provider_enum, use_cache=True)

            # 構建 System Prompt（詳細版本，參考 Orchestrator 規格書 3.1.4 節）
            system_prompt = """Role: 你是 AI-Box 的 Task Analyzer。
Objective: 分析管理員指令，提取系統設置所需的參數。

## 1. 識別動作 (Action)

- **query**: 查詢配置、查看狀態、讀取設置、顯示、查看、查詢
- **create**: 創建、新增、建立
- **update**: 修改、調整、變更、設定、改為、更新、設置
- **delete**: 刪除、移除、清除
- **list**: 列出、清單、有哪些、顯示所有
- **rollback**: 復原、回滾、撤銷、取消、恢復

## 2. 提取層級 (Level)

- **system**: 涉及「全系統」、「默認」、「全域」、「系統級」、「系統默認」
- **tenant**: 涉及「租戶」、「公司」、「Tenant ID」、「租戶級」、「tenant_xxx」
- **user**: 涉及「個人」、「特定用戶」、「用戶級」、「user_xxx」

## 3. 定義範圍 (Scope)

根據關鍵字歸類到對應的 scope：

- **genai.policy**: 模型、限流、API 限流、rate_limit、allowed_providers、allowed_models、default_model、GenAI 策略
- **genai.model_registry**: 模型註冊表、模型列表、model registry
- **genai.tenant_secrets**: API Key、密鑰、tenant secrets
- **llm.provider_config**: LLM 提供商、API 端點、provider config、endpoint
- **llm.moe_routing**: MoE 路由、模型路由、routing strategy
- **ontology.base**: Base Ontology、基礎知識架構、base ontology
- **ontology.domain**: Domain Ontology、領域知識架構、domain ontology
- **ontology.major**: Major Ontology、主要知識架構、major ontology
- **system.security**: 安全配置、安全策略、security policy
- **system.storage**: 存儲配置、存儲路徑、storage config
- **system.logging**: 日誌配置、日誌級別、logging config

## 4. 輸出格式要求

必須嚴格遵守 ConfigIntent 格式，返回 JSON：

```json
{
  "action": "query|create|update|delete|list|rollback",
  "scope": "genai.policy|llm.provider_config|ontology.base|...",
  "level": "system|tenant|user",
  "tenant_id": "tenant_xxx" | null,
  "user_id": "user_xxx" | null,
  "config_data": {...} | null,
  "clarification_needed": true|false,
  "clarification_question": "..." | null,
  "missing_slots": ["level", "config_data"] | [],
  "original_instruction": "原始指令"
}
```

## 5. 澄清機制

若資訊不足，請標註 `clarification_needed: true` 並生成 `clarification_question`。

常見缺失的槽位：
- **level**: 未明確指定是系統級、租戶級還是用戶級
- **scope**: 未明確指定配置範圍
- **config_data**: 更新操作時未明確指定要修改的具體配置項
- **tenant_id**: 租戶級操作時未指定租戶 ID
- **user_id**: 用戶級操作時未指定用戶 ID

## 6. 實務範例

**範例 1**：
指令：「幫我把租戶 A 的限流改為 500」
輸出：
```json
{
  "action": "update",
  "scope": "genai.policy",
  "level": "tenant",
  "tenant_id": "tenant_a",
  "config_data": {
    "rate_limit": 500
  },
  "clarification_needed": false,
  "missing_slots": [],
  "clarification_question": null,
  "original_instruction": "幫我把租戶 A 的限流改為 500"
}
```

**範例 2**：
指令：「查看系統的 LLM 配置」
輸出：
```json
{
  "action": "query",
  "scope": "genai.policy",
  "level": "system",
  "tenant_id": null,
  "user_id": null,
  "config_data": null,
  "clarification_needed": false,
  "missing_slots": [],
  "clarification_question": null,
  "original_instruction": "查看系統的 LLM 配置"
}
```

**範例 3**：
指令：「修改 LLM 配置」
輸出：
```json
{
  "action": "update",
  "scope": "genai.policy",
  "level": null,
  "tenant_id": null,
  "user_id": null,
  "config_data": null,
  "clarification_needed": true,
  "clarification_question": "請確認：1. 要修改哪一層配置？(系統級/租戶級/用戶級) 2. 要修改哪些具體配置項？",
  "missing_slots": ["level", "config_data"],
  "original_instruction": "修改 LLM 配置"
}
```

重要：必須只返回 JSON，不要包含任何其他文字或說明。"""

            # 構建用戶提示詞
            user_prompt = f"""分析以下配置操作指令，提取結構化意圖：

指令：{instruction}

請嚴格按照 System Prompt 的要求，返回符合 ConfigIntent 格式的 JSON。必須只返回 JSON，不要包含任何其他文字。"""

            # 構建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # 調用 LLM
            response = await client.chat(messages=messages, model=llm_routing.model)

            # 提取響應內容
            content = response.get("content") or response.get("text", "")
            if not content:
                raise ValueError("LLM 返回空響應")

            # 嘗試從響應中提取 JSON（可能包含 markdown 代碼塊）
            json_str = content.strip()
            if json_str.startswith("```"):
                # 移除 markdown 代碼塊標記
                json_str = re.sub(r"```(?:json)?\s*\n?", "", json_str)
                json_str = re.sub(r"\n?```\s*$", "", json_str).strip()

            # 解析 JSON
            try:
                intent_dict = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {json_str[:200]}")
                raise ValueError(f"LLM 返回的 JSON 格式錯誤: {e}") from e

            # 確保 original_instruction 字段存在
            if "original_instruction" not in intent_dict:
                intent_dict["original_instruction"] = instruction

            # 構建並返回 ConfigIntent
            config_intent = ConfigIntent(**intent_dict)

            logger.info(
                f"Config intent extracted: action={config_intent.action}, "
                f"scope={config_intent.scope}, level={config_intent.level}"
            )

            return config_intent

        except Exception as e:
            logger.error(f"Failed to extract config intent: {e}", exc_info=True)
            # 返回一個默認的 ConfigIntent，標記為需要澄清
            return ConfigIntent(
                action="query",
                scope="unknown",
                level=None,
                tenant_id=None,
                user_id=None,
                config_data=None,
                clarification_needed=True,
                clarification_question=f"無法解析配置指令，請提供更多信息。錯誤：{str(e)}",
                missing_slots=["scope", "level"],
                original_instruction=instruction,
            )

    async def _validate_specified_agent(
        self,
        agent_id: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        驗證前端指定的Agent

        Args:
            agent_id: Agent ID
            task: 任務描述
            context: 上下文信息

        Returns:
            驗證結果字典，包含 'valid' (bool) 和 'error' (str, 如果驗證失敗)
        """
        try:
            # 通過 Agent Registry 獲取 Agent 信息
            from agents.services.registry.models import AgentStatus
            from agents.services.registry.registry import get_agent_registry

            registry = get_agent_registry()
            agent_info = registry.get_agent_info(agent_id)

            # 檢查 Agent 是否存在
            if not agent_info:
                return {
                    "valid": False,
                    "error": f"指定的Agent '{agent_id}' 不存在",
                }

            # 檢查 Agent 狀態（必須為 ONLINE）
            if agent_info.status != AgentStatus.ONLINE:
                return {
                    "valid": False,
                    "error": f"指定的Agent '{agent_id}' 當前狀態為 {agent_info.status.value}，無法使用",
                }

            # 檢查 Agent 能力匹配（可選，如果需要）
            # 這裡可以添加更複雜的能力匹配邏輯
            # 例如：檢查 Agent 的能力是否匹配任務需求

            logger.info(f"Specified agent '{agent_id}' validation passed")
            return {"valid": True}

        except Exception as e:
            logger.error(f"Failed to validate specified agent: {e}", exc_info=True)
            return {
                "valid": False,
                "error": f"驗證Agent時發生錯誤：{str(e)}",
            }

    def _create_error_result(
        self,
        task_id: str,
        error_message: str,
        suggested_agents: Optional[List[str]] = None,
    ) -> TaskAnalysisResult:
        """
        創建錯誤結果

        Args:
            task_id: 任務ID
            error_message: 錯誤信息
            suggested_agents: 建議的Agent列表（可選）

        Returns:
            TaskAnalysisResult 對象（包含錯誤信息）
        """
        return TaskAnalysisResult(
            task_id=task_id,
            task_type=TaskType.QUERY,  # 默認類型
            workflow_type=WorkflowType.LANGCHAIN,  # 默認工作流
            llm_provider=LLMProvider.CHATGPT,  # 默認提供商
            confidence=0.0,
            requires_agent=False,
            analysis_details={
                "error": error_message,
                "error_type": "validation_error",
            },
            suggested_agents=suggested_agents or [],
            router_decision=None,
            decision_result=None,
            suggested_tools=[],
        )
