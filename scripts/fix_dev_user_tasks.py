#!/usr/bin/env python3
# 代碼功能說明: 處理 dev_user 的任務（刪除或修復）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""
處理 dev_user 任務腳本

可以：
1. 刪除所有 dev_user 的任務
2. 將 dev_user 的任務轉移給指定用戶（如 daniel@test.com）
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from arango import ArangoClient
from dotenv import load_dotenv

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)


# ArangoDB 配置
def get_arangodb_client():
    host = os.getenv("ARANGODB_HOST", "http://127.0.0.1:8529")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    host_part = host.split("//")[-1].split("/")[0]
    if ":" not in host_part:
        if host.endswith("/"):
            host = host[:-1]
        host = f"{host}:8529"
    client = ArangoClient(hosts=host)
    db = client.db(
        os.getenv("ARANGODB_DATABASE", "ai_box_kg"),
        username=os.getenv("ARANGODB_USERNAME", "root"),
        password=os.getenv("ARANGODB_PASSWORD", ""),
    )
    return client, db


def delete_dev_user_tasks(db, confirm: bool = False):
    """刪除所有 dev_user 的任務"""
    print("=" * 60)
    print("刪除 dev_user 的所有任務")
    print("=" * 60)

    if not confirm:
        response = input("\n⚠️  確定要刪除 dev_user 的所有任務嗎？(yes/no): ")
        if response.lower() != "yes":
            print("操作已取消")
            return

    try:
        # 查詢 dev_user 的所有任務
        query = """
        FOR task IN user_tasks
            FILTER task.user_id == @user_id
            RETURN task
        """
        cursor = db.aql.execute(query, bind_vars={"user_id": "dev_user"})
        tasks = list(cursor)

        if not tasks:
            print("\n✅ 沒有 dev_user 的任務")
            return

        print(f"\n找到 {len(tasks)} 個 dev_user 的任務：")
        for task in tasks:
            print(
                f"  - {task.get('title', task.get('task_id', 'N/A'))} (task_id: {task.get('task_id', 'N/A')})"
            )

        # 獲取任務 ID 列表
        task_ids = [task.get("task_id") for task in tasks if task.get("task_id")]

        # 刪除文件元數據
        print("\n[1] 刪除文件元數據...")
        if db.has_collection("file_metadata"):
            file_query = """
            FOR file IN file_metadata
                FILTER file.user_id == @user_id
                RETURN file
            """
            file_cursor = db.aql.execute(file_query, bind_vars={"user_id": "dev_user"})
            files = list(file_cursor)
            file_ids = [
                f.get("file_id") or f.get("_key")
                for f in files
                if f.get("file_id") or f.get("_key")
            ]

            collection = db.collection("file_metadata")
            for file_id in file_ids:
                try:
                    collection.delete(file_id)
                    print(f"    ✓ 已刪除文件: {file_id}")
                except Exception as e:
                    print(f"    ✗ 刪除文件失敗 {file_id}: {e}")
            print(f"    ✅ 共刪除 {len(file_ids)} 個文件元數據")

        # 刪除資料夾元數據
        print("\n[2] 刪除資料夾元數據...")
        if db.has_collection("folder_metadata"):
            folder_query = """
            FOR folder IN folder_metadata
                FILTER folder.user_id == @user_id
                RETURN folder
            """
            folder_cursor = db.aql.execute(folder_query, bind_vars={"user_id": "dev_user"})
            folders = list(folder_cursor)
            folder_keys = [f.get("_key") for f in folders if f.get("_key")]

            collection = db.collection("folder_metadata")
            for folder_key in folder_keys:
                try:
                    collection.delete(folder_key)
                    print(f"    ✓ 已刪除資料夾: {folder_key}")
                except Exception as e:
                    print(f"    ✗ 刪除資料夾失敗 {folder_key}: {e}")
            print(f"    ✅ 共刪除 {len(folder_keys)} 個資料夾")

        # 刪除任務記錄
        print("\n[3] 刪除任務記錄...")
        collection = db.collection("user_tasks")
        for task in tasks:
            task_key = task.get("_key")
            if task_key:
                try:
                    collection.delete(task_key)
                    print(f"    ✓ 已刪除任務: {task.get('title', task_key)}")
                except Exception as e:
                    print(f"    ✗ 刪除任務失敗 {task_key}: {e}")
        print(f"    ✅ 共刪除 {len(tasks)} 個任務")

        # 刪除任務目錄
        print("\n[4] 刪除任務目錄...")
        tasks_dir = project_root / "data" / "tasks"
        deleted_count = 0
        for task_id in task_ids:
            task_dir = tasks_dir / task_id
            if task_dir.exists() and task_dir.is_dir():
                try:
                    shutil.rmtree(task_dir)
                    deleted_count += 1
                    print(f"    ✓ 已刪除目錄: {task_dir}")
                except Exception as e:
                    print(f"    ✗ 刪除目錄失敗 {task_dir}: {e}")
        print(f"    ✅ 共刪除 {deleted_count} 個任務目錄")

        print("\n" + "=" * 60)
        print("✅ dev_user 任務清除完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 刪除時發生錯誤: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="處理 dev_user 的任務（刪除）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 刪除所有 dev_user 任務（需要確認）
  python3 scripts/fix_dev_user_tasks.py --delete

  # 自動確認（無需交互）
  python3 scripts/fix_dev_user_tasks.py --delete --yes
        """,
    )

    parser.add_argument("--delete", action="store_true", help="刪除所有 dev_user 的任務")

    parser.add_argument("--yes", "-y", action="store_true", help="自動確認，跳過交互提示")

    args = parser.parse_args()

    if not args.delete:
        parser.print_help()
        return

    client, db = get_arangodb_client()
    delete_dev_user_tasks(db, confirm=args.yes)


if __name__ == "__main__":
    main()
