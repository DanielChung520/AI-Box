# 代碼功能說明: 文檔自動拆解服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""文檔自動拆解服務 - 利用 AST 驅動策略將長文檔拆分為主文檔和分文檔"""

from typing import Any, Dict, List, Optional

import structlog

from services.api.models.modular_document import (
    ModularDocumentCreate,
    SubDocumentRef,
)
from services.api.processors.chunk_processor import ChunkProcessor, ChunkStrategy
from services.api.processors.markdown_ast import MarkdownASTParser

logger = structlog.get_logger(__name__)


class DocumentSplitterService:
    """文檔自動拆解服務"""

    def __init__(self):
        """初始化拆解服務"""
        self.logger = logger.bind(component="DocumentSplitterService")
        self.ast_parser = MarkdownASTParser()
        self.chunk_processor = ChunkProcessor(strategy=ChunkStrategy.AST_DRIVEN)

    def split_document(
        self,
        content: str,
        master_file_id: str,
        task_id: str,
        title: Optional[str] = None,
        min_heading_level: int = 1,
        max_heading_level: int = 3,
    ) -> Dict[str, Any]:
        """
        將長文檔拆分為主文檔和分文檔

        Args:
            content: Markdown 文檔內容
            master_file_id: 主文檔文件 ID
            task_id: 任務 ID
            title: 主文檔標題（可選，如果不提供則從內容提取第一個 H1 標題）
            min_heading_level: 最小標題層級（用於切分，默認為 1）
            max_heading_level: 最大標題層級（用於切分，默認為 3）

        Returns:
            包含主文檔內容和分文檔信息的字典：
            {
                "master_content": str,  # 主文檔內容（包含引用）
                "sub_documents": List[Dict],  # 分文檔列表
                "title": str,  # 主文檔標題
            }
        """
        try:
            # 解析 AST
            ast = self.ast_parser.parse_ast(content)
            headings = self.ast_parser.extract_headings(ast)

            # 過濾標題層級（只處理 H1-H3）
            filtered_headings = [
                h for h in headings if min_heading_level <= h["level"] <= max_heading_level
            ]

            if not filtered_headings:
                # 如果沒有符合條件的標題，返回原內容作為主文檔
                self.logger.warning(
                    "No headings found for splitting, returning original content as master",
                    master_file_id=master_file_id,
                )
                extracted_title = title or self._extract_first_h1_title(content) or "Untitled"
                return {
                    "master_content": content,
                    "sub_documents": [],
                    "title": extracted_title,
                }

            # 提取主文檔標題（如果未提供）
            if not title:
                title = self._extract_first_h1_title(content) or "Untitled"

            # 根據標題切分文檔
            sub_documents = self._split_by_headings(
                content=content,
                headings=filtered_headings,
                ast=ast,
                master_file_id=master_file_id,
            )

            # 生成主文檔內容（包含引用）
            master_content = self._generate_master_content(
                title=title,
                sub_documents=sub_documents,
            )

            return {
                "master_content": master_content,
                "sub_documents": sub_documents,
                "title": title,
            }

        except Exception as e:
            self.logger.error(
                f"Failed to split document: {e}",
                error=str(e),
                master_file_id=master_file_id,
            )
            raise

    def _extract_first_h1_title(self, content: str) -> Optional[str]:
        """
        從內容中提取第一個 H1 標題

        Args:
            content: Markdown 內容

        Returns:
            第一個 H1 標題，如果不存在則返回 None
        """
        try:
            ast = self.ast_parser.parse_ast(content)
            headings = self.ast_parser.extract_headings(ast)
            for heading in headings:
                if heading["level"] == 1:
                    return heading["text"]
        except Exception as e:
            self.logger.warning(f"Failed to extract H1 title: {e}")
        return None

    def _split_by_headings(
        self,
        content: str,
        headings: List[Dict[str, Any]],
        ast: Dict[str, Any],
        master_file_id: str,
    ) -> List[Dict[str, Any]]:
        """
        根據標題切分文檔

        Args:
            content: 文檔內容
            headings: 標題列表
            ast: AST 結構
            master_file_id: 主文檔文件 ID

        Returns:
            分文檔列表，每個包含：
            {
                "filename": str,  # 文件名
                "sub_file_id": str,  # 文件 ID（需要由調用方生成）
                "section_title": str,  # 章節標題
                "content": str,  # 章節內容
                "header_path": str,  # 標題路徑
                "order": int,  # 順序
            }
        """
        lines = content.splitlines(keepends=True)
        sub_documents: List[Dict[str, Any]] = []

        heading_tree = self.ast_parser.build_heading_tree(headings)

        for idx, heading in enumerate(headings):
            line_num = heading["line_number"]
            section_title = heading["text"]

            # 確定章節範圍
            start_line = line_num - 1  # 轉換為 0-based 索引
            end_line = (
                headings[idx + 1]["line_number"] - 1 if idx + 1 < len(headings) else len(lines)
            )

            # 提取章節內容
            section_lines = lines[start_line:end_line]
            section_content = "".join(section_lines).strip()

            if not section_content:
                continue

            # 生成文件名（基於標題，清理非法字符）
            filename = self._generate_filename(section_title, idx)

            # 生成標題路徑（Breadcrumbs）
            header_path = self.ast_parser.get_heading_path(heading_tree, line_num)

            sub_documents.append(
                {
                    "filename": filename,
                    "sub_file_id": "",  # 由調用方生成
                    "section_title": section_title,
                    "content": section_content,
                    "header_path": header_path,
                    "order": idx,
                    "line_number": line_num,
                }
            )

        return sub_documents

    def _generate_filename(self, title: str, index: int) -> str:
        """
        根據標題生成文件名

        Args:
            title: 章節標題
            index: 索引

        Returns:
            文件名（.md 擴展名）
        """
        # 清理標題中的非法字符
        import re

        # 移除 Markdown 格式（**bold**, *italic*, `code` 等）
        cleaned = re.sub(r"[*_`]", "", title)
        # 移除特殊字符，保留中文、英文、數字、空格
        cleaned = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", cleaned)
        # 將空格替換為下劃線
        cleaned = re.sub(r"\s+", "_", cleaned).strip()
        # 如果標題為空或太長，使用索引
        if not cleaned or len(cleaned) > 50:
            cleaned = f"section_{index + 1}"

        return f"{cleaned}.md"

    def _generate_master_content(self, title: str, sub_documents: List[Dict[str, Any]]) -> str:
        """
        生成主文檔內容（包含目錄和引用）

        Args:
            title: 主文檔標題
            sub_documents: 分文檔列表

        Returns:
            主文檔內容
        """
        lines = [f"# {title}\n"]

        # 添加目錄（可選）
        if sub_documents:
            lines.append("## 目錄\n\n")
            for sub_doc in sub_documents:
                section_title = sub_doc["section_title"]
                filename = sub_doc["filename"]
                lines.append(f"- [{section_title}]({filename})\n")
            lines.append("\n")

        # 添加引用
        for sub_doc in sub_documents:
            filename = sub_doc["filename"]
            section_title = sub_doc["section_title"]
            # 使用 Transclusion 語法
            lines.append(f"## {section_title}\n\n")
            lines.append(f"![[{filename}]]\n\n")

        return "".join(lines)

    def create_modular_document_from_split(
        self,
        split_result: Dict[str, Any],
        master_file_id: str,
        task_id: str,
        sub_file_ids: List[str],
    ) -> ModularDocumentCreate:
        """
        從拆解結果創建模組化文檔請求

        Args:
            split_result: 拆解結果（來自 split_document）
            master_file_id: 主文檔文件 ID
            task_id: 任務 ID
            sub_file_ids: 分文檔文件 ID 列表（必須與 sub_documents 順序對應）

        Returns:
            ModularDocumentCreate 請求對象
        """
        sub_docs_list = split_result.get("sub_documents", [])
        if len(sub_file_ids) != len(sub_docs_list):
            raise ValueError(
                f"Number of sub_file_ids ({len(sub_file_ids)}) "
                f"does not match number of sub_documents ({len(sub_docs_list)})"
            )

        sub_document_refs: List[SubDocumentRef] = []
        for idx, sub_doc in enumerate(sub_docs_list):
            filename = sub_doc["filename"]
            sub_file_id = sub_file_ids[idx]

            sub_ref = SubDocumentRef(
                sub_file_id=sub_file_id,
                filename=filename,
                section_title=sub_doc["section_title"],
                order=sub_doc["order"],
                transclusion_syntax=f"![[{filename}]]",
                header_path=sub_doc.get("header_path"),
            )
            sub_document_refs.append(sub_ref)

        return ModularDocumentCreate(
            master_file_id=master_file_id,
            title=split_result["title"],
            task_id=task_id,
            sub_documents=sub_document_refs,
        )
