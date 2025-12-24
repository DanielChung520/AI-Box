# 代碼功能說明: 解析器工廠
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""解析器工廠 - 實現解析器註冊和自動格式檢測"""

from pathlib import Path
from typing import Dict, Optional, Type

import structlog

from .parsers.base_parser import BaseParser
from .parsers.csv_parser import CsvParser
from .parsers.docx_parser import DocxParser
from .parsers.html_parser import HtmlParser
from .parsers.json_parser import JsonParser
from .parsers.md_parser import MdParser
from .parsers.pdf_parser import PdfParser
from .parsers.txt_parser import TxtParser
from .parsers.xlsx_parser import XlsxParser

logger = structlog.get_logger(__name__)


class ParserFactory:
    """解析器工廠"""

    def __init__(self):
        self.parsers: Dict[str, Type[BaseParser]] = {}
        self.extension_map: Dict[str, Type[BaseParser]] = {}
        self.mime_type_map: Dict[str, Type[BaseParser]] = {}
        self._register_default_parsers()
        self.logger = logger

    def _register_default_parsers(self):
        """註冊默認解析器"""
        # 註冊解析器
        parsers = [
            (TxtParser, [".txt"], ["text/plain"]),
            (MdParser, [".md"], ["text/markdown"]),
            (PdfParser, [".pdf"], ["application/pdf"]),
            (
                DocxParser,
                [".docx"],
                ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            ),
            (CsvParser, [".csv"], ["text/csv"]),
            (JsonParser, [".json"], ["application/json"]),
            (HtmlParser, [".html", ".htm"], ["text/html"]),
            (
                XlsxParser,
                [".xlsx"],
                ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            ),
        ]

        for parser_class, extensions, mime_types in parsers:
            # parser_class 是具體的實現類，不是抽象類
            self.register_parser(parser_class, extensions, mime_types)  # type: ignore[type-abstract]

    def register_parser(
        self,
        parser_class: Type[BaseParser],
        extensions: list,
        mime_types: list,
    ):
        """
        註冊解析器

        Args:
            parser_class: 解析器類
            extensions: 支持的文件擴展名列表
            mime_types: 支持的 MIME 類型列表
        """
        parser_name = parser_class.__name__

        # 註冊到解析器字典
        self.parsers[parser_name] = parser_class

        # 註冊擴展名映射
        for ext in extensions:
            self.extension_map[ext.lower()] = parser_class

        # 註冊 MIME 類型映射
        for mime_type in mime_types:
            self.mime_type_map[mime_type.lower()] = parser_class

        self.logger.info(
            "解析器已註冊",
            parser=parser_name,
            extensions=extensions,
            mime_types=mime_types,
        )

    def get_parser(
        self,
        file_path: Optional[str] = None,
        file_extension: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> BaseParser:
        """
        根據文件信息獲取解析器

        Args:
            file_path: 文件路徑
            file_extension: 文件擴展名
            mime_type: MIME 類型

        Returns:
            解析器實例

        Raises:
            ValueError: 如果無法確定解析器
        """
        # 優先使用文件路徑
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in self.extension_map:
                parser_class = self.extension_map[ext]
                try:
                    return parser_class()
                except ImportError as e:
                    self.logger.warning("解析器初始化失敗，嘗試降級", error=str(e))
                    # 降級為文本解析器
                    return TxtParser()

        # 使用文件擴展名
        if file_extension:
            ext = file_extension.lower()
            if not ext.startswith("."):
                ext = "." + ext
            if ext in self.extension_map:
                parser_class = self.extension_map[ext]
                try:
                    return parser_class()
                except ImportError:
                    return TxtParser()

        # 使用 MIME 類型
        if mime_type:
            mime_lower = mime_type.lower()
            if mime_lower in self.mime_type_map:
                parser_class = self.mime_type_map[mime_lower]
                try:
                    return parser_class()
                except ImportError:
                    return TxtParser()

        # 默認使用文本解析器
        self.logger.warning(
            "無法確定解析器，使用默認文本解析器",
            file_path=file_path,
            file_extension=file_extension,
            mime_type=mime_type,
        )
        return TxtParser()


# 全局工廠實例
_factory: Optional[ParserFactory] = None


def get_parser_factory() -> ParserFactory:
    """獲取解析器工廠實例（單例模式）"""
    global _factory
    if _factory is None:
        _factory = ParserFactory()
    return _factory
