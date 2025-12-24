"""
代碼功能說明: 文件編輯 Patch Engine（unified diff / JSON Patch / Search-and-Replace）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:30:07 (UTC+8)
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import jsonpatch


class PatchApplyError(RuntimeError):
    pass


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class UnifiedHunk:
    src_start: int
    src_len: int
    dst_start: int
    dst_len: int
    lines: List[str]


@dataclass
class SearchReplacePatch:
    """Search-and-Replace 協議的單個 Patch"""

    search_block: str
    replace_block: str
    confidence: Optional[float] = None


@dataclass
class MatchResult:
    """文本匹配結果"""

    position: int
    match_type: str  # 'exact', 'normalized', 'fuzzy'
    similarity: float  # 0.0-1.0


def apply_unified_diff(*, original: str, diff_text: str) -> str:
    """套用 unified diff 到原文。

    支援單檔 unified diff（不處理多檔 patch）。
    """

    orig_lines = original.splitlines()
    diff_lines = diff_text.splitlines()

    hunks: List[UnifiedHunk] = []
    current: Optional[UnifiedHunk] = None

    for raw in diff_lines:
        if raw.startswith("--- ") or raw.startswith("+++ "):
            continue
        if raw.startswith("@@ "):
            m = _HUNK_RE.match(raw)
            if not m:
                raise PatchApplyError(f"Invalid hunk header: {raw}")
            src_start = int(m.group(1))
            src_len = int(m.group(2) or "1")
            dst_start = int(m.group(3))
            dst_len = int(m.group(4) or "1")
            current = UnifiedHunk(
                src_start=src_start,
                src_len=src_len,
                dst_start=dst_start,
                dst_len=dst_len,
                lines=[],
            )
            hunks.append(current)
            continue
        if raw.startswith("\\ No newline at end of file"):
            continue
        if current is None:
            # ignore prelude lines
            continue
        if not raw:
            # empty line is still a context/add/remove line only if prefixed
            # but splitlines() drops prefix; here raw=="" means it had no prefix
            # treat as invalid
            raise PatchApplyError("Invalid diff line (missing prefix)")
        if raw[0] not in {" ", "+", "-"}:
            raise PatchApplyError(f"Invalid diff line prefix: {raw[:1]}")
        current.lines.append(raw)

    if not hunks:
        raise PatchApplyError("No hunks found in diff")

    out: List[str] = []
    src_idx = 0

    for hunk in hunks:
        hunk_src_idx = max(hunk.src_start - 1, 0)
        if hunk_src_idx < src_idx:
            raise PatchApplyError("Overlapping hunks are not supported")

        # copy unchanged region
        out.extend(orig_lines[src_idx:hunk_src_idx])
        src_idx = hunk_src_idx

        for op_line in hunk.lines:
            op = op_line[0]
            text = op_line[1:]

            if op == " ":
                # context must match
                if src_idx >= len(orig_lines) or orig_lines[src_idx] != text:
                    got = orig_lines[src_idx] if src_idx < len(orig_lines) else "<eof>"
                    raise PatchApplyError(
                        f"Context mismatch at line {src_idx+1}: expected {text!r}, got {got!r}"
                    )
                out.append(text)
                src_idx += 1
            elif op == "-":
                # removal must match
                if src_idx >= len(orig_lines) or orig_lines[src_idx] != text:
                    got = orig_lines[src_idx] if src_idx < len(orig_lines) else "<eof>"
                    raise PatchApplyError(
                        f"Removal mismatch at line {src_idx+1}: expected {text!r}, got {got!r}"
                    )
                src_idx += 1
            elif op == "+":
                out.append(text)
            else:
                raise PatchApplyError(f"Unsupported diff op: {op}")

    # append tail
    out.extend(orig_lines[src_idx:])

    # preserve trailing newline if original had one OR diff implies one
    joined = "\n".join(out)
    if original.endswith("\n"):
        return joined + "\n"
    return joined


def apply_json_patch(*, original_json_text: str, patch_ops: List[Dict[str, Any]]) -> str:
    try:
        obj = json.loads(original_json_text)
    except Exception as exc:  # noqa: BLE001
        raise PatchApplyError(f"Invalid base JSON: {exc}") from exc

    try:
        patch = jsonpatch.JsonPatch(patch_ops)
        new_obj = patch.apply(obj, in_place=False)
    except Exception as exc:  # noqa: BLE001
        raise PatchApplyError(f"JSON Patch apply failed: {exc}") from exc

    try:
        return json.dumps(new_obj, ensure_ascii=False, indent=2) + "\n"
    except Exception as exc:  # noqa: BLE001
        raise PatchApplyError(f"JSON serialization failed: {exc}") from exc


def detect_doc_format(*, filename: str, file_type: str) -> str:
    name = (filename or "").lower()
    ft = (file_type or "").lower()
    if name.endswith(".md") or ft in {"text/markdown", "text/x-markdown"}:
        return "md"
    if name.endswith(".json") or "json" in ft:
        return "json"
    return "txt"


def file_extension_for_format(doc_format: str, *, filename: str) -> str:
    # keep original extension if present
    if "." in filename:
        ext = "." + filename.split(".")[-1]
        return ext
    if doc_format == "md":
        return ".md"
    if doc_format == "json":
        return ".json"
    return ".txt"


def next_version_meta(
    *,
    current_custom_metadata: Optional[Dict[str, Any]],
) -> Tuple[int, Dict[str, Any]]:
    meta = dict(current_custom_metadata or {})
    current = meta.get("doc_version")
    try:
        base = int(current) if current is not None else 1
    except Exception:
        base = 1
    meta["doc_version"] = base
    return base, meta


def bump_version_meta(
    *,
    current_custom_metadata: Optional[Dict[str, Any]],
    new_version: int,
) -> Dict[str, Any]:
    meta = dict(current_custom_metadata or {})
    meta["doc_version"] = int(new_version)
    return meta


# ============================================================================
# Search-and-Replace 協議支持
# ============================================================================


def _normalize_whitespace(text: str) -> str:
    """標準化文本：去除多餘空白，保留單個空格和換行"""
    # 將多個連續空白字符替換為單個空格
    normalized = re.sub(r"[ \t]+", " ", text)
    # 將多個連續換行替換為單個換行
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _levenshtein_distance(s1: str, s2: str) -> int:
    """計算兩個字符串的 Levenshtein 距離"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _calculate_similarity(text1: str, text2: str) -> float:
    """計算兩個文本的相似度（0.0-1.0）"""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0

    max_len = max(len(text1), len(text2))
    if max_len == 0:
        return 1.0

    distance = _levenshtein_distance(text1, text2)
    similarity = 1.0 - (distance / max_len)
    return max(0.0, min(1.0, similarity))


