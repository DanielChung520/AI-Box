# 代碼功能說明: Transclusion 語法解析器
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""Transclusion 語法解析器 - 解析 ![[filename]] 語法並檢測循環引用"""

import re
from typing import Dict, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)

# Transclusion 語法正則表達式: ![[filename]] 或 ![[path/to/filename.md]]
_TRANSCLUSION_PATTERN = re.compile(r"!\[\[([^\]]+)\]\]", re.MULTILINE)


class TransclusionReference:
    """Transclusion 引用對象"""

    def __init__(
        self,
        syntax: str,
        filename: str,
        line_number: Optional[int] = None,
        column: Optional[int] = None,
    ):
        """
        初始化 Transclusion 引用

        Args:
            syntax: 完整的語法字符串（例如: ![[filename.md]]）
            filename: 提取的文件名（可能包含路徑）
            line_number: 行號（可選）
            column: 列號（可選）
        """
        self.syntax = syntax
        self.filename = filename
        self.line_number = line_number
        self.column = column

    def __repr__(self) -> str:
        return f"TransclusionReference(syntax='{self.syntax}', filename='{self.filename}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TransclusionReference):
            return False
        return self.filename == other.filename and self.syntax == other.syntax

    def __hash__(self) -> int:
        return hash((self.syntax, self.filename))


def parse_transclusion_syntax(text: str) -> List[TransclusionReference]:
    """
    解析文本中的 Transclusion 語法

    Args:
        text: 要解析的文本內容

    Returns:
        TransclusionReference 列表，按出現順序排列
    """
    references: List[TransclusionReference] = []
    lines = text.splitlines(keepends=True)
    current_pos = 0

    for line_num, line in enumerate(lines, start=1):
        for match in _TRANSCLUSION_PATTERN.finditer(line):
            syntax = match.group(0)
            filename = match.group(1).strip()
            column = match.start()

            if filename:
                ref = TransclusionReference(
                    syntax=syntax,
                    filename=filename,
                    line_number=line_num,
                    column=column,
                )
                references.append(ref)

        current_pos += len(line)

    return references


def extract_filename_from_reference(reference: str) -> Optional[str]:
    """
    從 Transclusion 語法中提取文件名

    Args:
        reference: Transclusion 語法字符串（例如: ![[filename.md]]）

    Returns:
        文件名（可能包含路徑），如果格式無效則返回 None
    """
    match = _TRANSCLUSION_PATTERN.match(reference.strip())
    if match:
        return match.group(1).strip()
    return None


def build_reference_graph(
    doc_references: Dict[str, List[str]],
) -> Dict[str, Set[str]]:
    """
    構建文檔引用圖（用於循環檢測）

    Args:
        doc_references: 文檔 ID 到其引用的文件 ID 列表的映射

    Returns:
        文檔 ID 到其直接引用的文件 ID 集合的映射
    """
    graph: Dict[str, Set[str]] = {}

    for doc_id, referenced_files in doc_references.items():
        graph[doc_id] = set(referenced_files)

    return graph


def detect_circular_reference(
    doc_id: str,
    reference_graph: Dict[str, Set[str]],
    max_depth: int = 100,
) -> Optional[List[str]]:
    """
    使用 DFS 檢測循環引用

    Args:
        doc_id: 起始文檔 ID
        reference_graph: 文檔引用圖（doc_id -> set of referenced_file_ids）
        max_depth: 最大搜索深度（防止無限遞歸）

    Returns:
        如果檢測到循環，返回循環路徑（文檔 ID 列表）；否則返回 None
    """
    visited: Set[str] = set()
    path: List[str] = []

    def dfs(current_id: str, depth: int) -> Optional[List[str]]:
        if depth > max_depth:
            logger.warning(
                f"Max depth {max_depth} exceeded while detecting circular reference",
                doc_id=doc_id,
                current_id=current_id,
            )
            return None

        if current_id in visited:
            # 找到循環
            if current_id in path:
                # 提取循環部分
                cycle_start = path.index(current_id)
                cycle_path = path[cycle_start:] + [current_id]
                return cycle_path
            return None

        visited.add(current_id)
        path.append(current_id)

        # 檢查所有引用的文件
        referenced = reference_graph.get(current_id, set())
        for ref_id in referenced:
            cycle = dfs(ref_id, depth + 1)
            if cycle:
                return cycle

        path.pop()
        return None

    return dfs(doc_id, 0)


def validate_references(
    references: List[TransclusionReference],
    existing_file_ids: Set[str],
    filename_to_id_map: Dict[str, str],
) -> Tuple[List[TransclusionReference], List[str]]:
    """
    驗證引用文件是否存在

    Args:
        references: TransclusionReference 列表
        existing_file_ids: 現有文件 ID 集合
        filename_to_id_map: 文件名到文件 ID 的映射

    Returns:
        (有效的引用列表, 無效的文件名列表)
    """
    valid_refs: List[TransclusionReference] = []
    invalid_files: List[str] = []

    for ref in references:
        # 嘗試通過文件名查找文件 ID
        file_id = filename_to_id_map.get(ref.filename)

        if file_id and file_id in existing_file_ids:
            valid_refs.append(ref)
        else:
            invalid_files.append(ref.filename)
            logger.warning(
                f"Reference file not found: {ref.filename}",
                filename=ref.filename,
                syntax=ref.syntax,
            )

    return valid_refs, invalid_files


def replace_transclusion_syntax(text: str, replacements: Dict[str, str]) -> str:
    """
    替換文本中的 Transclusion 語法為實際內容

    Args:
        text: 原始文本
        replacements: Transclusion 語法到替換內容的映射

    Returns:
        替換後的文本
    """
    result = text
    for syntax, content in replacements.items():
        result = result.replace(syntax, content)
    return result
