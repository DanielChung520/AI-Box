# 代碼功能說明: 備份監控系統數據
# 創建日期: 2026-01-18 18:54 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 18:54 UTC+8

"""備份監控系統數據腳本

用於在系統切換前備份舊監控系統的數據（service_status, service_logs, service_alerts 等）
"""

import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# 加載環境變數
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

from database.arangodb import ArangoDBClient


def backup_collection(client: ArangoDBClient, collection_name: str, backup_dir: Path) -> int:
    """
    備份 ArangoDB Collection 數據

    Args:
        client: ArangoDB 客戶端
        collection_name: Collection 名稱
        backup_dir: 備份目錄

    Returns:
        備份的文檔數量
    """
    if client.db is None:
        print("❌ ArangoDB client is not connected")
        return 0

    try:
        collection = client.db.collection(collection_name)
        if not collection.has():
            print(f"⚠️  Collection '{collection_name}' does not exist, skipping...")
            return 0

        # 查詢所有文檔
        cursor = client.db.aql.execute(f"FOR doc IN {collection_name} RETURN doc")
        documents = list(cursor)

        if not documents:
            print(f"⚠️  Collection '{collection_name}' is empty, skipping...")
            return 0

        # 保存到 JSON 文件
        backup_file = backup_dir / f"{collection_name}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2, ensure_ascii=False, default=str)

        print(f"✅ Backed up {len(documents)} documents from '{collection_name}' to {backup_file}")
        return len(documents)

    except Exception as e:
        print(f"❌ Failed to backup collection '{collection_name}': {str(e)}")
        return 0


def main():
    """主函數"""
    print("=" * 80)
    print("監控系統數據備份腳本")
    print("=" * 80)
    print()

    # 創建備份目錄
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_root / "backup" / f"monitoring_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 備份目錄: {backup_dir}")
    print()

    # 連接 ArangoDB
    try:
        client = ArangoDBClient()
        if client.db is None:
            print("❌ Failed to connect to ArangoDB")
            return 1

        print("✅ Connected to ArangoDB")
        print()

        # 需要備份的 Collections
        collections_to_backup = [
            "service_status",
            "service_logs",
            "service_alerts",
            "service_alert_rules",
        ]

        total_documents = 0
        successful_backups = 0

        # 備份每個 Collection
        for collection_name in collections_to_backup:
            count = backup_collection(client, collection_name, backup_dir)
            if count > 0:
                successful_backups += 1
                total_documents += count

        print()
        print("=" * 80)
        print("備份完成")
        print("=" * 80)
        print(f"✅ 成功備份 {successful_backups}/{len(collections_to_backup)} 個 Collections")
        print(f"✅ 總共備份 {total_documents} 個文檔")
        print(f"📁 備份位置: {backup_dir}")
        print()

        # 創建備份信息文件
        backup_info = {
            "timestamp": timestamp,
            "backup_date": datetime.now().isoformat(),
            "collections_backed_up": successful_backups,
            "total_documents": total_documents,
            "backup_dir": str(backup_dir),
        }

        info_file = backup_dir / "backup_info.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)

        print(f"📄 備份信息已保存到: {info_file}")
        print()

        return 0

    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
