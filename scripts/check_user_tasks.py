#!/usr/bin/env python3
# 代碼功能說明：檢查用戶任務的實際狀態
# 創建日期：2025-12-12
# 創建人：Daniel Chung
# 最後修改日期：2025-12-12

"""檢查用戶任務的實際狀態"""

import os
import sys

import requests

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_tasks_via_api(email: str = "daniel@test.com", password: str = "any"):
    """通過 API 檢查任務"""
    base_url = "http://localhost:8000"

    print(f"檢查用戶任務 - Email: {email}")
    print("=" * 80)

    # 1. 登錄獲取 token
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
    user_info = login_data.get("data", {})
    print("✅ 登錄成功")
    print(f"   User ID: {user_info.get('user_id', 'N/A')}")
    print(f"   Username: {user_info.get('username', 'N/A')}")
    print()

    # 2. 獲取當前用戶信息
    print("2. 獲取當前用戶信息...")
    me_response = requests.get(f"{base_url}/auth/me", headers={"Authorization": f"Bearer {token}"})

    if me_response.status_code == 200:
        me_data = me_response.json()
        if me_data.get("success"):
            user_data = me_data["data"]
            print("✅ 當前用戶信息:")
            print(f"   User ID: {user_data.get('user_id')}")
            print(f"   Email: {user_data.get('email')}")
            print()

    # 3. 查詢任務列表
    print("3. 查詢任務列表...")
    tasks_response = requests.get(
        f"{base_url}/user-tasks",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100},
    )

    if tasks_response.status_code != 200:
        print(f"❌ 查詢任務失敗: {tasks_response.status_code}")
        print(tasks_response.text)
        return

    tasks_data = tasks_response.json()
    if not tasks_data.get("success"):
        print(f"❌ 查詢任務失敗: {tasks_data.get('message')}")
        return

    tasks = tasks_data["data"].get("tasks", [])
    total = tasks_data["data"].get("total", 0)

    print("✅ 查詢成功")
    print(f"   返回任務數: {len(tasks)}")
    print(f"   總數: {total}")
    print()

    if not tasks:
        print("⚠️  沒有找到任務！")
        print()
        print("可能的原因：")
        print("1. 任務的 task_status 被設置為 'archive'（歸檔）")
        print("2. 任務的 user_id 與當前用戶不匹配")
        print("3. 數據庫中確實沒有任務")
        return

    # 4. 顯示任務詳情
    print("4. 任務詳情：")
    print("=" * 80)
    for i, task in enumerate(tasks, 1):
        print(f"\n任務 {i}:")
        print(f"  Task ID: {task.get('task_id')}")
        print(f"  User ID: {task.get('user_id')}")
        print(f"  Title: {task.get('title')}")
        print(f"  Status: {task.get('status')}")
        print(f"  Task Status: {task.get('task_status', 'N/A')}")
        print(f"  Created: {task.get('created_at')}")
        print(f"  Updated: {task.get('updated_at')}")

    # 5. 統計分析
    print()
    print("=" * 80)
    print("5. 統計分析：")

    status_counts = {}
    task_status_counts = {}
    user_id_counts = {}

    for task in tasks:
        status = task.get("status", "unknown")
        task_status = task.get("task_status", "N/A")
        user_id = task.get("user_id", "unknown")

        status_counts[status] = status_counts.get(status, 0) + 1
        task_status_counts[task_status] = task_status_counts.get(task_status, 0) + 1
        user_id_counts[user_id] = user_id_counts.get(user_id, 0) + 1

    print(f"Status 分布: {status_counts}")
    print(f"Task Status 分布: {task_status_counts}")
    print(f"User ID 分布: {user_id_counts}")


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "daniel@test.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "any"
    check_tasks_via_api(email, password)
