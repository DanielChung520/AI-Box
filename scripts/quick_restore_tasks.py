#!/usr/bin/env python3
# 代碼功能說明：快速恢復歸檔任務
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""快速恢復歸檔任務"""

import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
EMAIL = "daniel@test.com"
PASSWORD = "any"


def main():
    print("=" * 80)
    print("快速恢復歸檔任務")
    print("=" * 80)
    print()

    # 1. 登錄
    print("1. 登錄...")
    login_resp = requests.post(
        f"{BASE_URL}/auth/login", json={"username": EMAIL, "password": PASSWORD}
    )

    if login_resp.status_code != 200:
        print(f"❌ 登錄失敗: {login_resp.status_code}")
        return

    token = login_resp.json()["data"]["access_token"]
    print("✅ 登錄成功")
    print()

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 查詢所有任務（包括歸檔的）
    print("2. 查詢所有任務（包括歸檔的）...")
    tasks_resp = requests.get(
        f"{BASE_URL}/user-tasks",
        headers=headers,
        params={"limit": 1000, "include_archived": True},
    )

    if tasks_resp.status_code != 200:
        print(f"❌ 查詢失敗: {tasks_resp.status_code}")
        return

    all_tasks = tasks_resp.json()["data"]["tasks"]
    print(f"✅ 找到 {len(all_tasks)} 個任務")

    # 3. 找出歸檔的任務
    archived = [t for t in all_tasks if t.get("task_status") == "archive"]
    print(f"   其中 {len(archived)} 個是歸檔狀態")
    print()

    if not archived:
        print("✅ 沒有歸檔的任務需要恢復")
        return

    # 4. 顯示歸檔任務
    print("3. 歸檔的任務列表：")
    for i, task in enumerate(archived, 1):
        print(f"   {i}. {task.get('title')} (task_id: {task.get('task_id')})")
    print()

    # 5. 確認
    print(f"⚠️  將恢復 {len(archived)} 個歸檔任務")
    response = input("確認繼續？(yes/no): ")
    if response.lower() != "yes":
        print("已取消")
        return

    # 6. 批量恢復
    print()
    print("4. 恢復任務...")
    success = 0
    failed = 0

    for task in archived:
        task_id = task.get("task_id")
        title = task.get("title")

        try:
            update_resp = requests.put(
                f"{BASE_URL}/user-tasks/{task_id}",
                headers={**headers, "Content-Type": "application/json"},
                json={"task_status": "activate"},
            )

            if update_resp.status_code == 200 and update_resp.json().get("success"):
                print(f"   ✅ {title}")
                success += 1
            else:
                print(f"   ❌ {title} - {update_resp.status_code}")
                failed += 1
        except Exception as e:
            print(f"   ❌ {title} - {e}")
            failed += 1

    print()
    print("=" * 80)
    print(f"完成：成功 {success} 個，失敗 {failed} 個")
    print("=" * 80)


if __name__ == "__main__":
    main()
