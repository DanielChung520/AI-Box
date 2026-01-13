# 代碼功能說明: 能力匹配器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""能力匹配器 - 匹配 Agent、Tool、Model 的能力"""

import logging
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import CapabilityMatch, RouterDecision
from services.api.models.llm_model import LLMProvider, ModelCapability, ModelStatus

logger = logging.getLogger(__name__)


class CapabilityMatcher:
    """能力匹配器類"""

    def __init__(self):
        """初始化能力匹配器"""
        self._agent_registry = None
        self._tool_registry = None
        self._agent_capability_retriever = None

    def _get_agent_registry(self):
        """獲取 Agent Registry（懶加載）"""
        if self._agent_registry is None:
            try:
                # 使用全局單例，而不是創建新實例，確保能訪問已註冊的 Agent
                from agents.services.registry.registry import get_agent_registry

                self._agent_registry = get_agent_registry()
            except Exception as e:
                logger.warning(f"Failed to get Agent Registry: {e}")
                self._agent_registry = None
        return self._agent_registry

    def _get_tool_registry(self):
        """獲取 Tool Registry（懶加載）"""
        if self._tool_registry is None:
            try:
                from tools.registry_loader import get_tools_for_task_analysis

                self._tool_registry = get_tools_for_task_analysis()
            except Exception as e:
                logger.warning(f"Failed to initialize Tool Registry: {e}")
                self._tool_registry = None
        return self._tool_registry

    def _get_agent_capability_retriever(self):
        """獲取 Agent 能力檢索服務（懶加載）"""
        if self._agent_capability_retriever is None:
            try:
                from agents.task_analyzer.agent_capability_retriever import AgentCapabilityRetriever

                self._agent_capability_retriever = AgentCapabilityRetriever()
            except Exception as e:
                logger.warning(f"Failed to initialize AgentCapabilityRetriever: {e}")
                self._agent_capability_retriever = None
        return self._agent_capability_retriever

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
            # 隱含編輯意圖動詞
            "加入",
            "改成",
            "整理",
            "優化",
            "調整",
            "改善",
            "改進",
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
            # 文件擴展名（用於識別文件操作）
            ".md",
            ".py",
            ".json",
            ".txt",
            ".yaml",
            ".yml",
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
            "improve",
            "optimize",
            "refactor",
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in file_editing_keywords)

    def _extract_required_capabilities(self, router_decision: RouterDecision) -> List[str]:
        """
        從 Router 決策中提取所需能力

        Args:
            router_decision: Router 決策

        Returns:
            所需能力列表
        """
        capabilities = []

        # 根據 intent_type 添加能力
        if router_decision.intent_type == "analysis":
            capabilities.append("analysis")
            capabilities.append("reasoning")
        elif router_decision.intent_type == "retrieval":
            capabilities.append("retrieval")
            capabilities.append("search")
        elif router_decision.intent_type == "execution":
            capabilities.append("execution")
            capabilities.append("action")

        # 根據 complexity 添加能力
        if router_decision.complexity == "high":
            capabilities.append("complex_reasoning")
            capabilities.append("multi_step")

        # 根據 determinism_required 添加能力
        if router_decision.determinism_required:
            capabilities.append("deterministic")

        return capabilities

    def _extract_required_model_capabilities(
        self, router_decision: RouterDecision
    ) -> List[ModelCapability]:
        """
        從 Router 決策中提取所需的模型能力

        Args:
            router_decision: Router 決策

        Returns:
            所需的 ModelCapability 列表
        """
        capabilities = []

        # 根據 intent_type 映射能力
        if router_decision.intent_type == "conversation":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.STREAMING)
        elif router_decision.intent_type == "retrieval":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.COMPLETION)
        elif router_decision.intent_type == "analysis":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.REASONING)
        elif router_decision.intent_type == "execution":
            capabilities.append(ModelCapability.CHAT)
            capabilities.append(ModelCapability.FUNCTION_CALLING)

        # 根據複雜度添加能力
        if router_decision.complexity == "high":
            capabilities.append(ModelCapability.REASONING)

        # 確保 CHAT 能力始終存在（所有任務都需要對話能力）
        if ModelCapability.CHAT not in capabilities:
            capabilities.append(ModelCapability.CHAT)

        return capabilities

    def _calculate_model_scores(
        self,
        model: Any,
        router_decision: RouterDecision,
        required_capabilities: List[ModelCapability],
    ) -> Dict[str, float]:
        """
        計算模型的各項評分

        Args:
            model: LLM 模型對象
            router_decision: Router 決策
            required_capabilities: 所需能力列表

        Returns:
            包含各項評分的字典
        """

        scores: Dict[str, float] = {}

        # 1. 能力匹配度
        model_capabilities = set(model.capabilities)
        required_set = set(required_capabilities)
        if required_set:
            capability_match = len(required_set.intersection(model_capabilities)) / len(
                required_set
            )
        else:
            capability_match = 0.5  # 如果沒有明確要求，給中等匹配度
        scores["capability_match"] = capability_match

        # 2. 成本評分（基於 provider 和 context_window）
        # 本地模型（OLLAMA）成本最低，大模型（context_window 大）成本較高
        if model.provider == LLMProvider.OLLAMA:
            cost_score = 0.95  # 本地模型成本最低
        elif model.context_window and model.context_window > 100000:
            cost_score = 0.5  # 大上下文窗口模型成本較高
        elif model.context_window and model.context_window > 32000:
            cost_score = 0.7
        else:
            cost_score = 0.8
        scores["cost_score"] = cost_score

        # 3. 延遲評分（基於 provider）
        # 本地模型延遲最低，雲服務延遲中等
        if model.provider == LLMProvider.OLLAMA:
            latency_score = 0.9  # 本地模型延遲最低
        else:
            latency_score = 0.7  # 雲服務延遲中等
        scores["latency_score"] = latency_score

        # 4. 歷史成功率（默認值，後續可從 Routing Memory 獲取）
        success_history = 0.8
        scores["success_history"] = success_history

        # 5. 穩定度（基於 status 和 provider）
        if model.status == ModelStatus.ACTIVE:
            if model.provider in [LLMProvider.OLLAMA, LLMProvider.OPENAI, LLMProvider.GOOGLE]:
                stability = 0.9  # 穩定提供商
            else:
                stability = 0.8
        else:
            stability = 0.5  # 非活躍狀態穩定性較低
        scores["stability"] = stability

        # 根據複雜度調整評分
        if router_decision.complexity == "high":
            # 複雜任務需要更強的能力匹配度
            scores["capability_match"] = min(scores["capability_match"] * 1.1, 1.0)
        elif router_decision.complexity == "low":
            # 簡單任務可以優先考慮成本
            scores["cost_score"] = min(scores["cost_score"] * 1.1, 1.0)

        return scores

    async def match_agents(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配 Agent 能力

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的 Agent 列表（按匹配度排序）
        """
        # 檢查是否為文件編輯任務
        user_query = context.get("task", "") or context.get("query", "") if context else ""
        is_file_editing = self._is_file_editing_task(user_query)

        logger.info(
            f"CapabilityMatcher.match_agents: user_query='{user_query[:100]}...', "
            f"is_file_editing={is_file_editing}, needs_agent={router_decision.needs_agent}"
        )

        # 如果是文件編輯任務，即使 needs_agent=False，也應該匹配對應的 Agent（md-editor, xls-editor 等）
        if not router_decision.needs_agent and not is_file_editing:
            logger.info(
                f"CapabilityMatcher.match_agents: Skipping agent matching "
                f"(needs_agent={router_decision.needs_agent}, is_file_editing={is_file_editing})"
            )
            return []

        # 如果是文件編輯任務，強制設置 needs_agent=True（臨時設置，不影響原始決策）
        if is_file_editing and not router_decision.needs_agent:
            logger.info(
                f"File editing task detected (query: {user_query[:100]}...), "
                "forcing needs_agent=true to match file editing agents"
            )

        registry = self._get_agent_registry()
        if registry is None:
            logger.warning("Agent Registry not available, returning empty list")
            return []

        try:
            from agents.services.registry.discovery import AgentDiscovery

            # 提取所需能力
            required_capabilities = self._extract_required_capabilities(router_decision)

            # 使用 RAG 檢索匹配的 Agent（方案2：RAG 增強）
            rag_matches = []
            retriever = self._get_agent_capability_retriever()
            if retriever:
                try:
                    rag_matches = await retriever.retrieve_matching_agents(
                        user_input=user_query,
                        intent_type=router_decision.intent_type,
                        top_k=5,
                    )
                    if rag_matches:
                        logger.info(
                            f"CapabilityMatcher: RAG retrieved {len(rag_matches)} matching agents: "
                            f"{[m['agent_id'] for m in rag_matches]}"
                        )
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}, falling back to registry matching")

            # 如果是文件編輯/轉換任務，需要發現 System Agent（md-editor, xls-editor, md-to-pdf, xls-to-pdf, pdf-to-md）
            # 注意：document-editing-agent 已棄用，不應被調用
            # 因此需要包括 System Agents（include_system_agents=True）
            # 對於其他任務，可以使用 AgentDiscovery（會過濾 System Agents）
            if is_file_editing:
                from agents.services.registry.models import AgentStatus

                # 文件編輯/轉換任務：同時查詢 document_editing 和 document_conversion 類型的 Agent
                # 這樣可以涵蓋編輯任務（md-editor, xls-editor）和轉換任務（md-to-pdf, xls-to-pdf, pdf-to-md）
                agents = []

                # 1. 查詢 document_editing 類型的 Agent（包括 md-editor, xls-editor）
                editing_agents = registry.list_agents(
                    agent_type="document_editing",
                    status=AgentStatus.ONLINE,
                    include_system_agents=True,  # 包括 System Agents
                )
                logger.info(
                    f"CapabilityMatcher: Query with agent_type='document_editing' found {len(editing_agents)} agents"
                )
                agents.extend(editing_agents)

                # 2. 查詢 document_conversion 類型的 Agent（包括 md-to-pdf, xls-to-pdf, pdf-to-md）
                conversion_agents = registry.list_agents(
                    agent_type="document_conversion",
                    status=AgentStatus.ONLINE,
                    include_system_agents=True,  # 包括 System Agents
                )
                logger.info(
                    f"CapabilityMatcher: Query with agent_type='document_conversion' found {len(conversion_agents)} agents"
                )
                agents.extend(conversion_agents)

                # 3. 去重（使用 agent_id 作為唯一標識）
                seen_ids = set()
                unique_agents = []
                for agent in agents:
                    if agent.agent_id not in seen_ids:
                        seen_ids.add(agent.agent_id)
                        unique_agents.append(agent)
                agents = unique_agents

                logger.info(
                    f"CapabilityMatcher: Total found {len(agents)} unique agents "
                    f"(document_editing: {len(editing_agents)}, document_conversion: {len(conversion_agents)})"
                )
                # 記錄所有找到的 Agent ID（用於調試）
                if agents:
                    agent_ids = [a.agent_id for a in agents]
                    logger.info(f"CapabilityMatcher: Found agent IDs: {agent_ids}")
                    # 記錄每個 Agent 的詳細信息
                    for agent in agents:
                        logger.debug(
                            f"CapabilityMatcher: Agent {agent.agent_id} "
                            f"(type: {agent.agent_type}, capabilities: {agent.capabilities})"
                        )
                else:
                    logger.warning("CapabilityMatcher: No agents found for file editing task!")

                # 如果沒有找到任何 Agent，嘗試查找所有類型（包括 System Agents）
                if not agents:
                    logger.info(
                        "CapabilityMatcher: No document_editing/conversion agents found, trying all types..."
                    )
                    agents = registry.list_agents(
                        status=AgentStatus.ONLINE,
                        include_system_agents=True,  # 包括 System Agents
                    )
                    logger.info(
                        f"CapabilityMatcher: Query without agent_type filter found {len(agents)} agents"
                    )
                    # 打印所有找到的 Agent 信息（用於診斷）
                    for agent in agents:
                        logger.info(
                            f"CapabilityMatcher: Found agent: {agent.agent_id} "
                            f"(type: {agent.agent_type}, status: {agent.status}, "
                            f"is_system_agent: {agent.is_system_agent})"
                        )
                # 過濾能力匹配
                # 注意：過濾掉已棄用的 document-editing-agent
                agents = [a for a in agents if a.agent_id != "document-editing-agent"]
                # 對於文件編輯/轉換任務，能力匹配應該更寬鬆
                # 因為文件編輯 Agent 的能力（如 document_editing, excel_editing）與通用能力（execution, action）可能不重疊
                # 如果 Agent 類型是 document_editing 或 document_conversion，則認為匹配
                if required_capabilities and agents:
                    required_set = set(required_capabilities)
                    # 先嘗試完全匹配
                    fully_matched = [
                        a
                        for a in agents
                        if required_set.issubset(set(a.capabilities))
                    ]
                    # 如果沒有完全匹配，對於文件編輯/轉換任務，允許類型匹配
                    if not fully_matched:
                        # 對於文件編輯任務，如果 Agent 類型是 document_editing 或 document_conversion，則匹配
                        type_matched = [
                            a
                            for a in agents
                            if a.agent_type in ["document_editing", "document_conversion"]
                        ]
                        if type_matched:
                            agents = type_matched
                            logger.info(
                                f"CapabilityMatcher: No full capability match, using type match for file editing task: "
                                f"{[a.agent_id for a in agents]}"
                            )
                        else:
                            # 最後嘗試部分能力匹配
                            agents = [
                                a
                                for a in agents
                                if required_set.intersection(set(a.capabilities))
                            ]
                            logger.info(
                                f"CapabilityMatcher: No type match, using partial capability match: "
                                f"{[a.agent_id for a in agents]}"
                            )
                    else:
                        agents = fully_matched
                logger.info(
                    f"File editing/conversion task: Found {len(agents)} agents (including System Agents) "
                    f"for query: {user_query[:100]}..."
                )
            else:
                # 非文件編輯任務：使用 AgentDiscovery（會過濾 System Agents）
                discovery = AgentDiscovery(registry)
                agents = discovery.discover_agents(
                    required_capabilities=required_capabilities if required_capabilities else None,
                    user_id=context.get("user_id") if context else None,
                    user_roles=context.get("user_roles") if context else None,
                )

            # 過濾掉已棄用的 document-editing-agent
            agents = [a for a in agents if a.agent_id != "document-editing-agent"]
            logger.debug(
                f"CapabilityMatcher: Filtered out document-editing-agent, remaining agents: "
                f"{[a.agent_id for a in agents]}"
            )
            
            # 計算匹配度
            matches = []
            for agent in agents:
                agent_capabilities = set(agent.capabilities)
                required_set = set(required_capabilities)

                # 檢查 RAG 匹配結果（方案2：RAG 增強）
                rag_score = 0.0
                rag_match = next((m for m in rag_matches if m["agent_id"] == agent.agent_id), None)
                if rag_match:
                    rag_score = rag_match["score"]
                    logger.debug(
                        f"CapabilityMatcher: Agent {agent.agent_id} has RAG score: {rag_score:.2f}"
                    )

                # 計算能力匹配度
                if required_set:
                    capability_match = len(required_set.intersection(agent_capabilities)) / len(
                        required_set
                    )
                else:
                    capability_match = 0.5  # 如果沒有明確要求，給中等匹配度

                # 融合 RAG 分數（如果有的話）
                if rag_score > 0:
                    # 使用加權平均：70% 能力匹配 + 30% RAG 分數
                    capability_match = 0.7 * capability_match + 0.3 * rag_score
                    logger.debug(
                        f"CapabilityMatcher: Agent {agent.agent_id} combined score: "
                        f"capability={capability_match:.2f}, RAG={rag_score:.2f}"
                    )

                # 簡化的評分（實際應該從歷史數據獲取）
                cost_score = 0.7  # 默認值
                latency_score = 0.7  # 默認值
                success_history = 0.8  # 默認值
                stability = 0.8  # 默認值

                # 計算總評分
                total_score = (
                    0.35 * capability_match
                    + 0.20 * cost_score
                    + 0.15 * latency_score
                    + 0.20 * success_history
                    + 0.10 * stability
                )

                matches.append(
                    CapabilityMatch(
                        candidate_id=agent.agent_id,
                        candidate_type="agent",
                        capability_match=capability_match,
                        cost_score=cost_score,
                        latency_score=latency_score,
                        success_history=success_history,
                        stability=stability,
                        total_score=total_score,
                        metadata={
                            "agent_type": agent.agent_type,
                            "capabilities": agent.capabilities,
                            "load": agent.load,
                        },
                    )
                )

            # 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            logger.info(f"Matched {len(matches)} agents for router decision")
            return matches

        except Exception as e:
            logger.error(f"Failed to match agents: {e}", exc_info=True)
            return []

    async def match_tools(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配工具能力

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的工具列表（按匹配度排序）
        """
        if not router_decision.needs_tools:
            return []

        registry = self._get_tool_registry()
        if registry is None:
            logger.warning("Tool Registry not available, returning empty list")
            return []

        try:
            tools = registry.get("tools", [])

            # 提取所需能力
            required_capabilities = self._extract_required_capabilities(router_decision)

            # 從 context 中獲取用戶查詢和 allowed_tools（用於基於查詢文本的匹配）
            user_query = ""
            if context:
                user_query = context.get("task", "") or context.get("query", "") or ""
            user_query_lower = user_query.lower() if user_query else ""

            # 修改時間：2026-01-06 - 從 context 中獲取 allowed_tools，優先考慮啟用的工具
            allowed_tools = context.get("allowed_tools", []) or [] if context else []
            has_file_editing_enabled = (
                "document_editing" in allowed_tools or "file_editing" in allowed_tools
            )

            # 修改時間：2026-01-06 - 添加詳細日誌追蹤文件編輯工具匹配
            # 修改時間：2026-01-06 - 修復：標準 logging 不支持關鍵字參數，使用 extra 字典
            logger.info(
                "capability_matcher_tool_matching_start",
                extra={
                    "router_needs_tools": router_decision.needs_tools,
                    "router_intent_type": router_decision.intent_type,
                    "allowed_tools": allowed_tools,
                    "has_file_editing_enabled": has_file_editing_enabled,
                    "user_query": user_query[:200],
                    "tools_count": len(tools),
                    "note": "Starting tool matching - checking if document_editing tool will be matched",
                },
            )

            matches = []
            for tool in tools:
                tool_name = tool.get("name", "")
                tool_category = tool.get("category", "")
                tool_purpose = tool.get("purpose", "")
                tool_use_cases = tool.get("use_cases", [])

                # 基於工具名稱和類別的匹配（優先級最高）
                name_category_match = 0.0

                # 修改時間：2026-01-06 - 如果 Assistant 啟用了文件編輯功能，優先考慮 document_editing 工具
                if tool_name in ["document_editing", "file_editing"] and has_file_editing_enabled:
                    # 如果 Assistant 啟用了文件編輯功能，且 Router LLM 判斷需要工具，優先匹配
                    if router_decision.needs_tools:
                        # Router LLM 通過語義分析識別出需要工具（包括文件創建/編輯）
                        # 優先級：如果啟用了文件編輯功能，優先考慮 document_editing 工具
                        if router_decision.intent_type == "execution":
                            # 執行操作（文件創建/編輯）= 完美匹配
                            name_category_match = 1.0
                            logger.info(
                                "document_editing_tool_perfect_match",
                                extra={
                                    "tool_name": tool_name,
                                    "intent_type": router_decision.intent_type,
                                    "name_category_match": name_category_match,
                                    "user_query": user_query[:200],
                                    "note": "Perfect match: execution intent + file editing enabled",
                                },
                            )
                        elif router_decision.intent_type in ["retrieval", "analysis"]:
                            # 檢索或分析操作，也可能需要文件編輯（如生成報告）
                            name_category_match = 0.95
                            logger.info(
                                "document_editing_tool_high_match",
                                extra={
                                    "tool_name": tool_name,
                                    "intent_type": router_decision.intent_type,
                                    "name_category_match": name_category_match,
                                    "user_query": user_query[:200],
                                    "note": "High match: retrieval/analysis intent + file editing enabled",
                                },
                            )
                        else:
                            # 其他操作，也可能需要文件編輯
                            name_category_match = 0.9
                            logger.info(
                                "document_editing_tool_good_match",
                                extra={
                                    "tool_name": tool_name,
                                    "intent_type": router_decision.intent_type,
                                    "name_category_match": name_category_match,
                                    "user_query": user_query[:200],
                                    "note": "Good match: other intent + file editing enabled",
                                },
                            )
                    else:
                        logger.info(
                            "document_editing_tool_not_matched_router_needs_tools_false",
                            extra={
                                "tool_name": tool_name,
                                "router_needs_tools": router_decision.needs_tools,
                                "user_query": user_query[:200],
                                "note": "Router LLM did not set needs_tools=true, skipping document_editing tool",
                            },
                        )
                elif (
                    tool_name in ["document_editing", "file_editing"]
                    and not has_file_editing_enabled
                ):
                    logger.info(
                        "document_editing_tool_not_enabled",
                        extra={
                            "tool_name": tool_name,
                            "allowed_tools": allowed_tools,
                            "user_query": user_query[:200],
                            "note": "document_editing tool not in allowed_tools, Assistant may not have file editing enabled",
                        },
                    )
                    # 修改時間：2026-01-06 - 即使文件編輯工具未啟用，如果查詢中包含文件相關關鍵詞，仍然應該匹配（fallback）
                    if any(
                        keyword in user_query_lower
                        for keyword in [
                            "做成一份文件",
                            "做成一份檔案",
                            "做成文件",
                            "做成檔案",
                            "做成一份",
                            "製作成文件",
                            "製作成檔案",
                            "製作文件",
                            "製作檔案",
                            "生成文件",
                            "生成檔案",
                            "產生文件",
                            "產生檔案",
                            "創建文件",
                            "創建檔案",
                            "建立文件",
                            "建立檔案",
                            "新增文件",
                            "新增檔案",
                            "寫成文件",
                            "寫成檔案",
                            "輸出成文件",
                            "輸出成檔案",
                            "整理成文件",
                            "整理成檔案",
                            "編輯文件",
                            "編輯檔案",
                            "修改文件",
                            "修改檔案",
                            "更新文件",
                            "更新檔案",
                        ]
                    ):
                        # 關鍵詞匹配（fallback，用於向後兼容）
                        name_category_match = 0.9

                elif tool_name == "datetime" and any(
                    keyword in user_query_lower
                    for keyword in [
                        "時間",
                        "時間",
                        "time",
                        "現在",
                        "此刻",
                        "當前",
                        "當前時間",
                        "現在幾點",
                    ]
                ):
                    # datetime 工具 + 時間查詢 = 完美匹配
                    name_category_match = 1.0
                elif tool_category == "時間與日期" and any(
                    keyword in user_query_lower
                    for keyword in ["時間", "時間", "time", "現在", "此刻", "當前", "日期", "date"]
                ):
                    # 時間類別工具 + 時間查詢 = 高匹配度
                    name_category_match = 0.9
                elif tool_name == "weather" and any(
                    keyword in user_query_lower
                    for keyword in ["天氣", "weather", "氣象", "溫度", "temperature"]
                ):
                    # weather 工具 + 天氣查詢 = 完美匹配
                    name_category_match = 1.0
                elif tool_category == "天氣" and any(
                    keyword in user_query_lower
                    for keyword in ["天氣", "weather", "氣象", "溫度", "temperature"]
                ):
                    # 天氣類別工具 + 天氣查詢 = 高匹配度
                    name_category_match = 0.9
                elif tool_category in ["文件編輯", "文檔編輯", "文件處理"] and any(
                    keyword in user_query_lower
                    for keyword in [
                        "做成",
                        "製作",
                        "生成",
                        "產生",
                        "創建",
                        "建立",
                        "新增",
                        "寫成",
                        "輸出成",
                        "整理成",
                        "編輯",
                        "修改",
                        "更新",
                        "文件",
                        "檔案",
                    ]
                ):
                    # 文件編輯類別工具 + 文件相關查詢 = 高匹配度
                    name_category_match = 0.9

                # 簡單的匹配邏輯：檢查工具用途和使用場景
                tool_capabilities = []
                if "搜索" in tool_purpose or "search" in tool_purpose.lower():
                    tool_capabilities.append("search")
                    tool_capabilities.append("retrieval")
                if "計算" in tool_purpose or "calculate" in tool_purpose.lower():
                    tool_capabilities.append("calculation")
                if "查詢" in tool_purpose or "query" in tool_purpose.lower():
                    tool_capabilities.append("query")
                    tool_capabilities.append("retrieval")
                if "時間" in tool_purpose or "時間" in tool_purpose or "time" in tool_purpose.lower():
                    tool_capabilities.append("time")
                    tool_capabilities.append("retrieval")
                if "天氣" in tool_purpose or "weather" in tool_purpose.lower():
                    tool_capabilities.append("weather")
                    tool_capabilities.append("retrieval")

                # 根據 intent_type 匹配
                if router_decision.intent_type == "retrieval" and "search" in tool_capabilities:
                    tool_capabilities.append("retrieval")
                if router_decision.intent_type == "analysis" and "calculation" in tool_capabilities:
                    tool_capabilities.append("analysis")

                # 計算能力匹配度
                if name_category_match > 0.0:
                    # 如果有名稱/類別匹配，優先使用（最高優先級）
                    capability_match = name_category_match
                elif required_capabilities:
                    tool_cap_set = set(tool_capabilities)
                    required_set = set(required_capabilities)
                    capability_match = len(required_set.intersection(tool_cap_set)) / len(
                        required_set
                    )
                else:
                    # 如果沒有明確要求，根據 determinism_required 判斷
                    if router_decision.determinism_required:
                        # 確定性工具通常有明確的輸入輸出
                        capability_match = 0.6
                    else:
                        capability_match = 0.4

                # 簡化的評分
                cost_score = 0.9  # 工具通常成本較低
                latency_score = 0.8  # 工具通常延遲較低
                success_history = 0.85  # 默認值
                stability = 0.9  # 工具通常較穩定

                # 計算總評分
                total_score = (
                    0.35 * capability_match
                    + 0.20 * cost_score
                    + 0.15 * latency_score
                    + 0.20 * success_history
                    + 0.10 * stability
                )

                match_obj = CapabilityMatch(
                    candidate_id=tool_name,
                    candidate_type="tool",
                    capability_match=capability_match,
                    cost_score=cost_score,
                    latency_score=latency_score,
                    success_history=success_history,
                    stability=stability,
                    total_score=total_score,
                    metadata={
                        "category": tool.get("category"),
                        "purpose": tool_purpose,
                        "use_cases": tool_use_cases,
                    },
                )
                matches.append(match_obj)

                # 修改時間：2026-01-06 - 添加詳細日誌追蹤 document_editing 工具的匹配結果
                if tool_name in ["document_editing", "file_editing"]:
                    logger.info(
                        "document_editing_tool_match_result",
                        extra={
                            "tool_name": tool_name,
                            "total_score": total_score,
                            "capability_match": capability_match,
                            "name_category_match": name_category_match,
                            "cost_score": cost_score,
                            "latency_score": latency_score,
                            "success_history": success_history,
                            "stability": stability,
                            "router_needs_tools": router_decision.needs_tools,
                            "router_intent_type": router_decision.intent_type,
                            "has_file_editing_enabled": has_file_editing_enabled,
                            "user_query": user_query[:200],
                            "note": f"document_editing tool match result - score: {total_score:.2f}, will be selected if >= 0.5",
                        },
                    )

            # 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            # 修改時間：2026-01-06 - 添加詳細日誌追蹤工具匹配結果
            document_editing_match = next(
                (m for m in matches if m.candidate_id in ["document_editing", "file_editing"]),
                None,
            )
            if document_editing_match:
                logger.info(
                    "document_editing_tool_matched_in_results",
                    extra={
                        "tool_name": document_editing_match.candidate_id,
                        "total_score": document_editing_match.total_score,
                        "rank": matches.index(document_editing_match) + 1,
                        "total_matches": len(matches),
                        "top_3_tools": [(m.candidate_id, m.total_score) for m in matches[:3]],
                        "user_query": user_query[:200],
                        "note": f"document_editing tool matched with score {document_editing_match.total_score:.2f}, rank {matches.index(document_editing_match) + 1}/{len(matches)}",
                    },
                )
            else:
                logger.info(
                    "document_editing_tool_not_matched",
                    extra={
                        "top_3_tools": (
                            [(m.candidate_id, m.total_score) for m in matches[:3]]
                            if matches
                            else []
                        ),
                        "router_needs_tools": router_decision.needs_tools,
                        "router_intent_type": router_decision.intent_type,
                        "has_file_editing_enabled": has_file_editing_enabled,
                        "allowed_tools": allowed_tools,
                        "user_query": user_query[:200],
                        "note": "document_editing tool not matched - check if Assistant enabled file editing or Router LLM set needs_tools=true",
                    },
                )

            logger.info(f"Matched {len(matches)} tools for router decision")
            return matches

        except Exception as e:
            logger.error(f"Failed to match tools: {e}", exc_info=True)
            return []

    async def match_models(
        self, router_decision: RouterDecision, context: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        匹配模型能力 - 改進版本

        Args:
            router_decision: Router 決策
            context: 上下文信息

        Returns:
            匹配的模型列表（按匹配度排序）
        """
        try:
            from services.api.models.llm_model import LLMModelQuery
            from services.api.services.llm_model_service import LLMModelService

            # 1. 從 ArangoDB 獲取所有可用模型
            model_service = LLMModelService()
            query = LLMModelQuery(
                status=ModelStatus.ACTIVE,
                limit=1000,  # 獲取所有可用模型
            )
            all_models = model_service.get_all(query)

            if not all_models:
                logger.warning("No active models found in database")
                return []

            # 2. 提取所需能力
            required_capabilities = self._extract_required_model_capabilities(router_decision)

            # 3. 計算每個模型的匹配度和評分
            matches = []
            for model in all_models:
                # 計算各項評分
                scores = self._calculate_model_scores(model, router_decision, required_capabilities)

                # 計算總評分（使用與 Agent/Tool 相同的權重）
                total_score = (
                    0.35 * scores["capability_match"]
                    + 0.20 * scores["cost_score"]
                    + 0.15 * scores["latency_score"]
                    + 0.20 * scores["success_history"]
                    + 0.10 * scores["stability"]
                )

                # 構建候選 ID（格式：provider:model_id）
                candidate_id = f"{model.provider.value}:{model.model_id}"

                matches.append(
                    CapabilityMatch(
                        candidate_id=candidate_id,
                        candidate_type="model",
                        capability_match=scores["capability_match"],
                        cost_score=scores["cost_score"],
                        latency_score=scores["latency_score"],
                        success_history=scores["success_history"],
                        stability=scores["stability"],
                        total_score=total_score,
                        metadata={
                            "provider": model.provider.value,
                            "model_id": model.model_id,
                            "model_name": model.name,
                            "capabilities": [cap.value for cap in model.capabilities],
                            "context_window": model.context_window,
                            "status": model.status.value,
                            "is_default": model.is_default,
                        },
                    )
                )

            # 4. 按總評分排序
            matches.sort(key=lambda x: x.total_score, reverse=True)

            logger.info(
                f"Matched {len(matches)} models for router decision "
                f"(intent={router_decision.intent_type}, complexity={router_decision.complexity})"
            )

            return matches

        except Exception as e:
            logger.error(f"Failed to match models: {e}", exc_info=True)
            # 失敗時返回空列表，而不是使用舊的 LLMRouter 邏輯
            return []
