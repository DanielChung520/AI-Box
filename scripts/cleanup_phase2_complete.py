#!/usr/bin/env python3
# 代碼功能說明: 完整清理階段二測試產生的數據（包含 ArangoDB 和 ChromaDB）
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""完整清理階段二測試產生的數據

清理內容：
1. RQ 任務隊列（file_processing, kg_extraction, vectorization）
2. Redis 狀態記錄（processing:status, upload:progress, kg:chunk_state）
3. ArangoDB 數據（file_metadata, processing_status, upload_progress, entities, relations）
4. ChromaDB 向量數據（所有測試相關的 collections）
5. 測試日誌文件
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 手動載入 .env 文件（如果存在）
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

import structlog

from database.arangodb import ArangoDBClient
from database.chromadb import ChromaDBClient
from database.chromadb.collection import ChromaCollection
from database.redis import get_redis_client

logger = structlog.get_logger(__name__)


def cleanup_rq_jobs():
    """清理 RQ 任務隊列"""
    try:
        redis_client = get_redis_client()

        queues = [
            "rq:queue:file_processing",
            "rq:queue:kg_extraction",
            "rq:queue:vectorization",
        ]

        total_cleaned = 0
        for queue in queues:
            count = redis_client.llen(queue)
            if count > 0:
                redis_client.delete(queue)
                logger.info(f"清理 RQ 隊列: {queue}, 刪除 {count} 個任務")
                total_cleaned += count

        job_keys = redis_client.keys("rq:job:*")
        if job_keys:
            redis_client.delete(*job_keys)
            logger.info(f"清理 RQ 任務數據: {len(job_keys)} 個任務")
            total_cleaned += len(job_keys)

        logger.info(f"RQ 任務清理完成，共清理 {total_cleaned} 個任務")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理 RQ 任務失敗: {e}", exc_info=True)
        return 0


def cleanup_redis_status():
    """清理 Redis 狀態記錄"""
    try:
        redis_client = get_redis_client()

        status_keys = redis_client.keys("processing:status:*")
        upload_keys = redis_client.keys("upload:progress:*")
        kg_state_keys = redis_client.keys("kg:chunk_state:*")
        kg_lock_keys = redis_client.keys("kg:continue_lock:*")

        total_cleaned = 0
        for keys in [status_keys, upload_keys, kg_state_keys, kg_lock_keys]:
            if keys:
                redis_client.delete(*keys)
                total_cleaned += len(keys)
                logger.info(f"清理 Redis 鍵: {len(keys)} 個")

        logger.info(f"Redis 狀態清理完成，共清理 {total_cleaned} 個鍵")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理 Redis 狀態失敗: {e}", exc_info=True)
        return 0


def cleanup_arangodb_data():
    """清理 ArangoDB 測試數據"""
    try:
        client = ArangoDBClient(
            username=os.getenv("ARANGODB_USERNAME", "root"),
            password=os.getenv("ARANGODB_PASSWORD", "changeme"),
        )

        if client.db is None:
            logger.warning("ArangoDB 未連接，跳過清理")
            return 0

        collections_to_clean = [
            "file_metadata",
            "processing_status",
            "upload_progress",
        ]

        total_cleaned = 0
        for collection_name in collections_to_clean:
            if client.db.has_collection(collection_name):
                collection = client.db.collection(collection_name)
                count = collection.count()
                if count > 0:
                    collection.truncate()
                    logger.info(f"清理 ArangoDB collection: {collection_name}, 刪除 {count} 個文檔")
                    total_cleaned += count

        # 清理知識圖譜數據
        entities_collection = "entities"
        relations_collection = "relations"

        if client.db.has_collection(entities_collection):
            entities = client.db.collection(entities_collection)
            entities_count = entities.count()
            if entities_count > 0:
                entities.truncate()
                logger.info(f"清理 ArangoDB entities: {entities_count} 個")
                total_cleaned += entities_count

        if client.db.has_collection(relations_collection):
            relations = client.db.collection(relations_collection)
            relations_count = relations.count()
            if relations_count > 0:
                relations.truncate()
                logger.info(f"清理 ArangoDB relations: {relations_count} 個")
                total_cleaned += relations_count

        logger.info(f"ArangoDB 數據清理完成，共清理 {total_cleaned} 個文檔")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理 ArangoDB 數據失敗: {e}", exc_info=True)
        return 0


def cleanup_chromadb_vectors():
    """清理 ChromaDB 向量數據"""
    try:
        chroma_client = ChromaDBClient(
            host=os.getenv("CHROMADB_HOST", "localhost"),
            port=int(os.getenv("CHROMADB_PORT", "8001")),
            mode=os.getenv("CHROMADB_MODE", "http"),
            persist_directory=os.getenv("CHROMADB_PERSIST_DIR", "./data/datasets/chromadb"),
        )

        collections = chroma_client.list_collections()
        logger.info(f"找到 {len(collections)} 個 ChromaDB collections")

        total_cleaned = 0
        for collection_name in collections:
            try:
                # 獲取 collection 並檢查文檔數量
                collection = chroma_client.get_or_create_collection(collection_name)
                collection_obj = ChromaCollection(collection)
                count = collection_obj.count()

                if count > 0:
                    # 刪除 collection（會刪除所有向量）
                    chroma_client.delete_collection(collection_name)
                    logger.info(f"清理 ChromaDB collection: {collection_name}, 刪除 {count} 個向量")
                    total_cleaned += count
            except Exception as e:
                logger.warning(f"清理 ChromaDB collection {collection_name} 失敗: {e}")

        logger.info(f"ChromaDB 向量清理完成，共清理 {total_cleaned} 個向量")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理 ChromaDB 向量失敗: {e}", exc_info=True)
        return 0


