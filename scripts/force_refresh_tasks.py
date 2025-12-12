#!/usr/bin/env python3
"""
代碼功能說明: 強制刷新任務狀態，清除前端緩存並重新同步
創建日期: 2025-01-27
創建人: Daniel Chung
最後修改日期: 2025-01-27
"""

import requests
import sys

# API 配置
API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def login(username: str, password: str = "test") -> dict:
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


def get_user_tasks(token: str, include_archived: bool = True) -> dict:
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


def check_and_fix_tasks(username: str):
    """檢查並修復任務狀態"""
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

    # 列出所有任務及其狀態
    print("4. 任務詳細信息：")
    print("-" * 80)
    activate_tasks = []
    archive_tasks = []

    for task in tasks_all:
        task_id = task.get("task_id")
        title = task.get("title", "無標題")
        task_status = task.get("task_status", "未設置")
        status = task.get("status", "未知")

        is_in_active_list = any(t.get("task_id") == task_id for t in tasks_active)

        if task_status == "activate":
            activate_tasks.append(task_id)
            marker = "✅" if is_in_active_list else "⚠️"
            print(f"{marker} [{task_id}] {title}")
            print(f"     狀態: {status}, task_status: {task_status}")
            if not is_in_active_list:
                print("     ⚠️  警告：任務狀態為 activate，但未出現在激活列表中！")
        else:
            archive_tasks.append(task_id)
            print(f"❌ [{task_id}] {title}")
            print(f"     狀態: {status}, task_status: {task_status}")
        print()

    print("-" * 80)
    print("\n📋 診斷結果：")
    print(f"   - 總任務數: {len(tasks_all)}")
    print(f"   - activate 任務數: {len(activate_tasks)}")
    print(f"   - archive 任務數: {len(archive_tasks)}")
    print(f"   - API 返回的激活任務數: {len(tasks_active)}")

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
        print(f"\n⚠️  發現 {len(inconsistent_tasks)} 個狀態不一致的任務：")
        for task in inconsistent_tasks:
            print(
                f"   - [{task['task_id']}] {task['title']} (task_status: {task['task_status']})"
            )

    print("\n💡 解決方案：")
    print("   1. 打開瀏覽器開發者工具（F12）")
    print("   2. 在 Console 中執行以下命令清除 localStorage：")
    print("      localStorage.clear();")
    print("   3. 然後執行以下命令強制刷新頁面：")
    print("      location.reload();")
    print("\n   或者，在前端頁面中：")
    print("   1. 按 F5 或 Cmd+R 刷新頁面")
    print("   2. 如果還是不行，清除瀏覽器緩存（Ctrl+Shift+Delete 或 Cmd+Shift+Delete）")
    print("   3. 重新登錄")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "daniel@test.com"
    check_and_fix_tasks(username)
