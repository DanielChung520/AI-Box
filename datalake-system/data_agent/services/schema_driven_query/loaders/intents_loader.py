# 代碼功能說明: Intents 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Intents 載入器"""

from typing import Dict, Any


def load_intents_from_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    從 JSON 数据載入 Intents

    Args:
        data: JSON 數據

    Returns:
        Dict: Intents 結構
    """
    if not data or "intents" not in data:
        return {"version": "1.0", "intents": {}}

    intents = {}
    for intent_name, intent_data in data.get("intents", {}).items():
        intent_dict = {
            "description": intent_data.get("description", ""),
            "input": {
                "filters": intent_data.get("input", {}).get("filters", []),
                "required_filters": intent_data.get("input", {}).get("required_filters", []),
            },
            "output": {
                "metrics": intent_data.get("output", {}).get("metrics", []),
                "dimensions": intent_data.get("output", {}).get("dimensions", []),
            },
            "constraints": intent_data.get("constraints", {}),
        }
        # 包含額外欄位（如 mart_table）
        if "mart_table" in intent_data:
            intent_dict["mart_table"] = intent_data["mart_table"]

        intents[intent_name] = intent_dict

    return {"version": data.get("version", "1.0"), "intents": intents}
