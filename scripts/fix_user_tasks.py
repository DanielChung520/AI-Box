#!/usr/bin/env python3
"""
修復用戶任務的 user_id
將錯誤的 user_id 改正為正確的用戶 email

使用方法：
    python3 scripts/fix_user_tasks.py --email daniel@test.com           # 預覽模式
    python3 scripts/fix_user_tasks.py --email daniel@test.com --apply   # 實際執行
"""

import argparse
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.arangodb import ArangoDBClient


def fix_user_tasks(email: str, dry_run: bool = True, confirm: bool = False):
    """修復指定用戶的任務 user_id"""

    # 檢測正確的 user_id 格式
    # 嘗試不同的格式
    possible_user_ids = [
        email,  # daniel@test.com
        f"user_{email}",  # user_daniel@test.com
    ]

    client = ArangoDBClient()
    if not client.connect():
        print("❌ 無法連接到 ArangoDB")
        return False

    db = client.db
    collection = db.collection("user_tasks")

    # 獲取所有任務
    cursor = collection.all()
    all_tasks = list(cursor)

    print(f"\n📊 數據庫中總共有 {len(all_tasks)} 個任務")
    print(f"\n👤 要修復的用戶: {email}")

    # 找出需要修復的任務
    tasks_to_fix = []
    for task in all_tasks:
        task_user_id = task.get("user_id")
        task_id = task.get("task_id")
        task_title = task.get("title", "")[:30]

        # 檢查這個任務是否應該屬於這個用戶
        # 通過任務的 _key 來判斷（格式：user_id_task_id）
        task_key = task.get("_key", "")

        # 修復：將所有不是 systemAdmin 的任務改為 daniel@test.com
        # 因為這些任務都是 daniel@test.com 創建的
        if task_user_id == "systemAdmin" or task_user_id == "unauthenticated":
            tasks_to_fix.append(
                {
                    "task_id": task_id,
                    "title": task_title,
                    "current_user_id": task_user_id,
                    "new_user_id": email,
                    "_key": task_key,
                }
            )

    print(f"\n🔧 需要修復的任務數量: {len(tasks_to_fix)}")

    if not tasks_to_fix:
        print("✅ 沒有需要修復的任務")
        return True

    # 顯示前 10 個要修復的任務
    print("\n📝 要修復的任務（前 10 個）：")
    for i, task in enumerate(tasks_to_fix[:10], 1):
        print(
            f"  {i}. [{task['task_id']}] {task['title']}... (當前: {task['current_user_id']} → 新: {task['new_user_id']})"
        )

    if len(tasks_to_fix) > 10:
        print(f"  ... 還有 {len(tasks_to_fix) - 10} 個任務")

    if dry_run:
        print("\n🔍 這是預覽模式，要實際執行修復，請添加 --apply 參數")
        print(f"   執行後將會更新 {len(tasks_to_fix)} 個任務的 user_id")
        return True

    if not confirm:
        print(f"\n⚠️  確定要修復這 {len(tasks_to_fix)} 個任務嗎？")
        print("   這個操作不可逆，請確認後再執行")
        print("   要執行修復，請添加 --yes 參數")
        return True

    # 執行修復
    fixed_count = 0
    for task in tasks_to_fix:
        try:
            # 更新任務的 user_id
            collection.update(task["_key"], {"user_id": task["new_user_id"]})
            fixed_count += 1
            print(f"  ✅ 已修復: {task['task_id']}")
        except Exception as e:
            print(f"  ❌ 修復失敗: {task['task_id']} - {e}")

    print(f"\n✅ 修復完成！共修復 {fixed_count}/{len(tasks_to_fix)} 個任務")
    return True


def main():
    parser = argparse.ArgumentParser(description="修復用戶任務的 user_id")
    parser.add_argument("--email", required=True, help="用戶 email")
    parser.add_argument("--dry-run", action="store_true", default=True, help="預覽模式（預設）")
    parser.add_argument("--apply", action="store_true", help="實際執行修復")
    parser.add_argument("--yes", action="store_true", help="跳過確認，直接執行")

    args = parser.parse_args()

    # 確定模式
    dry_run = not args.apply

    # 顯示模式
    if dry_run:
        print("🔍 預覽模式")
    else:
        print("⚠️  執行修復模式")

    # 執行修復
    success = fix_user_tasks(email=args.email, dry_run=dry_run, confirm=args.yes)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
