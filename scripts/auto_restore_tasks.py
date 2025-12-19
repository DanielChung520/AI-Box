#!/usr/bin/env python3
# 代碼功能說明：自動恢復歸檔任務（無需確認）
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""自動恢復歸檔任務"""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
EMAIL = "daniel@test.com"
PASSWORD = "any"


def main():
    print("=" * 80)
    print("自動恢復歸檔任務")
    print("=" * 80)
    print()

    # 1. 登錄
    print("1. 登錄...")
    try:
        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": EMAIL, "password": PASSWORD},
            timeout=5,
        )

        if login_resp.status_code != 200:
            print(f"❌ 登錄失敗: {login_resp.status_code}")
            print(login_resp.text)
            return

        token = login_resp.json()["data"]["access_token"]
        print("✅ 登錄成功")
        print()
    except requests.exceptions.RequestException as e:
        print(f"❌ 連接失敗: {e}")
        print("請確認 API 服務正在運行 (http://localhost:8000)")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 查詢所有任務（包括歸檔的）
    print("2. 查詢所有任務（包括歸檔的）...")
    try:
        tasks_resp = requests.get(
            f"{BASE_URL}/user-tasks",
            headers=headers,
            params={"limit": 1000, "include_archived": True},
            timeout=10,
        )

        if tasks_resp.status_code != 200:
            print(f"❌ 查詢失敗: {tasks_resp.status_code}")
            print(tasks_resp.text)
            return

        tasks_data = tasks_resp.json()
        if not tasks_data.get("success"):
            print(f"❌ 查詢失敗: {tasks_data.get('message')}")
            return

        all_tasks = tasks_data["data"]["tasks"]
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

        # 5. 批量恢復（自動執行，無需確認）
        print(f"4. 自動恢復 {len(archived)} 個歸檔任務...")
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
                    timeout=5,
                )

                if update_resp.status_code == 200:
                    update_data = update_resp.json()
                    if update_data.get("success"):
                        print(f"   ✅ {title}")
                        success += 1
                    else:
                        print(f"   ❌ {title} - {update_data.get('message')}")
                        failed += 1
                else:
                    print(f"   ❌ {title} - HTTP {update_resp.status_code}")
                    failed += 1
            except Exception as e:
                print(f"   ❌ {title} - {e}")
                failed += 1

        print()
        print("=" * 80)
        print(f"完成：成功 {success} 個，失敗 {failed} 個")
        print("=" * 80)

    except requests.exceptions.RequestException as e:
        print(f"❌ 請求失敗: {e}")


if __name__ == "__main__":
    main()
