# 代碼功能說明: OrchestratorService - 統一意圖分類與調度服務
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""OrchestratorService - 統一意圖分類與調度服務

使用 OrchestratorIntentRAG 作為第一層意圖分類器，根據分類結果調度到
相應的處理策略：直接回覆、知識庫查詢、轉發到 Agent、或 LLM Fallback。
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from api.routers.chat_module.config import ChatConfig, IntentResult, IntentStrategy
from api.routers.chat import _get_endpoint_url
from services.api.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class OrchestratorService:
    """OrchestratorService - 統一意圖分類與調度"""

    def __init__(self):
        """初始化 OrchestratorService"""
        self.intent_rag = None
        self._init_intent_rag()

    def _init_intent_rag(self):
        """初始化 OrchestratorIntentRAG"""
        try:
            from agents.services.orchestrator_intent_rag_client import (
                get_orchestrator_intent_rag,
            )

            self.intent_rag = get_orchestrator_intent_rag()
            logger.info("[OrchestratorService] OrchestratorIntentRAG 初始化成功")
        except Exception as e:
            logger.warning(f"[OrchestratorService] 無法初始化 OrchestratorIntentRAG: {e}")

    async def process(
        self,
        messages: List[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理聊天請求

        Args:
            messages: 訊息列表
            config: ChatConfig 配置
            context: 上下文資訊

        Returns:
            處理結果字典
        """
        # Step 1: 提取用戶輸入
        user_text = self._extract_user_text(messages)
        if not user_text:
            return {
                "content": "抱歉，我無法理解您的輸入。",
                "intent": {},
                "strategy": IntentStrategy.DIRECT_RESPONSE.value,
            }

        logger.info(
            f"[OrchestratorService] 處理請求: {user_text[:50]}..., config={config.model_dump()}"
        )

        # Step 2: 意圖分類 (OrchestratorIntentRAG)
        intent_result = await self._classify_intent(user_text, config)

        logger.info(
            f"[OrchestratorService] intent: {intent_result.intent_name}, "
            f"strategy: {intent_result.action_strategy}, score: {intent_result.score:.2f}"
        )

        # Step 3: 根據策略調度外部服務
        if intent_result.action_strategy == IntentStrategy.DIRECT_RESPONSE:
            return await self._handle_direct_response(intent_result, context)

        elif intent_result.action_strategy == IntentStrategy.KNOWLEDGE_RAG:
            return await self._route_to_ka_agent(
                user_text, intent_result, messages, config, context
            )

        elif intent_result.action_strategy == IntentStrategy.ROUTE_TO_AGENT:
            return await self._route_to_bpa(user_text, intent_result, messages, config, context)

        elif intent_result.action_strategy == IntentStrategy.ROUTE_TO_SPECIFIC_AGENT:
            return await self._route_to_specific_agent(
                user_text, intent_result, messages, config, context
            )

        else:
            # Fallback: 調用 MoE (LLM)
            return await self._route_to_llm(user_text, intent_result, messages, config, context)

    def _extract_user_text(self, messages: List[ChatMessage]) -> str:
        """從訊息列表中提取最後的用戶輸入"""
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                return msg.content
        return ""

    async def _classify_intent(self, user_text: str, config: ChatConfig) -> IntentResult:
        """使用 OrchestratorIntentRAG 進行意圖分類"""
        if not config.intent_rag_enabled:
            return IntentResult(
                intent_name="UNKNOWN",
                description="意圖分類未啟用",
                priority=99,
                action_strategy=IntentStrategy.LLM_FALLBACK,
                response_template="",
                score=0.0,
            )

        try:
            result = self.intent_rag.sync_classify(user_text)

            if result is None:
                logger.warning("[OrchestratorService] OrchestratorIntentRAG 返回 None")
                return IntentResult(
                    intent_name="UNKNOWN",
                    description="無法識別意圖",
                    priority=99,
                    action_strategy=IntentStrategy.LLM_FALLBACK,
                    response_template="",
                    score=0.0,
                )

            # 檢查置信度
            if result.score < config.intent_threshold:
                logger.info(f"[OrchestratorService] 置信度低，使用 LLM fallback")
                return IntentResult(
                    intent_name=result.intent_name,
                    description=result.description,
                    priority=result.priority,
                    action_strategy=IntentStrategy.LLM_FALLBACK,
                    response_template=result.response_template,
                    score=result.score,
                )

            # 映射 action_strategy
            strategy = self._map_strategy(result.action_strategy.value)

            return IntentResult(
                intent_name=result.intent_name,
                description=result.description,
                priority=result.priority,
                action_strategy=strategy,
                response_template=result.response_template,
                score=result.score,
            )

        except Exception as e:
            logger.error(f"[OrchestratorService] 意圖分類失敗: {e}")
            return IntentResult(
                intent_name="UNKNOWN",
                description=f"意圖分類錯誤: {str(e)}",
                priority=99,
                action_strategy=IntentStrategy.LLM_FALLBACK,
                response_template="",
                score=0.0,
            )

    def _map_strategy(self, action_strategy: str) -> IntentStrategy:
        """映射 action_strategy 字串到 IntentStrategy 枚舉"""
        strategy_map = {
            "DIRECT_RESPONSE": IntentStrategy.DIRECT_RESPONSE,
            "direct_response": IntentStrategy.DIRECT_RESPONSE,
            "KNOWLEDGE_RAG": IntentStrategy.KNOWLEDGE_RAG,
            "knowledge_rag": IntentStrategy.KNOWLEDGE_RAG,
            "ROUTE_TO_BPA": IntentStrategy.ROUTE_TO_AGENT,
            "route_to_bpa": IntentStrategy.ROUTE_TO_AGENT,
            "route_to_agent": IntentStrategy.ROUTE_TO_AGENT,
            "ROUTE_TO_SPECIFIC_AGENT": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT,
            "route_to_specific_agent": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT,
            "LLM_FALLBACK": IntentStrategy.LLM_FALLBACK,
            "llm_fallback": IntentStrategy.LLM_FALLBACK,
        }
        return strategy_map.get(action_strategy, IntentStrategy.LLM_FALLBACK)

    async def _handle_direct_response(
        self, intent_result: IntentResult, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """處理直接回覆"""
        content = intent_result.response_template or "您好！請告訴我可以如何幫助您。"

        return {
            "content": content,
            "intent": intent_result.model_dump(),
            "strategy": IntentStrategy.DIRECT_RESPONSE.value,
        }

    async def _route_to_ka_agent(
        self,
        user_text: str,
        intent_result: IntentResult,
        messages: List[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """調用 KA-Agent (知識庫)"""
        logger.info(f"[OrchestratorService] 調用 KA-Agent")

        try:
            from api.routers.chat_module.services.external_client import (
                get_ka_agent_client,
            )

            client = get_ka_agent_client()
            result = await client.query(
                query=user_text,
                session_id=context.get("session_id"),
                user_id=context.get("user_id"),
            )

            # 提取內容
            content = result.get("data", {}).get("answer") or result.get("message", "")
            if not content:
                content = "[知識庫無回覆]"

            return {
                "content": content,
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.KNOWLEDGE_RAG.value,
                "agent_type": "ka",
                "routing": {"provider": "ka-agent"},
            }

        except Exception as e:
            logger.error(f"[OrchestratorService] KA-Agent 調用失敗: {e}")
            return {
                "content": f"[知識庫服務錯誤: {str(e)}]",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.KNOWLEDGE_RAG.value,
            }

    async def _route_to_bpa(
        self,
        user_text: str,
        intent_result: IntentResult,
        messages: List[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """調用 BPA (業務代理)

        流程：
        1. 從 context 獲取前端指定的 agent_id
        2. 如果沒有 agent_id，返回提示訊息讓用戶選擇
        3. 通過 _get_endpoint_url 獲取 endpoint
        4. 通過 endpoint_url 動態調用 BPA Agent
        """
        logger.info(f"[OrchestratorService] 調用 BPA")

        # 從 context 獲取前端指定的 agent_id
        agent_id = context.get("agent_id")

        # 檢查是否有指定 agent_id
        if not agent_id:
            # 返回提示訊息，讓用戶選擇 Agent
            logger.info("[OrchestratorService] 未指定 agent_id，返回提示訊息")
            return {
                "content": "抱歉，您的問題必須指定業務代理（Agent）進行回答，請您選取業務代理，確認後，重新詢問",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_AGENT.value,
                "needs_agent_selection": True,
            }

        # 通過 _get_endpoint_url 獲取 endpoint
        endpoint_url = _get_endpoint_url(agent_id)
        if not endpoint_url:
            logger.error(f"[OrchestratorService] Agent endpoint not found: {agent_id}")
            return {
                "content": f"找不到 Agent [{agent_id}] 的端點配置，請確認該 Agent 是否已正確註冊",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_AGENT.value,
                "needs_agent_selection": True,
            }

        logger.info(f"[OrchestratorService] 調用 BPA Agent: {agent_id}, endpoint: {endpoint_url}")

        # 通過 endpoint_url 動態調用 BPA Agent
        try:
            result = await self._call_bpa_agent(
                endpoint_url=endpoint_url,
                instruction=user_text,
                context=context,
            )

            # 提取內容
            if isinstance(result, dict):
                content = (
                    result.get("data", {}).get("content")
                    or result.get("message")
                    or result.get("content", "")
                    or result.get("result", {}).get("response", "")
                )
            else:
                content = str(result)

            if not content:
                content = f"[{agent_id} 無回覆]"

            return {
                "content": content,
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_AGENT.value,
                "agent_type": "bpa",
                "agent_id": agent_id,
                "routing": {"provider": "bpa", "agent": agent_id, "endpoint": endpoint_url},
            }

        except Exception as e:
            logger.error(f"[OrchestratorService] BPA 調用失敗: {e}")
            return {
                "content": f"[{agent_id}] 服務錯誤: {str(e)}",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_AGENT.value,
                "agent_type": "bpa",
                "agent_id": agent_id,
                "error": str(e),
            }

    async def _call_bpa_agent(
        self,
        endpoint_url: str,
        instruction: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通過 endpoint_url 動態調用 BPA Agent"""
        payload = {
            "task_id": f"bpa-{context.get('session_id', 'unknown')}",
            "task_data": {"instruction": instruction},
            "metadata": {
                "session_id": context.get("session_id"),
                "user_id": context.get("user_id"),
                "tenant_id": context.get("tenant_id"),
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{endpoint_url}/execute", json=payload)
            response.raise_for_status()
            return response.json()

    async def _route_to_specific_agent(
        self,
        user_text: str,
        intent_result: IntentResult,
        messages: List[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """調用指定的 Agent"""
        logger.info(f"[OrchestratorService] 調用指定 Agent")

        # 從 context 獲取前端指定的 agent_id
        agent_id = context.get("agent_id")

        # 檢查是否有指定 agent_id
        if not agent_id:
            return {
                "content": "抱歉，您的問題必須指定業務代理（Agent）進行回答，請您選取業務代理，確認後，重新詢問",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT.value,
                "needs_agent_selection": True,
            }

        # 通過 _get_endpoint_url 獲取 endpoint
        endpoint_url = _get_endpoint_url(agent_id)
        if not endpoint_url:
            return {
                "content": f"找不到 Agent [{agent_id}] 的端點配置",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT.value,
                "needs_agent_selection": True,
            }

        try:
            result = await self._call_bpa_agent(
                endpoint_url=endpoint_url,
                instruction=user_text,
                context=context,
            )

            content = result.get("data", {}).get("content") or result.get("message", "")
            if not content:
                content = f"[{agent_id} 無回覆]"

            return {
                "content": content,
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT.value,
                "agent_type": "specific",
                "agent_id": agent_id,
                "routing": {"provider": "agent", "agent": agent_id},
            }

        except Exception as e:
            logger.error(f"[OrchestratorService] 指定 Agent 調用失敗: {e}")
            return {
                "content": f"[{agent_id}] 服務錯誤: {str(e)}",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.ROUTE_TO_SPECIFIC_AGENT.value,
            }

    async def _route_to_llm(
        self,
        user_text: str,
        intent_result: IntentResult,
        messages: List[ChatMessage],
        config: ChatConfig,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """調用 LLM (MoE)"""
        logger.info(f"[OrchestratorService] 調用 LLM (MoE)")

        try:
            from api.routers.chat_module.services.external_client import get_moe_client

            client = get_moe_client()

            # 構建訊息格式
            chat_messages = [{"role": m.role, "content": m.content} for m in messages]

            result = await client.chat(
                messages=chat_messages,
                model="auto",
                temperature=0.7,
            )

            content = result.get("content", "")
            if not content:
                content = "抱歉，服務暫時不可用。"

            return {
                "content": content,
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.LLM_FALLBACK.value,
                "routing": {"provider": "moe", "model": "auto"},
            }

        except Exception as e:
            logger.error(f"[OrchestratorService] LLM 調用失敗: {e}")
            return {
                "content": "抱歉，服務暫時不可用。",
                "intent": intent_result.model_dump(),
                "strategy": IntentStrategy.LLM_FALLBACK.value,
                "error": str(e),
            }


# 全局實例
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service() -> OrchestratorService:
    """獲取全局 OrchestratorService 實例"""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service
