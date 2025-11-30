# 代碼功能說明: Markdown 文件解析器
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""Markdown 文件解析器 - 保留結構信息"""

from typing import List, Dict, Any
import re
from .base_parser import BaseParser


class MdParser(BaseParser):
    """Markdown 文件解析器"""

    def __init__(self):
        super().__init__()

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析 Markdown 文件

        Args:
            file_path: 文件路徑

        Returns:
            解析結果，包含文本內容和結構元數據
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 提取結構信息
            sections = self._extract_sections(content)
            headers = self._extract_headers(content)

            return {
                "text": content,
                "metadata": {
                    "encoding": "utf-8",
                    "line_count": len(content.splitlines()),
                    "char_count": len(content),
                    "sections": sections,
                    "headers": headers,
                    "has_code_blocks": "```" in content,
                },
            }
        except Exception as e:
            self.logger.error("Markdown 文件解析失敗", file_path=file_path, error=str(e))
            raise

    def parse_from_bytes(
        self, file_content: bytes, encoding: str = "utf-8", **kwargs
    ) -> Dict[str, Any]:
        """
        從字節內容解析 Markdown

        Args:
            file_content: 文件內容（字節）
            encoding: 編碼格式
            **kwargs: 其他參數

        Returns:
            解析結果
        """
        try:
            text = file_content.decode(encoding)
            sections = self._extract_sections(text)
            headers = self._extract_headers(text)

            return {
                "text": text,
                "metadata": {
                    "encoding": encoding,
                    "line_count": len(text.splitlines()),
                    "char_count": len(text),
                    "sections": sections,
                    "headers": headers,
                    "has_code_blocks": "```" in text,
                },
            }
        except Exception as e:
            self.logger.error("Markdown 解析失敗", error=str(e))
            raise

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """提取章節信息"""
        sections = []
        lines = content.splitlines()
        current_section = None

        for i, line in enumerate(lines):
            # 匹配標題（# 開頭）
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()

                if current_section:
                    sections.append(current_section)

                current_section = {
                    "level": level,
                    "title": title,
                    "start_line": i,
                    "end_line": None,
                }

        if current_section:
            current_section["end_line"] = len(lines) - 1
            sections.append(current_section)

        return sections

    def _extract_headers(self, content: str) -> List[Dict[str, Any]]:
        """提取所有標題"""
        headers = []
        lines = content.splitlines()

        for i, line in enumerate(lines):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                headers.append({"level": level, "title": title, "line": i})

        return headers

    def get_supported_extensions(self) -> list:
        return [".md"]
