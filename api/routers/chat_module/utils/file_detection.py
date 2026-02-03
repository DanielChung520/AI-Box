"""
代碼功能說明: 文件意圖檢測工具函數（新架構）
創建日期: 2026-01-28 12:40 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-28 12:40 UTC+8

提取自 chat.py 的文件意圖檢測相關函數。
"""

import re


def looks_like_create_file_intent(text: str) -> bool:
    """
    Chat 輸入框：判斷是否有「新增/輸出成檔案」意圖（MVP 以 heuristic 為主）。

    Args:
        text: 用戶輸入文本

    Returns:
        是否為創建文件意圖
    """
    t = (text or "").strip()
    if not t:
        return False

    # 明確要求：新增檔案 / 建立檔案 / 產生檔案 / 另存等
    keywords = [
        "新增檔案",
        "建立檔案",
        "產生檔案",
        "生成檔案",
        "生成文件",  # 修改時間：2026-01-06 - 添加「生成文件」關鍵詞
        "幫我生成文件",  # 修改時間：2026-01-06 - 添加「幫我生成文件」關鍵詞
        "幫我生成檔案",  # 修改時間：2026-01-06 - 添加「幫我生成檔案」關鍵詞
        "輸出成檔案",
        "輸出成文件",
        "寫成檔案",
        "寫成文件",
        "保存成",
        "存成",
        "另存",
        "做成一份文件",
        "做成一份檔案",
        "做成文件",
        "做成檔案",
        "做成一份",
        "製作成文件",
        "製作成檔案",
        "製作文件",
        "製作檔案",
    ]
    if any(k in t for k in keywords):
        return True

    # 隱含意圖：整理以上對話（通常是要生成文件）
    implicit = [
        "幫我整理以上對話",
        "整理以上對話",
        "整理這段對話",
        "整理對話",
        "整理成文件",
        "整理成檔案",
    ]
    if any(k in t for k in implicit):
        return True

    # 出現明確檔名（含副檔名）也視為建檔意圖
    if re.search(r"[A-Za-z0-9_\-\u4e00-\u9fff/]+\.(md|txt|json)\b", t):
        return True

    return False


def looks_like_edit_file_intent(text: str) -> bool:
    """
    檢測是否為編輯檔案意圖。
    模式：
    - "幫我修改 @xxx.md"
    - "在 @xxx.md 中增加"
    - "編輯 @xxx.md"
    - "更新 @xxx.md"
    - "幫我在 @xxx.md 增加一些文字"

    Args:
        text: 用戶輸入文本

    Returns:
        是否為編輯文件意圖
    """
    t = (text or "").strip()
    if not t:
        return False

    # 檢測 @filename 模式
    if re.search(r"@[A-Za-z0-9_\-\u4e00-\u9fff/]+\.(md|txt|json)\b", t):
        # 配合編輯關鍵詞
        edit_keywords = [
            "修改",
            "編輯",
            "更新",
            "增加",
            "添加",
            "刪除",
            "移除",
            "幫我",
            "請",
            "在",
            "中",
            "裡",
        ]
        if any(k in t for k in edit_keywords):
            return True

    return False
