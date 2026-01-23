#!/usr/bin/env python3
"""
修補腳本：為任務的 fileTree 中的檔案創建 file_metadata 記錄

用途：
- 修復數據不一致問題（任務有 fileTree 但 file_metadata 沒有記錄）
- 從任務的 fileTree 提取檔案資訊並創建對應的 metadata 記錄

使用方法：
    python3 scripts/fix_missing_file_metadata.py --task-id 1768995433434 --user-id daniel@test.com

或修復所有任務：
    python3 scripts/fix_missing_file_metadata.py --all
"""

import argparse
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

from system.infra.config.config import get_config_section


def get_arangodb_client():
    """獲取 ArangoDB client"""
    arangodb_config = get_config_section("datastores", "arangodb", default={})
    host = arangodb_config.get("host", "localhost")
    port = arangodb_config.get("port", 8529)
    protocol = arangodb_config.get("protocol", "http")
    database = arangodb_config.get("database", "ai_box_kg")
    username = arangodb_config.get("credentials", {}).get("username", "root")
    password = arangodb_config.get("credentials", {}).get("password", "changeme")

    from arango import ArangoClient

    client = ArangoClient(host=f"{protocol}://{host}", port=port)
    db = client.db(database, username=username, password=password)
    return db


def get_file_metadata_collection(db):
    """獲取 file_metadata collection"""
    return db.collection("file_metadata")


def get_user_tasks_collection(db):
    """獲取 user_tasks collection"""
    return db.collection("user_tasks")


def extract_files_from_filetree(
    filetree: List[Dict[str, Any]], task_id: str
) -> List[Dict[str, Any]]:
    """從 fileTree 中提取所有檔案"""
    files = []

    def traverse(node):
        if isinstance(node, dict):
            if node.get("type") == "file":
                files.append(
                    {
                        "file_id": node.get("id"),
                        "filename": node.get("name"),
                        "task_id": task_id,
                    }
                )
            elif node.get("type") == "folder" and node.get("children"):
                for child in node.get("children", []):
                    traverse(child)
        elif isinstance(node, list):
            for item in node:
                traverse(item)

    for item in filetree:
        traverse(item)

    return files


def create_file_metadata(
    collection,
    file_id: str,
    filename: str,
    task_id: str,
    user_id: str,
    storage_path: str = None,
) -> Dict[str, Any]:
    """創建 file_metadata 記錄"""
    existing = collection.get(file_id)
    if existing:
        print(f"  ⚠️  檔案已存在: {filename} ({file_id})")
        return existing

    doc = {
        "_key": file_id,
        "file_id": file_id,
        "filename": filename,
        "file_type": "markdown",
        "file_size": 0,
        "user_id": user_id,
        "task_id": task_id,
        "folder_id": None,
        "storage_path": storage_path or f"tasks/{task_id}/{file_id}",
        "tags": [],
        "description": None,
        "custom_metadata": {},
        "status": "uploaded",
        "processing_status": None,
        "chunk_count": None,
        "vector_count": None,
        "kg_status": None,
        "access_control": {
            "owner_id": user_id,
            "tenant_id": None,
            "visibility": "private",
            "data_classification": "internal",
            "sensitivity_labels": [],
            "sharing_enabled": False,
            "external_access_enabled": False,
        },
        "data_classification": "internal",
        "sensitivity_labels": [],
        "upload_time": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    collection.insert(doc)
    print(f"  ✅ 創建 metadata: {filename} ({file_id})")
    return doc


def fix_task_file_metadata(
    db,
    task_id: str,
    user_id: str,
) -> int:
    """修復單個任務的 file_metadata"""
    task_collection = get_user_tasks_collection(db)
    file_collection = get_file_metadata_collection(db)

    # 獲取任務文檔
    task = None
    for doc_key in [f"{user_id}_{task_id}", task_id]:
        task = task_collection.get(doc_key)
        if task:
            break

    if not task:
        print(f"❌ 任務不存在: {task_id}")
        return 0

    task_user_id = task.get("user_id")
    if task_user_id and task_user_id != user_id:
        print(f"⚠️  任務不屬於用戶 {user_id}，實際用戶: {task_user_id}")
        user_id = task_user_id

    filetree = task.get("fileTree", [])
    if not filetree:
        print(f"⚠️  任務沒有 fileTree: {task_id}")
        return 0

    print(f"\n📁 處理任務: {task_id}")
    print(f"   標題: {task.get('title', 'Unknown')}")
    print(f"   用戶: {user_id}")

    # 從 fileTree 提取檔案
    files = extract_files_from_filetree(filetree, task_id)
    print(f"   發現 {len(files)} 個檔案")

    # 為每個檔案創建 metadata
    created_count = 0
    for file_info in files:
        try:
            create_file_metadata(
                file_collection,
                file_id=file_info["file_id"],
                filename=file_info["filename"],
                task_id=task_id,
                user_id=user_id,
            )
            created_count += 1
        except Exception as e:
            print(f"  ❌ 創建失敗: {file_info['filename']} - {e}")

    return created_count


def main():
    parser = argparse.ArgumentParser(description="修補任務的 file_metadata 記錄")
    parser.add_argument(
        "--task-id",
        type=str,
        help="任務 ID",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="用戶 ID",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="修復所有任務",
    )

    args = parser.parse_args()

    if not args.task_id and not args.all:
        print("錯誤: 請指定 --task-id 或 --all")
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print("🔧 File Metadata 修補工具")
    print("=" * 60)

    try:
        db = get_arangodb_client()
        print(f"✅ 連接到 ArangoDB: {db.name}")
    except Exception as e:
        print(f"❌ 連接 ArangoDB 失敗: {e}")
        sys.exit(1)

    start_time = time.time()

    if args.all:
        # 修復所有任務
        task_collection = get_user_tasks_collection(db)
        tasks = list(task_collection.all())

        print(f"\n📋 找到 {len(tasks)} 個任務")

        total_created = 0
        for task_doc in tasks:
            task_id = task_doc.get("task_id")
            user_id = task_doc.get("user_id")
            created = fix_task_file_metadata(db, task_id, user_id)
            total_created += created

        print(f"\n✅ 完成！共創建 {total_created} 個 file_metadata 記錄")

    else:
        # 修復指定任務
        if not args.user_id:
            print("錯誤: 請提供 --user-id")
            sys.exit(1)

        created = fix_task_file_metadata(db, args.task_id, args.user_id)
        print(f"\n✅ 完成！創建 {created} 個 file_metadata 記錄")

    elapsed_time = time.time() - start_time
    print(f"\n⏱️  耗時: {elapsed_time:.2f} 秒")


if __name__ == "__main__":
    main()
