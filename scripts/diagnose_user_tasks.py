#!/usr/bin/env python3
# 代碼功能說明：診斷用戶任務問題，檢查 user_id 不匹配的情況
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""診斷用戶任務問題腳本

用於檢查為什麼使用 daniel@test.com 登錄時看不到之前創建的任務。
問題可能是 user_id 不匹配。
"""

import os
import sys

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict

from database.arangodb import ArangoDBClient


def get_user_id_from_email(email: str) -> str:
    """根據 email 生成 user_id（與 auth.py 中的邏輯一致）"""
    return email if "@" in email else f"user_{email}"


def diagnose_user_tasks(email: str = "daniel@test.com"):
    """診斷用戶任務問題"""
    print(f"診斷用戶任務問題 - Email: {email}")
    print("=" * 80)

    # 計算預期的 user_id
    expected_user_id = get_user_id_from_email(email)
    print(f"預期的 user_id: {expected_user_id}")
    print()

    # 連接數據庫
    try:
        client = ArangoDBClient()
        if client.db is None:
            print("❌ ArangoDB 未連接")
            return

        # 查詢所有任務
        aql_query = """
        FOR task IN user_tasks
            SORT task.created_at DESC
            RETURN {
                _key: task._key,
                task_id: task.task_id,
                user_id: task.user_id,
                title: task.title,
                created_at: task.created_at
            }
        """

        cursor = client.db.aql.execute(aql_query)
        all_tasks = list(cursor)

        print(f"數據庫中共有 {len(all_tasks)} 個任務")
        print()

        # 分類任務
        matching_tasks = []
        other_tasks = []

        for task in all_tasks:
            task_user_id = task.get("user_id")
            if task_user_id == expected_user_id:
                matching_tasks.append(task)
            else:
                other_tasks.append(task)

        print(f"✅ 匹配的任務（user_id = {expected_user_id}）: {len(matching_tasks)} 個")
        if matching_tasks:
            print("   這些任務應該可以正常顯示：")
            for task in matching_tasks[:5]:  # 只顯示前5個
                print(f"   - {task.get('title')} (task_id: {task.get('task_id')})")
            if len(matching_tasks) > 5:
                print(f"   ... 還有 {len(matching_tasks) - 5} 個任務")
        print()

        print(f"❌ 不匹配的任務（user_id != {expected_user_id}）: {len(other_tasks)} 個")
        if other_tasks:
            print("   這些任務不會顯示，因為 user_id 不匹配：")
            # 統計不同的 user_id
            user_id_counts: Dict[str, int] = {}
            for task in other_tasks:
                uid = task.get("user_id", "unknown")
                user_id_counts[uid] = user_id_counts.get(uid, 0) + 1

            for uid, count in sorted(user_id_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   - user_id: {uid} ({count} 個任務)")
                # 顯示該 user_id 的示例任務
                examples = [t for t in other_tasks if t.get("user_id") == uid][:2]
                for task in examples:
                    print(f"     • {task.get('title')} (task_id: {task.get('task_id')})")
        print()

        # 提供修復建議
        if other_tasks:
            print("=" * 80)
            print("修復建議：")
            print()
            print("如果這些任務應該屬於當前用戶，可以運行修復腳本：")
            print(f"  python3 scripts/fix_user_tasks.py --email {email} --dry-run")
            print()
            print("或者手動更新任務的 user_id：")
            for uid in sorted(set(t.get("user_id") for t in other_tasks)):
                if uid != expected_user_id:
                    print(f"  - 將 user_id='{uid}' 的任務更新為 user_id='{expected_user_id}'")

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "daniel@test.com"
    diagnose_user_tasks(email)
