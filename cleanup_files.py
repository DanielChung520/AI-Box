# 代碼功能說明: 清理指定文件的所有相關數據（ArangoDB、ChromaDB、SeaWeedFS）
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""
清理指定文件的所有相關數據

功能：
1. 通過文件名查找 file_id
2. 刪除 ChromaDB 中的向量數據
3. 刪除 ArangoDB 中的知識圖譜關聯（保留 ontologies）
4. 刪除 ArangoDB 中的文件元數據
5. 刪除 SeaWeedFS 中的實際文件
6. 刪除 Redis 中的處理狀態
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import structlog

from api.routers.file_upload import get_storage
from database.arangodb import ArangoDBClient
from database.redis import get_redis_client
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.vector_store_service import VectorStoreService

logger = structlog.get_logger(__name__)

# 要清理的文件名列表
FILES_TO_CLEANUP = [
    "东方伊厨-预制菜发展策略报告20250902.pdf",
    "企業級AI驅動開發架構設計_完整版.pdf",
    "生质能源-Daniel笔记.pdf",
]


def find_file_by_name(filename: str) -> Optional[Dict]:
    """
    通過文件名查找文件元數據

    Args:
        filename: 文件名

    Returns:
        文件元數據字典，如果找不到則返回 None
    """
    try:
        arangodb_client = ArangoDBClient()

        if arangodb_client.db is None or arangodb_client.db.aql is None:
            logger.error("ArangoDB 連接失敗")
            return None

        # 在所有任務中搜索文件（因為我們不知道 task_id）
        aql = """
        FOR doc IN file_metadata
            FILTER doc.filename == @filename
            RETURN doc
        """
        cursor = arangodb_client.db.aql.execute(aql, bind_vars={"filename": filename})
        results = list(cursor)

        if results:
            logger.info("找到文件", filename=filename, file_id=results[0].get("file_id"))
            return results[0]
        else:
            logger.warning("未找到文件", filename=filename)
            return None

    except Exception as e:
        logger.error("查找文件失敗", filename=filename, error=str(e))
        return None


def cleanup_file(file_id: str, filename: str) -> Dict[str, any]:
    """
    清理文件的所有相關數據

    Args:
        file_id: 文件 ID
        filename: 文件名

    Returns:
        清理結果字典
    """
    results = {
        "file_id": file_id,
        "filename": filename,
        "vector_deleted": False,
        "kg_deleted": False,
        "metadata_deleted": False,
        "file_deleted": False,
        "redis_deleted": False,
        "errors": [],
    }

    # 1. 刪除 ChromaDB 中的向量數據
    try:
        vector_store_service = VectorStoreService()
        vector_store_service.delete_vectors_by_file_id(file_id=file_id)
        results["vector_deleted"] = True
        logger.info("✅ 向量數據刪除成功", file_id=file_id, filename=filename)
    except Exception as e:
        error_msg = f"刪除向量數據失敗: {str(e)}"
        results["errors"].append(error_msg)
        logger.warning(error_msg, file_id=file_id, filename=filename, error=str(e))

    # 2. 刪除 ArangoDB 中的知識圖譜關聯（保留 ontologies）
    try:
        kg_builder = KGBuilderService()
        cleanup = kg_builder.remove_file_associations(file_id=file_id)
        results["kg_deleted"] = True
        results["kg_cleanup"] = cleanup
        logger.info(
            "✅ 知識圖譜關聯清理成功",
            file_id=file_id,
            filename=filename,
            **cleanup,
        )
    except Exception as e:
        error_msg = f"清理知識圖譜失敗: {str(e)}"
        results["errors"].append(error_msg)
        logger.warning(error_msg, file_id=file_id, filename=filename, error=str(e))

    # 3. 獲取文件元數據（用於獲取 storage_path 和 task_id）
    file_metadata = None
    try:
        arangodb_client = ArangoDBClient()
        if arangodb_client.db is not None:
            collection = arangodb_client.db.collection("file_metadata")
            file_metadata = collection.get(file_id)
    except Exception as e:
        logger.warning("獲取文件元數據失敗", file_id=file_id, error=str(e))

    # 4. 刪除 ArangoDB 中的文件元數據
    try:
        metadata_service = FileMetadataService()
        success = metadata_service.delete(file_id)
        if success:
            results["metadata_deleted"] = True
            logger.info("✅ 文件元數據刪除成功", file_id=file_id, filename=filename)
        else:
            results["errors"].append("文件元數據刪除失敗（文件可能不存在）")
            logger.warning("文件元數據刪除失敗", file_id=file_id, filename=filename)
    except Exception as e:
        error_msg = f"刪除文件元數據失敗: {str(e)}"
        results["errors"].append(error_msg)
        logger.error(error_msg, file_id=file_id, filename=filename, error=str(e))

    # 5. 刪除 SeaWeedFS 中的實際文件
    try:
        storage = get_storage()
        task_id = file_metadata.get("task_id") if file_metadata else None
        storage_path = file_metadata.get("storage_path") if file_metadata else None
        success = storage.delete_file(
            file_id=file_id, task_id=task_id, metadata_storage_path=storage_path
        )
        if success:
            results["file_deleted"] = True
            logger.info("✅ 實際文件刪除成功", file_id=file_id, filename=filename)
        else:
            results["errors"].append("實際文件刪除失敗（文件可能不存在）")
            logger.warning("實際文件刪除失敗", file_id=file_id, filename=filename)
    except Exception as e:
        error_msg = f"刪除實際文件失敗: {str(e)}"
        results["errors"].append(error_msg)
        logger.warning(error_msg, file_id=file_id, filename=filename, error=str(e))

    # 6. 刪除 Redis 中的處理狀態
    try:
        redis_client = get_redis_client()
        redis_client.delete(f"upload:progress:{file_id}")
        redis_client.delete(f"processing:status:{file_id}")
        redis_client.delete(f"kg:chunk_state:{file_id}")
        redis_client.delete(f"kg:continue_lock:{file_id}")
        results["redis_deleted"] = True
        logger.info("✅ Redis 處理狀態刪除成功", file_id=file_id, filename=filename)
    except Exception as e:
        error_msg = f"刪除 Redis 狀態失敗: {str(e)}"
        results["errors"].append(error_msg)
        logger.warning(error_msg, file_id=file_id, filename=filename, error=str(e))

    return results


