"""
代碼功能說明: Document Editing Agent 服務
創建日期: 2025-12-20
創建人: Daniel Chung
最後修改日期: 2025-12-20
"""

import json
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class DocumentEditingService:
    """文檔編輯服務 - 處理 Agent 編輯指令交互"""

    def __init__(self):
        self.logger = logger.bind(component="DocumentEditingService")

    async def generate_editing_patches(
        self,
        instruction: str,
        file_content: str,
        doc_format: str = "md",
        cursor_position: Optional[int] = None,
    ) -> Tuple[str, Dict[str, Any], str]:
        """
        根據用戶指令生成文檔編輯 patches

        Args:
            instruction: 用戶的編輯指令
            file_content: 文件內容
            doc_format: 文檔格式（md/txt/json）
            cursor_position: 游標位置（可選）

        Returns:
            (patch_kind, patch_payload, summary) 元組
            - patch_kind: "search_replace" | "unified_diff" | "json_patch"
            - patch_payload: patch 數據
            - summary: 變更摘要
        """
        self.logger.info(
            "Generating editing patches",
            doc_format=doc_format,
            instruction_length=len(instruction),
            content_length=len(file_content),
        )

        # 構建 Prompt
        prompt = self._build_patch_prompt(
            doc_format=doc_format,
            instruction=instruction,
            base_content=file_content,
            cursor_position=cursor_position,
        )

        # 調用 LLM 生成 patches
        patch_kind, patch_payload, summary = await self._call_llm_for_patch(prompt)

        self.logger.info(
            "Generated editing patches",
            patch_kind=patch_kind,
            summary=summary[:100] if summary else "",
        )

        return patch_kind, patch_payload, summary

    def _build_patch_prompt(
        self,
        *,
        doc_format: str,
        instruction: str,
        base_content: str,
        cursor_position: Optional[int] = None,
    ) -> str:
        """
        構建用於生成 patches 的 Prompt

        Args:
            doc_format: 文檔格式
            instruction: 用戶指令
            base_content: 文件內容
            cursor_position: 游標位置（可選）

        Returns:
            Prompt 字符串
        """
        if doc_format == "json":
            return (
                "你是一個嚴格的 JSON 編輯器。\n"
                "請根據指令，輸出 RFC6902 JSON Patch（JSON array），僅包含 op/path/value（必要時）。\n"
                "不要輸出任何解釋文字，只輸出 JSON。\n\n"
                f"指令：{instruction}\n\n"
                "base_json：\n"
                f"{base_content}\n"
            )

        # md/txt - 優先使用 Search-and-Replace 格式
        cursor_context = ""
        if cursor_position is not None and cursor_position > 0:
            # 在游標附近提供上下文（前後各 1000 字符）
            start = max(0, cursor_position - 1000)
            end = min(len(base_content), cursor_position + 1000)
            context_content = base_content[start:end]
            cursor_context = (
                f"\n游標位置：約第 {cursor_position} 字符\n上下文內容：\n{context_content}\n"
            )

        return (
            "你是一個專業的文檔編輯助手。你的任務是根據用戶要求，對 Markdown 文件進行精確的局部修改。\n"
            "**要求：**\n"
            "1. **禁止重寫全文**：僅輸出需要修改的部分。\n"
            "2. **格式要求**：你必須使用以下 JSON 格式輸出所有的修改指令：\n"
            "```json\n"
            "{\n"
            '  "patches": [\n'
            "    {\n"
            '      "search_block": "需要被替換的原始文本（必須與原文件完全一致）",\n'
            '      "replace_block": "修改後的新文本"\n'
            "    }\n"
            "  ],\n"
            '  "thought_chain": "思考過程說明（可選）"\n'
            "}\n"
            "```\n"
            "3. **精確匹配**：`search_block` 中的內容必須是原文件中真實存在的片段（包含空格、換行與縮排）。\n"
            "4. **多處修改**：若有多處修改，請並列多組 patches 區塊。\n"
            "5. **插入操作**：若要插入新內容，請在 `search_block` 中定位插入點的前一段文字，並在 `replace_block` 中包含該段文字加上新內容。\n\n"
            f"**用戶指令：**\n{instruction}\n\n"
            f"**文件內容：**\n{base_content}\n"
            f"{cursor_context}\n"
            "**輸出要求：**直接開始輸出 JSON，不要解釋「好的，我幫你修改了」或「根據您的要求」。"
        )

    async def _call_llm_for_patch(self, prompt: str) -> Tuple[str, Any, str]:
        """
        調用 LLM 生成 patches

        Args:
            prompt: Prompt 字符串

        Returns:
            (patch_kind, patch_payload, summary) 元組
        """
        # 延遲 import，避免啟動成本
        from llm.moe.moe_manager import LLMMoEManager

        moe = LLMMoEManager()
        result = await moe.generate(prompt)
        content = str(result.get("content") or result.get("text") or "")
        content = content.strip()

        # 嘗試 parse JSON
        try:
            parsed = json.loads(content)
            # 檢查是否為 Search-and-Replace 格式（包含 "patches" 鍵的對象）
            if isinstance(parsed, dict) and "patches" in parsed:
                patches = parsed.get("patches", [])
                if isinstance(patches, list) and len(patches) > 0:
                    # 驗證 patches 格式
                    for patch in patches:
                        if not isinstance(patch, dict):
                            break
                        if "search_block" not in patch or "replace_block" not in patch:
                            break
                    else:
                        # 所有 patch 格式正確
                        thought_chain = parsed.get("thought_chain", "")
                        return "search_replace", parsed, thought_chain
            # 檢查是否為 JSON Patch（數組格式）
            if isinstance(parsed, list):
                return "json_patch", parsed, ""
        except Exception as e:
            self.logger.warning(
                f"Failed to parse JSON from LLM response: {e}", content=content[:200]
            )

        # 默認使用 unified_diff 格式
        return "unified_diff", content, ""

    def convert_to_search_replace_patches(
        self, patch_kind: str, patch_payload: Any
    ) -> List[Dict[str, Any]]:
        """
        將不同格式的 patches 轉換為 Search-and-Replace 格式

        Args:
            patch_kind: patch 類型
            patch_payload: patch 數據

        Returns:
            Search-and-Replace patches 列表
        """
        if patch_kind == "search_replace":
            if isinstance(patch_payload, dict) and "patches" in patch_payload:
                return patch_payload["patches"]
            return []

        # 對於其他格式，目前不支持自動轉換
        # 可以後續實現 unified_diff 到 search_replace 的轉換
        self.logger.warning(
            "Cannot convert patch format to search_replace",
            patch_kind=patch_kind,
        )
        return []
