#!/usr/bin/env python3
# 代碼功能說明: 圖譜質量評估腳本
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""圖譜質量評估腳本

功能：
1. 通過系統 API 獲取圖譜統計
2. 分析實體、關係、三元組質量
3. 生成質量評估報告

使用方法:
    python scripts/evaluate_kg_quality.py <file_id>

範例:
    python scripts/evaluate_kg_quality.py d6b8c42a-aac5-40b1-8c87-4a9680e1d4f3
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    from datetime import datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def get_kg_stats(file_id: str) -> Dict[str, Any]:
    """獲取圖譜統計（使用系統服務）"""
    try:
        from database.redis import get_redis_client
        import json

        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)

        if status_data_str:
            status_data = json.loads(status_data_str)
            kg_extraction = status_data.get("kg_extraction", {})
            return {
                "triples_count": kg_extraction.get("triples_count", 0),
                "entities_count": kg_extraction.get("entities_count", 0),
                "relations_count": kg_extraction.get("relations_count", 0),
                "mode": kg_extraction.get("mode", "all_chunks"),
            }
        return {"triples_count": 0, "entities_count": 0, "relations_count": 0}
    except Exception as e:
        print(f"⚠️  獲取圖譜統計失敗: {e}")
        return {"triples_count": 0, "entities_count": 0, "relations_count": 0}


def get_processing_status(file_id: str) -> Dict[str, Any]:
    """獲取處理狀態（使用系統服務）"""
    try:
        from services.api.services.upload_status_service import UploadStatusService

        status_service = UploadStatusService()
        status = status_service.get_processing_status(file_id)
        if status:
            # 轉換 Pydantic 模型為字典
            if hasattr(status, "model_dump"):
                return status.model_dump()
            elif hasattr(status, "dict"):
                return status.dict()
            else:
                return {}
        return {}
    except Exception as e:
        print(f"⚠️  獲取處理狀態失敗: {e}")
        return {}


def get_kg_data(file_id: str, limit: int = 1000) -> Dict[str, Any]:
    """獲取圖譜詳細數據（使用系統服務）"""
    try:
        from database.arangodb import get_arangodb_client

        client = get_arangodb_client()
        if client.db is None or client.db.aql is None:
            return {"entities": [], "relations": []}

        # 查詢實體
        entities_query = """
        FOR entity IN entities
            FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
            LIMIT @limit
            RETURN entity
        """
        entities = list(
            client.db.aql.execute(entities_query, bind_vars={"file_id": file_id, "limit": limit})
        )

        # 查詢關係
        relations_query = """
        FOR relation IN relations
            FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
            LIMIT @limit
            RETURN relation
        """
        relations = list(
            client.db.aql.execute(relations_query, bind_vars={"file_id": file_id, "limit": limit})
        )

        return {
            "entities": entities or [],
            "relations": relations or [],
        }
    except Exception as e:
        print(f"⚠️  獲取圖譜數據失敗: {e}")
        return {"entities": [], "relations": []}


