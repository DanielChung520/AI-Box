# 代碼功能說明: 文件分塊處理器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""文件分塊處理器 - 實現多種分塊策略"""

import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class ChunkStrategy(Enum):
    """分塊策略枚舉"""

    FIXED_SIZE = "fixed_size"  # 固定大小分塊
    SLIDING_WINDOW = "sliding_window"  # 滑動窗口分塊
    SEMANTIC = "semantic"  # 語義分塊（基於段落、句子邊界）
    AST_DRIVEN = "ast_driven"  # AST 驅動分塊（基於標題層級)


class ChunkConfig:
    """分塊配置類 - 長期可配置策略"""

    def __init__(
        self,
        chunk_size: int = 768,
        min_chunk_size: int = 50,
        max_chunk_size: int = 2000,
        max_code_block_size: int = 2000,
        table_context_lines: int = 3,
        combine_text_paragraphs: bool = True,
        separate_code_blocks: bool = True,
        separate_tables: bool = True,
        enable_quality_check: bool = True,
        enable_adaptive_size: bool = True,
    ):
        """
        初始化分塊配置

        Args:
            chunk_size: 默認分塊大小（字符數）
            min_chunk_size: 最小分塊大小（字符數）
            max_chunk_size: 最大分塊大小（字符數）
            max_code_block_size: 代碼塊最大大小（字符數）
            table_context_lines: 表格上下文行數（前後各保留的行數）
            combine_text_paragraphs: 是否組合文本段落
            separate_code_blocks: 是否將代碼塊單獨成塊
            separate_tables: 是否將表格單獨成塊
            enable_quality_check: 是否啟用質量檢查
            enable_adaptive_size: 是否啟用自適應大小
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.max_code_block_size = max_code_block_size
        self.table_context_lines = table_context_lines
        self.combine_text_paragraphs = combine_text_paragraphs
        self.separate_code_blocks = separate_code_blocks
        self.separate_tables = separate_tables
        self.enable_quality_check = enable_quality_check
        self.enable_adaptive_size = enable_adaptive_size


class ChunkProcessor:
    """文件分塊處理器"""

    def __init__(
        self,
        chunk_size: int = 768,
        overlap: float = 0.2,
        strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
        min_tokens: int = 500,
        max_tokens: int = 1000,
        config: Optional[ChunkConfig] = None,
    ):
        """
        初始化分塊處理器

        Args:
            chunk_size: 分塊大小（字符數，不是 tokens，用於非 AST 策略，默認 768）
            overlap: 重疊比例（0-1之間）
            strategy: 分塊策略
            min_tokens: 最小 Token 數（用於 AST 策略）
            max_tokens: 最大 Token 數（用於 AST 策略）
            config: 分塊配置對象（可選，如果不提供則使用默認配置）
        """
        self.config = config or ChunkConfig(chunk_size=chunk_size)
        self.chunk_size = self.config.chunk_size
        self.overlap = overlap
        self.strategy = strategy
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.logger = logger.bind(
            chunk_size=self.chunk_size,
            overlap=overlap,
            strategy=strategy.value,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
        )

    def process(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        處理文本，生成分塊

        Args:
            text: 文本內容
            file_id: 文件 ID
            metadata: 文件元數據

        Returns:
            分塊列表，每個分塊包含 chunk_id、file_id、chunk_index、text、metadata
        """
        if self.strategy == ChunkStrategy.FIXED_SIZE:
            return self._fixed_size_chunk(text, file_id, metadata)
        elif self.strategy == ChunkStrategy.SLIDING_WINDOW:
            return self._sliding_window_chunk(text, file_id, metadata)
        elif self.strategy == ChunkStrategy.SEMANTIC:
            return self._semantic_chunk(text, file_id, metadata)
        elif self.strategy == ChunkStrategy.AST_DRIVEN:
            return self._ast_driven_chunk(text, file_id, metadata)
        else:
            raise ValueError(f"不支持的分塊策略: {self.strategy}")

    def _fixed_size_chunk(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """固定大小分塊"""
        chunks: List[Dict[str, Any]] = []
        text_length = len(text)

        for i in range(0, text_length, self.chunk_size):
            chunk_text = text[i : i + self.chunk_size]
            chunk_id = str(uuid.uuid4())

            chunk_metadata = {
                "start_position": i,
                "end_position": min(i + self.chunk_size, text_length),
                "chunk_size": len(chunk_text),
            }

            # 合併文件元數據
            if metadata:
                chunk_metadata.update(metadata)

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "chunk_index": len(chunks),
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                }
            )

        return chunks

    def _sliding_window_chunk(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """滑動窗口分塊（帶重疊）"""
        chunks = []
        text_length = len(text)
        step_size = int(self.chunk_size * (1 - self.overlap))

        i = 0
        chunk_index = 0

        while i < text_length:
            chunk_text = text[i : i + self.chunk_size]
            chunk_id = str(uuid.uuid4())

            chunk_metadata = {
                "start_position": i,
                "end_position": min(i + self.chunk_size, text_length),
                "chunk_size": len(chunk_text),
                "overlap": self.overlap,
            }

            # 合併文件元數據
            if metadata:
                chunk_metadata.update(metadata)

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "metadata": chunk_metadata,
                }
            )

            i += step_size
            chunk_index += 1

        return chunks

    def _detect_tables(self, text: str) -> List[tuple[int, int]]:
        """
        檢測 Markdown 表格的位置範圍

        Args:
            text: 文本內容

        Returns:
            表格位置列表，每個元素為 (start_char_index, end_char_index)
        """
        tables: List[tuple[int, int]] = []
        lines = text.split("\n")
        current_table_start: Optional[int] = None
        current_char_pos = 0
        consecutive_table_lines = 0

        for i, line in enumerate(lines):
            line_with_newline = line + "\n"
            line_stripped = line.strip()

            # 檢測表格行：以 | 開頭且包含多個 |
            is_table_row = line_stripped.startswith("|") and line_stripped.count("|") >= 2

            # 檢測表格分隔行（包含 --- 或 :-- 等）
            is_separator = line_stripped.startswith("|") and (
                "---" in line_stripped or ":--" in line_stripped or "-:" in line_stripped
            )

            if is_table_row or is_separator:
                if current_table_start is None:
                    # 開始新的表格
                    current_table_start = current_char_pos
                    consecutive_table_lines = 1
                else:
                    consecutive_table_lines += 1
            else:
                # 非表格行
                if current_table_start is not None:
                    # 表格結束（遇到非表格行）
                    # 需要至少2行（表頭+分隔行）才算有效表格
                    if consecutive_table_lines >= 2:
                        tables.append((current_table_start, current_char_pos))
                    current_table_start = None
                    consecutive_table_lines = 0

            current_char_pos += len(line_with_newline)

        # 處理文檔末尾的表格
        if current_table_start is not None and consecutive_table_lines >= 2:
            tables.append((current_table_start, len(text)))

        return tables

    def _split_text_with_special_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        將文本分割為文本段落和特殊塊（代碼塊、表格）

        Returns:
            段落列表，每個元素包含：
            - text: 段落文本
            - type: 'text' 或 'code_block' 或 'table'
            - start_pos: 起始位置
            - end_pos: 結束位置
        """
        segments: List[Dict[str, Any]] = []
        code_blocks = self._detect_code_blocks(text)
        tables = self._detect_tables(text)

        # 合併所有特殊塊位置，按起始位置排序
        special_blocks: List[Dict[str, Any]] = []
        for start, end in code_blocks:
            special_blocks.append({"type": "code_block", "start": start, "end": end})
        for start, end in tables:
            special_blocks.append({"type": "table", "start": start, "end": end})

        special_blocks.sort(key=lambda x: x["start"])

        # 如果沒有特殊塊，整個文本就是一個文本段落
        if not special_blocks:
            return [{"type": "text", "text": text, "start_pos": 0, "end_pos": len(text)}]

        current_pos = 0

        for block in special_blocks:
            block_start = block["start"]
            block_end = block["end"]

            # 添加特殊塊之前的文本段落
            if block_start > current_pos:
                text_segment = text[current_pos:block_start].strip()
                if text_segment:
                    segments.append(
                        {
                            "type": "text",
                            "text": text_segment,
                            "start_pos": current_pos,
                            "end_pos": block_start,
                        }
                    )

            # 添加特殊塊
            block_text = text[block_start:block_end]
            segments.append(
                {
                    "type": block["type"],
                    "text": block_text,
                    "start_pos": block_start,
                    "end_pos": block_end,
                }
            )

            current_pos = block_end

        # 添加最後的文本段落
        if current_pos < len(text):
            text_segment = text[current_pos:].strip()
            if text_segment:
                segments.append(
                    {
                        "type": "text",
                        "text": text_segment,
                        "start_pos": current_pos,
                        "end_pos": len(text),
                    }
                )

        return segments

    def _evaluate_chunk_quality(self, chunk_text: str, chunk_type: str = "text") -> Dict[str, Any]:
        """
        評估 chunk 質量

        Args:
            chunk_text: chunk 文本內容
            chunk_type: chunk 類型（'text', 'code_block', 'table'）

        Returns:
            質量指標字典
        """
        quality_metrics = {
            "size": len(chunk_text),
            "type": chunk_type,
            "is_too_small": len(chunk_text) < self.config.min_chunk_size,
            "is_too_large": len(chunk_text) > self.config.max_chunk_size,
            "has_code": "```" in chunk_text,
            "has_table": "|" in chunk_text and "---" in chunk_text,
            "paragraph_count": chunk_text.count("\n\n"),
            "line_count": chunk_text.count("\n"),
            "token_estimate": len(chunk_text) // 4,  # 簡單估算：1 token ≈ 4 字符
        }

        # 對於代碼塊，檢查是否超過最大大小
        if chunk_type == "code_block":
            quality_metrics["exceeds_max_code_block_size"] = (
                len(chunk_text) > self.config.max_code_block_size
            )

        # 計算質量分數（0-100）
        quality_score = 100
        if quality_metrics["is_too_small"]:
            quality_score -= 30
        if quality_metrics["is_too_large"]:
            quality_score -= 30
        if chunk_type == "code_block" and quality_metrics.get("exceeds_max_code_block_size"):
            quality_score -= 20

        quality_metrics["quality_score"] = max(0, quality_score)
        quality_metrics["quality_level"] = (
            "excellent" if quality_score >= 80 else "good" if quality_score >= 60 else "poor"
        )

        return quality_metrics

    def _get_effective_chunk_size(self, segment_type: str) -> int:
        """
        根據內容類型返回有效的 chunk 大小

        Args:
            segment_type: 內容類型（'text', 'code_block', 'table'）

        Returns:
            有效的 chunk 大小（字符數）
        """
        if not self.config.enable_adaptive_size:
            return self.config.chunk_size

        if segment_type == "code_block":
            # 代碼塊可以更大，但不超過最大限制
            return min(self.config.chunk_size * 2, self.config.max_code_block_size)
        elif segment_type == "table":
            # 表格保持原大小
            return self.config.chunk_size
        else:
            # 文本段落使用標準大小
            return self.config.chunk_size

    def _merge_table_with_context(
        self, table_text: str, full_text: str, table_start_pos: int, table_end_pos: int
    ) -> str:
        """
        將表格與上下文合併

        Args:
            table_text: 表格文本
            full_text: 完整文本
            table_start_pos: 表格起始位置
            table_end_pos: 表格結束位置

        Returns:
            包含上下文的表格文本
        """
        if not self.config.table_context_lines or self.config.table_context_lines <= 0:
            return table_text

        lines = full_text.split("\n")
        table_start_line = full_text[:table_start_pos].count("\n")
        table_end_line = full_text[:table_end_pos].count("\n")

        # 提取表格前的上下文
        context_start_line = max(0, table_start_line - self.config.table_context_lines)
        context_before = "\n".join(lines[context_start_line:table_start_line])

        # 提取表格後的上下文
        context_end_line = min(len(lines), table_end_line + 1 + self.config.table_context_lines)
        context_after = "\n".join(lines[table_end_line + 1 : context_end_line])

        # 合併上下文和表格
        result_parts = []
        if context_before.strip():
            result_parts.append(context_before)
        result_parts.append(table_text)
        if context_after.strip():
            result_parts.append(context_after)

        return "\n\n".join(result_parts)

    def _handle_large_code_block(self, code_block_text: str, file_id: str) -> List[str]:
        """
        處理過大的代碼塊

        Args:
            code_block_text: 代碼塊文本
            file_id: 文件 ID

        Returns:
            處理後的代碼塊列表（可能拆分為多個）
        """
        if len(code_block_text) <= self.config.max_code_block_size:
            # 大小合適，直接返回
            return [code_block_text]

        # 過大的代碼塊，嘗試按函數/類拆分
        self.logger.warning(
            "Code block exceeds max size",
            size=len(code_block_text),
            max_size=self.config.max_code_block_size,
        )

        # 簡單策略：按空行拆分（大多數代碼在函數/類之間有空行）
        parts = re.split(r"\n\s*\n", code_block_text)
        result_blocks = []
        current_block = ""

        for part in parts:
            if len(current_block) + len(part) + 2 <= self.config.max_code_block_size:
                current_block += "\n\n" + part if current_block else part
            else:
                if current_block:
                    result_blocks.append(current_block)
                current_block = part

        if current_block:
            result_blocks.append(current_block)

        # 如果拆分後仍然有塊過大，直接截斷（添加警告）
        final_blocks = []
        for block in result_blocks:
            if len(block) > self.config.max_code_block_size:
                self.logger.warning(
                    "Code block part still too large, truncating",
                    size=len(block),
                    max_size=self.config.max_code_block_size,
                )
                # 保留前 N 字符並添加警告標記
                truncated = block[: self.config.max_code_block_size - 100]
                truncated += "\n\n<!-- WARNING: Code block truncated due to size limit -->"
                final_blocks.append(truncated)
            else:
                final_blocks.append(block)

        return final_blocks

    def _semantic_chunk(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """語義分塊（基於段落、句子邊界，代碼塊和表格單獨成塊）"""
        chunks = []

        # 先分割為文本段落和特殊塊（代碼塊、表格）
        segments = self._split_text_with_special_blocks(text)

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for segment in segments:
            segment_type = segment["type"]
            segment_text = segment["text"]

            # 代碼塊和表格單獨成塊
            if segment_type in ("code_block", "table"):
                # 先保存當前的文本塊
                if current_chunk.strip():
                    chunk_id = str(uuid.uuid4())
                    chunk_metadata = {
                        "start_position": current_start,
                        "end_position": current_start + len(current_chunk),
                        "chunk_size": len(current_chunk),
                        "strategy": "semantic",
                    }

                    if metadata:
                        chunk_metadata.update(metadata)

                    # 質量評估
                    if self.config.enable_quality_check:
                        quality = self._evaluate_chunk_quality(current_chunk.strip(), "text")
                        chunk_metadata["quality"] = quality

                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "file_id": file_id,
                            "chunk_index": chunk_index,
                            "text": current_chunk.strip(),
                            "metadata": chunk_metadata,
                        }
                    )
                    chunk_index += 1

                # 處理特殊塊（代碼塊或表格）
                if segment_type == "code_block":
                    # 處理代碼塊（可能拆分）
                    code_blocks = self._handle_large_code_block(segment_text, file_id)
                    for code_block in code_blocks:
                        chunk_id = str(uuid.uuid4())
                        chunk_metadata = {
                            "start_position": segment["start_pos"],
                            "end_position": segment["end_pos"],
                            "chunk_size": len(code_block),
                            "strategy": "semantic",
                            "block_type": "code_block",
                        }

                        if metadata:
                            chunk_metadata.update(metadata)

                        # 質量評估
                        if self.config.enable_quality_check:
                            quality = self._evaluate_chunk_quality(code_block, "code_block")
                            chunk_metadata["quality"] = quality

                        chunks.append(
                            {
                                "chunk_id": chunk_id,
                                "file_id": file_id,
                                "chunk_index": chunk_index,
                                "text": code_block,
                                "metadata": chunk_metadata,
                            }
                        )
                        chunk_index += 1
                elif segment_type == "table":
                    # 處理表格（合併上下文）
                    table_with_context = self._merge_table_with_context(
                        segment_text, text, segment["start_pos"], segment["end_pos"]
                    )
                    chunk_id = str(uuid.uuid4())
                    chunk_metadata = {
                        "start_position": segment["start_pos"],
                        "end_position": segment["end_pos"],
                        "chunk_size": len(table_with_context),
                        "strategy": "semantic",
                        "block_type": "table",
                        "has_context": len(table_with_context) > len(segment_text),
                    }

                    if metadata:
                        chunk_metadata.update(metadata)

                    # 質量評估
                    if self.config.enable_quality_check:
                        quality = self._evaluate_chunk_quality(table_with_context, "table")
                        chunk_metadata["quality"] = quality

                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "file_id": file_id,
                            "chunk_index": chunk_index,
                            "text": table_with_context,
                            "metadata": chunk_metadata,
                        }
                    )
                    chunk_index += 1

                current_chunk = ""
                current_start = segment["end_pos"]
            else:
                # 文本段落：可以組合，但不超過 chunk_size
                # 使用自適應大小
                effective_chunk_size = (
                    self._get_effective_chunk_size("text")
                    if self.config.combine_text_paragraphs
                    else self.config.chunk_size
                )

                # 先按段落分割文本段落
                paragraphs = self._split_paragraphs(segment_text)

                for para in paragraphs:
                    # 如果當前塊加上新段落超過大小限制，保存當前塊
                    if len(current_chunk) + len(para) > effective_chunk_size and current_chunk:
                        chunk_id = str(uuid.uuid4())
                        chunk_metadata = {
                            "start_position": current_start,
                            "end_position": current_start + len(current_chunk),
                            "chunk_size": len(current_chunk),
                            "strategy": "semantic",
                        }

                        if metadata:
                            chunk_metadata.update(metadata)

                        # 質量評估
                        if self.config.enable_quality_check:
                            quality = self._evaluate_chunk_quality(current_chunk.strip(), "text")
                            chunk_metadata["quality"] = quality

                        chunks.append(
                            {
                                "chunk_id": chunk_id,
                                "file_id": file_id,
                                "chunk_index": chunk_index,
                                "text": current_chunk.strip(),
                                "metadata": chunk_metadata,
                            }
                        )

                        # 開始新塊
                        current_chunk = para
                        current_start = current_start + len(current_chunk) - len(para)
                        chunk_index += 1
                    else:
                        # 如果段落本身超過大小限制，按句子分割
                        if len(para) > effective_chunk_size:
                            # 先保存當前塊
                            if current_chunk:
                                chunk_id = str(uuid.uuid4())
                                chunk_metadata = {
                                    "start_position": current_start,
                                    "end_position": current_start + len(current_chunk),
                                    "chunk_size": len(current_chunk),
                                    "strategy": "semantic",
                                }

                                if metadata:
                                    chunk_metadata.update(metadata)

                                # 質量評估
                                if self.config.enable_quality_check:
                                    quality = self._evaluate_chunk_quality(
                                        current_chunk.strip(), "text"
                                    )
                                    chunk_metadata["quality"] = quality

                                chunks.append(
                                    {
                                        "chunk_id": chunk_id,
                                        "file_id": file_id,
                                        "chunk_index": chunk_index,
                                        "text": current_chunk.strip(),
                                        "metadata": chunk_metadata,
                                    }
                                )

                                current_start = current_start + len(current_chunk)
                                chunk_index += 1
                                current_chunk = ""

                            # 按句子分割長段落
                            sentences = self._split_sentences(para)
                            for sentence in sentences:
                                if (
                                    len(current_chunk) + len(sentence) > effective_chunk_size
                                    and current_chunk
                                ):
                                    chunk_id = str(uuid.uuid4())
                                    chunk_metadata = {
                                        "start_position": current_start,
                                        "end_position": current_start + len(current_chunk),
                                        "chunk_size": len(current_chunk),
                                        "strategy": "semantic",
                                    }

                                    if metadata:
                                        chunk_metadata.update(metadata)

                                    # 質量評估
                                    if self.config.enable_quality_check:
                                        quality = self._evaluate_chunk_quality(
                                            current_chunk.strip(), "text"
                                        )
                                        chunk_metadata["quality"] = quality

                                    chunks.append(
                                        {
                                            "chunk_id": chunk_id,
                                            "file_id": file_id,
                                            "chunk_index": chunk_index,
                                            "text": current_chunk.strip(),
                                            "metadata": chunk_metadata,
                                        }
                                    )

                                    current_start = current_start + len(current_chunk)
                                    chunk_index += 1
                                    current_chunk = sentence
                                else:
                                    current_chunk += sentence
                        else:
                            current_chunk += para

        # 保存最後一個塊
        if current_chunk.strip():
            chunk_id = str(uuid.uuid4())
            chunk_metadata = {
                "start_position": current_start,
                "end_position": current_start + len(current_chunk),
                "chunk_size": len(current_chunk),
                "strategy": "semantic",
            }

            if metadata:
                chunk_metadata.update(metadata)

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "chunk_index": chunk_index,
                    "text": current_chunk.strip(),
                    "metadata": chunk_metadata,
                }
            )

            # 質量評估
            if self.config.enable_quality_check:
                quality = self._evaluate_chunk_quality(current_chunk.strip(), "text")
                chunk_metadata["quality"] = quality

        # 記錄質量統計
        if self.config.enable_quality_check:
            quality_stats = self._calculate_quality_stats(chunks)
            self.logger.info("Chunk quality statistics", **quality_stats)

        return chunks

    def _calculate_quality_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        計算 chunks 的質量統計

        Args:
            chunks: chunk 列表

        Returns:
            質量統計字典
        """
        if not chunks:
            return {}

        total_chunks = len(chunks)
        quality_scores = []
        too_small_count = 0
        too_large_count = 0
        code_block_count = 0
        table_count = 0

        for chunk in chunks:
            quality = chunk.get("metadata", {}).get("quality", {})
            if quality:
                quality_scores.append(quality.get("quality_score", 0))
                if quality.get("is_too_small"):
                    too_small_count += 1
                if quality.get("is_too_large"):
                    too_large_count += 1

            block_type = chunk.get("metadata", {}).get("block_type")
            if block_type == "code_block":
                code_block_count += 1
            elif block_type == "table":
                table_count += 1

        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        return {
            "total_chunks": total_chunks,
            "avg_quality_score": round(avg_quality_score, 2),
            "too_small_count": too_small_count,
            "too_large_count": too_large_count,
            "code_block_count": code_block_count,
            "table_count": table_count,
            "text_chunk_count": total_chunks - code_block_count - table_count,
        }

    def _detect_code_blocks(self, text: str) -> List[tuple[int, int]]:
        """
        檢測代碼塊（包括 Mermaid）的位置範圍

        Args:
            text: 文本內容

        Returns:
            代碼塊位置列表，每個元素為 (start_char_index, end_char_index)
        """
        code_blocks: List[tuple[int, int]] = []
        lines = text.split("\n")
        current_block_start: Optional[int] = None
        current_char_pos = 0

        for i, line in enumerate(lines):
            line_with_newline = line + "\n"
            line_stripped = line.strip()

            # 檢測代碼塊標記（```）
            if line_stripped.startswith("```"):
                if current_block_start is None:
                    # 開始新的代碼塊
                    current_block_start = current_char_pos
                else:
                    # 結束當前代碼塊（包含結束的 ```）
                    code_blocks.append(
                        (current_block_start, current_char_pos + len(line_with_newline))
                    )
                    current_block_start = None

            current_char_pos += len(line_with_newline)

        # 處理未閉合的代碼塊（如果有的話）
        if current_block_start is not None:
            code_blocks.append((current_block_start, len(text)))

        return code_blocks

    def _is_in_code_block(self, position: int, code_blocks: List[tuple[int, int]]) -> bool:
        """
        檢查位置是否在代碼塊內

        Args:
            position: 字符位置
            code_blocks: 代碼塊位置列表

        Returns:
            如果位置在代碼塊內返回 True
        """
        for start, end in code_blocks:
            if start <= position < end:
                return True
        return False

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本，保護代碼塊不被切斷"""
        lines = text.split("\n")
        paragraphs: List[str] = []
        current_para: List[str] = []
        in_code_block = False

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 檢查是否為代碼塊標記（```）
            if line_stripped.startswith("```"):
                # 切換代碼塊狀態
                in_code_block = not in_code_block
                current_para.append(line)
            else:
                current_para.append(line)

                # 只在非代碼塊區域檢查段落邊界
                if not in_code_block:
                    # 檢查是否為段落邊界（雙換行）
                    is_last_line = i == len(lines) - 1
                    current_line_empty = not line.strip()
                    next_line_empty = (
                        not is_last_line and not lines[i + 1].strip() if not is_last_line else False
                    )

                    # 如果當前行為空，且下一行也為空，則形成段落邊界
                    if current_line_empty and next_line_empty:
                        # 保存當前段落（去除末尾的空行）
                        para_text = "\n".join(current_para[:-1]).strip()
                        if para_text:
                            paragraphs.append(para_text)
                        current_para = []

        # 保存最後一個段落
        if current_para:
            para_text = "\n".join(current_para).strip()
            if para_text:
                paragraphs.append(para_text)

        # 如果沒有找到段落（例如整個文本就是一個代碼塊），返回原文
        return paragraphs if paragraphs else [text]

    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        # 簡單的句子分割（可以改進）
        # 匹配句號、問號、感嘆號後跟空格或換行
        sentences = re.split(r"([.!?]\s+)", text)
        # 重新組合句子和標點
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        return [s.strip() for s in result if s.strip()]

    def _ast_driven_chunk(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """AST 驅動分塊（基於標題層級）"""
        try:
            from .markdown_ast import MarkdownASTParser

            ast_parser = MarkdownASTParser()
            ast = ast_parser.parse_ast(text)
            headings = ast_parser.extract_headings(ast)
            heading_tree = ast_parser.build_heading_tree(headings)

            # 過濾 H1-H3 標題
            relevant_headings = [h for h in headings if 1 <= h["level"] <= 3]

            if not relevant_headings:
                # 如果沒有標題，回退到語義分塊
                self.logger.warning("未找到 H1-H3 標題，回退到語義分塊")
                return self._semantic_chunk(text, file_id, metadata)

            # 基於標題切片
            chunks = self._slice_by_headings(text, relevant_headings, heading_tree, ast_parser)

            # Token 負載平衡
            balanced_chunks = self._balance_chunk_tokens(chunks)

            # 添加元數據
            result_chunks = []
            for chunk_idx, chunk in enumerate(balanced_chunks):
                chunk_id = str(uuid.uuid4())
                header_path = ast_parser.get_heading_path(heading_tree, chunk.get("start_line", 1))

                chunk_metadata = {
                    "start_position": chunk.get("start_position", 0),
                    "end_position": chunk.get("end_position", len(text)),
                    "start_line": chunk.get("start_line", 1),
                    "end_line": chunk.get("end_line", 1),
                    "token_count": chunk.get("token_count", 0),
                    "header_path": header_path,
                    "strategy": "ast_driven",
                }

                if metadata:
                    chunk_metadata.update(metadata)

                result_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "file_id": file_id,
                        "chunk_index": chunk_idx,
                        "text": chunk["text"],
                        "metadata": chunk_metadata,
                    }
                )

            return result_chunks
        except ImportError as e:
            self.logger.warning("AST 解析器不可用，回退到語義分塊", error=str(e))
            return self._semantic_chunk(text, file_id, metadata)
        except Exception as e:
            self.logger.error("AST 驅動分塊失敗", error=str(e))
            # 回退到語義分塊
            return self._semantic_chunk(text, file_id, metadata)

    def _slice_by_headings(
        self,
        text: str,
        headings: List[Dict[str, Any]],
        heading_tree: Dict[str, Any],
        ast_parser: Any,
    ) -> List[Dict[str, Any]]:
        """基於標題切片文本"""
        lines = text.splitlines()
        chunks: List[Dict[str, Any]] = []

        # 按標題分割文本
        for i, heading in enumerate(headings):
            start_line = heading["line_number"]
            end_line = headings[i + 1]["line_number"] if i + 1 < len(headings) else len(lines)

            # 提取該標題下的內容
            chunk_lines = lines[start_line - 1 : end_line - 1]
            chunk_text = "\n".join(chunk_lines)

            # 計算 Token 數
            token_count = self._calculate_tokens(chunk_text)

            chunks.append(
                {
                    "text": chunk_text,
                    "start_line": start_line,
                    "end_line": end_line - 1,
                    "start_position": sum(len(lines[j]) + 1 for j in range(start_line - 1)),
                    "end_position": sum(len(lines[j]) + 1 for j in range(end_line - 1)),
                    "token_count": token_count,
                }
            )

        return chunks

    def _calculate_tokens(self, text: str) -> int:
        """計算文本的 Token 數量"""
        if not TIKTOKEN_AVAILABLE:
            # 簡單估算：1 token ≈ 4 字符
            return len(text) // 4

        try:
            # 使用 cl100k_base 編碼（GPT-3.5/GPT-4 使用）
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception as e:
            self.logger.warning("Token 計算失敗，使用估算", error=str(e))
            return len(text) // 4

    def _balance_chunk_tokens(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """平衡切片 Token 數量"""
        balanced: List[Dict[str, Any]] = []

        for chunk in chunks:
            token_count = chunk.get("token_count", 0)

            # 如果切片太小，嘗試合併
            if token_count < self.min_tokens and balanced:
                # 合併到上一個切片
                last_chunk = balanced[-1]
                merged_text = last_chunk["text"] + "\n\n" + chunk["text"]
                merged_tokens = self._calculate_tokens(merged_text)

                if merged_tokens <= self.max_tokens:
                    # 可以合併
                    last_chunk["text"] = merged_text
                    last_chunk["token_count"] = merged_tokens
                    last_chunk["end_line"] = chunk["end_line"]
                    last_chunk["end_position"] = chunk["end_position"]
                    continue

            # 如果切片太大，拆分
            if token_count > self.max_tokens:
                split_chunks = self._split_large_chunk(chunk)
                balanced.extend(split_chunks)
            else:
                balanced.append(chunk)

        return balanced

    def _split_large_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """拆分過大的切片"""
        text = chunk["text"]

        # 按段落拆分
        paragraphs = self._split_paragraphs(text)
        split_chunks: List[Dict[str, Any]] = []
        current_chunk_text = ""
        current_start_line = chunk["start_line"]

        for para in paragraphs:
            if self._calculate_tokens(current_chunk_text + "\n\n" + para) > self.max_tokens:
                # 保存當前切片
                if current_chunk_text:
                    split_chunks.append(
                        {
                            "text": current_chunk_text,
                            "start_line": current_start_line,
                            "end_line": current_start_line
                            + len(current_chunk_text.splitlines())
                            - 1,
                            "start_position": chunk["start_position"],
                            "end_position": chunk["start_position"] + len(current_chunk_text),
                            "token_count": self._calculate_tokens(current_chunk_text),
                        }
                    )
                # 開始新切片
                current_chunk_text = para
                current_start_line = chunk["start_line"] + len(split_chunks) * 10  # 估算
            else:
                current_chunk_text += "\n\n" + para if current_chunk_text else para

        # 保存最後一個切片
        if current_chunk_text:
            split_chunks.append(
                {
                    "text": current_chunk_text,
                    "start_line": current_start_line,
                    "end_line": chunk["end_line"],
                    "start_position": chunk["start_position"] + len(text) - len(current_chunk_text),
                    "end_position": chunk["end_position"],
                    "token_count": self._calculate_tokens(current_chunk_text),
                }
            )

        return split_chunks if split_chunks else [chunk]


def create_chunk_processor_from_config(config: dict) -> ChunkProcessor:
    """
    從配置創建分塊處理器

    Args:
        config: 配置文件中的 chunk_processing 區塊

    Returns:
        ChunkProcessor 實例
    """
    chunk_size = config.get("chunk_size", 512)
    overlap = config.get("overlap", 0.2)
    strategy_str = config.get("strategy", "semantic")

    try:
        strategy = ChunkStrategy(strategy_str)
    except ValueError:
        strategy = ChunkStrategy.SEMANTIC

    return ChunkProcessor(chunk_size=chunk_size, overlap=overlap, strategy=strategy)
