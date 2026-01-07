"""
代碼功能說明: Document Editing Agent 服務
創建日期: 2025-12-20
創建人: Daniel Chung
最後修改日期: 2026-01-06
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
        # 性能優化：大文件處理（> 10MB）
        file_size_mb = len(file_content.encode("utf-8")) / (1024 * 1024)
        if file_size_mb > 10:
            self.logger.warning(
                "Large file detected",
                file_size_mb=round(file_size_mb, 2),
                doc_format=doc_format,
            )

        self.logger.info(
            "Generating editing patches",
            doc_format=doc_format,
            instruction_length=len(instruction),
            content_length=len(file_content),
            file_size_mb=round(file_size_mb, 2) if file_size_mb > 1 else None,
        )

        # 構建 Prompt（已優化：大文件時只傳遞上下文窗口）
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
        # 性能優化：大文件時只傳遞上下文窗口，避免傳遞完整文件內容
        file_size_mb = len(base_content.encode("utf-8")) / (1024 * 1024)
        LARGE_FILE_THRESHOLD_MB = 10
        CONTEXT_WINDOW_SIZE = 2000  # 前後各 2000 字符

        if file_size_mb > LARGE_FILE_THRESHOLD_MB:
            # 大文件：只傳遞游標附近的上下文窗口
            if cursor_position is not None and cursor_position > 0:
                start = max(0, cursor_position - CONTEXT_WINDOW_SIZE)
                end = min(len(base_content), cursor_position + CONTEXT_WINDOW_SIZE)
                context_content = base_content[start:end]
                cursor_context = (
                    f"\n游標位置：約第 {cursor_position} 字符（文件總長度：{len(base_content)} 字符）\n"
                    f"上下文內容（前後各 {CONTEXT_WINDOW_SIZE} 字符）：\n{context_content}\n"
                )
                # 大文件時不傳遞完整內容，只傳遞上下文
                content_to_use = context_content
            else:
                # 沒有游標位置時，傳遞文件開頭部分
                content_to_use = base_content[: CONTEXT_WINDOW_SIZE * 2]
                cursor_context = (
                    f"\n注意：這是一個大文件（{round(file_size_mb, 2)} MB），"
                    f"僅顯示前 {CONTEXT_WINDOW_SIZE * 2} 字符作為參考。\n"
                    f"請根據用戶指令和文件開頭內容進行修改。\n"
                )
        else:
            # 小文件：傳遞完整內容
            content_to_use = base_content
            cursor_context = ""
            if cursor_position is not None and cursor_position > 0:
                # 在游標附近提供上下文（前後各 1000 字符）
                start = max(0, cursor_position - 1000)
                end = min(len(base_content), cursor_position + 1000)
                context_content = base_content[start:end]
                cursor_context = f"\n游標位置：約第 {cursor_position} 字符\n上下文內容：\n{context_content}\n"

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
            "5. **插入操作**：若要插入新內容，請在 `search_block` 中定位插入點的前一段文字，並在 `replace_block` 中包含該段文字加上新內容。\n"
            "6. **日期時間記錄**（重要）：\n"
            "   - 如果用戶指令要求更新文件頭註釋中的「最後修改日期」，你必須先調用 `datetime` 工具獲取當前時間。\n"
            "   - 如果用戶指令要求添加或更新文件中的日期時間信息（如創建日期、更新日期），你必須先調用 `datetime` 工具獲取當前時間。\n"
            "   - 使用 `datetime` 工具時，不要指定 `timezone` 參數，讓系統自動使用系統時區。\n"
            "   - 獲取時間後，使用工具返回的 `datetime` 字段值（格式：YYYY-MM-DD HH:MM:SS）來更新文件中的日期時間。\n"
            "   - 示例：如果文件頭註釋中有「最後修改日期：2025-12-30」，你應該先調用 `datetime` 工具，然後將結果更新為當前時間。\n"
            "7. **Mermaid 圖表渲染**（重要）：\n"
            "   - **版本要求**：系統使用 Mermaid 10.0 版本進行渲染，請確保生成的 Mermaid 代碼符合 10.0 語法規範。\n"
            "   - **符號衝突處理**：\n"
            "     * 節點標籤中包含特殊字符（如 `/`、`(`、`)`、`[`、`]`、`{`、`}`、`|`、`&`、`<`、`>` 等）時，必須使用雙引號包裹整個標籤文本。\n"
            '     * 示例：`A["API/接口"]` 而不是 `A[API/接口]`，`B["用戶(Admin)"]` 而不是 `B[用戶(Admin)]`。\n'
            '     * 路徑或 URL 中包含 `/` 時，必須使用引號包裹：`A["https://example.com/api"]`。\n'
            "   - **段落換行**：\n"
            "     * 節點標籤中的多行文本必須使用 `<br>` 標籤進行換行，不能使用 `\\n` 或直接換行。\n"
            '     * 示例：`A["第一行<br>第二行<br>第三行"]` 而不是 `A["第一行\\n第二行\\n第三行"]`。\n'
            "   - **節點 ID 規範**：\n"
            "     * 節點 ID 不能包含空格、特殊字符（如 `/`、`(`、`)` 等）。\n"
            "     * 建議使用下劃線或連字符：`api_gateway` 或 `api-gateway`，避免使用 `api/gateway`。\n"
            "   - **引號轉義**：\n"
            '     * 如果節點標籤中包含雙引號，需要使用轉義：`A["用戶說：\\"你好\\""]`。\n'
            "   - **避免保留字衝突**：\n"
            "     * 避免使用 Mermaid 保留字（如 `style`、`classDef`、`click`、`link`、`class` 等）作為節點 ID 或類名。\n"
            "     * 如需使用，請添加前綴或後綴：`user_style`、`btn_classDef` 等。\n"
            "   - **語法檢查**：\n"
            "     * 確保所有箭頭方向正確（`-->`、`<--`、`<-->`）。\n"
            '     * 確保子圖（subgraph）語法正確：`subgraph id["標籤"]`。\n'
            "     * 確保節點定義完整，避免未定義的節點引用。\n"
            "   - **示例（正確的 Mermaid 代碼）**：\n"
            "     ```mermaid\n"
            "     graph TD\n"
            '         A["API/接口"] -->|請求| B["處理器<br>後端服務"]\n'
            '         B -->|響應| C["用戶(Admin)<br>管理員"]\n'
            '         subgraph api["API 服務"]\n'
            "             A\n"
            "             B\n"
            "         end\n"
            "     ```\n\n"
            f"**用戶指令：**\n{instruction}\n\n"
            f"**文件內容：**\n{content_to_use}\n"
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
