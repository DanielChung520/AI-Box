# 代碼功能說明: Concepts 載入器
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Concepts 載入器"""

from typing import Dict, Any

TYPE_MAPPING = {
    "CODE": "DIMENSION",
    "STRING": "DIMENSION",
    "DATE": "DIMENSION",
    "NUMBER": "METRIC",
    "INTEGER": "METRIC",
    "DECIMAL": "METRIC",
}


def load_concepts_from_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    從 JSON 数据載入 Concepts

    Args:
        data: JSON 數據

    Returns:
        Dict: Concepts 結構
    """
    if not data or "concepts" not in data:
        return {"version": "1.0", "concepts": {}}

    concepts = {}
    for concept_name, concept_data in data.get("concepts", {}).items():
        raw_type = concept_data.get("type", "DIMENSION")
        mapped_type = TYPE_MAPPING.get(raw_type, raw_type)
        concepts[concept_name] = {
            "type": mapped_type,
            "labels": concept_data.get("labels", []),
            "description": concept_data.get("description", ""),
            "data_type": concept_data.get("data_type", "STRING"),
        }

    return {"version": data.get("version", "1.0"), "concepts": concepts}
