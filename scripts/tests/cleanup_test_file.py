# 代碼功能說明: 清理測試文件數據腳本
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""清理測試文件數據 - 刪除文件、向量、知識圖譜等相關數據"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 先加載 .env 文件（在導入其他模組之前）
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)
        print(f"✅ 已加載 .env 文件: {env_file}")
    except ImportError:
        print("⚠️  python-dotenv 未安裝，無法自動加載 .env 文件")
else:
    print(f"⚠️  未找到 .env 文件: {env_file}")

import structlog

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.api.services.file_metadata_service import FileMetadataService
from genai.api.services.kg_builder_service import KGBuilderService
from services.api.services.vector_store_service import get_vector_store_service

logger = structlog.get_logger(__name__)


async def cleanup_file_data(file_id: str, user_id: str = "test-user") -> dict:
    """
    清理文件相關的所有數據

    Args:
        file_id: 文件ID
        user_id: 用戶ID（用於清理向量數據）

    Returns:
        清理結果字典
    """
    result = {
        "file_id": file_id,
        "vectors_deleted": False,
        "kg_cleaned": False,
        "metadata_deleted": False,
        "errors": [],
    }

    # 1. 刪除 ChromaDB 中的向量
    try:
        vector_store_service = get_vector_store_service()
        vector_store_service.delete_vectors_by_file_id(file_id=file_id, user_id=user_id)
        result["vectors_deleted"] = True
        logger.info("已刪除文件關聯的向量", file_id=file_id)
    except Exception as e:
        error_msg = f"刪除向量失敗: {str(e)}"
        result["errors"].append(error_msg)
        logger.warning("刪除向量失敗", file_id=file_id, error=str(e))

    # 2. 清理 ArangoDB 中的知識圖譜關聯
    try:
        kg_builder = KGBuilderService()
        cleanup = kg_builder.remove_file_associations(file_id=file_id)
        result["kg_cleaned"] = True
        result["kg_cleanup_details"] = cleanup
        logger.info("已清理文件關聯的知識圖譜資料", file_id=file_id, **cleanup)
    except Exception as e:
        error_msg = f"清理知識圖譜失敗: {str(e)}"
        result["errors"].append(error_msg)
        logger.warning("清理知識圖譜失敗", file_id=file_id, error=str(e))

    # 3. 刪除文件元數據
    try:
        metadata_service = FileMetadataService()
        metadata_service.delete(file_id)
        result["metadata_deleted"] = True
        logger.info("已刪除文件元數據", file_id=file_id)
    except Exception as e:
        error_msg = f"刪除文件元數據失敗: {str(e)}"
        result["errors"].append(error_msg)
        logger.warning("刪除文件元數據失敗", file_id=file_id, error=str(e))

    return result


async def cleanup_from_test_result(test_result_file: str) -> None:
    """
    從測試結果文件中讀取 file_id 並清理數據

    Args:
        test_result_file: 測試結果文件路徑
    """
    result_path = Path(test_result_file)
    if not result_path.exists():
        logger.error("測試結果文件不存在", file=test_result_file)
        return

    with open(result_path, "r", encoding="utf-8") as f:
        test_result = json.load(f)

    file_id = test_result.get("file_id")
    if not file_id:
        logger.error("測試結果文件中沒有 file_id", file=test_result_file)
        return

    logger.info("開始清理測試數據", file_id=file_id, test_result_file=test_result_file)
    result = await cleanup_file_data(file_id=file_id)
    logger.info("清理完成", **result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


async def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="清理測試文件數據")
    parser.add_argument(
        "--file-id",
        type=str,
        help="要清理的文件ID",
    )
    parser.add_argument(
        "--test-result",
        type=str,
        help="測試結果文件路徑（從中讀取 file_id）",
        default="scripts/kg_extract_test_result.json",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="test-user",
        help="用戶ID（用於清理向量數據）",
    )

    args = parser.parse_args()

    if args.file_id:
        # 直接指定 file_id
        logger.info("清理指定文件數據", file_id=args.file_id)
        result = await cleanup_file_data(file_id=args.file_id, user_id=args.user_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 從測試結果文件讀取
        await cleanup_from_test_result(args.test_result)


if __name__ == "__main__":
    asyncio.run(main())