def analyze_entity_quality(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析實體質量"""
    if not entities:
        return {
            "total_count": 0,
            "type_distribution": {},
            "normalization_issues": [],
            "length_distribution": {},
            "quality_score": 0.0,
        }

    type_distribution = {}
    normalization_issues = []
    lengths = []

    for entity in entities:
        # 統計類型分布
        entity_type = entity.get("type", "UNKNOWN")
        type_distribution[entity_type] = type_distribution.get(entity_type, 0) + 1

        # 檢查名稱規範化（全角字符）
        entity_name = entity.get("name", "")
        fullwidth_chars = "ＡＢＣＤＥＦＧ１２３４５６７８９０，。：；？！（）［］｛｝"
        found_chars = [c for c in entity_name if c in fullwidth_chars]
        if found_chars:
            normalization_issues.append(
                {"entity_id": entity.get("_id", ""), "name": entity_name, "issues": found_chars}
            )

        # 統計長度
        lengths.append(len(entity_name))

    # 計算質量分數
    normalization_score = 1.0 - (len(normalization_issues) / len(entities)) if entities else 1.0
    diversity_score = min(len(type_distribution) / 10.0, 1.0)  # 假設 10 種以上類型為優秀
    quality_score = (normalization_score * 0.7 + diversity_score * 0.3) * 100

    return {
        "total_count": len(entities),
        "type_distribution": type_distribution,
        "normalization_issues": normalization_issues,
        "length_distribution": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "avg": sum(lengths) / len(lengths) if lengths else 0,
        },
        "quality_score": quality_score,
    }


def analyze_relation_quality(relations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析關係質量"""
    if not relations:
        return {
            "total_count": 0,
            "type_distribution": {},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0, "rejected": 0},
            "connection_validity": {"valid": 0, "invalid": 0},
            "quality_score": 0.0,
        }

    type_distribution = {}
    confidence_distribution = {"high": 0, "medium": 0, "low": 0, "rejected": 0}
    valid_connections = 0
    invalid_connections = 0

    for relation in relations:
        # 統計類型分布
        relation_type = relation.get("type", "UNKNOWN")
        type_distribution[relation_type] = type_distribution.get(relation_type, 0) + 1

        # 統計置信度分布
        confidence = relation.get("confidence", 0.0)
        if confidence >= 0.9:
            confidence_distribution["high"] += 1
        elif confidence >= 0.7:
            confidence_distribution["medium"] += 1
        elif confidence >= 0.5:
            confidence_distribution["low"] += 1
        else:
            confidence_distribution["rejected"] += 1

        # 檢查連接有效性（檢查 _from 和 _to 是否存在）
        if relation.get("_from") and relation.get("_to"):
            valid_connections += 1
        else:
            invalid_connections += 1

    # 計算質量分數
    confidence_score = (
        (
            confidence_distribution["high"] * 1.0
            + confidence_distribution["medium"] * 0.7
            + confidence_distribution["low"] * 0.5
        )
        / len(relations)
        if relations
        else 0.0
    )
    validity_score = valid_connections / len(relations) if relations else 1.0
    diversity_score = min(len(type_distribution) / 10.0, 1.0)
    quality_score = (confidence_score * 0.5 + validity_score * 0.3 + diversity_score * 0.2) * 100

    return {
        "total_count": len(relations),
        "type_distribution": type_distribution,
        "confidence_distribution": confidence_distribution,
        "connection_validity": {"valid": valid_connections, "invalid": invalid_connections},
        "quality_score": quality_score,
    }


def analyze_triple_quality(
    entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """分析三元組質量（實體 + 關係）"""
    triples_count = len(relations)  # 每個關係對應一個三元組

    if triples_count == 0:
        return {
            "total_count": 0,
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0, "rejected": 0},
            "core_nodes_count": 0,
            "completeness": 0.0,
            "quality_score": 0.0,
        }

    confidence_distribution = {"high": 0, "medium": 0, "low": 0, "rejected": 0}
    core_nodes = 0

    for relation in relations:
        confidence = relation.get("confidence", 0.0)
        if confidence >= 0.9:
            confidence_distribution["high"] += 1
            core_nodes += 1
        elif confidence >= 0.7:
            confidence_distribution["medium"] += 1
        elif confidence >= 0.5:
            confidence_distribution["low"] += 1
        else:
            confidence_distribution["rejected"] += 1

    # 計算完整性（有 subject 和 object 的三元組比例）
    complete_triples = sum(
        1 for r in relations if r.get("_from") and r.get("_to") and r.get("type")
    )
    completeness = complete_triples / triples_count if triples_count > 0 else 0.0

    # 計算質量分數
    confidence_score = (
        (
            confidence_distribution["high"] * 1.0
            + confidence_distribution["medium"] * 0.7
            + confidence_distribution["low"] * 0.5
        )
        / triples_count
        if triples_count > 0
        else 0.0
    )
    quality_score = (confidence_score * 0.7 + completeness * 0.3) * 100

    return {
        "total_count": triples_count,
        "confidence_distribution": confidence_distribution,
        "core_nodes_count": core_nodes,
        "completeness": completeness,
        "quality_score": quality_score,
    }


