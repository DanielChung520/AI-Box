# 代碼功能說明: 驗證知識圖譜提取結果完整性
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""驗證批量處理結果的完整性

檢查：
1. 所有文件都已處理
2. 向量化記錄完整性（ChromaDB）
3. 知識圖譜提取記錄完整性（ArangoDB）
4. 文件授權設置（SystemSecurity 安全組）
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from dotenv import load_dotenv

load_dotenv()

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.arangodb import ArangoDBClient
from database.chromadb import ChromaDBClient
from services.api.services.file_metadata_service import get_metadata_service

logger = structlog.get_logger(__name__)


def load_progress(progress_file: str) -> Dict[str, Any]:
    """加載進度文件"""
    if not os.path.exists(progress_file):
        logger.error("進度文件不存在", file=progress_file)
        return {}

    with open(progress_file, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_file_metadata(file_id: str) -> Dict[str, Any]:
    """驗證文件元數據

    Args:
        file_id: 文件ID

    Returns:
        驗證結果
    """
    result: Dict[str, Any] = {
        "file_id": file_id,
        "exists": False,
        "has_metadata": False,
        "has_access_control": False,
        "is_system_security": False,
        "access_level": None,
        "authorized_groups": [],
        "data_classification": None,
    }

    try:
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(file_id)

        if file_metadata:
            result["exists"] = True
            result["has_metadata"] = True

            # 檢查訪問控制
            access_control = getattr(file_metadata, "access_control", None)
            if access_control:
                result["has_access_control"] = True
                if isinstance(access_control, dict):
                    result["access_level"] = access_control.get("access_level")
                    result["authorized_groups"] = access_control.get("authorized_security_groups", [])
                    result["data_classification"] = access_control.get("data_classification")

                    # 檢查是否為 SystemSecurity 授權
                    if (
                        result["access_level"] == "security_group"
                        and "SystemSecurity" in result["authorized_groups"]
                    ):
                        result["is_system_security"] = True
                elif hasattr(access_control, "access_level"):
                    result["access_level"] = access_control.access_level
                    result["authorized_groups"] = getattr(access_control, "authorized_security_groups", [])
                    result["data_classification"] = getattr(access_control, "data_classification", None)

                    if (
                        result["access_level"] == "security_group"
                        and "SystemSecurity" in result["authorized_groups"]
                    ):
                        result["is_system_security"] = True

            # 檢查數據分類
            data_classification = getattr(file_metadata, "data_classification", None)
            if data_classification:
                result["data_classification"] = data_classification

    except Exception as e:
        logger.error("驗證文件元數據失敗", file_id=file_id, error=str(e))
        result["error"] = str(e)

    return result


def verify_vectorization(file_id: str) -> Dict[str, Any]:
    """驗證向量化記錄

    Args:
        file_id: 文件ID

    Returns:
        驗證結果
    """
    result: Dict[str, Any] = {
        "file_id": file_id,
        "has_vectors": False,
        "vector_count": 0,
        "collection_name": None,
    }

    try:
        chroma_client = ChromaDBClient()
        # 嘗試從多個可能的 collection 中查找
        collections = ["system", "default", file_id]

        for collection_name in collections:
            try:
                collection = chroma_client.get_collection(collection_name)
                if collection:
                    # 查詢包含該 file_id 的向量
                    results = collection.get(
                        where={"file_id": file_id},
                        limit=1000,
                    )

                    if results and results.get("ids"):
                        result["has_vectors"] = True
                        result["vector_count"] = len(results["ids"])
                        result["collection_name"] = collection_name
                        break
            except Exception:
                continue

    except Exception as e:
        logger.warning("驗證向量化記錄失敗", file_id=file_id, error=str(e))
        result["error"] = str(e)

    return result


def verify_knowledge_graph(file_id: str) -> Dict[str, Any]:
    """驗證知識圖譜記錄

    Args:
        file_id: 文件ID

    Returns:
        驗證結果
    """
    result: Dict[str, Any] = {
        "file_id": file_id,
        "has_entities": False,
        "has_relations": False,
        "entity_count": 0,
        "relation_count": 0,
    }

    try:
        arango_client = ArangoDBClient()
        if arango_client.db is None:
            result["error"] = "ArangoDB 未連接"
            return result

        # 查詢實體
        entities_collection = arango_client.db.collection("entities")
        if entities_collection:
            aql = """
                FOR entity IN entities
                    FILTER entity.file_id == @file_id
                    COLLECT WITH COUNT INTO count
                    RETURN count
            """
            cursor = arango_client.db.aql.execute(
                aql,
                bind_vars={"file_id": file_id},
            )
            entity_count = list(cursor)[0] if cursor else 0
            result["entity_count"] = entity_count
            result["has_entities"] = entity_count > 0

        # 查詢關係
        relations_collection = arango_client.db.collection("relations")
        if relations_collection:
            aql = """
                FOR relation IN relations
                    FILTER relation.file_id == @file_id
                    COLLECT WITH COUNT INTO count
                    RETURN count
            """
            cursor = arango_client.db.aql.execute(
                aql,
                bind_vars={"file_id": file_id},
            )
            relation_count = list(cursor)[0] if cursor else 0
            result["relation_count"] = relation_count
            result["has_relations"] = relation_count > 0

    except Exception as e:
        logger.warning("驗證知識圖譜記錄失敗", file_id=file_id, error=str(e))
        result["error"] = str(e)

    return result


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="驗證知識圖譜提取結果")
    parser.add_argument(
        "--progress-json",
        type=str,
        default="system_docs_processing_progress.json",
        help="進度文件路徑",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="verification_report.json",
        help="驗證報告輸出文件",
    )

    args = parser.parse_args()

    # 加載進度文件
    progress = load_progress(args.progress_json)
    if not progress:
        logger.error("無法加載進度文件", file=args.progress_json)
        sys.exit(1)

    # 獲取所有文件記錄
    files_data = progress.get("files") or progress.get("results") or []
    if not files_data:
        logger.error("進度文件中沒有文件記錄 (keys 'files' or 'results' not found or empty)")
        sys.exit(1)

    logger.info("開始驗證", total_files=len(files_data))

    # 驗證每個文件
    verification_results: List[Dict[str, Any]] = []
    statistics = {
        "total": len(files_data),
        "has_metadata": 0,
        "has_access_control": 0,
        "is_system_security": 0,
        "has_vectors": 0,
        "has_entities": 0,
        "has_relations": 0,
        "completed": 0,
        "partial_completed": 0,
        "failed": 0,
    }

    for file_data in files_data:
        file_path = file_data.get("file_path") or file_data.get("file_name")
        file_id = file_data.get("file_id")
        if not file_id:
            logger.warning("文件沒有 file_id", file_path=file_path)
            continue

        logger.info("驗證文件", file_id=file_id, file_path=file_path)

        # 驗證文件元數據和授權
        metadata_result = verify_file_metadata(file_id)
        vector_result = verify_vectorization(file_id)
        kg_result = verify_knowledge_graph(file_id)

        # 組合結果
        file_result = {
            "file_path": file_path,
            "file_id": file_id,
            "metadata": metadata_result,
            "vectorization": vector_result,
            "knowledge_graph": kg_result,
        }

        # 判斷整體狀態
        has_metadata = metadata_result.get("has_metadata", False)
        has_vectors = vector_result.get("has_vectors", False)
        has_kg = kg_result.get("has_entities", False) or kg_result.get("has_relations", False)

        if has_metadata and has_vectors and has_kg:
            file_result["overall_status"] = "completed"
            statistics["completed"] += 1
        elif has_metadata and (has_vectors or has_kg):
            file_result["overall_status"] = "partial_completed"
            statistics["partial_completed"] += 1
        else:
            file_result["overall_status"] = "failed"
            statistics["failed"] += 1

        # 更新統計
        if has_metadata:
            statistics["has_metadata"] += 1
        if metadata_result.get("has_access_control"):
            statistics["has_access_control"] += 1
        if metadata_result.get("is_system_security"):
            statistics["is_system_security"] += 1
        if has_vectors:
            statistics["has_vectors"] += 1
        if kg_result.get("has_entities"):
            statistics["has_entities"] += 1
        if kg_result.get("has_relations"):
            statistics["has_relations"] += 1

        verification_results.append(file_result)

    # 生成報告
    report = {
        "verification_time": str(Path(__file__).stat().st_mtime),
        "statistics": statistics,
        "results": verification_results,
    }

    # 保存報告
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    logger.info(
        "驗證完成",
        total=statistics["total"],
        completed=statistics["completed"],
        partial_completed=statistics["partial_completed"],
        failed=statistics["failed"],
        has_metadata=statistics["has_metadata"],
        is_system_security=statistics["is_system_security"],
        has_vectors=statistics["has_vectors"],
        has_entities=statistics["has_entities"],
        has_relations=statistics["has_relations"],
    )

    print("\n驗證報告摘要:")
    print(f"  總文件數: {statistics['total']}")
    print(f"  ✅ 完成: {statistics['completed']}")
    print(f"  ⚠️  部分完成: {statistics['partial_completed']}")
    print(f"  ❌ 失敗: {statistics['failed']}")
    print(f"  有元數據: {statistics['has_metadata']}")
    print(f"  SystemSecurity 授權: {statistics['is_system_security']}")
    print(f"  有向量: {statistics['has_vectors']}")
    print(f"  有實體: {statistics['has_entities']}")
    print(f"  有關係: {statistics['has_relations']}")
    print(f"\n詳細報告已保存到: {args.output}")


if __name__ == "__main__":
    main()
