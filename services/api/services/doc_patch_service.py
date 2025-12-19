"""
代碼功能說明: 文件編輯 Patch Engine（unified diff / JSON Patch）
創建日期: 2025-12-14 10:27:19 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-14 10:27:19 (UTC+8)
"""

from __future__ import annotations

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
