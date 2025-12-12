#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 代碼功能說明: 清理指定用戶的數據（任務、文件、目錄）
# 創建日期: 2025-12-09 12:45 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-09 12:45 (UTC+8)

"""
清理指定用戶的所有數據（整合測試版本）

修改時間：2025-12-09 - 整合測試版本，移除 dev_user 相關邏輯
- 禁止清理 dev_user
- 使用正確的數據目錄結構（data/tasks, data/datasets）
"""

import sys
from pathlib import Path
from typing import List

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from database.arangodb import ArangoDBClient
    from dotenv import load_dotenv
except ImportError as e:
    print(f"[ERROR] 無法導入必需的模組: {e}")
    print("請確保已安裝所有依賴並在項目根目錄執行")
    sys.exit(1)

import shutil


def clear_user_data(user_email: str) -> bool:
    """清理指定用戶的所有數據

    Args:
        user_email: 用戶郵箱

    Returns:
        是否成功
    """
    # 修改時間：2025-12-09 - 整合測試：禁止清理 dev_user
    if user_email == "dev_user":
        print("[ERROR] 整合測試環境禁止清理 dev_user 數據")
        return False

    # 加載環境變數
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    # 初始化 ArangoDB 客戶端
    try:
        client = ArangoDBClient()

        if client.db is None:
            print("[ERROR] 無法連接到 ArangoDB")
            return False
    except Exception as e:
        print(f"[ERROR] 初始化 ArangoDB 客戶端失敗: {e}")
        return False

    print(f"[INFO] 開始清理用戶數據: {user_email}")

    deleted_count = {
        "tasks": 0,
        "files": 0,
        "folders": 0,
        "directories": 0,
        "file_objects": 0,
    }

    try:
        # 1. 查詢並刪除任務
        print("[INFO] 查詢用戶任務...")
        tasks_collection = client.db.collection("user_tasks")

        # 查詢該用戶的所有任務
        aql = """
        FOR task IN user_tasks
            FILTER task.user_id == @user_id
            RETURN task
        """
        cursor = client.db.aql.execute(aql, bind_vars={"user_id": user_email})
        tasks = list(cursor)

        print(f"[INFO] 找到 {len(tasks)} 個任務")

        # 收集所有 task_id 以便後續刪除文件系統目錄
        task_ids: List[str] = []

        for task in tasks:
            task_id = task.get("task_id")
            if not task_id:
                # 嘗試從 _key 推斷 task_id
                key = task.get("_key", "")
                if key.startswith(f"{user_email}_"):
                    task_id = key.replace(f"{user_email}_", "")

            if task_id:
                task_ids.append(task_id)

            # 刪除任務記錄
            try:
                tasks_collection.delete(task.get("_key"))
                deleted_count["tasks"] += 1
                print(
                    f"  [DELETE] 任務: {task.get('title', task_id)} (task_id: {task_id})"
                )
            except Exception as e:
                print(f"  [WARN] 無法刪除任務 {task.get('_key')}: {e}")

        # 2. 查詢並刪除文件元數據
        print("[INFO] 查詢文件元數據...")
        files_collection = client.db.collection("file_metadata")

        aql = """
        FOR file IN file_metadata
            FILTER file.user_id == @user_id
            RETURN file
        """
        cursor = client.db.aql.execute(aql, bind_vars={"user_id": user_email})
        files = list(cursor)

        print(f"[INFO] 找到 {len(files)} 個文件元數據記錄")

        file_paths_to_delete: List[str] = []

        for file_meta in files:
            file_id = file_meta.get("file_id") or file_meta.get("_key")
            storage_path = file_meta.get("storage_path")

            if storage_path:
                file_paths_to_delete.append(storage_path)

            # 刪除文件元數據記錄
            try:
                files_collection.delete(file_meta.get("_key"))
                deleted_count["files"] += 1
                print(f"  [DELETE] 文件元數據: {file_meta.get('filename', file_id)}")
            except Exception as e:
                print(f"  [WARN] 無法刪除文件元數據 {file_meta.get('_key')}: {e}")

        # 3. 查詢並刪除文件夾元數據
        print("[INFO] 查詢文件夾元數據...")
        folders_collection = client.db.collection("folder_metadata")

        aql = """
        FOR folder IN folder_metadata
            FILTER folder.user_id == @user_id
            RETURN folder
        """
        cursor = client.db.aql.execute(aql, bind_vars={"user_id": user_email})
        folders = list(cursor)

        print(f"[INFO] 找到 {len(folders)} 個文件夾元數據記錄")

        for folder in folders:
            try:
                folders_collection.delete(folder.get("_key"))
                deleted_count["folders"] += 1
                print(
                    f"  [DELETE] 文件夾: {folder.get('folder_name', folder.get('_key'))}"
                )
            except Exception as e:
                print(f"  [WARN] 無法刪除文件夾 {folder.get('_key')}: {e}")

        # 4. 刪除文件系統中的任務工作區目錄（新結構）
        print("[INFO] 刪除文件系統中的任務工作區...")
        tasks_root = project_root / "data" / "tasks"

        if tasks_root.exists():
            for task_id in task_ids:
                task_dir = tasks_root / task_id
                if task_dir.exists():
                    try:
                        shutil.rmtree(task_dir)
                        deleted_count["directories"] += 1
                        print(f"  [DELETE] 任務目錄: {task_dir}")
                    except Exception as e:
                        print(f"  [WARN] 無法刪除目錄 {task_dir}: {e}")

        # 5. 刪除文件系統中的實際文件
        print("[INFO] 刪除文件系統中的實際文件...")

        for file_path in file_paths_to_delete:
            file_path_obj = Path(file_path)

            # 安全檢查：確保路徑在項目範圍內
            try:
                resolved_path = file_path_obj.resolve()
                project_resolved = project_root.resolve()

                # 檢查是否在項目範圍內
                if not str(resolved_path).startswith(str(project_resolved)):
                    print(f"  [WARN] 跳過項目外路徑: {file_path}")
                    continue
            except (ValueError, OSError) as e:
                print(f"  [WARN] 路徑檢查失敗 {file_path}: {e}")
                continue

            if file_path_obj.exists() and file_path_obj.is_file():
                try:
                    file_path_obj.unlink()
                    deleted_count["file_objects"] += 1
                    print(f"  [DELETE] 文件: {file_path}")
                except Exception as e:
                    print(f"  [WARN] 無法刪除文件 {file_path}: {e}")

        # 輸出總結
        print("\n[INFO] 清理完成！")
        print(f"  - 已刪除任務: {deleted_count['tasks']}")
        print(f"  - 已刪除文件元數據: {deleted_count['files']}")
        print(f"  - 已刪除文件夾元數據: {deleted_count['folders']}")
        print(f"  - 已刪除任務目錄: {deleted_count['directories']}")
        print(f"  - 已刪除文件: {deleted_count['file_objects']}")

        return True

    except Exception as e:
        print(f"[ERROR] 清理過程中發生錯誤: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("[ERROR] 請提供用戶郵箱作為參數")
        print("用法: python3 clear_user_data.py <user_email>")
        print("範例: python3 clear_user_data.py daniel@test.com")
        sys.exit(1)

    user_email = sys.argv[1]

    # 修改時間：2025-12-09 - 整合測試：禁止清理 dev_user
    if user_email == "dev_user":
        print("[ERROR] 整合測試環境禁止清理 dev_user 數據")
        print("如需清理其他用戶，請使用實際的用戶郵箱")
        sys.exit(1)

    success = clear_user_data(user_email)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
