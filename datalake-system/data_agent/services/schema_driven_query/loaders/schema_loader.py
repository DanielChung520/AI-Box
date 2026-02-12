# 代碼功能說明: Schema 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Schema 載入器"""

import yaml
from pathlib import Path
from typing import Dict, Any


def load_schema_from_file(path: Path) -> Dict[str, Any]:
    """
    從 YAML 文件載入 Schema

    Args:
        path: YAML 文件路徑

    Returns:
        Dict: Schema 結構
    """
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data or {}
