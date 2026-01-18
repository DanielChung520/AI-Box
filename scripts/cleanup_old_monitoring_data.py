# 代碼功能說明: 清理舊監控系統數據（可選）
# 創建日期: 2026-01-18 18:54 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 18:54 UTC+8

"""清理舊監控系統數據腳本（可選）

用於在新系統穩定運行後，清理舊監控系統的數據（service_status, service_logs 等）
注意：此操作不可逆，請確保已備份數據且新系統穩定運行
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# 加載環境變數
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

from database.arangodb import ArangoDBClient


def cleanup_collection(client: ArangoDBClient, collection_name: str, dry_run: bool = True) -> int:
    """
    清理 ArangoDB Collection 數據

    Args:
        client: ArangoDB 客戶端
        collection_name: Collection 名稱
        dry_run: 是否為試運行（不實際刪除）

    Returns:
        將要刪除或已刪除的文檔數量
    """
    if client.db is None:
        print("❌ ArangoDB client is not connected")
        return 0

    try:
        collection = client.db.collection(collection_name)
        if not collection.has():
            print(f"⚠️  Collection '{collection_name}' does not exist, skipping...")
            return 0

        # 查詢文檔數量
        cursor = client.db.aql.execute(f"RETURN LENGTH({collection_name})")
        count = list(cursor)[0] if cursor else 0

        if count == 0:
            print(f"⚠️  Collection '{collection_name}' is empty, skipping...")
            return 0

        if dry_run:
            print(f"🔍 [DRY RUN] 將刪除 {count} 個文檔 from '{collection_name}'")
        else:
            # 實際刪除所有文檔
            cursor = client.db.aql.execute(
                f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}"
            )
            print(f"✅ 已刪除 {count} 個文檔 from '{collection_name}'")

        return count

    except Exception as e:
        print(f"❌ Failed to cleanup collection '{collection_name}': {str(e)}")
        return 0


def main():
    """主函數"""
    if len(sys.argv) < 2 or sys.argv[1] not in ["--dry-run", "--execute"]:
        print("用法: python cleanup_old_monitoring_data.py <--dry-run|--execute>")
        print("  --dry-run  - 試運行，只顯示將要刪除的數據，不實際刪除")
        print("  --execute  - 實際執行清理操作（不可逆）")
        print()
        print("⚠️  警告：此操作將永久刪除舊監控系統的數據！")
        print("   請確保：")
        print("   1. 已備份數據（使用 backup_monitoring_data.py）")
        print("   2. 新系統已穩定運行至少 24 小時")
        print("   3. 已確認不再需要舊系統數據")
        return 1

    dry_run = sys.argv[1] == "--dry-run"

    if not dry_run:
        print("=" * 80)
        print("⚠️  警告：此操作將永久刪除舊監控系統的數據！")
        print("=" * 80)
        print()
        confirm = input("請輸入 'YES' 確認執行清理操作: ")
        if confirm != "YES":
            print("❌ 操作已取消")
            return 1
        print()

    print("=" * 80)
    print(f"清理舊監控系統數據 ({'試運行' if dry_run else '實際執行'})")
    print("=" * 80)
    print()

    # 連接 ArangoDB
    try:
        client = ArangoDBClient()
        if client.db is None:
            print("❌ Failed to connect to ArangoDB")
            return 1

        print("✅ Connected to ArangoDB")
        print()

        # 需要清理的 Collections
        collections_to_cleanup = [
            "service_status",
            "service_logs",
            # 注意：service_alerts 和 service_alert_rules 可能還需要保留
            # 因為新系統的告警也會存儲在這裡
        ]

        total_documents = 0
        successful_cleanups = 0

        # 清理每個 Collection
        for collection_name in collections_to_cleanup:
            count = cleanup_collection(client, collection_name, dry_run=dry_run)
            if count > 0:
                successful_cleanups += 1
                total_documents += count

        print()
        print("=" * 80)
        print("清理完成" if not dry_run else "試運行完成")
        print("=" * 80)
        print(f"✅ 處理 {successful_cleanups}/{len(collections_to_cleanup)} 個 Collections")
        print(f"✅ 總共 {'將刪除' if dry_run else '已刪除'} {total_documents} 個文檔")
        print()

        if dry_run:
            print("💡 提示：如需實際執行清理，請使用 --execute 參數")
        else:
            print("✅ 清理操作已完成")

        return 0

    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
