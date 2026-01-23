#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: SystemDocs 測試數據清理腳本
創建日期: 2026-01-21
創建人: Daniel Chung

功能:
- 清理 ArangoDB 的 user_tasks、file_metadata、entities、relations
- 清理 Qdrant 的相關 collections
- 清理 SeaWeedFS 的 tasks/SystemDocs/ 文件

使用場景:
- 第三階段批量測試前清理
- 第四階段完整處理前清理
- 每次重新測試時清理

使用方法:
    python3 scripts/cleanup_test_data.py [--dry-run]

示例:
    # 預覽要刪除的內容（不實際刪除）
    python3 scripts/cleanup_test_data.py --dry-run

    # 執行清理（需要確認）
    python3 scripts/cleanup_test_data.py
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import httpx
from arango import ArangoClient
from qdrant_client import QdrantClient

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 專案根目錄
BASE_DIR = Path(__file__).resolve().parent.parent

# 任務配置（可通過環境變數覆蓋）
TASK_ID = os.getenv("TEST_TASK_ID", "SystemDocs")
USER_ID = os.getenv("TEST_USER_ID", "systemAdmin")

# ArangoDB 配置
ARANGO_HOST = os.getenv("ARANGO_HOST", "http://localhost:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")
ARANGO_USERNAME = os.getenv("ARANGO_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "changeme")

# Qdrant 配置
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# SeaweedFS 配置
SEAWEEDFS_HOST = os.getenv("SEAWEEDFS_HOST", "localhost")
SEAWEEDFS_PORT = int(os.getenv("SEAWEEDFS_PORT", "8888"))
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("SEAWEEDFS_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("SEAWEEDFS_SECRET_KEY", "admin123")


def print_header(title: str) -> None:
    """打印標題"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_status(message: str, status: str = "INFO") -> None:
    """打印狀態信息"""
    status_symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "DRY_RUN": "🔍",
    }
    symbol = status_symbols.get(status, "ℹ️")
    print(f"{symbol} {message}")


def cleanup_arangodb() -> Dict[str, int]:
    """清理 ArangoDB 數據"""
    print_header("清理 ArangoDB")

    stats = {"user_tasks": 0, "file_metadata": 0, "entities": 0, "relations": 0}

    try:
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)

        # 1. 清理 user_tasks
        try:
            coll = db.collection("user_tasks")
            cursor = db.aql.execute(
                "FOR t IN user_tasks FILTER t.task_id == @task_id RETURN t",
                bind_vars={"task_id": TASK_ID},
            )
            docs = list(cursor)
            if docs:
                for doc in docs:
                    coll.delete(doc)
                    stats["user_tasks"] += 1
                print_status(f"已刪除 {len(docs)} 個 user_tasks 記錄", "SUCCESS")
            else:
                print_status("無 user_tasks 記錄需要清理", "INFO")
        except Exception as e:
            print_status(f"清理 user_tasks 失敗: {e}", "WARNING")

        # 2. 清理 file_metadata
        try:
            coll = db.collection("file_metadata")
            cursor = db.aql.execute(
                "FOR f IN file_metadata FILTER f.task_id == @task_id RETURN f",
                bind_vars={"task_id": TASK_ID},
            )
            docs = list(cursor)
            file_ids = [doc["_key"] for doc in docs]
            if docs:
                for doc in docs:
                    coll.delete(doc)
                    stats["file_metadata"] += 1
                print_status(f"已刪除 {len(docs)} 個 file_metadata 記錄", "SUCCESS")
            else:
                print_status("無 file_metadata 記錄需要清理", "INFO")
        except Exception as e:
            print_status(f"清理 file_metadata 失敗: {e}", "WARNING")

        # 3. 清理 entities
        try:
            coll = db.collection("entities")
            cursor = db.aql.execute(
                "FOR e IN entities FILTER e.task_id == @task_id RETURN e",
                bind_vars={"task_id": TASK_ID},
            )
            docs = list(cursor)
            if docs:
                for doc in docs:
                    coll.delete(doc)
                    stats["entities"] += 1
                print_status(f"已刪除 {len(docs)} 個 entities 記錄", "SUCCESS")
            else:
                print_status("無 entities 記錄需要清理", "INFO")
        except Exception as e:
            print_status(f"清理 entities 失敗: {e}", "WARNING")

        # 4. 清理 relations
        try:
            coll = db.collection("relations")
            cursor = db.aql.execute(
                "FOR r IN relations FILTER r.task_id == @task_id RETURN r",
                bind_vars={"task_id": TASK_ID},
            )
            docs = list(cursor)
            if docs:
                for doc in docs:
                    coll.delete(doc)
                    stats["relations"] += 1
                print_status(f"已刪除 {len(docs)} 個 relations 記錄", "SUCCESS")
            else:
                print_status("無 relations 記錄需要清理", "INFO")
        except Exception as e:
            print_status(f"清理 relations 失敗: {e}", "WARNING")

    except Exception as e:
        print_status(f"ArangoDB 連接失敗: {e}", "ERROR")

    return stats


def cleanup_qdrant() -> int:
    """清理 Qdrant collections"""
    print_header("清理 Qdrant")

    deleted_count = 0

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = client.get_collections()

        for coll in collections.collections:
            # 刪除以 file_ 開頭且包含 task_id 相關標識的 collections
            if coll.name.startswith("file_"):
                try:
                    # 檢查是否屬於當前任務
                    # 通過 collection 名稱判斷（file_id 是 UUID，通常包含文件標識）
                    # 這裡我們刪除所有 file_* collections（風險較高，請謹慎使用）
                    # 更好的做法是根據 file_metadata 中的 file_id 來刪除

                    # 方案：獲取所有 file_metadata，根據 file_id 刪除對應的 collections
                    client.delete_collection(coll.name)
                    deleted_count += 1
                    print_status(f"已刪除 Collection: {coll.name}", "SUCCESS")
                except Exception as e:
                    print_status(f"刪除 Collection {coll.name} 失敗: {e}", "WARNING")

        if deleted_count == 0:
            print_status("無 file_* collections 需要清理", "INFO")

    except Exception as e:
        print_status(f"Qdrant 連接失敗: {e}", "ERROR")

    return deleted_count


def cleanup_qdrant_by_file_ids(file_ids: List[str]) -> int:
    """根據 file_ids 清理 Qdrant collections（更精確的清理）"""
    print_header("清理 Qdrant（按 File IDs）")

    deleted_count = 0

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = client.get_collections()

        for file_id in file_ids:
            coll_name = f"file_{file_id}"
            for coll in collections.collections:
                if coll.name == coll_name:
                    try:
                        client.delete_collection(coll.name)
                        deleted_count += 1
                        print_status(f"已刪除 Collection: {coll.name}", "SUCCESS")
                    except Exception as e:
                        print_status(f"刪除 Collection {coll.name} 失敗: {e}", "WARNING")
                    break

        if deleted_count == 0:
            print_status("無匹配的 collections 需要清理", "INFO")

    except Exception as e:
        print_status(f"Qdrant 連接失敗: {e}", "ERROR")

    return deleted_count


def get_file_ids_from_arangodb() -> List[str]:
    """從 ArangoDB 獲取指定 task_id 的 file_ids"""
    try:
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)

        cursor = db.aql.execute(
            "FOR f IN file_metadata FILTER f.task_id == @task_id RETURN f._key",
            bind_vars={"task_id": TASK_ID},
        )
        return list(cursor)
    except Exception as e:
        print_status(f"獲取 file_ids 失敗: {e}", "ERROR")
        return []


def cleanup_seaweedfs() -> Dict[str, int]:
    """清理 SeaweedFS 文件"""
    print_header("清理 SeaweedFS")

    stats = {"deleted": 0, "errors": 0}

    # 構建 Filer API URL
    filer_url = f"http://{SEAWEEDFS_HOST}:{SEAWEEDFS_PORT}"

    # 目標路徑：/bucket-ai-box-assets/tasks/SystemDocs/
    base_path = f"/{SEAWEEDFS_BUCKET}/tasks/{TASK_ID}/"

    try:
        # 列出目錄內容
        url = f"{filer_url}{base_path}?format=json"
        import base64

        auth_header = (
            "Basic "
            + base64.b64encode(f"{SEAWEEDFS_ACCESS_KEY}:{SEAWEEDFS_SECRET_KEY}".encode()).decode()
        )

        req = httpx.Request("GET", url, headers={"Authorization": auth_header})
        client = httpx.Client()
        response = client.send(req)

        if response.status_code == 404:
            print_status(f"路徑不存在: {base_path}", "INFO")
            return stats

        if response.status_code != 200:
            print_status(f"無法訪問 SeaweedFS: {response.status_code}", "ERROR")
            return stats

        entries = response.json().get("entries", [])

        if not entries:
            print_status(f"目錄為空: {base_path}", "INFO")
            return stats

        # 遞歸刪除文件
        def delete_recursive(entries, base):
            deleted = 0
            errors = 0
            for entry in entries:
                full_path = entry.get("FullPath", "")
                is_dir = entry.get("IsDir", False)

                if is_dir:
                    sub_deleted, sub_errors = delete_recursive(
                        entry.get("SubEntries", []), full_path
                    )
                    deleted += sub_deleted
                    errors += sub_errors
                else:
                    # 刪除文件
                    delete_url = f"{filer_url}{full_path}"
                    delete_req = httpx.Request(
                        "DELETE", delete_url, headers={"Authorization": auth_header}
                    )
                    try:
                        delete_response = client.send(delete_req)
                        if delete_response.status_code in [200, 202, 204]:
                            deleted += 1
                            print_status(f"已刪除: {full_path}", "SUCCESS")
                        else:
                            errors += 1
                            print_status(f"刪除失敗: {full_path}", "ERROR")
                    except Exception as e:
                        errors += 1
                        print_status(f"刪除異常: {full_path} - {e}", "ERROR")
            return deleted, errors

        stats["deleted"], stats["errors"] = delete_recursive(entries, base_path)

    except Exception as e:
        print_status(f"SeaweedFS 清理失敗: {e}", "ERROR")

    return stats


def dry_run_cleanup() -> None:
    """預覽清理內容（不實際刪除）"""
    print_header("🔍 預覽清理內容（DRY RUN）")

    print_status(f"即將清理以下內容（任務: {TASK_ID}）", "DRY_RUN")
    print(f"\n{'=' * 60}")

    # ArangoDB 預覽
    print_status("ArangoDB 將清理的數據：", "DRY_RUN")
    try:
        client = ArangoClient(hosts=ARANGO_HOST)
        db = client.db(ARANGO_DB, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)

        collections = ["user_tasks", "file_metadata", "entities", "relations"]
        for coll_name in collections:
            try:
                cursor = db.aql.execute(
                    f"FOR d IN {coll_name} FILTER d.task_id == @task_id RETURN d",
                    bind_vars={"task_id": TASK_ID},
                )
                count = len(list(cursor))
                print(f"  - {coll_name}: {count} 筆")
            except Exception:
                print(f"  - {coll_name}: 無法查詢")

    except Exception as e:
        print(f"  無法連接 ArangoDB: {e}")

    print()

    # Qdrant 預覽
    print_status("Qdrant 將清理的 Collections：", "DRY_RUN")
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        collections = client.get_collections()

        file_collections = [c for c in collections.collections if c.name.startswith("file_")]
        for coll in file_collections:
            print(f"  - {coll.name}")
        print(f"  共 {len(file_collections)} 個 collections")

    except Exception as e:
        print(f"  無法連接 Qdrant: {e}")

    print()

    # SeaweedFS 預覽
    print_status("SeaweedFS 將清理的路徑：", "DRY_RUN")
    print(f"  /{SEAWEEDFS_BUCKET}/tasks/{TASK_ID}/")

    print(f"\n{'=' * 60}")
    print_status("以上為預覽內容，實際執行時會進行刪除", "DRY_RUN")


def execute_cleanup(dry_run: bool = False) -> None:
    """執行清理"""
    if dry_run:
        dry_run_cleanup()
        return

    print_header("執行清理")

    # 獲取 file_ids（用於精確清理 Qdrant）
    file_ids = get_file_ids_from_arangodb()
    print_status(f"找到 {len(file_ids)} 個 file_ids 需要清理", "INFO")

    # 1. 清理 ArangoDB
    arango_stats = cleanup_arangodb()

    # 2. 清理 Qdrant（按 file_ids）
    qdrant_count = cleanup_qdrant_by_file_ids(file_ids)

    # 3. 清理 SeaweedFS
    seaweed_stats = cleanup_seaweedfs()

    # 打印摘要
    print_header("清理摘要")

    print("\n📦 ArangoDB:")
    for coll_name, count in arango_stats.items():
        print(f"  - {coll_name}: {count} 筆")

    print("\n🔢 Qdrant:")
    print(f"  - Collections: {qdrant_count} 個")

    print("\n🌊 SeaweedFS:")
    print(f"  - 已刪除: {seaweed_stats['deleted']} 個文件")
    if seaweed_stats["errors"] > 0:
        print(f"  - 失敗: {seaweed_stats['errors']} 個")

    print(f"\n{'=' * 60}")
    print_status("清理完成！", "SUCCESS")


def confirm_cleanup() -> bool:
    """確認清理操作"""
    print("\n" + "=" * 80)
    print("⚠️  警告：即將清理測試數據 ⚠️")
    print("=" * 80)
    print(f"\n任務 ID: {TASK_ID}")
    print(f"用戶 ID: {USER_ID}")
    print("\n此操作將刪除：")
    print("  - ArangoDB: user_tasks, file_metadata, entities, relations")
    print("  - Qdrant: 所有 file_* collections")
    print(f"  - SeaweedFS: /{SEAWEEDFS_BUCKET}/tasks/{TASK_ID}/")
    print("\n此操作不可逆！")
    print("=" * 80)

    response = input("\n確認執行清理? (yes/no): ")
    return response.lower() == "yes"


def main() -> int:
    """主函數"""
    parser = argparse.ArgumentParser(
        description="SystemDocs 測試數據清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 預覽清理內容（不刪除）
  python3 scripts/cleanup_test_data.py --dry-run

  # 執行清理（需要確認）
  python3 scripts/cleanup_test_data.py

  # 直接執行（不詢問，危險！）
  python3 scripts/cleanup_test_data.py --yes
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅預覽，不實際刪除",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳過確認直接執行（危險操作）",
    )

    args = parser.parse_args()

    print_header("SystemDocs 測試數據清理")
    print(f"任務 ID: {TASK_ID}")
    print(f"用戶 ID: {USER_ID}")

    # 預覽模式
    if args.dry_run:
        execute_cleanup(dry_run=True)
        return 0

    # 確認
    if not args.yes:
        if not confirm_cleanup():
            print("已取消")
            return 0

    # 執行清理
    execute_cleanup(dry_run=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