def cleanup_test_logs():
    """清理測試日誌文件"""
    try:
        log_files = [
            "logs/rq_worker_rq_worker_ai_box.log",
            "logs/batch_test_100.log",
            "scripts/batch_test_100_progress.json",
            "scripts/batch_test_100_results.json",
            "scripts/system_docs_processing_progress.json",
            "scripts/system_docs_processing_results.json",
        ]

        total_cleaned = 0
        for log_file in log_files:
            log_path = project_root / log_file
            if log_path.exists():
                log_path.unlink()
                logger.info(f"刪除測試日誌: {log_file}")
                total_cleaned += 1

        logger.info(f"測試日誌清理完成，共清理 {total_cleaned} 個文件")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理測試日誌失敗: {e}", exc_info=True)
        return 0


def verify_cleanup():
    """驗證清理結果"""
    print("\n" + "=" * 60)
    print("驗證清理結果")
    print("=" * 60)

    results = {}

    # 驗證 RQ 隊列
    try:
        redis_client = get_redis_client()
        queues = ["rq:queue:file_processing", "rq:queue:kg_extraction", "rq:queue:vectorization"]
        total_jobs = sum(redis_client.llen(q) for q in queues)
        results["RQ 任務"] = "✅ 已清理" if total_jobs == 0 else f"⚠️ 仍有 {total_jobs} 個任務"
    except Exception as e:
        results["RQ 任務"] = f"❌ 檢查失敗: {e}"

    # 驗證 Redis 狀態
    try:
        redis_client = get_redis_client()
        status_keys = redis_client.keys("processing:status:*")
        upload_keys = redis_client.keys("upload:progress:*")
        total_keys = len(status_keys) + len(upload_keys)
        results["Redis 狀態"] = "✅ 已清理" if total_keys == 0 else f"⚠️ 仍有 {total_keys} 個鍵"
    except Exception as e:
        results["Redis 狀態"] = f"❌ 檢查失敗: {e}"

    # 驗證 ArangoDB
    try:
        client = ArangoDBClient(
            username=os.getenv("ARANGODB_USERNAME", "root"),
            password=os.getenv("ARANGODB_PASSWORD", "changeme"),
        )
        if client.db:
            collections = [
                "file_metadata",
                "processing_status",
                "upload_progress",
                "entities",
                "relations",
            ]
            total_docs = sum(
                client.db.collection(c).count() for c in collections if client.db.has_collection(c)
            )
            results["ArangoDB 數據"] = "✅ 已清理" if total_docs == 0 else f"⚠️ 仍有 {total_docs} 個文檔"
        else:
            results["ArangoDB 數據"] = "❌ 無法連接"
    except Exception as e:
        results["ArangoDB 數據"] = f"❌ 檢查失敗: {e}"

    # 驗證 ChromaDB
    try:
        chroma_client = ChromaDBClient(
            host=os.getenv("CHROMADB_HOST", "localhost"),
            port=int(os.getenv("CHROMADB_PORT", "8001")),
            mode=os.getenv("CHROMADB_MODE", "http"),
            persist_directory=os.getenv("CHROMADB_PERSIST_DIR", "./data/datasets/chromadb"),
        )
        collections = chroma_client.list_collections()
        results["ChromaDB 向量"] = (
            "✅ 已清理" if len(collections) == 0 else f"⚠️ 仍有 {len(collections)} 個 collections"
        )
    except Exception as e:
        results["ChromaDB 向量"] = f"❌ 檢查失敗: {e}"

    # 顯示驗證結果
    for key, value in results.items():
        print(f"  {key}: {value}")

    return results


def main():
    """主函數"""
    print("=" * 60)
    print("完整清理階段二測試數據")
    print("=" * 60)
    print()

    # 確認清理
    response = input("⚠️  此操作將清理所有階段二測試數據，是否繼續？(yes/no): ")
    if response.lower() != "yes":
        print("清理已取消")
        return

    print()
    print("開始清理...")
    print()

    results = {
        "rq_jobs": cleanup_rq_jobs(),
        "redis_status": cleanup_redis_status(),
        "arangodb_data": cleanup_arangodb_data(),
        "chromadb_vectors": cleanup_chromadb_vectors(),
        "test_logs": cleanup_test_logs(),
    }

    print()
    print("=" * 60)
    print("清理完成")
    print("=" * 60)
    print()
    print("清理統計：")
    for key, value in results.items():
        print(f"  {key}: {value}")
    print()

    # 驗證清理結果
    verify_cleanup()

    print()
    print("=" * 60)
    print("清理完成，系統已準備好進行第三階段測試")
    print("=" * 60)


if __name__ == "__main__":
    main()
