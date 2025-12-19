# 代碼功能說明: HTML 文件解析器
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""HTML 文件解析器 - 使用 BeautifulSoup"""

from typing import Any, Dict

from .base_parser import BaseParser

try:
    from bs4 import BeautifulSoup

    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False


class HtmlParser(BaseParser):
    """HTML 文件解析器"""

    def __init__(self):
        super().__init__()
        if not HTML_AVAILABLE:
            raise ImportError("beautifulsoup4 未安裝，請運行: pip install beautifulsoup4")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 HTML 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")

            # 提取文本內容
            text = soup.get_text(separator="\n", strip=True)

            # 提取標題
            title = soup.title.string if soup.title else None

            return {
                "text": text,
                "metadata": {
                    "title": title,
                    "char_count": len(text),
                    "has_links": len(soup.find_all("a")) > 0,
                },
            }
        except Exception as e:
            self.logger.error("HTML 文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(self, file_content: bytes, **kwargs: Any) -> Dict[str, Any]:
        """從字節內容解析 HTML"""
        encoding: str = kwargs.get("encoding", "utf-8")
        try:
            html_content = file_content.decode(encoding)
            soup = BeautifulSoup(html_content, "html.parser")

            text = soup.get_text(separator="\n", strip=True)
            title = soup.title.string if soup.title else None

            return {
                "text": text,
                "metadata": {
                    "title": title,
                    "char_count": len(text),
                    "has_links": len(soup.find_all("a")) > 0,
                },
            }
        except Exception as e:
            self.logger.error("HTML 解析失敗", error=str(e))
            raise

    def get_supported_extensions(self) -> list:
        return [".html", ".htm"]
