# 代碼功能說明: Markdown AST 解析器
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""Markdown AST 解析器 - 使用 markdown-it-py"""

from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)

try:
    from markdown_it import MarkdownIt

    MARKDOWN_IT_AVAILABLE = True
except ImportError:
    MARKDOWN_IT_AVAILABLE = False


class MarkdownASTParser:
    """Markdown AST 解析器"""

    def __init__(self):
        """初始化 AST 解析器"""
        self.logger = logger.bind(component="MarkdownASTParser")
        if not MARKDOWN_IT_AVAILABLE:
            self.logger.warning("markdown-it-py 未安裝，AST 解析功能將不可用")

    def parse_ast(self, content: str) -> Dict[str, Any]:
        """
        解析 Markdown 為 AST 結構

        Args:
            content: Markdown 文本內容

        Returns:
            AST 結構字典
        """
        if not MARKDOWN_IT_AVAILABLE:
            raise ImportError("markdown-it-py 未安裝，請運行: pip install markdown-it-py")

        try:
            md = MarkdownIt()
            tokens = md.parse(content)

            return {
                "tokens": tokens,
                "content": content,
            }
        except Exception as e:
            self.logger.error("Markdown AST 解析失敗", error=str(e))
            raise

    def extract_headings(self, ast: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        從 AST 中提取標題節點

        Args:
            ast: AST 結構

        Returns:
            標題列表，每個標題包含 level、text、line_number
        """
        headings: List[Dict[str, Any]] = []
        tokens = ast.get("tokens", [])

        for token in tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])  # 從 <h1> 提取 1
                # 查找對應的文本內容
                text = ""
                line_number = token.map[0] + 1 if token.map else 0

                # 查找下一個 inline token 獲取文本
                token_idx = tokens.index(token)
                if token_idx + 1 < len(tokens):
                    next_token = tokens[token_idx + 1]
                    if next_token.type == "inline":
                        text = next_token.content.strip()

                headings.append(
                    {
                        "level": level,
                        "text": text,
                        "line_number": line_number,
                    }
                )

        return headings

    def build_heading_tree(self, headings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        構建標題層級樹結構

        Args:
            headings: 標題列表

        Returns:
            標題樹結構
        """
        if not headings:
            return {"root": None, "children": []}

        tree: Dict[str, Any] = {"root": None, "children": []}
        stack: List[Dict[str, Any]] = [tree]

        for heading in headings:
            level = heading["level"]
            current_node = {
                "heading": heading,
                "children": [],
            }

            # 找到合適的父節點
            while len(stack) > 1 and stack[-1]["heading"]["level"] >= level:
                stack.pop()

            # 添加到當前節點的子節點
            parent = stack[-1]
            if "children" not in parent:
                parent["children"] = []
            parent["children"].append(current_node)
            stack.append(current_node)

        return tree

    def get_heading_path(self, heading_tree: Dict[str, Any], target_line: int) -> str:
        """
        根據行號獲取標題路徑（Breadcrumbs）

        Args:
            heading_tree: 標題樹結構
            target_line: 目標行號

        Returns:
            標題路徑字符串，例如："# 產品規格 > ## 功能描述 > ### 編輯器"
        """
        current_path: List[tuple[int, str]] = []

        def traverse(node: Dict[str, Any]) -> None:
            if "heading" in node:
                heading = node["heading"]
                if heading["line_number"] <= target_line:
                    level = heading["level"]
                    text = heading["text"]
                    # 更新路徑：移除同級或更低級的標題
                    while current_path and current_path[-1][0] >= level:
                        current_path.pop()
                    current_path.append((level, text))

            if "children" in node:
                for child in node["children"]:
                    traverse(child)

        traverse(heading_tree)
        path_parts = [f"{'#' * level} {text}" for level, text in current_path]

        return " > ".join(path_parts) if path_parts else ""

    def ast_to_text_mapping(self, ast: Dict[str, Any]) -> Dict[int, int]:
        """
        創建 AST 節點到文本位置的映射

        Args:
            ast: AST 結構

        Returns:
            映射字典，key 為行號，value 為字符位置
        """
        mapping: Dict[int, int] = {}
        tokens = ast.get("tokens", [])
        content = ast.get("content", "")

        for token in tokens:
            if token.map:
                line_start, line_end = token.map
                # 計算該行的字符位置
                lines_before = content.split("\n")[:line_start]
                char_pos = sum(len(line) + 1 for line in lines_before)  # +1 for newline
                mapping[line_start + 1] = char_pos  # 行號從 1 開始

        return mapping
