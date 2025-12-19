#!/usr/bin/env python3
"""
代碼功能說明: 檢查任務同步狀態，診斷前端無法看到任務的問題
創建日期: 2025-01-27
創建人: Daniel Chung
最後修改日期: 2025-01-27
"""

import sys
from typing import Any, Dict

import requests

# API 配置
API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def login(username: str, password: str = "test") -> Dict[str, Any]:
    """登錄獲取 token"""
    url = f"{API_BASE_URL}{API_PREFIX}/auth/login"
    response = requests.post(
        url,
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code != 200:
        print(f"❌ 登錄失敗: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()
    return {
        "access_token": data.get("access_token"),
        "user_id": data.get("user_id"),
    }


def get_user_tasks(token: str, include_archived: bool = True) -> Dict[str, Any]:
    """獲取用戶任務列表"""
    url = f"{API_BASE_URL}{API_PREFIX}/user-tasks"
    params = {"include_archived": "true" if include_archived else "false"}
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    if response.status_code != 200:
        print(f"❌ 獲取任務失敗: {response.status_code}")
        print(response.text)
        return {}

    return response.json()


def check_task_status(username: str):
    """檢查任務狀態"""
    print(f"🔍 檢查用戶 {username} 的任務狀態...\n")

    # 登錄
    print("1. 登錄中...")
    auth = login(username)
    token = auth["access_token"]
    user_id = auth["user_id"]
    print(f"✅ 登錄成功，user_id: {user_id}\n")

    # 獲取所有任務（包括歸檔的）
    print("2. 獲取所有任務（包括歸檔的）...")
    response_all = get_user_tasks(token, include_archived=True)

    if not response_all.get("success"):
        print(f"❌ 獲取任務失敗: {response_all.get('message')}")
        return

    tasks_all = response_all.get("data", {}).get("tasks", [])
    print(f"✅ 找到 {len(tasks_all)} 個任務（包括歸檔的）\n")

    # 獲取激活的任務
    print("3. 獲取激活的任務...")
    response_active = get_user_tasks(token, include_archived=False)
    tasks_active = response_active.get("data", {}).get("tasks", [])
    print(f"✅ 找到 {len(tasks_active)} 個激活的任務\n")

    # 統計任務狀態
    print("4. 任務狀態統計：")
    status_count = {}
    for task in tasks_all:
        status = task.get("task_status", "未設置")
        status_count[status] = status_count.get(status, 0) + 1

    for status, count in status_count.items():
        print(f"   - {status}: {count} 個任務")
    print()

    # 列出所有任務
    print("5. 任務列表：")
    print("-" * 80)
    for task in tasks_all:
        task_id = task.get("task_id")
        title = task.get("title", "無標題")
        task_status = task.get("task_status", "未設置")
        status = task.get("status", "未知")

        # 標記是否在激活列表中
        is_active = any(t.get("task_id") == task_id for t in tasks_active)
        marker = "✅" if is_active else "❌"

        print(f"{marker} [{task_id}] {title}")
        print(f"     狀態: {status}, task_status: {task_status}")
        if not is_active and task_status == "activate":
            print("     ⚠️  警告：任務狀態為 activate，但未出現在激活列表中！")
        print()

    print("-" * 80)
    print("\n📋 診斷結果：")

    # 檢查是否有狀態不一致的任務
    inconsistent_tasks = []
    for task in tasks_all:
        task_status = task.get("task_status")
        task_id = task.get("task_id")
        is_in_active_list = any(t.get("task_id") == task_id for t in tasks_active)

        if task_status == "activate" and not is_in_active_list:
            inconsistent_tasks.append(
                {
                    "task_id": task_id,
                    "title": task.get("title"),
                    "task_status": task_status,
                }
            )

    if inconsistent_tasks:
        print(f"⚠️  發現 {len(inconsistent_tasks)} 個狀態不一致的任務：")
        for task in inconsistent_tasks:
            print(f"   - [{task['task_id']}] {task['title']} (task_status: {task['task_status']})")
        print("\n💡 解決方案：")
        print("   1. 刷新前端頁面，讓前端重新同步任務")
        print("   2. 或者清除瀏覽器的 localStorage，然後重新登錄")
        print("   3. 或者在前端控制台執行：")
        print("      localStorage.clear(); location.reload();")
    else:
        print("✅ 所有任務狀態一致")
        print("\n💡 如果前端仍然看不到任務，請嘗試：")
        print("   1. 刷新頁面（F5 或 Cmd+R）")
        print("   2. 清除瀏覽器緩存和 localStorage")
        print("   3. 重新登錄")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "daniel@test.com"
    check_task_status(username)
