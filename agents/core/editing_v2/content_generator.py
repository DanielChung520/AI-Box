# 代碼功能說明: 內容生成器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""內容生成器

實現 LLM 內容生成功能（使用可重現配置）。
"""

from typing import List, Optional

from agents.builtin.document_editing_v2.models import Action
from agents.core.editing_v2.llm_config import DEFAULT_LLM_CONFIG, LLMConfig
from agents.core.editing_v2.markdown_parser import MarkdownBlock


class ContentGenerator:
    """內容生成器

    使用 LLM 生成編輯內容。
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        初始化內容生成器

        Args:
            llm_config: LLM 配置（如果為 None，使用默認配置）
        """
        self.llm_config = llm_config or DEFAULT_LLM_CONFIG

    async def generate_content(
        self,
        target_block: MarkdownBlock,
        action: Action,
        context_blocks: List[MarkdownBlock],
        context_text: str,
    ) -> str:
        """
        生成編輯內容

        Args:
            target_block: 目標 Block
            action: 編輯操作
            context_blocks: 上下文 Block 列表
            context_text: 格式化的上下文文本

        Returns:
            生成的內容

        Raises:
            Exception: LLM 調用失敗時拋出
        """
        # 構建 prompt
        prompt = self._build_prompt(target_block, action, context_text)

        # 調用 LLM（使用現有的 LLM 基礎設施）
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = await moe.generate(
            prompt,
            **self.llm_config.to_llm_params(),
        )

        content = str(result.get("content") or result.get("text") or "")
        return content.strip()

    def _build_prompt(self, target_block: MarkdownBlock, action: Action, context_text: str) -> str:
        """
        構建 LLM Prompt

        Args:
            target_block: 目標 Block
            action: 編輯操作
            context_text: 上下文文本

        Returns:
            Prompt 字符串
        """
        prompt_parts = [
            "你是一個專業的 Markdown 編輯助手。",
            "請根據用戶指令，對指定的 Block 進行編輯。",
            "",
            f"**編輯操作**: {action.mode}",
            f"**目標 Block ID**: {target_block.block_id}",
            f"**目標 Block 類型**: {target_block.block_type}",
            "",
            "**上下文內容**:",
            context_text,
            "",
            "**目標 Block 內容**:",
            target_block.content,
            "",
        ]

        if action.content:
            prompt_parts.extend(
                [
                    "**用戶要求的內容**:",
                    action.content,
                    "",
                ]
            )

        prompt_parts.append("**輸出要求**: 只輸出編輯後的 Block 內容，不要輸出解釋文字。")

        return "\n".join(prompt_parts)
