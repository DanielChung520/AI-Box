# 代碼功能說明: Contextual Header 生成器 (Prompt C 整合封裝員)
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""Contextual Header 生成器 - 實現 Prompt C 整合封裝員規格

功能：
1. 為每個 chunk 生成 Contextual Header
2. 整合全局摘要（Prompt A）和 TOC 路徑
3. 確保 chunk 單獨檢索時具備完整上下文

符合規格書 Prompt C 規格：
- 輸入：全局背景、當前目錄路徑、原始段落內容
- 輸出：50字以內的脈絡標頭
- 輸出範例：『[背景：國琿機械熱解爐說明書 > 維護手冊 > 集塵器清理] 本段落說明集塵器的清理頻率與注意事項：...』
"""

from typing import Any, Dict, List, Optional

import structlog

from llm.moe.moe_manager import LLMMoEManager

logger = structlog.get_logger(__name__)


class ContextualHeaderGenerator:
    """Contextual Header 整合員（實現 Prompt C）"""

    def __init__(self, moe_manager: Optional[LLMMoEManager] = None):
        """
        初始化 Contextual Header 生成器

        Args:
            moe_manager: MoE 管理器實例（可選，如果不提供則自動創建）
        """
        self.moe = moe_manager or LLMMoEManager()

    def _format_global_context(self, global_context: Dict[str, Any]) -> str:
        """
        格式化全局背景摘要

        Args:
            global_context: 全局背景字典（包含 theme, structure_outline, key_terms, target_audience）

        Returns:
            格式化的背景字符串
        """
        if not global_context:
            return "未指定背景"

        parts = []

        if global_context.get("theme"):
            parts.append(f"主題：{global_context['theme']}")

        if global_context.get("target_audience"):
            parts.append(f"目標受眾：{global_context['target_audience']}")

        if global_context.get("key_terms"):
            key_terms = global_context["key_terms"]
            if isinstance(key_terms, list) and key_terms:
                terms_str = ", ".join(key_terms[:5])
                parts.append(f"關鍵術語：{terms_str}")

        return " | ".join(parts) if parts else "未指定背景"

    def _format_toc_path(self, toc_path: Optional[str]) -> str:
        """
        格式化 TOC 路徑

        Args:
            toc_path: TOC 路徑字符串

        Returns:
            格式化的小節路徑
        """
        if not toc_path:
            return "未指定章節"
        return toc_path

    def _get_system_prompt(self) -> str:
        """獲取系統提示詞"""
        return """你現在負責生成 RAG 檢索前綴。你的任務是為原始段落寫一段精簡的『脈絡標頭 (Contextual Header)』，確保該段落即使單獨被檢索，也能讓 AI 知道它是關於什麼、在哪個章節。

【要求】
1. 輸出必須在 50 字以內（包含標點符號）
2. 格式：[背景：{主題} > {章節}] {段落簡述}
3. 簡述應概括段落的核心內容，避免冗長
4. 如果無法確定內容，請基於章節標題推斷

【輸出範例】
[背景：國琿機械熱解爐操作手冊 > 維護手冊 > 集塵器清理] 說明集塵器的清理頻率與注意事項

【輸入數據】
全局背景：{{global_context}}
當前目錄路徑：{{toc_path}}
原始段落內容：{{chunk_content}}

