# 代碼功能說明: 讀取 AI-Box config.json / config.example.json 的通用工具
# 創建日期: 2025-11-25 23:57 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 23:57 (UTC+8)

"""提供專案級設定檔載入功能。"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
FALLBACK_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"


def _read_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_config_path(custom_path: Optional[str]) -> Optional[Path]:
    if custom_path:
        candidate = Path(custom_path).expanduser()
        if candidate.exists():
            return candidate
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    if FALLBACK_CONFIG_PATH.exists():
        return FALLBACK_CONFIG_PATH
    return None


@lru_cache
def load_project_config() -> Dict[str, Any]:
    """
    嘗試依序載入 config/config.json → config/config.example.json。

    Returns:
        dict: 設定內容（若找不到設定檔則回傳空 dict）
    """
    path = _resolve_config_path(os.getenv("AI_BOX_CONFIG_PATH"))
    if not path:
        return {}
    try:
        return _read_config(path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config at {path}: {exc}") from exc


def get_config_section(*keys: str, default: Optional[Any] = None) -> Any:
    """
    取得巢狀設定值，若鍵不存在可回傳預設值。

    Args:
        *keys: 巢狀鍵路徑，例如 ("services", "ollama").
        default: 預設值
    """
    config = load_project_config()
    node: Any = config
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node
