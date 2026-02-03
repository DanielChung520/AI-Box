# 代碼功能說明: 清理 ArangoDB 測試數據
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""清理 ArangoDB 測試數據腳本

清理所有測試文件相關的 ArangoDB 數據：
- 知識圖譜實體和關係
- 文件元數據（可選）
- 處理狀態記錄
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

# 加載 .env 文件（在導入其他模組之前）
try:
    from dotenv import load_dotenv

    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"✅ 已加載 .env 文件: {env_file}")
except ImportError:
    print("⚠️  python-dotenv 未安裝，無法自動加載 .env 文件")

logger = structlog.get_logger(__name__)

TEST_USER_ID = os.getenv("TEST_USER_ID", "test-user")


def cleanup_kg_data(file_ids: list):
    """清理指定文件ID的知識圖譜數據"""
    from genai.api.services.kg_builder_service import KGBuilderService

    kg_service = KGBuilderService()
    cleaned_count = 0

    for file_id in file_ids:
        try:
            logger.info(f"清理知識圖譜數據: {file_id[:8]}...")

            # 刪除實體和關係的 file_id 關聯
            result = kg_service.remove_file_associations(file_id)
            logger.info(
                f"  ✅ 已清理知識圖譜數據: {file_id[:8]}... "
                f"(實體: {result.get('entities_removed', 0)}, "
                f"關係: {result.get('relations_removed', 0)})"
            )
            cleaned_count += 1

        except Exception as e:
            logger.error(f"  ❌ 清理知識圖譜數據失敗 {file_id[:8]}...: {e}")

    logger.info(f"總共清理了 {cleaned_count}/{len(file_ids)} 個文件的知識圖譜數據")
    return cleaned_count


def cleanup_file_metadata(file_ids: list, force: bool = False):
    """清理指定文件ID的文件元數據"""
    from services.api.services.file_metadata_service import FileMetadataService

    metadata_service = FileMetadataService()
    cleaned_count = 0

    for file_id in file_ids:
        try:
            logger.info(f"清理文件元數據: {file_id[:8]}...")

            # 檢查文件是否存在
            metadata = metadata_service.get(file_id)
            if metadata:
                if force:
                    metadata_service.delete(file_id)
                    logger.info(f"  ✅ 已刪除文件元數據: {file_id[:8]}...")
                    cleaned_count += 1
                else:
                    logger.info("  ℹ️  文件元數據存在但未刪除（使用 --force 強制刪除）")
            else:
                logger.info(f"  ℹ️  文件元數據不存在: {file_id[:8]}...")

        except Exception as e:
            logger.error(f"  ❌ 清理文件元數據失敗 {file_id[:8]}...: {e}")

    if force:
        logger.info(f"總共清理了 {cleaned_count}/{len(file_ids)} 個文件的元數據")
    return cleaned_count


def cleanup_processing_status(file_ids: list):
    """清理指定文件ID的處理狀態記錄"""
    from services.api.services.upload_status_service import get_upload_status_service

    upload_status_service = get_upload_status_service()
    cleaned_count = 0

    for file_id in file_ids:
        try:
            logger.info(f"清理處理狀態: {file_id[:8]}...")

            # 刪除處理狀態記錄
            upload_status_service.delete_processing_status(file_id)
            logger.info(f"  ✅ 已清理處理狀態: {file_id[:8]}...")
            cleaned_count += 1

        except Exception as e:
            logger.warning(f"  ⚠️  清理處理狀態失敗 {file_id[:8]}...: {e}")

    logger.info(f"總共清理了 {cleaned_count}/{len(file_ids)} 個文件的處理狀態")
    return cleaned_count