【任務】
請生成脈絡標頭（50字以內）："""

    async def generate_header(
        self,
        global_context: Optional[Dict[str, Any]],
        toc_path: Optional[str],
        raw_chunk_content: str,
        file_id: str,
        user_id: str,
    ) -> str:
        """
        為單個 chunk 生成 Contextual Header

        Args:
            global_context: 全局背景摘要（來自 Prompt A）
            toc_path: 當前目錄路徑（可選）
            raw_chunk_content: 原始段落內容
            file_id: 文件 ID
            user_id: 用戶 ID

        Returns:
            Contextual Header 字符串
        """
        try:
            formatted_context = self._format_global_context(global_context or {})
            formatted_toc = self._format_toc_path(toc_path)

            truncated_content = (
                raw_chunk_content[:500] if len(raw_chunk_content) > 500 else raw_chunk_content
            )

            prompt = self._get_system_prompt()
            prompt = prompt.replace("{{global_context}}", formatted_context)
            prompt = prompt.replace("{{toc_path}}", formatted_toc)
            prompt = prompt.replace("{{chunk_content}}", truncated_content)

            result = await self.moe.generate(
                prompt,
                scene="semantic_understanding",
                temperature=0.3,
                max_tokens=100,
                user_id=user_id,
                file_id=file_id,
            )

            header_text = result.get("text", "").strip()

            if not header_text:
                logger.warning(
                    "生成 Contextual Header 為空",
                    file_id=file_id,
                    toc_path=toc_path,
                )
                return self._generate_fallback_header(global_context, toc_path)

            header_text = self._truncate_to_limit(header_text)

            logger.info(
                "Contextual Header 生成成功",
                file_id=file_id,
                header_length=len(header_text),
                toc_path=toc_path,
            )

            return header_text

        except Exception as e:
            logger.error(
                "生成 Contextual Header 失敗",
                file_id=file_id,
                error=str(e),
                exc_info=True,
            )
            return self._generate_fallback_header(global_context, toc_path)

    def _truncate_to_limit(self, text: str, max_chars: int = 50) -> str:
        """
        截斷文本到指定長度

        Args:
            text: 原始文本
            max_chars: 最大字符數

        Returns:
            截斷後的文本
        """
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_newline = truncated.rfind("\n")
        last_space = truncated.rfind(" ")

        if last_newline > max_chars * 0.7:
            return truncated[:last_newline]
        elif last_space > max_chars * 0.7:
            return truncated[:last_space]

        return truncated[: max_chars - 3].rstrip("，、。；：") + "..."

    def _generate_fallback_header(
        self,
        global_context: Optional[Dict[str, Any]],
        toc_path: Optional[str],
    ) -> str:
        """
        生成回退的 Contextual Header（當 LLM 調用失敗時使用）

        Args:
            global_context: 全局背景摘要
            toc_path: TOC 路徑

        Returns:
            簡化的 Contextual Header
        """
        theme = global_context.get("theme", "") if global_context else ""
        path = toc_path or ""

        if theme and path:
            return f"[{theme} > {path}] 相關內容"
        elif theme:
            return f"[{theme}] 相關內容"
        elif path:
            return f"[{path}] 相關內容"
        else:
            return "[文件內容]"

    async def generate_headers_batch(
        self,
        chunks: List[Dict[str, Any]],
        global_context: Optional[Dict[str, Any]],
        file_id: str,
        user_id: str,
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        批量為多個 chunks 生成 Contextual Headers

        Args:
            chunks: chunk 列表
            global_context: 全局背景摘要
            file_id: 文件 ID
            user_id: 用戶 ID
            concurrency: 並發數量

        Returns:
            更新後的 chunk 列表（包含 contextual_header）
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def generate_with_semaphore(chunk: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                toc_path = chunk.get("metadata", {}).get("header_path", "")
                if isinstance(toc_path, list):
                    toc_path = " > ".join(toc_path)

                header = await self.generate_header(
                    global_context=global_context,
                    toc_path=toc_path,
                    raw_chunk_content=chunk.get("text", ""),
                    file_id=file_id,
                    user_id=user_id,
                )

                chunk["metadata"]["contextual_header"] = header
                return chunk

        tasks = [generate_with_semaphore(chunk) for chunk in chunks]
        updated_chunks = await asyncio.gather(*tasks, return_exceptions=True)

        processed_chunks = []
        for i, result in enumerate(updated_chunks):
            if isinstance(result, Exception):
                logger.error(
                    "批量生成 Contextual Header 失敗",
                    chunk_index=i,
                    error=str(result),
                )
                chunks[i]["metadata"]["contextual_header"] = self._generate_fallback_header(
                    global_context, chunks[i].get("metadata", {}).get("header_path", "")
                )
                processed_chunks.append(chunks[i])
            else:
                processed_chunks.append(result)

        logger.info(
            "批量 Contextual Header 生成完成",
            file_id=file_id,
            total_chunks=len(chunks),
            success_count=len(
                [c for c in processed_chunks if c["metadata"].get("contextual_header")]
            ),
        )

        return processed_chunks

    def generate_header_sync(
        self,
        global_context: Optional[Dict[str, Any]],
        toc_path: Optional[str],
        raw_chunk_content: str,
    ) -> str:
        """
        同步生成 Contextual Header（簡化版本，不調用 LLM）

        Args:
            global_context: 全局背景摘要
            toc_path: TOC 路徑
            raw_chunk_content: 原始段落內容

        Returns:
            Contextual Header 字符串
        """
        theme = global_context.get("theme", "") if global_context else ""
        path = toc_path or ""

        if theme and path:
            return f"[{theme} > {path}]"
        elif theme:
            return f"[{theme}]"
        elif path:
            return f"[{path}]"
        else:
            return ""

    def update_chunks_with_headers(
        self,
        chunks: List[Dict[str, Any]],
        global_context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        同步更新 chunks 的 Contextual Header（使用簡化方法）

        Args:
            chunks: chunk 列表
            global_context: 全局背景摘要

        Returns:
            更新後的 chunk 列表
        """
        for chunk in chunks:
            toc_path = chunk.get("metadata", {}).get("header_path", "")
            if isinstance(toc_path, list):
                toc_path = " > ".join(toc_path)

            header = self.generate_header_sync(
                global_context=global_context,
                toc_path=toc_path,
                raw_chunk_content=chunk.get("text", ""),
            )

            if header:
                chunk["metadata"]["contextual_header"] = header

        return chunks


def get_contextual_header_generator() -> ContextualHeaderGenerator:
    """獲取 ContextualHeaderGenerator 實例"""
    return ContextualHeaderGenerator()
