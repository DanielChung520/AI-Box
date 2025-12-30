# 代碼功能說明: 文本轉換工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本轉換工具

支持 Markdown 轉 HTML、HTML 轉純文本、文本編碼轉換等。
"""

from __future__ import annotations

import html
from html.parser import HTMLParser
from typing import Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 支持的格式
SUPPORTED_FORMATS = {"markdown", "html", "plain", "text"}


class TextConverterInput(ToolInput):
    """文本轉換輸入參數"""

    text: str  # 輸入文本
    from_format: str  # 源格式（如 "markdown", "html", "plain"）
    to_format: str  # 目標格式


class TextConverterOutput(ToolOutput):
    """文本轉換輸出結果"""

    converted_text: str  # 轉換後的文本
    original_text: str  # 原始文本
    from_format: str  # 源格式
    to_format: str  # 目標格式


class HTMLToTextParser(HTMLParser):
    """HTML 轉純文本解析器"""

    def __init__(self) -> None:
        """初始化 HTML 解析器"""
        super().__init__()
        self.text: list[str] = []
        self._skip_tags = {"script", "style", "head", "meta", "link"}

    def handle_data(self, data: str) -> None:
        """處理文本數據"""
        self.text.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        """處理開始標籤"""
        if tag.lower() in self._skip_tags:
            return
        # 添加換行符（用於塊級元素）
        if tag.lower() in {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li"}:
            if self.text and not self.text[-1].endswith("\n"):
                self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """處理結束標籤"""
        if tag.lower() in {"p", "div", "li"}:
            if self.text and not self.text[-1].endswith("\n"):
                self.text.append("\n")

    def get_text(self) -> str:
        """獲取純文本"""
        return "".join(self.text).strip()


class TextConverter(BaseTool[TextConverterInput, TextConverterOutput]):
    """文本轉換工具

    支持 Markdown 轉 HTML、HTML 轉純文本、文本編碼轉換等。
    """

    @property
    def name(self) -> str:
        """工具名稱"""
        return "text_converter"

    @property
    def description(self) -> str:
        """工具描述"""
        return "文本轉換工具，支持 Markdown 轉 HTML、HTML 轉純文本等格式轉換"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _validate_format(self, format_name: str) -> None:
        """
        驗證格式是否支持

        Args:
            format_name: 格式名稱

        Raises:
            ToolValidationError: 格式不支持
        """
        if format_name.lower() not in SUPPORTED_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_FORMATS))
            raise ToolValidationError(
                f"Unsupported format: {format_name}. Supported formats: {supported}",
                field="from_format" if format_name == format_name else "to_format",
            )

    def _markdown_to_html(self, text: str) -> str:
        """
        將 Markdown 轉換為 HTML（簡單實現）

        Args:
            text: Markdown 文本

        Returns:
            HTML 文本
        """
        # 簡單的 Markdown 轉 HTML（不依賴外部庫）
        # 只支持基本格式：標題、粗體、斜體、鏈接、列表
        lines = text.split("\n")
        html_lines: list[str] = []
        in_list = False

        for line in lines:
            line = line.strip()

            # 標題
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            # 列表
            elif line.startswith("- ") or line.startswith("* "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{line[2:]}</li>")
            # 段落
            elif line:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                # 簡單的粗體和斜體處理
                line = line.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
                line = line.replace("*", "<em>", 1).replace("*", "</em>", 1)
                html_lines.append(f"<p>{line}</p>")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False

        if in_list:
            html_lines.append("</ul>")

        return "\n".join(html_lines)

    def _html_to_text(self, text: str) -> str:
        """
        將 HTML 轉換為純文本

        Args:
            text: HTML 文本

        Returns:
            純文本
        """
        parser = HTMLToTextParser()
        parser.feed(text)
        return parser.get_text()

    def _convert_text(self, text: str, from_format: str, to_format: str) -> str:
        """
        轉換文本格式

        Args:
            text: 輸入文本
            from_format: 源格式
            to_format: 目標格式

        Returns:
            轉換後的文本

        Raises:
            ToolValidationError: 轉換失敗
        """
        from_format_lower = from_format.lower()
        to_format_lower = to_format.lower()

        # 相同格式，直接返回
        if from_format_lower == to_format_lower:
            return text

        # Markdown 轉 HTML
        if from_format_lower == "markdown" and to_format_lower == "html":
            return self._markdown_to_html(text)

        # HTML 轉純文本
        if from_format_lower == "html" and to_format_lower in ("plain", "text"):
            return self._html_to_text(text)

        # HTML 轉 Markdown（簡單實現）
        if from_format_lower == "html" and to_format_lower == "markdown":
            # 先轉為純文本，然後簡單格式化
            plain_text = self._html_to_text(text)
            # 這裡可以添加更複雜的 HTML 到 Markdown 轉換邏輯
            return plain_text

        # 純文本轉 HTML（簡單實現）
        if from_format_lower in ("plain", "text") and to_format_lower == "html":
            # 將換行符轉換為 <br>
            html_text = html.escape(text).replace("\n", "<br>\n")
            return f"<p>{html_text}</p>"

        # 純文本轉 Markdown（簡單實現）
        if from_format_lower in ("plain", "text") and to_format_lower == "markdown":
            # 簡單的文本轉 Markdown（每行作為段落）
            lines = text.split("\n")
            return "\n\n".join(lines)

        raise ToolValidationError(
            f"Unsupported conversion: {from_format} -> {to_format}",
            field="from_format",
        )

    async def execute(self, input_data: TextConverterInput) -> TextConverterOutput:
        """
        執行文本轉換

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 驗證格式
            self._validate_format(input_data.from_format)
            self._validate_format(input_data.to_format)

            # 轉換文本
            converted_text = self._convert_text(
                input_data.text, input_data.from_format, input_data.to_format
            )

            logger.debug(
                "text_conversion_completed",
                from_format=input_data.from_format,
                to_format=input_data.to_format,
                original_length=len(input_data.text),
                converted_length=len(converted_text),
            )

            return TextConverterOutput(
                converted_text=converted_text,
                original_text=input_data.text,
                from_format=input_data.from_format,
                to_format=input_data.to_format,
            )

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("text_conversion_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to convert text: {str(e)}", tool_name=self.name
            ) from e
