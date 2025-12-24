# 代碼功能說明: PDF 文件解析器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""PDF 文件解析器 - 使用 PyPDF2 和 pdfplumber"""

import re
from typing import Any, Dict, List, Optional

from .base_parser import BaseParser

try:
    import PyPDF2

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF  # noqa: F401

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PdfParser(BaseParser):
    """PDF 文件解析器"""

    def __init__(self):
        super().__init__()
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 未安裝，請運行: pip install PyPDF2")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析 PDF 文件

        Args:
            file_path: 文件路徑

        Returns:
            解析結果，包含文本內容和頁面元數據
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 未安裝")

        try:
            text_parts = []
            pages_metadata: List[Dict[str, Any]] = []

            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)

                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        text_parts.append(page_text)

                        pages_metadata.append(
                            {
                                "page_number": page_num,
                                "char_count": len(page_text),
                                "has_text": len(page_text.strip()) > 0,
                            }
                        )
                    except Exception as e:
                        self.logger.warning(
                            "PDF 頁面解析失敗",
                            file_path=file_path,
                            page_num=page_num,
                            error=str(e),
                        )
                        pages_metadata.append(
                            {
                                "page_number": page_num,
                                "char_count": 0,
                                "has_text": False,
                                "error": str(e),
                            }
                        )

            full_text = "\n\n".join(text_parts)

            return {
                "text": full_text,
                "metadata": {
                    "num_pages": num_pages,
                    "pages": pages_metadata,
                    "char_count": len(full_text),
                },
            }
        except Exception as e:
            self.logger.error("PDF 文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(self, file_content: bytes, **kwargs) -> Dict[str, Any]:
        """
        從字節內容解析 PDF

        Args:
            file_content: 文件內容（字節）
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 未安裝")

        try:
            from io import BytesIO

            text_parts = []
            pages_metadata: List[Dict[str, Any]] = []

            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            num_pages = len(pdf_reader.pages)

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    text_parts.append(page_text)

                    pages_metadata.append(
                        {
                            "page_number": page_num,
                            "char_count": len(page_text),
                            "has_text": len(page_text.strip()) > 0,
                        }
                    )
                except Exception as e:
                    self.logger.warning(
                        "PDF 頁面解析失敗",
                        page_num=page_num,
                        error=str(e),
                    )
                    pages_metadata.append(
                        {
                            "page_number": page_num,
                            "char_count": 0,
                            "has_text": False,
                            "error": str(e),
                        }
                    )

            full_text = "\n\n".join(text_parts)

            return {
                "text": full_text,
                "metadata": {
                    "num_pages": num_pages,
                    "pages": pages_metadata,
                    "char_count": len(full_text),
                },
            }
        except Exception as e:
            self.logger.error("PDF 解析失敗", error=str(e))
            raise

    def parse_to_markdown(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        extract_images: bool = True,
    ) -> Dict[str, Any]:
        """
        將 PDF 轉換為 Markdown 格式

        Args:
            file_path: PDF 文件路徑
            output_dir: 圖片輸出目錄（可選）
            extract_images: 是否提取圖片

        Returns:
            轉換結果，包含 markdown 文本、元數據和映射表
        """
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 未安裝")

        try:
            from ..offset_mapper import OffsetMapper

            original_text = ""
            images: List[Dict[str, Any]] = []
            tables: List[Dict[str, Any]] = []
            headings: List[Dict[str, Any]] = []

            # 使用 PyPDF2 提取原始文本
            num_pages = 0
            with open(file_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)
                text_parts = []
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    text_parts.append(page_text)
                original_text = "\n\n".join(text_parts)

            # 使用 pdfplumber 提取表格（如果可用）
            if PDFPLUMBER_AVAILABLE:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        for page_num, page in enumerate(pdf.pages, start=1):
                            # 提取表格
                            page_tables = page.extract_tables()
                            for table_idx, table in enumerate(page_tables):
                                if table:
                                    markdown_table = self._table_to_markdown(table)
                                    tables.append(
                                        {
                                            "page": page_num,
                                            "table_index": table_idx,
                                            "markdown": markdown_table,
                                        }
                                    )
                except Exception as e:
                    self.logger.warning("pdfplumber 表格提取失敗", error=str(e))

            # 識別標題
            headings = self._identify_headings(original_text)

            # 轉換為 Markdown
            markdown_text = self._text_to_markdown(original_text, headings, tables, images)

            # 創建偏移量映射
            mapper = OffsetMapper()
            offset_mapping = mapper.create_mapping(original_text, markdown_text)

            return {
                "text": markdown_text,
                "metadata": {
                    "original_text": original_text,
                    "num_pages": num_pages,
                    "headings": headings,
                    "tables": tables,
                    "images": images,
                    "offset_mapping": offset_mapping,
                    "mapping_stats": mapper.get_mapping_stats(),
                },
            }
        except Exception as e:
            self.logger.error("PDF 轉 Markdown 失敗", file_path=file_path, error=str(e))
            raise

    def _table_to_markdown(self, table: List[List[Optional[str]]]) -> str:
        """
        將表格數據轉換為 Markdown 表格格式

        Args:
            table: 表格數據（二維列表）

        Returns:
            Markdown 表格字符串
        """
        if not table:
            return ""

        markdown_lines: List[str] = []
        # 清理表格數據
        cleaned_table: List[List[str]] = []
        for row in table:
            cleaned_row: List[str] = [str(cell).strip() if cell else "" for cell in row]
            cleaned_table.append(cleaned_row)

        if not cleaned_table:
            return ""

        # 生成表頭
        header = cleaned_table[0]
        markdown_lines.append("| " + " | ".join(header) + " |")
        markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 生成數據行
        for row in cleaned_table[1:]:
            # 確保行長度與表頭一致
            normalized_row: List[str] = [str(cell) for cell in row]
            while len(normalized_row) < len(header):
                normalized_row.append("")
            normalized_row = normalized_row[: len(header)]
            markdown_lines.append("| " + " | ".join(normalized_row) + " |")

        return "\n".join(markdown_lines)

    def _identify_headings(self, text: str) -> List[Dict[str, Any]]:
        """
        識別文本中的標題層級

        Args:
            text: 文本內容

        Returns:
            標題列表，每個標題包含 level、text、line_number
        """
        headings: List[Dict[str, Any]] = []
        lines = text.splitlines()

        for line_num, line in enumerate(lines, start=1):
            line_stripped = line.strip()

            # 檢查是否為標題（基於字體大小和格式的啟發式規則）
            # 這裡使用簡單的規則：全大寫、短行、特定格式等
            if len(line_stripped) < 100 and line_stripped:
                # 檢查是否全大寫（可能是標題）
                if line_stripped.isupper() and len(line_stripped.split()) <= 10:
                    headings.append(
                        {
                            "level": 1,
                            "text": line_stripped,
                            "line_number": line_num,
                        }
                    )
                # 檢查是否以數字開頭（可能是編號標題）
                elif re.match(r"^\d+[\.\)]\s+", line_stripped):
                    headings.append(
                        {
                            "level": 2,
                            "text": line_stripped,
                            "line_number": line_num,
                        }
                    )

        return headings

    def _text_to_markdown(
        self,
        text: str,
        headings: List[Dict[str, Any]],
        tables: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
    ) -> str:
        """
        將文本轉換為 Markdown 格式

        Args:
            text: 原始文本
            headings: 標題列表
            tables: 表格列表
            images: 圖片列表

        Returns:
            Markdown 格式的文本
        """
        lines = text.splitlines()
        markdown_lines: List[str] = []

        # 標記已處理的標題行
        heading_lines = {h["line_number"]: h for h in headings}

        for line_num, line in enumerate(lines, start=1):
            if line_num in heading_lines:
                heading = heading_lines[line_num]
                # 轉換為 Markdown 標題
                level = heading["level"]
                title = heading["text"]
                markdown_lines.append("#" * level + " " + title)
            else:
                # 普通文本行
                markdown_lines.append(line)

        # 在適當位置插入表格
        # 這裡簡化處理，將所有表格放在文檔末尾
        if tables:
            markdown_lines.append("\n## 表格\n")
            for table_info in tables:
                markdown_lines.append(table_info["markdown"])
                markdown_lines.append("")

        return "\n".join(markdown_lines)

    def get_supported_extensions(self) -> list:
        return [".pdf"]
