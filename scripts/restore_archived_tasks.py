#!/usr/bin/env python3
# 代碼功能說明：恢復歸檔的任務
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""恢復歸檔的任務腳本

用於將歸檔的任務恢復為激活狀態。
"""

import argparse
import os
import sys

import requests

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def restore_archived_tasks(
    email: str = "daniel@test.com",
    password: str = "any",
    dry_run: bool = True,
):
    """恢復歸檔的任務"""
    base_url = "http://localhost:8000"

    print(f"恢復歸檔任務 - Email: {email}")
    print(f"模式: {'預覽（dry-run）' if dry_run else '實際執行'}")
    print("=" * 80)

    # 1. 登錄
    print("1. 登錄...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={"username": email, "password": password},
        headers={"Content-Type": "application/json"},
    )

    if login_response.status_code != 200:
        print(f"❌ 登錄失敗: {login_response.status_code}")
        print(login_response.text)
        return

    login_data = login_response.json()
    if not login_data.get("success"):
        print(f"❌ 登錄失敗: {login_data.get('message')}")
        return

    token = login_data["data"]["access_token"]
    user_id = login_data["data"].get("user_id", email)
    print(f"✅ 登錄成功 (user_id: {user_id})")
    print()

    # 2. 查詢所有任務（包括歸檔的）
    print("2. 查詢所有任務（包括歸檔的）...")
    tasks_response = requests.get(
        f"{base_url}/user-tasks",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 1000, "include_archived": True},
    )

    if tasks_response.status_code != 200:
        print(f"❌ 查詢任務失敗: {tasks_response.status_code}")
        print(tasks_response.text)
        return

    tasks_data = tasks_response.json()
    if not tasks_data.get("success"):
        print(f"❌ 查詢任務失敗: {tasks_data.get('message')}")
        return

    all_tasks = tasks_data["data"].get("tasks", [])
    print(f"✅ 找到 {len(all_tasks)} 個任務（包括歸檔的）")
    print()

    # 3. 找出歸檔的任務
    archived_tasks = [task for task in all_tasks if task.get("task_status") == "archive"]

    if not archived_tasks:
        print("✅ 沒有歸檔的任務需要恢復")
        return

    print(f"3. 找到 {len(archived_tasks)} 個歸檔的任務：")
    for i, task in enumerate(archived_tasks, 1):
        print(f"   {i}. {task.get('title')} (task_id: {task.get('task_id')})")
    print()

    if dry_run:
        print("⚠️  這是預覽模式，不會實際修改數據")
        print("   要實際執行恢復，請使用 --no-dry-run 參數")
        return

    # 4. 確認
    print("⚠️  警告：這將恢復所有歸檔的任務！")
    response = input("確認繼續？(yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        return

    # 5. 恢復任務
    print()
    print("4. 恢復任務...")
    restored_count = 0
    error_count = 0

    for task in archived_tasks:
        task_id = task.get("task_id")
        title = task.get("title")

        try:
            update_response = requests.put(
                f"{base_url}/user-tasks/{task_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"task_status": "activate"},
            )

            if update_response.status_code == 200:
                update_data = update_response.json()
                if update_data.get("success"):
                    print(f"✅ 已恢復: {title} (task_id: {task_id})")
                    restored_count += 1
                else:
                    print(f"❌ 恢復失敗: {title} - {update_data.get('message')}")
                    error_count += 1
            else:
                print(f"❌ 恢復失敗: {title} - HTTP {update_response.status_code}")
                error_count += 1

        except Exception as e:
            print(f"❌ 恢復任務 {task_id} 時出錯: {e}")
            error_count += 1

    print()
    print("=" * 80)
    print("恢復完成：")
    print(f"  ✅ 成功: {restored_count} 個")
    print(f"  ❌ 失敗: {error_count} 個")
    print(f"  📊 總計: {len(archived_tasks)} 個")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="恢復歸檔的任務")
    parser.add_argument(
        "--email",
        type=str,
        default="daniel@test.com",
        help="用戶 email",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="any",
        help="用戶密碼",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="預覽模式（不實際修改數據）",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_false",
        dest="dry_run",
        help="實際執行恢復（不使用預覽模式）",
    )

    args = parser.parse_args()

    restore_archived_tasks(
        email=args.email,
        password=args.password,
        dry_run=args.dry_run,
    )
