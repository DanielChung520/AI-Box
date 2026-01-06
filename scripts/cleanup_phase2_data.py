#!/usr/bin/env python3
# 代碼功能說明: 清理階段二測試產生的數據
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""清理階段二測試產生的數據

清理內容：
1. RQ 任務隊列（file_processing, kg_extraction, vectorization）
2. Redis 狀態記錄（processing:status, upload:progress）
3. ArangoDB 數據（file_metadata, processing_status, entities, relations）
4. ChromaDB 向量數據
5. 測試日誌文件
"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.redis import get_redis_client
from database.arangodb import ArangoDBClient
from services.api.services.vector_store_service import get_vector_store_service
from genai.api.services.kg_builder_service import KGBuilderService
import structlog

logger = structlog.get_logger(__name__)


def cleanup_rq_jobs():
    """清理 RQ 任務隊列"""
    try:
        redis_client = get_redis_client()
        
        # 清理所有 RQ 隊列
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
        
        # 清理 RQ 任務數據
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
        
        # 清理處理狀態
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
        client = ArangoDBClient()
        if client.db is None:
            logger.warning("ArangoDB 未連接，跳過清理")
            return 0
        
        collections = [
            "file_metadata",
            "processing_status",
            "upload_progress",
        ]
        
        total_cleaned = 0
        for collection_name in collections:
            if client.db.has_collection(collection_name):
                collection = client.db.collection(collection_name)
                count = collection.count()
                if count > 0:
                    # 只清理測試相關的數據（可以根據 file_id 或其他標識過濾）
                    # 這裡清理所有數據，實際使用時可能需要更精確的過濾
                    collection.truncate()
                    logger.info(f"清理 ArangoDB collection: {collection_name}, 刪除 {count} 個文檔")
                    total_cleaned += count
        
        # 清理知識圖譜數據（entities 和 relations）
        kg_builder = KGBuilderService()
        # 注意：這裡需要知道測試文件的 file_id，或者清理所有
        # 為了安全，這裡只清理沒有關聯的實體和關係
        logger.info("清理知識圖譜數據需要指定 file_id，跳過自動清理")
        
        logger.info(f"ArangoDB 數據清理完成，共清理 {total_cleaned} 個文檔")
        return total_cleaned
    except Exception as e:
        logger.error(f"清理 ArangoDB 數據失敗: {e}", exc_info=True)
        return 0


def cleanup_chromadb_vectors():
    """清理 ChromaDB 向量數據"""
    try:
        vector_store = get_vector_store_service()
        
        # 獲取所有 collections
        # 注意：ChromaDB 的清理需要知道 file_id 或 collection_name
        # 這裡只記錄，實際清理需要指定 file_id
        logger.info("ChromaDB 向量清理需要指定 file_id，跳過自動清理")
        logger.info("如需清理，請使用: vector_store.delete_vectors_by_file_id(file_id, user_id)")
        
        return 0
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


def main():
    """主函數"""
    print("=" * 60)
    print("清理階段二測試數據")
    print("=" * 60)
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
    print("注意：")
    print("  - ArangoDB 和 ChromaDB 的數據清理需要指定 file_id")
    print("  - 如需清理特定文件的數據，請使用專門的清理腳本")
    print("  - 建議在清理前備份重要數據")


if __name__ == "__main__":
    main()
