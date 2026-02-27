# MM-Agent SSE Event Emitter
# 用於在意圖分類和任務分析過程中發送階段性成果彙報

import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MMStageEvent:
    """MM-Agent 階段事件"""

    stage: str  # 階段名稱
    message: str  # 人類可讀的消息
    data: Dict[str, Any] = field(default_factory=dict)  # 實際數據
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: str = ""


class MMEventEmitter:
    """MM-Agent SSE 事件發射器

    用於在意圖分類、任務分析過程中發送階段性成果彙報，
    包含 LLM 思考過程和決策依據。
    """

    # 階段定義
    STAGE_REQUEST_RECEIVED = "request_received"
    STAGE_GAI_CLASSIFYING = "gai_classifying"
    STAGE_BPA_CLASSIFYING = "bpa_classifying"
    STAGE_LLM_ANALYZING = "llm_analyzing"
    STAGE_LLM_THINKING = "llm_thinking"
    STAGE_ENTITY_EXTRACTING = "entity_extracting"
    STAGE_INTENT_CLASSIFIED = "intent_classified"
    STAGE_ROUTING = "routing"
    STAGE_ROUTED = "routed"
    STAGE_ERROR = "error"

    def __init__(self):
        self._callbacks: List[Callable] = []

    def add_callback(self, callback: Callable):
        """添加回調函數"""
        self._callbacks.append(callback)

    async def emit(self, event: MMStageEvent):
        """發出事件"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.warning(f"SSE callback error: {e}")

    # 便捷方法

    async def request_received(self, task_id: str, instruction: str):
        """階段 1: 接收到請求"""
        preview = instruction[:50] + "..." if len(instruction) > 50 else instruction
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_REQUEST_RECEIVED,
                message=f"📥 已接收到您的請求：「{preview}」",
                data={"instruction": instruction},
                task_id=task_id,
            )
        )

    async def gai_classifying(self, task_id: str):
        """階段 2: GAI 意圖分類"""
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_GAI_CLASSIFYING,
                message="🔍 正在分析對話類型（問候、感謝、取消等）...",
                data={},
                task_id=task_id,
            )
        )

    async def bpa_classifying(self, task_id: str):
        """階段 3: BPA 意圖分類"""
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_BPA_CLASSIFYING,
                message="🏷️ 正在識別任務意圖（知識查詢、數據查詢、複雜任務等）...",
                data={},
                task_id=task_id,
            )
        )

    async def llm_analyzing(self, task_id: str):
        """階段 4: LLM 分析中"""
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_LLM_ANALYZING,
                message="🧠 正在使用 LLM 進行深度語義分析...",
                data={},
                task_id=task_id,
            )
        )

    async def llm_thinking(self, task_id: str, thinking: str):
        """階段 5: LLM 思考過程"""
        # 截取關鍵思考內容
        thinking_preview = thinking[:200] + "..." if len(thinking) > 200 else thinking
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_LLM_THINKING,
                message=f"💭 LLM 思考中：{thinking_preview}",
                data={"thinking": thinking},
                task_id=task_id,
            )
        )

    async def entity_extracting(self, task_id: str, entities: Dict[str, Any]):
        """階段 6: 實體提取"""
        entity_msgs = []
        for entity_type, value in entities.items():
            if value:
                entity_msgs.append(f"{entity_type}: {value}")

        msg = (
            "📌 已識別關鍵資訊：" + ", ".join(entity_msgs)
            if entity_msgs
            else "📌 正在提取關鍵資訊..."
        )

        await self.emit(
            MMStageEvent(
                stage=self.STAGE_ENTITY_EXTRACTING,
                message=msg,
                data={"entities": entities},
                task_id=task_id,
            )
        )

    async def intent_classified(
        self,
        task_id: str,
        gai_intent: str,
        bpa_intent: str,
        confidence: float,
        needs_clarification: bool = False,
    ):
        """階段 7: 意圖分類完成"""
        intent_emoji = {
            "GREETING": "👋",
            "THANKS": "🙏",
            "CANCEL": "❌",
            "CONFIRM": "✅",
            "HISTORY": "📜",
            "EXPORT": "📤",
            "FEEDBACK": "💬",
            "COMPLAIN": "😔",
            "BUSINESS": "💼",
        }

        bpa_emoji = {
            "KNOWLEDGE_QUERY": "📚",
            "SIMPLE_QUERY": "📊",
            "COMPLEX_TASK": "🔄",
            "CLARIFICATION": "❓",
            "CONTINUE_WORKFLOW": "▶️",
        }

        gai_icon = intent_emoji.get(gai_intent, "📝")
        bpa_icon = bpa_emoji.get(bpa_intent, "📋")

        clarification_msg = "（需要澄清）" if needs_clarification else ""
        conf_str = f"{confidence * 100:.0f}%"

        await self.emit(
            MMStageEvent(
                stage=self.STAGE_INTENT_CLASSIFIED,
                message=f"✅ 意圖分類完成：{gai_icon} {gai_intent} → {bpa_icon} {bpa_intent} {clarification_msg}（信心度：{conf_str}）",
                data={
                    "gai_intent": gai_intent,
                    "bpa_intent": bpa_intent,
                    "confidence": confidence,
                    "needs_clarification": needs_clarification,
                },
                task_id=task_id,
            )
        )

    async def routing(self, task_id: str, target_agent: str):
        """階段 8: 路由决策"""
        agent_emoji = {
            "KA-Agent": "📚",
            "Data-Agent": "📊",
            "ReAct": "🔄",
            "MM-Agent": "🏭",
        }

        agent_icon = agent_emoji.get(target_agent, "➡️")

        routing_msg = {
            "KA-Agent": "正在轉發至知識庫Agent進行處理...",
            "Data-Agent": "正在轉發至數據Agent進行處理...",
            "ReAct": "正在啟動編排引擎處理複雜任務...",
            "MM-Agent": "正在由庫管員Agent處理...",
        }

        msg = routing_msg.get(target_agent, f"正在轉發至 {target_agent}...")

        await self.emit(
            MMStageEvent(
                stage=self.STAGE_ROUTING,
                message=f"📡 {agent_icon} {msg}",
                data={"target_agent": target_agent},
                task_id=task_id,
            )
        )

    async def routed(
        self,
        task_id: str,
        target_agent: str,
        success: bool,
        message: str = "",
    ):
        """階段 9: 路由完成"""
        status = "✅" if success else "❌"

        await self.emit(
            MMStageEvent(
                stage=self.STAGE_ROUTED,
                message=f"{status} 已路由至 {target_agent}：{message}"
                if message
                else f"{status} 已路由至 {target_agent}",
                data={"target_agent": target_agent, "success": success, "message": message},
                task_id=task_id,
            )
        )

    async def error(self, task_id: str, error_code: str, message: str):
        """錯誤"""
        await self.emit(
            MMStageEvent(
                stage=self.STAGE_ERROR,
                message=f"❌ 發生錯誤：{message}",
                data={"error_code": error_code, "message": message},
                task_id=task_id,
            )
        )


# 全局實例
_event_emitter = MMEventEmitter()


def get_mm_event_emitter() -> MMEventEmitter:
    """獲取全局事件發射器"""
    return _event_emitter
