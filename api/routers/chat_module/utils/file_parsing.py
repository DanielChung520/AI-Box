"""
代碼功能說明: 文件路徑解析工具函數（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

提取自 chat.py 的文件路徑解析相關函數。
"""

import re
from pathlib import Path
from typing import Optional, Tuple


def parse_target_path(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    從 user text 嘗試解析出 "dir/file.ext"；只支援 md/txt/json。
    回傳 (folder_path, filename)；folder_path 以 "a/b" 形式（不含末尾 /）。

    Args:
        text: 用戶輸入文本

    Returns:
        (folder_path, filename) 元組
    """
    t = (text or "").strip()
    matches = re.findall(
        r"([A-Za-z0-9_\-\u4e00-\u9fff/]+\.(?:md|txt|json))\b",
        t,
    )
    if matches:
        raw_path = matches[-1].lstrip("/").strip()
        parts = [p for p in raw_path.split("/") if p]
        if not parts:
            return None, None
        if len(parts) == 1:
            return None, parts[0]
        return "/".join(parts[:-1]), parts[-1]

    # 只有指定目錄但未指定檔名（例如：放到 docs 目錄）
    m = re.search(r"在\s*([A-Za-z0-9_\-\u4e00-\u9fff/]+)\s*目錄", t)
    if m:
        folder = m.group(1).strip().strip("/").strip()
        return folder or None, None

    return None, None


def parse_file_reference(text: str) -> Optional[str]:
    """
    從文本中提取檔案引用（@filename）。
    返回檔名（不含 @ 符號）。

    Args:
        text: 用戶輸入文本

    Returns:
        檔名（不含 @ 符號），如果未找到則返回 None
    """
    t = (text or "").strip()
    # 匹配 @filename.ext 模式
    match = re.search(r"@([A-Za-z0-9_\-\u4e00-\u9fff/]+\.(?:md|txt|json))\b", t)
    if match:
        return match.group(1)
    return None


def default_filename_for_intent(text: str) -> str:
    """
    根據用戶意圖生成默認文件名

    修改時間：2026-01-06 - 增強文件名生成邏輯，支持更多意圖識別

    Args:
        text: 用戶輸入文本

    Returns:
        默認文件名
    """
    t = (text or "").strip()

    # 優先匹配 "主題：XXX" 或 "主題: XXX" 模式
    topic_pattern = r"主題[：:]\s*([A-Za-z0-9_\-\u4e00-\u9fff\s]+?)(?:\s|，|,|$)"
    topic_match = re.search(topic_pattern, t, re.IGNORECASE)
    if topic_match:
        topic = topic_match.group(1).strip()
        # 清理主題名稱，移除特殊字符，保留字母、數字、中文、連字符和下劃線
        topic_clean = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", topic)
        # 限制長度
        if len(topic_clean) > 50:
            topic_clean = topic_clean[:50]
        if topic_clean:
            return f"{topic_clean}.md"

    # 匹配 "產生XXX文件"、"生成XXX文件"、"創建XXX文件" 等模式
    pattern = r"(?:產生|生成|創建|建立|製作|做成|寫成|輸出成|整理成)\s*([A-Za-z0-9_\-\u4e00-\u9fff\s]+?)\s*(?:文件|檔案|文檔|document)"
    match = re.search(pattern, t, re.IGNORECASE)
    if match:
        topic = match.group(1).strip()
        # 清理主題名稱，移除特殊字符，保留字母、數字、中文、連字符和下劃線
        topic_clean = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", topic)
        # 限制長度
        if len(topic_clean) > 50:
            topic_clean = topic_clean[:50]
        return f"{topic_clean}.md"

    # 原有邏輯
    if "整理" in t and "對話" in t:
        return "conversation-summary.md"

    return "ai-output.md"


def file_type_for_filename(filename: str) -> str:
    """
    根據文件名推斷文件類型（MIME type）

    Args:
        filename: 文件名

    Returns:
        MIME 類型字符串
    """
    ext = Path(filename).suffix.lower()
    if ext == ".md":
        return "text/markdown"
    if ext == ".txt":
        return "text/plain"
    if ext == ".json":
        return "application/json"
    return "text/plain"