def main():
    """主函數"""
    print("=" * 80)
    print("開始清理文件數據")
    print("=" * 80)
    print(f"要清理的文件數量: {len(FILES_TO_CLEANUP)}")
    print(f"文件列表: {', '.join(FILES_TO_CLEANUP)}")
    print()

    all_results: List[Dict] = []

    for filename in FILES_TO_CLEANUP:
        print(f"\n處理文件: {filename}")
        print("-" * 80)

        # 查找文件
        file_metadata = find_file_by_name(filename)
        if not file_metadata:
            print(f"❌ 未找到文件: {filename}")
            all_results.append(
                {
                    "filename": filename,
                    "status": "not_found",
                    "file_id": None,
                }
            )
            continue

        file_id = file_metadata.get("file_id")
        if not file_id:
            print(f"❌ 文件元數據中沒有 file_id: {filename}")
            all_results.append(
                {
                    "filename": filename,
                    "status": "no_file_id",
                    "file_id": None,
                }
            )
            continue

        print(f"找到文件 ID: {file_id}")

        # 清理文件
        result = cleanup_file(file_id, filename)
        all_results.append(result)

        # 打印結果
        print("\n清理結果:")
        print(f"  - 向量數據: {'✅' if result['vector_deleted'] else '❌'}")
        print(f"  - 知識圖譜: {'✅' if result['kg_deleted'] else '❌'}")
        print(f"  - 文件元數據: {'✅' if result['metadata_deleted'] else '❌'}")
        print(f"  - 實際文件: {'✅' if result['file_deleted'] else '❌'}")
        print(f"  - Redis 狀態: {'✅' if result['redis_deleted'] else '❌'}")

        if result.get("errors"):
            print(f"  錯誤: {', '.join(result['errors'])}")

    # 打印總結
    print("\n" + "=" * 80)
    print("清理完成總結")
    print("=" * 80)

    found_count = sum(1 for r in all_results if r.get("file_id"))
    not_found_count = len(all_results) - found_count

    print(f"總文件數: {len(FILES_TO_CLEANUP)}")
    print(f"找到文件: {found_count}")
    print(f"未找到文件: {not_found_count}")

    if found_count > 0:
        print("\n清理詳情:")
        for result in all_results:
            if result.get("file_id"):
                print(f"\n  {result['filename']} ({result['file_id']}):")
                print(f"    向量: {'✅' if result.get('vector_deleted') else '❌'}")
                print(f"    圖譜: {'✅' if result.get('kg_deleted') else '❌'}")
                print(f"    元數據: {'✅' if result.get('metadata_deleted') else '❌'}")
                print(f"    文件: {'✅' if result.get('file_deleted') else '❌'}")
                print(f"    Redis: {'✅' if result.get('redis_deleted') else '❌'}")
                if result.get("errors"):
                    for error in result["errors"]:
                        print(f"    ⚠️  {error}")

    print("\n✅ 清理完成！")
    print("注意: Ontology 數據已保留（ontologies collection 未刪除）")


if __name__ == "__main__":
    main()
