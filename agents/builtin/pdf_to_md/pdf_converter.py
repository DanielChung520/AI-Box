# 代碼功能說明: PDF 轉換器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""PDF 轉換器

實現通過 PyMuPDF 將 PDF 轉換為 Markdown。
"""

import logging
from typing import Any, Dict, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)


class PdfConverter:
    """PDF 轉換器

    提供 PDF 到 Markdown 的轉換功能。
    """

    def __init__(self):
        """初始化 PDF 轉換器"""
        self.logger = logger

        if fitz is None:
            raise ImportError(
                "PyMuPDF is not installed. Please install it with: pip install PyMuPDF"
            )

    def convert(
        self,
        pdf_path: str,
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        將 PDF 轉換為 Markdown

        Args:
            pdf_path: PDF 文件路徑
            output_path: 輸出 Markdown 文件路徑
            options: 轉換選項

        Returns:
            轉換是否成功
        """
        try:
            # 打開 PDF
            doc = fitz.open(pdf_path)

            markdown_content = []
            extraction_mode = options.get("extraction_mode", "text") if options else "text"

            for page_num in range(len(doc)):
                page = doc[page_num]

                if extraction_mode == "text":
                    # 提取文本
                    text = page.get_text()
                    if text.strip():
                        markdown_content.append(f"## Page {page_num + 1}\n\n{text}\n")
                elif extraction_mode == "layout":
                    # 提取布局文本
                    blocks = page.get_text("blocks")
                    for block in blocks:
                        if block[6] == 0:  # 文本塊
                            markdown_content.append(block[4])

            doc.close()

            # 寫入 Markdown 文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(markdown_content))

            self.logger.info(f"Markdown converted successfully: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"PDF to Markdown conversion error: {e}", exc_info=True)
            return False
