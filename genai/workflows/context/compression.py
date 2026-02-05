# 代碼功能說明: 上下文壓縮與摘要 Agent
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""上下文壓縮 Agent，負責對長對話進行摘要和壓縮以節省 Token。"""

import logging
from typing import List, Optional

from llm.moe.moe_manager import LLMMoEManager
from genai.workflows.context.models import ContextMessage

logger = logging.getLogger(__name__)


class ContextCompressionAgent:
    """上下文壓縮 Agent，使用 LLM 對對話歷史進行智能摘要。"""

    def __init__(self, moe_manager: Optional[LLMMoEManager] = None):
        self.moe_manager = moe_manager or LLMMoEManager()
        self.summary_prompt = """
        請對以下對話歷史進行精煉摘要。
        保留關鍵的任務進展、用戶偏好、已決策的事項和重要的數據引用。
        摘要應該簡潔，以便作為後續對話的上下文。
        使用繁體中文。

        對話歷史:
        {history}

        請產出摘要:
        """

    async def summarize_messages(self, messages: List[ContextMessage]) -> str:
        """
        對消息列表進行摘要。

        Args:
            messages: 消息列表

        Returns:
            摘要文本
        """
        if not messages:
            return ""

        # 格式化對話歷史
        history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        try:
            # 選擇模型（使用 task_analysis 場景）
            _model_result = self.moe_manager.select_model("task_analysis")

            # 調用 LLM 生成摘要
            # 這裡假設 LLMMoEManager 有一個直接調用方法，或者我們通過 client 調用
            # 為了簡化，我們使用模擬調用，實際項目中應整合 llm 服務
            _prompt = self.summary_prompt.format(history=history_text)

            logger.info(f"Summarizing {len(messages)} messages...")

            # 模擬 LLM 調用
            # result = await llm_client.generate(prompt, model_result.model)
            # return result.text

            return f"[自動摘要] 此前對話涵蓋了 {len(messages)} 條消息，主要討論了：{history_text[:200]}..."

        except Exception as e:
            logger.error(f"Failed to summarize messages: {e}", exc_info=True)
            return f"[摘要失敗] 無法壓縮上下文。原因: {str(e)}"

    async def compress_context(
        self, messages: List[ContextMessage], target_tokens: int = 2000
    ) -> List[ContextMessage]:
        """
        壓縮上下文，保留最新消息並摘要舊消息。

        Args:
            messages: 原始消息列表
            target_tokens: 目標 Token 數

        Returns:
            壓縮後的消息列表
        """
        if len(messages) <= 10:  # 消息較少時不壓縮
            return messages

        # 保留最近的 5 條消息
        recent_messages = messages[-5:]
        older_messages = messages[:-5]

        # 對舊消息進行摘要
        summary_content = await self.summarize_messages(older_messages)

        # 創建摘要消息
        summary_msg = ContextMessage(
            role="system",
            content=f"此前對話摘要: {summary_content}",
            metadata={"type": "summary", "original_count": len(older_messages)},
        )

        return [summary_msg] + recent_messages
