# 代碼功能說明: 文本摘要工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本摘要工具

支持提取關鍵詞、生成文本摘要、文本長度統計等功能。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import List, Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的操作類型
SUPPORTED_OPERATIONS = {
    "keywords",  # 提取關鍵詞
    "summary",  # 生成摘要
    "stats",  # 統計信息
}


class TextSummarizerInput(ToolInput):
    """文本摘要輸入參數"""

    text: str  # 輸入文本
    operation: str  # 操作類型（如 "keywords", "summary", "stats"）
    max_keywords: Optional[int] = 10  # 最大關鍵詞數量（用於 keywords 操作）
    summary_length: Optional[int] = 3  # 摘要句子數量（用於 summary 操作）


class TextSummarizerOutput(ToolOutput):
    """文本摘要輸出結果"""

    result: str  # 結果文本（關鍵詞、摘要或統計信息）
    operation: str  # 操作類型
    keywords: Optional[List[str]] = None  # 關鍵詞列表（用於 keywords 操作）
    stats: Optional[dict] = None  # 統計信息（用於 stats 操作）


class TextSummarizer(BaseTool[TextSummarizerInput, TextSummarizerOutput]):
    """文本摘要工具

    支持提取關鍵詞、生成文本摘要、文本長度統計等功能。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "text_summarizer"

    @property
    def description(self) -> str:
        """工具描述"""
        return "文本摘要工具，支持提取關鍵詞、生成文本摘要、文本長度統計等功能"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_operation(self, operation: str) -> None:
        """
        驗證操作類型是否支持

        Args:
            operation: 操作類型

        Raises:
            ToolValidationError: 操作類型不支持
        """
        if operation.lower() not in SUPPORTED_OPERATIONS:
            supported = ", ".join(sorted(SUPPORTED_OPERATIONS))
            raise ToolValidationError(
                f"Unsupported operation: {operation}. Supported operations: {supported}",
                field="operation",
            )

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        提取關鍵詞（簡單實現：基於詞頻）

        Args:
            text: 輸入文本
            max_keywords: 最大關鍵詞數量

        Returns:
            關鍵詞列表
        """
        # 轉為小寫並分割單詞
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # 過濾常見停用詞（簡單列表）
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "them",
            "their",
            "there",
        }

        # 計算詞頻
        word_freq = Counter(word for word in words if word not in stop_words)

        # 返回最常見的關鍵詞
        return [word for word, _ in word_freq.most_common(max_keywords)]

    def _generate_summary(self, text: str, summary_length: int = 3) -> str:
        """
        生成文本摘要（簡單實現：提取前 N 句）

        Args:
            text: 輸入文本
            summary_length: 摘要句子數量

        Returns:
            摘要文本
        """
        # 按句子分割（簡單實現：按句號、問號、感嘆號分割）
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 返回前 N 句
        summary_sentences = sentences[:summary_length]
        return ". ".join(summary_sentences) + ("." if summary_sentences else "")

    def _calculate_stats(self, text: str) -> dict:
        """
        計算文本統計信息

        Args:
            text: 輸入文本

        Returns:
            統計信息字典
        """
        # 字符數（包括空格）
        char_count = len(text)

        # 字符數（不包括空格）
        char_count_no_spaces = len(text.replace(" ", ""))

        # 單詞數（簡單實現：按空白分割）
        words = text.split()
        word_count = len(words)

        # 句子數（簡單實現：按句號、問號、感嘆號分割）
        sentences = re.split(r"[.!?]+", text)
        sentence_count = len([s for s in sentences if s.strip()])

        # 段落數（按雙換行分割）
        paragraphs = text.split("\n\n")
        paragraph_count = len([p for p in paragraphs if p.strip()])

        # 行數
        line_count = len(text.split("\n"))

        return {
            "char_count": char_count,
            "char_count_no_spaces": char_count_no_spaces,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "line_count": line_count,
        }

    async def execute(self, input_data: TextSummarizerInput) -> TextSummarizerOutput:
        """
        執行文本摘要操作

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證操作類型
            self._validate_operation(input_data.operation)

            operation_lower = input_data.operation.lower()

            if operation_lower == "keywords":
                # 提取關鍵詞
                keywords = self._extract_keywords(input_data.text, input_data.max_keywords or 10)
                result_text = ", ".join(keywords)

                logger.debug(
                    "keywords_extracted",
                    keyword_count=len(keywords),
                    keywords=keywords,
                )

                return TextSummarizerOutput(
                    result=result_text,
                    operation=input_data.operation,
                    keywords=keywords,
                )

            elif operation_lower == "summary":
                # 生成摘要
                summary = self._generate_summary(input_data.text, input_data.summary_length or 3)

                logger.debug(
                    "summary_generated",
                    summary_length=len(summary),
                    sentence_count=input_data.summary_length or 3,
                )

                return TextSummarizerOutput(
                    result=summary,
                    operation=input_data.operation,
                )

            elif operation_lower == "stats":
                # 計算統計信息
                stats = self._calculate_stats(input_data.text)
                result_text = f"Characters: {stats['char_count']}, Words: {stats['word_count']}, Sentences: {stats['sentence_count']}"

                logger.debug("stats_calculated", stats=stats)

                return TextSummarizerOutput(
                    result=result_text,
                    operation=input_data.operation,
                    stats=stats,
                )

            else:
                raise ToolValidationError(
                    f"Unknown operation: {input_data.operation}", field="operation"
                )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("text_summarization_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to summarize text: {str(e)}", tool_name=self.name
            ) from e
