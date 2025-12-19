# 代碼功能說明: 文件分塊處理器
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件分塊處理器 - 實現多種分塊策略"""

import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ChunkStrategy(Enum):
    """分塊策略枚舉"""

    FIXED_SIZE = "fixed_size"  # 固定大小分塊
    SLIDING_WINDOW = "sliding_window"  # 滑動窗口分塊
    SEMANTIC = "semantic"  # 語義分塊（基於段落、句子邊界）


class ChunkProcessor:
    """文件分塊處理器"""

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: float = 0.2,
        strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
    ):
        """
        初始化分塊處理器

        Args:
            chunk_size: 分塊大小（字符數，不是 tokens）
            overlap: 重疊比例（0-1之間）
            strategy: 分塊策略
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy
        self.logger = logger.bind(chunk_size=chunk_size, overlap=overlap, strategy=strategy.value)

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
