#!/usr/bin/env python3
# 代碼功能說明：直接從數據庫恢復歸檔任務
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""直接從數據庫恢復歸檔任務（不通過 API）"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.arangodb import ArangoDBClient


def get_user_id_from_email(email: str) -> str:
    """根據 email 生成 user_id"""
    return email if "@" in email else f"user_{email}"


def main():
    email = "daniel@test.com"
    user_id = get_user_id_from_email(email)

    print("=" * 80)
    print("直接從數據庫恢復歸檔任務")
    print(f"Email: {email}")
    print(f"User ID: {user_id}")
    print("=" * 80)
    print()

    try:
        client = ArangoDBClient()
        if client.db is None:
            print("❌ ArangoDB 未連接")
            return

        collection = client.db.collection("user_tasks")

        # 1. 查詢所有歸檔的任務
        print("1. 查詢歸檔的任務...")
        aql_query = """
        FOR task IN user_tasks
            FILTER task.user_id == @user_id
            FILTER task.task_status == "archive"
            RETURN task
        """

        cursor = client.db.aql.execute(aql_query, bind_vars={"user_id": user_id})
        archived_tasks = list(cursor)

        print(f"✅ 找到 {len(archived_tasks)} 個歸檔任務")
        print()

        if not archived_tasks:
            print("✅ 沒有歸檔的任務需要恢復")
            return

        # 2. 顯示歸檔任務
        print("2. 歸檔任務列表：")
        for i, task in enumerate(archived_tasks, 1):
            print(f"   {i}. {task.get('title')} (task_id: {task.get('task_id')})")
        print()

        # 3. 批量恢復
        print(f"3. 恢復 {len(archived_tasks)} 個歸檔任務...")
        success = 0
        failed = 0

        for task in archived_tasks:
            task_id = task.get("task_id")
            title = task.get("title")
            doc_key = task.get("_key")

            try:
                # 更新 task_status 為 activate
                task["task_status"] = "activate"
                collection.update(task)
                print(f"   ✅ {title}")
                success += 1
            except Exception as e:
                print(f"   ❌ {title} - {e}")
                failed += 1

        print()
        print("=" * 80)
        print(f"完成：成功 {success} 個，失敗 {failed} 個")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
