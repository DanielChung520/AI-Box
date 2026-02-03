#!/usr/bin/env python3
# 代碼功能說明: 清理重複創建的測試任務和工作區目錄
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""
清理重複創建的測試任務和工作區目錄

問題分析：
- 2026-01-27 17:54: 創建了 344 個測試任務（除 KA-Agent 和 MM-Agent 外）
- 2026-01-28 02:31: 為所有任務創建了工作區目錄

清理策略：
1. 保留 KA-Agent 和 MM-Agent 任務及其工作區目錄
2. 刪除其他所有測試任務和工作區目錄
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from database.arangodb import ArangoDBClient

# 要保留的 Agent 任務
KEEP_TASK_IDS = ["KA-Agent", "MM-Agent"]

# 目錄路徑
TASKS_DIR = project_root / "data" / "tasks"


def cleanup_user_tasks() -> dict:
    """清理 ArangoDB 中的 user_tasks"""
    client = ArangoDBClient()
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    collection = client.db.collection("user_tasks")

    # 查詢所有任務
    cursor = client.db.aql.execute("FOR task IN user_tasks RETURN task")
    all_tasks = list(cursor)

    tasks_to_keep = []
    tasks_to_delete = []

    for task in all_tasks:
        task_id = task.get("task_id", task.get("_key"))
        title = task.get("title", "N/A")
        user_id = task.get("user_id")

        if task_id in KEEP_TASK_IDS:
            tasks_to_keep.append(task)
        else:
            tasks_to_delete.append(task)

    print(f"📊 user_tasks 統計:")
    print(f"  總數: {len(all_tasks)}")
    print(f"  保留: {len(tasks_to_keep)}")
    print(f"  刪除: {len(tasks_to_delete)}")

    # 列出要保留的任務
    if tasks_to_keep:
        print(f"\n✅ 將保留的任務:")
        for task in tasks_to_keep:
            task_id = task.get("task_id")
            title = task.get("title")
            user_id = task.get("user_id")
            print(f"  - task_id: {task_id}, title: {title}, user_id: {user_id}")

    # 列出要刪除的任務（前 10 個）
    if tasks_to_delete:
        print(f"\n❌ 將刪除的任務 ({len(tasks_to_delete)} 個):")
        for task in tasks_to_delete[:10]:
            task_id = task.get("task_id")
            title = task.get("title")
            user_id = task.get("user_id")
            print(f"  - task_id: {task_id}, title: {title}, user_id: {user_id}")
        if len(tasks_to_delete) > 10:
            print(f"  ... 還有 {len(tasks_to_delete) - 10} 個任務")

    # 刪除任務
    deleted_count = 0
    error_count = 0

    for task in tasks_to_delete:
        try:
            task_key = task.get("_key")
            if not task_key:
                continue

            collection.delete(task_key)
            deleted_count += 1
            if deleted_count % 50 == 0:
                print(f"  已刪除 {deleted_count}/{len(tasks_to_delete)} 個任務...")
        except Exception as e:
            print(f"  ❌ 刪除失敗: {task_key}, 錯誤: {e}")
            error_count += 1

    print(f"\n✅ user_tasks 清理完成:")
    print(f"  成功刪除: {deleted_count}")
    print(f"  錯誤: {error_count}")
    print(f"  保留: {len(tasks_to_keep)}")

    return {
        "total": len(all_tasks),
        "deleted": deleted_count,
        "kept": len(tasks_to_keep),
        "errors": error_count,
    }


def cleanup_workspace_dirs() -> dict:
    """清理文件系統中的工作區目錄"""
    if not TASKS_DIR.exists():
        print(f"⚠️  目錄不存在: {TASKS_DIR}")
        return {"total": 0, "deleted": 0, "kept": 0, "errors": 0}

    # 獲取所有子目錄
    all_dirs = [d for d in TASKS_DIR.iterdir() if d.is_dir()]

    dirs_to_keep = []
    dirs_to_delete = []

    for dir_path in all_dirs:
        task_id = dir_path.name

        if task_id in KEEP_TASK_IDS:
            dirs_to_keep.append(dir_path)
        else:
            dirs_to_delete.append(dir_path)

    print(f"\n📁 工作區目錄統計:")
    print(f"  總數: {len(all_dirs)}")
    print(f"  保留: {len(dirs_to_keep)}")
    print(f"  刪除: {len(dirs_to_delete)}")

    # 列出要保留的目錄
    if dirs_to_keep:
        print(f"\n✅ 將保留的目錄:")
        for dir_path in dirs_to_keep:
            print(f"  - {dir_path.name}")

    # 列出要刪除的目錄（前 10 個）
    if dirs_to_delete:
        print(f"\n❌ 將刪除的目錄 ({len(dirs_to_delete)} 個):")
        for dir_path in dirs_to_delete[:10]:
            print(f"  - {dir_path.name}")
        if len(dirs_to_delete) > 10:
            print(f"  ... 還有 {len(dirs_to_delete) - 10} 個目錄")

    # 刪除目錄
    deleted_count = 0
    error_count = 0

    for dir_path in dirs_to_delete:
        try:
            shutil.rmtree(dir_path)
            deleted_count += 1
            if deleted_count % 50 == 0:
                print(f"  已刪除 {deleted_count}/{len(dirs_to_delete)} 個目錄...")
        except Exception as e:
            print(f"  ❌ 刪除失敗: {dir_path.name}, 錯誤: {e}")
            error_count += 1

    print(f"\n✅ 工作區目錄清理完成:")
    print(f"  成功刪除: {deleted_count}")
    print(f"  錯誤: {error_count}")
    print(f"  保留: {len(dirs_to_keep)}")

    return {
        "total": len(all_dirs),
        "deleted": deleted_count,
        "kept": len(dirs_to_keep),
        "errors": error_count,
    }


def main():
    """主函數"""
    print("=" * 60)
    print("清理重複創建的測試任務和工作區目錄")
    print(f"執行時間: {datetime.now().isoformat()}")
    print("=" * 60)

    # 清理 ArangoDB 中的 user_tasks
    print("\n🔍 第一步：清理 ArangoDB user_tasks")
    user_tasks_result = cleanup_user_tasks()

    # 清理文件系統中的工作區目錄
    print("\n🔍 第二步：清理工作區目錄")
    workspace_result = cleanup_workspace_dirs()

    # 總結
    print("\n" + "=" * 60)
    print("📋 清理總結")
    print("=" * 60)
    print(f"ArangoDB user_tasks:")
    print(f"  總數: {user_tasks_result['total']}")
    print(f"  刪除: {user_tasks_result['deleted']}")
    print(f"  保留: {user_tasks_result['kept']}")
    print(f"  錯誤: {user_tasks_result['errors']}")
    print(f"\n工作區目錄:")
    print(f"  總數: {workspace_result['total']}")
    print(f"  刪除: {workspace_result['deleted']}")
    print(f"  保留: {workspace_result['kept']}")
    print(f"  錯誤: {workspace_result['errors']}")
    print("=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