def cleanup_from_test_results(result_file: str, force_metadata: bool = False):
    """從測試結果文件中讀取 file_id 並清理"""
    if not os.path.exists(result_file):
        logger.error(f"測試結果文件不存在: {result_file}")
        return

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    file_ids = []

    for result in results:
        file_id = result.get("file_id")
        if file_id:
            file_ids.append(file_id)

    logger.info(f"從測試結果中找到 {len(file_ids)} 個文件ID")

    if not file_ids:
        logger.warning("沒有找到需要清理的文件ID")
        return

    print("=" * 80)
    print("開始清理 ArangoDB 測試數據")
    print("=" * 80)

    # 1. 清理知識圖譜數據
    print("\n1. 清理知識圖譜數據...")
    kg_count = cleanup_kg_data(file_ids)

    # 2. 清理處理狀態
    print("\n2. 清理處理狀態...")
    status_count = cleanup_processing_status(file_ids)

    # 3. 清理文件元數據（可選）
    if force_metadata:
        print("\n3. 清理文件元數據...")
        metadata_count = cleanup_file_metadata(file_ids, force=True)
    else:
        print("\n3. 跳過文件元數據清理（使用 --force-metadata 強制清理）")
        metadata_count = 0

    print("\n" + "=" * 80)
    print("清理完成")
    print("=" * 80)
    print(f"知識圖譜數據: {kg_count}/{len(file_ids)} 個文件")
    print(f"處理狀態: {status_count}/{len(file_ids)} 個文件")
    if force_metadata:
        print(f"文件元數據: {metadata_count}/{len(file_ids)} 個文件")
    print("=" * 80)


def cleanup_all_test_data(force_metadata: bool = False):
    """清理所有測試相關的數據（危險操作）"""
    from database.arangodb import ArangoDBClient

    client = ArangoDBClient()
    if client.db is None:
        logger.error("ArangoDB 未連接")
        return

    print("=" * 80)
    print("⚠️  警告: 這將清理所有測試數據")
    print("=" * 80)
    print("此操作將刪除:")
    print("  - 所有知識圖譜實體和關係")
    print("  - 所有處理狀態記錄")
    if force_metadata:
        print("  - 所有文件元數據")
    print("=" * 80)

    response = input("確認繼續? (yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        return

    # 這裡可以實現批量清理邏輯
    # 但為了安全，建議使用 file_ids 方式
    logger.warning("批量清理所有數據功能需要謹慎使用，建議使用 file_ids 方式")


def main():
    parser = argparse.ArgumentParser(description="清理 ArangoDB 測試數據")
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
        "--force-metadata",
        action="store_true",
        help="強制刪除文件元數據（默認只清理KG和狀態）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="清理所有測試數據（危險操作，需要確認）",
    )

    args = parser.parse_args()

    if args.all:
        cleanup_all_test_data(force_metadata=args.force_metadata)
    elif args.file_ids:
        logger.info(f"清理指定的 {len(args.file_ids)} 個文件")
        print("=" * 80)
        print("開始清理 ArangoDB 測試數據")
        print("=" * 80)

        # 1. 清理知識圖譜數據
        print("\n1. 清理知識圖譜數據...")
        kg_count = cleanup_kg_data(args.file_ids)

        # 2. 清理處理狀態
        print("\n2. 清理處理狀態...")
        status_count = cleanup_processing_status(args.file_ids)

        # 3. 清理文件元數據（可選）
        if args.force_metadata:
            print("\n3. 清理文件元數據...")
            metadata_count = cleanup_file_metadata(args.file_ids, force=True)
        else:
            print("\n3. 跳過文件元數據清理（使用 --force-metadata 強制清理）")
            metadata_count = 0

        print("\n" + "=" * 80)
        print("清理完成")
        print("=" * 80)
        print(f"知識圖譜數據: {kg_count}/{len(args.file_ids)} 個文件")
        print(f"處理狀態: {status_count}/{len(args.file_ids)} 個文件")
        if args.force_metadata:
            print(f"文件元數據: {metadata_count}/{len(args.file_ids)} 個文件")
        print("=" * 80)
    else:
        cleanup_from_test_results(args.test_result, force_metadata=args.force_metadata)


if __name__ == "__main__":
    main()
