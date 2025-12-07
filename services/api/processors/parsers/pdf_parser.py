# 代碼功能說明: PDF 文件解析器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""PDF 文件解析器 - 使用 PyPDF2"""

from typing import Dict, Any, List
from .base_parser import BaseParser

try:
    import PyPDF2

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


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

    def get_supported_extensions(self) -> list:
        return [".pdf"]
