# 代碼功能說明: 清理 user_tasks 集合，僅保留 KA-Agent 和 MM-Agent 任務
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""
清理 ArangoDB user_tasks 集合，僅保留 KA-Agent 和 MM-Agent 任務

用法:
    python scripts/cleanup_user_tasks_except_agents.py [--dry-run] [--yes]

選項:
    --dry-run: 僅顯示將要刪除的任務，不實際刪除
    --yes:     跳過確認提示，直接執行刪除
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from database.arangodb import ArangoDBClient
import structlog

logger = structlog.get_logger(__name__)

# 要保留的 Agent 任務標識
KEEP_TASK_IDS = ["KA-Agent", "MM-Agent"]
KEEP_TASK_PATTERNS = ["KA-Agent", "MM-Agent"]


def should_keep_task(task: Dict[str, Any]) -> bool:
    """
    判斷任務是否應該保留

    Args:
        task: 任務文檔

    Returns:
        True 如果應該保留，False 如果應該刪除
    """
    task_id = task.get("task_id", "")
    title = task.get("title", "")

    # 檢查 task_id 是否匹配
    if task_id in KEEP_TASK_IDS:
        return True

    # 檢查 title 是否包含保留模式
    for pattern in KEEP_TASK_PATTERNS:
        if pattern in str(task_id) or pattern in str(title):
            return True

    return False


def cleanup_user_tasks(dry_run: bool = False, skip_confirm: bool = False) -> None:
    """
    清理 user_tasks 集合，僅保留 KA-Agent 和 MM-Agent 任務

    Args:
        dry_run: 如果為 True，僅顯示將要刪除的任務，不實際刪除
        skip_confirm: 如果為 True，跳過確認提示
    """
    client = ArangoDBClient()
    if client.db is None:
        logger.error("ArangoDB client is not connected")
        raise RuntimeError("ArangoDB client is not connected")

    collection = client.db.collection("user_tasks")

    # 查詢所有任務
    aql = """
    FOR task IN user_tasks
        RETURN task
    """
    cursor = client.db.aql.execute(aql)
    all_tasks = list(cursor)

    logger.info(f"Found {len(all_tasks)} tasks in user_tasks collection")

    # 分類任務
    tasks_to_keep: List[Dict[str, Any]] = []
    tasks_to_delete: List[Dict[str, Any]] = []

    for task in all_tasks:
        if should_keep_task(task):
            tasks_to_keep.append(task)
        else:
            tasks_to_delete.append(task)

    logger.info(f"Tasks to keep: {len(tasks_to_keep)}")
    logger.info(f"Tasks to delete: {len(tasks_to_delete)}")

    # 顯示要保留的任務
    if tasks_to_keep:
        print("\n✅ 將保留的任務:")
        for task in tasks_to_keep:
            task_id = task.get("task_id", task.get("_key", "unknown"))
            title = task.get("title", "N/A")
            user_id = task.get("user_id", "unknown")
            print(f"  - task_id: {task_id}, title: {title}, user_id: {user_id}")

    # 顯示要刪除的任務
    if tasks_to_delete:
        print(f"\n❌ 將刪除的任務 ({len(tasks_to_delete)} 個):")
        for task in tasks_to_delete[:20]:  # 只顯示前 20 個
            task_id = task.get("task_id", task.get("_key", "unknown"))
            title = task.get("title", "N/A")
            user_id = task.get("user_id", "unknown")
            print(f"  - task_id: {task_id}, title: {title}, user_id: {user_id}")
        if len(tasks_to_delete) > 20:
            print(f"  ... 還有 {len(tasks_to_delete) - 20} 個任務")

    if dry_run:
        print("\n🔍 DRY RUN 模式：未實際刪除任何任務")
        return

    if not tasks_to_delete:
        print("\n✅ 沒有需要刪除的任務")
        return

    # 確認刪除
    if not skip_confirm:
        print(f"\n⚠️  即將刪除 {len(tasks_to_delete)} 個任務")
        response = input("確認刪除？(yes/no): ").strip().lower()
        if response != "yes":
            print("❌ 已取消")
            return

    # 執行刪除
    print(f"\n🗑️  開始刪除 {len(tasks_to_delete)} 個任務...")
    deleted_count = 0
    error_count = 0

    for task in tasks_to_delete:
        try:
            task_key = task.get("_key")
            if not task_key:
                logger.warning("Task missing _key, skipping", task=task)
                error_count += 1
                continue

            collection.delete(task_key)
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"  已刪除 {deleted_count}/{len(tasks_to_delete)} 個任務...")
        except Exception as e:
            logger.error("Failed to delete task", task_key=task.get("_key"), error=str(e))
            error_count += 1

    print(f"\n✅ 刪除完成:")
    print(f"  - 成功刪除: {deleted_count} 個")
    print(f"  - 錯誤: {error_count} 個")
    print(f"  - 保留: {len(tasks_to_keep)} 個")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="清理 user_tasks 集合，僅保留 KA-Agent 和 MM-Agent 任務"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅顯示將要刪除的任務，不實際刪除",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳過確認提示，直接執行刪除",
    )
    args = parser.parse_args()

    try:
        cleanup_user_tasks(dry_run=args.dry_run, skip_confirm=args.yes)
    except Exception as e:
        logger.error("Cleanup failed", error=str(e), exc_info=True)
        print(f"\n❌ 清理失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
