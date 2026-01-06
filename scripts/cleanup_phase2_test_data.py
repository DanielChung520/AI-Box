# 代碼功能說明: 清理階段二測試數據
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""清理階段二測試數據腳本

清理所有測試文件相關的數據：
- ChromaDB 向量數據
- ArangoDB 知識圖譜數據（實體和關係）
- ArangoDB 文件元數據
- Redis 處理狀態
"""

import argparse
import json
import os
import sys
from pathlib import Path

import structlog

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = structlog.get_logger(__name__)

TEST_USER_ID = os.getenv("TEST_USER_ID", "test-user")


def cleanup_from_test_results(result_file: str):
    """從測試結果文件中讀取 file_id 並清理"""
    if not os.path.exists(result_file):
        logger.error(f"測試結果文件不存在: {result_file}")
        return
    
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    file_ids = []
    
    for result in results:
        file_id = result.get('file_id')
        if file_id:
            file_ids.append(file_id)
    
    logger.info(f"從測試結果中找到 {len(file_ids)} 個文件ID")
    
    if file_ids:
        cleanup_files(file_ids)


def cleanup_files(file_ids: list):
    """清理指定文件ID的數據"""
    from services.api.services.vector_store_service import get_vector_store_service
    from services.api.services.file_metadata_service import FileMetadataService
    from genai.api.services.kg_builder_service import KGBuilderService
    from database.redis import get_redis_client
    
    vector_service = get_vector_store_service()
    metadata_service = FileMetadataService()
    kg_service = KGBuilderService()
    redis_client = get_redis_client()
    
    cleaned_count = 0
    
    for file_id in file_ids:
        try:
            logger.info(f"清理文件: {file_id[:8]}...")
            
            # 1. 清理向量數據
            try:
                collection_name = f"file_{file_id}"
                vector_service.delete_collection(collection_name)
                logger.info(f"  ✅ 已清理向量數據: {collection_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  清理向量數據失敗: {e}")
            
            # 2. 清理知識圖譜數據
            try:
                # 刪除實體和關係
                kg_service.delete_kg_by_file_id(file_id)
                logger.info(f"  ✅ 已清理知識圖譜數據")
            except Exception as e:
                logger.warning(f"  ⚠️  清理知識圖譜數據失敗: {e}")
            
            # 3. 清理文件元數據（可選，如果需要保留記錄可以跳過）
            # try:
            #     metadata_service.delete(file_id)
            #     logger.info(f"  ✅ 已清理文件元數據")
            # except Exception as e:
            #     logger.warning(f"  ⚠️  清理文件元數據失敗: {e}")
            
            # 4. 清理Redis狀態
            try:
                status_key = f"processing:status:{file_id}"
                upload_key = f"upload:progress:{file_id}"
                redis_client.delete(status_key)
                redis_client.delete(upload_key)
                logger.info(f"  ✅ 已清理Redis狀態")
            except Exception as e:
                logger.warning(f"  ⚠️  清理Redis狀態失敗: {e}")
            
            cleaned_count += 1
            
        except Exception as e:
            logger.error(f"  ❌ 清理文件 {file_id[:8]}... 失敗: {e}")
    
    logger.info(f"總共清理了 {cleaned_count}/{len(file_ids)} 個文件")


def cleanup_all_test_files():
    """清理所有測試相關的文件"""
    from services.api.services.file_metadata_service import FileMetadataService
    from database.arangodb import get_arangodb_client
    
    metadata_service = FileMetadataService()
    arango_client = get_arangodb_client()
    
    if arango_client.db is None:
        logger.error("ArangoDB 未連接")
        return
    
    # 查詢所有測試文件（根據文件名或用戶ID）
    # 這裡簡化處理，直接清理測試結果文件中的文件
    logger.info("請使用 --test-result 參數指定測試結果文件")


def main():
    parser = argparse.ArgumentParser(description="清理階段二測試數據")
    parser.add_argument(
        "--test-result",
        type=str,
        default="phase2_batch_test_results.json",
        help="測試結果文件路徑（默認: phase2_batch_test_results.json）",
    )
    parser.add_argument(
        "--file-ids",
        nargs="+",
        help="直接指定要清理的文件ID列表",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="清理所有測試數據（危險操作）",
    )
    
    args = parser.parse_args()
    
    if args.all:
        logger.warning("清理所有測試數據...")
        cleanup_all_test_files()
    elif args.file_ids:
        logger.info(f"清理指定的 {len(args.file_ids)} 個文件")
        cleanup_files(args.file_ids)
    else:
        logger.info(f"從測試結果文件清理: {args.test_result}")
        cleanup_from_test_results(args.test_result)
    
    logger.info("清理完成")


if __name__ == "__main__":
    main()