def find_text_position(
    *,
    original: str,
    search_block: str,
    cursor_position: Optional[int] = None,
    fuzzy_threshold: float = 0.8,
) -> MatchResult:
    """在原文中查找 search_block 的位置，支持多種匹配策略

    Args:
        original: 原始文本
        search_block: 要查找的文本塊
        cursor_position: 游標位置（可選，用於上下文匹配）
        fuzzy_threshold: 模糊匹配閾值（0.0-1.0）

    Returns:
        MatchResult: 匹配結果

    Raises:
        PatchApplyError: 如果無法找到匹配位置
    """
    if not search_block:
        raise PatchApplyError("search_block cannot be empty")

    # 策略 1: 精確匹配
    exact_pos = original.find(search_block)
    if exact_pos != -1:
        return MatchResult(
            position=exact_pos,
            match_type="exact",
            similarity=1.0,
        )

    # 策略 2: 標準化匹配（去除多餘空白）
    normalized_original = _normalize_whitespace(original)
    normalized_search = _normalize_whitespace(search_block)
    normalized_pos = normalized_original.find(normalized_search)
    if normalized_pos != -1:
        # 將標準化位置映射回原始位置
        # 簡單實現：在原始文本中查找標準化後的文本
        # 注意：這是一個簡化實現，完整實現需要更複雜的位置映射
        for i in range(len(original) - len(search_block) + 1):
            normalized_slice = _normalize_whitespace(original[i : i + len(search_block) * 2])
            if normalized_search in normalized_slice:
                return MatchResult(
                    position=i,
                    match_type="normalized",
                    similarity=0.95,  # 標準化匹配的相似度
                )

    # 策略 3: 模糊匹配（Levenshtein Distance）
    # 如果提供了游標位置，在游標附近 ±1000 字符範圍內搜索
    search_window_start = 0
    search_window_end = len(original)

    if cursor_position is not None:
        search_window_start = max(0, cursor_position - 1000)
        search_window_end = min(len(original), cursor_position + 1000)

    best_match: Optional[MatchResult] = None
    best_similarity = 0.0

    # 在搜索窗口內滑動搜索
    window_size = len(search_block)
    step = max(1, window_size // 10)  # 步長為窗口大小的 10%

    for i in range(search_window_start, search_window_end - window_size + 1, step):
        window_text = original[i : i + window_size]
        similarity = _calculate_similarity(window_text, search_block)

        if similarity >= fuzzy_threshold and similarity > best_similarity:
            best_similarity = similarity
            best_match = MatchResult(
                position=i,
                match_type="fuzzy",
                similarity=similarity,
            )

    if best_match:
        return best_match

    # 如果所有策略都失敗，拋出錯誤
    raise PatchApplyError(
        f"Could not find search_block in original text. "
        f"Tried exact match, normalized match, and fuzzy match (threshold={fuzzy_threshold})"
    )


def search_replace_to_unified_diff(
    *,
    original: str,
    patches: List[SearchReplacePatch],
    cursor_position: Optional[int] = None,
) -> str:
    """將 Search-and-Replace 協議轉換為 unified diff 格式

    Args:
        original: 原始文本
        patches: Search-and-Replace patches 列表
        cursor_position: 游標位置（可選，用於上下文匹配）

    Returns:
        unified diff 格式的字符串

    Raises:
        PatchApplyError: 如果轉換失敗
    """
    if not patches:
        raise PatchApplyError("patches list cannot be empty")

    # 先應用所有 patches 到原文（從後往前處理，避免位置偏移問題）
    # 找到所有匹配位置
    match_results: List[Tuple[SearchReplacePatch, MatchResult]] = []
    for patch in patches:
        match_result = find_text_position(
            original=original,
            search_block=patch.search_block,
            cursor_position=cursor_position,
        )
        match_results.append((patch, match_result))

    # 按位置從後往前排序
    match_results.sort(key=lambda x: x[1].position, reverse=True)

    # 應用所有 patches（從後往前）
    modified_text = original
    for patch, match_result in match_results:
        pos = match_result.position
        # 替換文本
        modified_text = (
            modified_text[:pos]
            + patch.replace_block
            + modified_text[pos + len(patch.search_block) :]
        )

    # 使用 difflib 生成 unified diff
    # 注意：splitlines(keepends=True) 會保留換行符，但 difflib 需要不帶換行符的行
    orig_lines = original.splitlines(keepends=False)
    mod_lines = modified_text.splitlines(keepends=False)

    # 如果原文或修改後文本以換行結尾，需要特殊處理
    if original.endswith("\n"):
        orig_lines.append("")
    if modified_text.endswith("\n"):
        mod_lines.append("")

    # 使用 difflib.unified_diff 生成 unified diff
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile="original",
        tofile="modified",
        lineterm="",
        n=3,  # 上下文行數
    )

    # 轉換為字符串，過濾掉空行
    diff_lines_filtered: List[str] = []
    for line in diff:
        # 保留所有非空行，以及以特殊前綴開頭的行
        if line.strip() or line.startswith(("---", "+++", "@@")):
            diff_lines_filtered.append(line)

    diff_text = "\n".join(diff_lines_filtered)
    if diff_text and not diff_text.endswith("\n"):
        diff_text += "\n"

    return diff_text


