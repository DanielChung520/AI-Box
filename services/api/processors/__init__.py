# 代碼功能說明: 文件處理器模組
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""文件處理器模組 - 提供文件解析和分塊功能"""

from .chunk_processor import ChunkProcessor, ChunkStrategy, create_chunk_processor_from_config
from .contextual_header_generator import ContextualHeaderGenerator, get_contextual_header_generator
from .dual_track_processor import DualTrackProcessor, get_dual_track_processor
from .parsers.image_parser import ImageParser
from .parsers.visual_parser import VisualParser, get_visual_parser
from .visual_element_processor import VisualElementProcessor, get_visual_element_processor

__all__ = [
    "ChunkProcessor",
    "ChunkStrategy",
    "create_chunk_processor_from_config",
    "ImageParser",
    "VisualParser",
    "get_visual_parser",
    "VisualElementProcessor",
    "get_visual_element_processor",
    "ContextualHeaderGenerator",
    "get_contextual_header_generator",
    "DualTrackProcessor",
    "get_dual_track_processor",
]
