#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: 按用戶清理所有測試數據（ArangoDB, Qdrant, SeaweedFS）
創建日期: 2026-01-23 10:10 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-23 10:10 UTC+8
"""

import argparse
import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
from arango import ArangoClient
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 專案根目錄
project_root = Path(__file__).resolve().parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# 配置
ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "changeme")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

SEAWEEDFS_HOST = os.getenv("SEAWEEDFS_HOST", "localhost")
SEAWEEDFS_PORT = int(os.getenv("SEAWEEDFS_PORT", "8888"))
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("SEAWEEDFS_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("SEAWEEDFS_SECRET_KEY", "admin123")


def print_header(title: str):
    print(f"\n{'='*20} {title} {'='*20}")


def print_status(message: str, status: str = "INFO"):
    colors = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "DRY_RUN": "\033[95m",  # Magenta
        "END": "\033[0m",
    }
    symbol = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "DRY_RUN": "🔍"}
    print(f"{colors.get(status, '')}{symbol.get(status, '')} {message}{colors['END']}")


def get_user_tasks(db, user_id: str) -> List[Dict[str, Any]]:
    aql = "FOR t IN user_tasks FILTER t.user_id == @user_id RETURN t"
    return list(db.aql.execute(aql, bind_vars={"user_id": user_id}))


def get_user_files(db, user_id: str) -> List[Dict[str, Any]]:
    aql = "FOR f IN file_metadata FILTER f.user_id == @user_id RETURN f"
    return list(db.aql.execute(aql, bind_vars={"user_id": user_id}))


def cleanup_arangodb(user_id: str, dry_run: bool) -> Dict[str, int]:
    print_header("清理 ArangoDB")
    stats = {"user_tasks": 0, "file_metadata": 0, "entities": 0, "relations": 0}

    try:
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)

        # 1. 清理 user_tasks
        tasks = get_user_tasks(db, user_id)
        print_status(f"找到 {len(tasks)} 個任務", "INFO")
        for task in tasks:
            if dry_run:
                print_status(
                    f"[DRY_RUN] 將刪除任務: {task.get('task_id')} ({task.get('title')})", "DRY_RUN"
                )
            else:
                db.collection("user_tasks").delete(task)
            stats["user_tasks"] += 1

        # 2. 清理 file_metadata
        files = get_user_files(db, user_id)
        print_status(f"找到 {len(files)} 個文件元數據", "INFO")
        for f in files:
            if dry_run:
                print_status(
                    f"[DRY_RUN] 將刪除文件: {f.get('file_id')} ({f.get('filename')})", "DRY_RUN"
                )
            else:
                db.collection("file_metadata").delete(f)
            stats["file_metadata"] += 1

        # 3. 清理 entities 和 relations
        collections = ["entities", "relations"]
        for coll_name in collections:
            aql = f"FOR d IN {coll_name} FILTER d.user_id == @user_id RETURN d"
            docs = list(db.aql.execute(aql, bind_vars={"user_id": user_id}))
            print_status(f"找到 {len(docs)} 個 {coll_name} 記錄", "INFO")
            for doc in docs:
                if dry_run:
                    print_status(f"[DRY_RUN] 將刪除 {coll_name}: {doc.get('_key')}", "DRY_RUN")
                else:
                    db.collection(coll_name).delete(doc)
                stats[coll_name] += 1

    except Exception as e:
        print_status(f"ArangoDB 清理失敗: {e}", "ERROR")

    return stats


def cleanup_qdrant(file_ids: List[str], dry_run: bool) -> int:
    print_header("清理 Qdrant")
    deleted_count = 0
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        for file_id in file_ids:
            coll_name = f"file_{file_id}"
            try:
                if dry_run:
                    print_status(f"[DRY_RUN] 將刪除 Qdrant Collection: {coll_name}", "DRY_RUN")
                else:
                    client.delete_collection(coll_name)
                    print_status(f"已刪除 Qdrant Collection: {coll_name}", "SUCCESS")
                deleted_count += 1
            except Exception:
                pass
    except Exception as e:
        print_status(f"Qdrant 清理失敗: {e}", "ERROR")
    return deleted_count


def cleanup_seaweedfs(task_ids: List[str], dry_run: bool) -> int:
    print_header("清理 SeaweedFS")
    deleted_count = 0
    filer_url = f"http://{SEAWEEDFS_HOST}:{SEAWEEDFS_PORT}"

    auth_header = (
        "Basic "
        + base64.b64encode(f"{SEAWEEDFS_ACCESS_KEY}:{SEAWEEDFS_SECRET_KEY}".encode()).decode()
    )

    for task_id in task_ids:
        path = f"/{SEAWEEDFS_BUCKET}/tasks/{task_id}/"
        if dry_run:
            print_status(f"[DRY_RUN] 將刪除 SeaweedFS 目錄: {path}", "DRY_RUN")
            deleted_count += 1
        else:
            try:
                url = f"{filer_url}{path}?recursive=true"
                resp = httpx.delete(url, headers={"Authorization": auth_header})
                if resp.status_code in [200, 204, 404]:
                    print_status(f"已刪除 SeaweedFS 目錄: {path}", "SUCCESS")
                    deleted_count += 1
                else:
                    print_status(f"刪除 SeaweedFS 目錄失敗: {path} ({resp.status_code})", "WARNING")
            except Exception as e:
                print_status(f"SeaweedFS 刪除出錯: {e}", "ERROR")
    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="按用戶清理所有測試數據")
    parser.add_argument("user_id", help="用戶 ID (Email)")
    parser.add_argument("--dry-run", action="store_true", help="預覽要刪除的內容")
    parser.add_argument("--yes", action="store_true", help="直接執行，不詢問")
    args = parser.parse_args()

    user_id = args.user_id
    dry_run = args.dry_run

    if not dry_run and not args.yes:
        confirm = input(f"⚠️ 確定要刪除用戶 {user_id} 的所有數據嗎？(y/N): ")
        if confirm.lower() != "y":
            print("已取消")
            return

    try:
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
        tasks = get_user_tasks(db, user_id)
        files = get_user_files(db, user_id)

        task_ids = [t.get("task_id") for t in tasks if t.get("task_id")]
        file_ids = [f.get("file_id") for f in files if f.get("file_id")]

        print_status(f"分析用戶 {user_id}: {len(task_ids)} 個任務, {len(file_ids)} 個文件", "INFO")

        arango_stats = cleanup_arangodb(user_id, dry_run)
        qdrant_count = cleanup_qdrant(file_ids, dry_run)
        seaweed_count = cleanup_seaweedfs(task_ids, dry_run)

        print_header("清理總結")
        print(f"ArangoDB 任務: {arango_stats['user_tasks']}")
        print(f"ArangoDB 文件: {arango_stats['file_metadata']}")
        print(f"ArangoDB 實體: {arango_stats['entities']}")
        print(f"ArangoDB 關係: {arango_stats['relations']}")
        print(f"Qdrant Collections: {qdrant_count}")
        print(f"SeaweedFS 目錄: {seaweed_count}")

    except Exception as e:
        print_status(f"執行失敗: {e}", "ERROR")


if __name__ == "__main__":
    main()