def check_ontology_compliance(
    entities: List[Dict[str, Any]], relations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """檢查 Ontology 符合性（簡化版本）"""
    # 這裡可以添加更詳細的 Ontology 符合性檢查
    # 當前只檢查實體和關係是否有類型定義
    entity_types_without_definition = set()
    relation_types_without_definition = set()

    for entity in entities:
        entity_type = entity.get("type")
        if entity_type and entity_type == "UNKNOWN":
            entity_types_without_definition.add(entity_type)

    for relation in relations:
        relation_type = relation.get("type")
        if relation_type and relation_type == "UNKNOWN":
            relation_types_without_definition.add(relation_type)

    compliance_score = 1.0
    if entities:
        compliance_score -= len(entity_types_without_definition) / len(entities) * 0.5
    if relations:
        compliance_score -= len(relation_types_without_definition) / len(relations) * 0.5
    compliance_score = max(0.0, compliance_score) * 100

    return {
        "entity_types_without_definition": list(entity_types_without_definition),
        "relation_types_without_definition": list(relation_types_without_definition),
        "compliance_score": compliance_score,
    }


def generate_report(
    file_id: str,
    kg_stats: Dict[str, Any],
    processing_status: Dict[str, Any],
    entity_quality: Dict[str, Any],
    relation_quality: Dict[str, Any],
    triple_quality: Dict[str, Any],
    ontology_compliance: Dict[str, Any],
) -> Dict[str, Any]:
    """生成評估報告"""
    timestamp = int(time.time())
    report_dir = project_root / "logs" / "kg_quality"
    report_dir.mkdir(parents=True, exist_ok=True)

    # 計算總體評估
    overall_score = (
        entity_quality.get("quality_score", 0) * 0.3
        + relation_quality.get("quality_score", 0) * 0.4
        + triple_quality.get("quality_score", 0) * 0.2
        + ontology_compliance.get("compliance_score", 0) * 0.1
    )

    if overall_score >= 80:
        overall_rating = "good"
    elif overall_score >= 60:
        overall_rating = "fair"
    else:
        overall_rating = "poor"

    report_data = {
        "file_id": file_id,
        "timestamp": timestamp,
        "evaluation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kg_stats": kg_stats,
        "processing_status": processing_status,
        "entity_quality": entity_quality,
        "relation_quality": relation_quality,
        "triple_quality": triple_quality,
        "ontology_compliance": ontology_compliance,
        "overall": {
            "score": overall_score,
            "rating": overall_rating,
        },
    }

    # 保存 JSON 報告
    json_file = report_dir / f"evaluation_{file_id}_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2, default=json_serial)

    # 生成 Markdown 報告
    markdown_file = report_dir / f"evaluation_{file_id}_{timestamp}.md"
    with open(markdown_file, "w", encoding="utf-8") as f:
        f.write("# 圖譜質量評估報告\n\n")
        f.write(f"**文件 ID**: `{file_id}`\n")
        f.write(f"**評估時間**: {report_data['evaluation_time']}\n\n")

        f.write("## 總體評估\n\n")
        f.write(f"- **總體評分**: {overall_score:.1f}/100\n")
        f.write(f"- **總體等級**: {overall_rating.upper()}\n\n")

        f.write("## 圖譜統計\n\n")
        f.write(f"- 實體數量 (NER): {kg_stats.get('entities_count', 0)}\n")
        f.write(f"- 關係數量 (RE): {kg_stats.get('relations_count', 0)}\n")
        f.write(f"- 三元組數量 (RT): {kg_stats.get('triples_count', 0)}\n\n")

        f.write("## 實體質量分析\n\n")
        f.write(f"- 總數: {entity_quality.get('total_count', 0)}\n")
        f.write(f"- 質量分數: {entity_quality.get('quality_score', 0):.1f}/100\n")
        f.write("- 類型分布:\n")
        for entity_type, count in entity_quality.get("type_distribution", {}).items():
            f.write(f"  - `{entity_type}`: {count}\n")
        f.write("\n")

        f.write("## 關係質量分析\n\n")
        f.write(f"- 總數: {relation_quality.get('total_count', 0)}\n")
        f.write(f"- 質量分數: {relation_quality.get('quality_score', 0):.1f}/100\n")
        f.write("- 置信度分布:\n")
        conf_dist = relation_quality.get("confidence_distribution", {})
        f.write(f"  - 高置信度 (≥0.9): {conf_dist.get('high', 0)}\n")
        f.write(f"  - 中置信度 (0.7-0.9): {conf_dist.get('medium', 0)}\n")
        f.write(f"  - 低置信度 (0.5-0.7): {conf_dist.get('low', 0)}\n")
        f.write(f"  - 被拒絕 (<0.5): {conf_dist.get('rejected', 0)}\n")
        f.write("\n")

        f.write("## 三元組質量分析\n\n")
        f.write(f"- 總數: {triple_quality.get('total_count', 0)}\n")
        f.write(f"- 質量分數: {triple_quality.get('quality_score', 0):.1f}/100\n")
        f.write(f"- 核心節點數量: {triple_quality.get('core_nodes_count', 0)}\n")
        f.write(f"- 完整性: {triple_quality.get('completeness', 0):.1%}\n")
        f.write("\n")

        f.write("## Ontology 符合性檢查\n\n")
        f.write(f"- 符合性分數: {ontology_compliance.get('compliance_score', 0):.1f}/100\n")
        if ontology_compliance.get("entity_types_without_definition"):
            f.write(
                f"- 未定義的實體類型: {ontology_compliance['entity_types_without_definition']}\n"
            )
        if ontology_compliance.get("relation_types_without_definition"):
            f.write(
                f"- 未定義的關係類型: {ontology_compliance['relation_types_without_definition']}\n"
            )
        f.write("\n")

    print(f"\n[報告] JSON 報告已保存到: {json_file}")
    print(f"[報告] Markdown 報告已保存到: {markdown_file}")

    return report_data


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法: python scripts/evaluate_kg_quality.py <file_id>")
        sys.exit(1)

    file_id = sys.argv[1]

    print("=" * 80)
    print("圖譜質量評估")
    print("=" * 80)
    print(f"文件 ID: {file_id}\n")

    # 1. 獲取圖譜統計
    print("[1] 獲取圖譜統計...")
    kg_stats = get_kg_stats(file_id)
    print(f"  ✅ 實體數量: {kg_stats.get('entities_count', 0)}")
    print(f"  ✅ 關係數量: {kg_stats.get('relations_count', 0)}")
    print(f"  ✅ 三元組數量: {kg_stats.get('triples_count', 0)}")

    # 2. 獲取處理狀態
    print("\n[2] 獲取處理狀態...")
    processing_status = get_processing_status(file_id)
    kg_extraction = processing_status.get("kg_extraction", {})
    print(f"  ✅ KG 提取狀態: {kg_extraction.get('status', 'N/A')}")
    print(f"  ✅ KG 提取進度: {kg_extraction.get('progress', 0)}%")

    # 3. 獲取圖譜詳細數據
    print("\n[3] 獲取圖譜詳細數據...")
    kg_data = get_kg_data(file_id, limit=1000)
    entities = kg_data.get("entities", [])
    relations = kg_data.get("relations", [])
    print(f"  ✅ 獲取實體: {len(entities)} 個")
    print(f"  ✅ 獲取關係: {len(relations)} 個")

    # 4. 質量分析
    print("\n[4] 執行質量分析...")
    entity_quality = analyze_entity_quality(entities)
    relation_quality = analyze_relation_quality(relations)
    triple_quality = analyze_triple_quality(entities, relations)
    ontology_compliance = check_ontology_compliance(entities, relations)

    print(f"  ✅ 實體質量分數: {entity_quality.get('quality_score', 0):.1f}/100")
    print(f"  ✅ 關係質量分數: {relation_quality.get('quality_score', 0):.1f}/100")
    print(f"  ✅ 三元組質量分數: {triple_quality.get('quality_score', 0):.1f}/100")
    print(f"  ✅ Ontology 符合性分數: {ontology_compliance.get('compliance_score', 0):.1f}/100")

    # 5. 生成報告
    print("\n[5] 生成評估報告...")
    report_data = generate_report(
        file_id,
        kg_stats,
        processing_status,
        entity_quality,
        relation_quality,
        triple_quality,
        ontology_compliance,
    )

    # 輸出摘要
    print("\n" + "=" * 80)
    print("評估摘要")
    print("=" * 80)
    overall = report_data["overall"]
    print(f"總體評分: {overall['score']:.1f}/100")
    print(f"總體等級: {overall['rating'].upper()}")
    print(f"實體數量: {entity_quality.get('total_count', 0)}")
    print(f"關係數量: {relation_quality.get('total_count', 0)}")
    print(f"三元組數量: {triple_quality.get('total_count', 0)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