def apply_search_replace_patches(
    *,
    original: str,
    patches: List[Dict[str, Any]],
    cursor_position: Optional[int] = None,
) -> str:
    """應用 Search-and-Replace patches 到原文

    Args:
        original: 原始文本
        patches: Search-and-Replace patches 列表（字典格式）
        cursor_position: 游標位置（可選）

    Returns:
        應用 patches 後的新文本

    Raises:
        PatchApplyError: 如果應用失敗
    """
    # 轉換字典格式為 SearchReplacePatch 對象
    search_replace_patches: List[SearchReplacePatch] = []
    for patch_dict in patches:
        if not isinstance(patch_dict, dict):
            raise PatchApplyError(f"Invalid patch format: expected dict, got {type(patch_dict)}")

        search_block = patch_dict.get("search_block")
        replace_block = patch_dict.get("replace_block")

        if not search_block or not isinstance(search_block, str):
            raise PatchApplyError("patch must have 'search_block' as a non-empty string")
        if not isinstance(replace_block, str):
            raise PatchApplyError("patch must have 'replace_block' as a string")

        confidence = patch_dict.get("confidence")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise PatchApplyError("patch 'confidence' must be a number if provided")

        search_replace_patches.append(
            SearchReplacePatch(
                search_block=search_block,
                replace_block=replace_block,
                confidence=float(confidence) if confidence is not None else None,
            )
        )

    # 轉換為 unified diff
    diff_text = search_replace_to_unified_diff(
        original=original,
        patches=search_replace_patches,
        cursor_position=cursor_position,
    )

    # 使用現有的 apply_unified_diff 函數應用
    return apply_unified_diff(original=original, diff_text=diff_text)
