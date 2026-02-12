# 代碼功能說明: Bindings 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Bindings 載入器"""

from typing import Dict, Any

AGGREGATION_MAPPING = {
    "": "NONE",
    None: "NONE",
    "SUM": "SUM",
    "AVG": "AVG",
    "COUNT": "COUNT",
    "MIN": "MIN",
    "MAX": "MAX",
}


def load_bindings_from_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    從 JSON 数据載入 Bindings

    Args:
        data: JSON 數據

    Returns:
        Dict: Bindings 結構
    """
    if not data:
        return {
            "version": "1.0",
            "datasource": {"type": "ORACLE"},
            "bindings": {},
        }

    bindings = {}
    for concept_name, binding_data in data.get("bindings", {}).items():
        bindings[concept_name] = {}
        for datasource, binding in binding_data.items():
            raw_agg = binding.get("aggregation")
            mapped_agg = AGGREGATION_MAPPING.get(raw_agg, "NONE")
            bindings[concept_name][datasource] = {
                "table": binding.get("table", ""),
                "column": binding.get("column", ""),
                "aggregation": mapped_agg,
                "operator": binding.get("operator", "="),
            }

    return {
        "version": data.get("version", "1.0"),
        "datasource": data.get("datasource", {"type": "ORACLE"}),
        "bindings": bindings,
    }
