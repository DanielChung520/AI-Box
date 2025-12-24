# 代碼功能說明: 文件分塊處理器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

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
    AST_DRIVEN = "ast_driven"  # AST 驅動分塊（基於標題層級）


class ChunkProcessor:
    """文件分塊處理器"""

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: float = 0.2,
        strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
        min_tokens: int = 500,
        max_tokens: int = 1000,
    ):
        """
        初始化分塊處理器

        Args:
            chunk_size: 分塊大小（字符數，不是 tokens，用於非 AST 策略）
            overlap: 重疊比例（0-1之間）
            strategy: 分塊策略
            min_tokens: 最小 Token 數（用於 AST 策略）
            max_tokens: 最大 Token 數（用於 AST 策略）
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.logger = logger.bind(
            chunk_size=chunk_size,
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

    def _semantic_chunk(
        self,
        text: str,
        file_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """語義分塊（基於段落、句子邊界）"""
        chunks = []

        # 首先按段落分割
        paragraphs = self._split_paragraphs(text)

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            # 如果當前塊加上新段落超過大小限制，保存當前塊
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
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

                # 開始新塊
                current_chunk = para
                current_start = current_start + len(current_chunk) - len(para)
                chunk_index += 1
            else:
                # 如果段落本身超過大小限制，按句子分割
                if len(para) > self.chunk_size:
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
                        if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
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

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 按雙換行符分割
        paragraphs = re.split(r"\n\s*\n", text)
        # 過濾空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs

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
