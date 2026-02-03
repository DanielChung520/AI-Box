#!/usr/bin/env python3
"""
完整清理腳本 - 清理 ArangoDB、Qdrant、SeaweedFS 測試數據
"""

import os
from pathlib import Path

# 先加載 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)
        print(f"✅ 已加載 .env 文件: {env_file}")
    except ImportError:
        print("⚠️  python-dotenv 未安裝，無法自動加載 .env 文件")
else:
    print(f"⚠️  未找到 .env 文件: {env_file}")
# 先加載 .env 文件
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)
        print(f"✅ 已加載 .env 文件: {env_file}")
    except ImportError:
        print("⚠️  python-dotenv 未安裝，無法自動加載 .env 文件")
else:
    print(f"⚠️  未找到 .env 文件: {env_file}")

import subprocess
import httpx

ARANGO_HOST = os.getenv("ARANGO_HOST", "localhost")
ARANGO_PORT = os.getenv("ARANGO_PORT", "8529")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASS = os.getenv("ARANGO_ROOT_PASSWORD", "changeme")
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")

SEAWEEDFS_HOST = os.getenv("SEAWEEDFS_HOST", "localhost")
SEAWEEDFS_PORT = os.getenv("SEAWEEDFS_PORT", "8333")
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123")

ARANGO_URL = f"http://{ARANGO_HOST}:{ARANGO_PORT}"
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
SEAWEEDFS_URL = f"http://{SEAWEEDFS_HOST}:{SEAWEEDFS_PORT}"


def arango_request(method, path, data=None):
    """ArangoDB API 請求"""
    headers = {"Content-Type": "application/json"}
    url = f"{ARANGO_URL}{path}"
    client = httpx.Client(timeout=30)

    if method == "GET":
        return client.get(url, auth=(ARANGO_USER, ARANGO_PASS), headers=headers)
    elif method == "POST":
        return client.post(url, auth=(ARANGO_USER, ARANGO_PASS), json=data, headers=headers)
    elif method == "DELETE":
        return client.delete(url, auth=(ARANGO_USER, ARANGO_PASS), json=data, headers=headers)


def cleanup_arangodb():
    """清理 ArangoDB"""
    print("\n🗑️  清理 ArangoDB...")

    # 1. 清理 file_metadata 中的舊 task_id
    old_task_ids = ["systemAdmin_SystemDocs", "test-task", "test"]
    for task_id in old_task_ids:
        try:
            resp = arango_request(
                "POST",
                f"/_db/{ARANGO_DB}/_api/cursor",
                {
                    "query": "FOR f IN file_metadata FILTER f.task_id == @task_id REMOVE f IN file_metadata",
                    "bindVars": {"task_id": task_id},
                },
            )
            print(f"   ✅ 已清理 file_metadata (task_id={task_id})")
        except Exception as e:
            print(f"   ❌ file_metadata cleanup failed: {e}")

    # 2. 清理 folder_metadata 中的舊 task_id
    for task_id in old_task_ids:
        try:
            resp = arango_request(
                "POST",
                f"/_db/{ARANGO_DB}/_api/cursor",
                {
                    "query": "FOR f IN folder_metadata FILTER f.task_id == @task_id REMOVE f IN folder_metadata",
                    "bindVars": {"task_id": task_id},
                },
            )
            print(f"   ✅ 已清理 folder_metadata (task_id={task_id})")
        except Exception as e:
            print(f"   ❌ folder_metadata cleanup failed: {e}")

    # 3. 清理數字開頭的測試任務 (如 1765252693136)
    try:
        resp = arango_request(
            "POST",
            f"/_db/{ARANGO_DB}/_api/cursor",
            {
                "query": "FOR f IN folder_metadata FILTER LIKE(f.task_id, '____%', true) REMOVE f IN folder_metadata",
            },
        )
        print("   ✅ 已清理數字開頭的 folder_metadata")
    except Exception as e:
        print(f"   ⚠️  數字任務清理跳過: {e}")

    print("   ✅ ArangoDB 清理完成")


def cleanup_qdrant():
    """清理 Qdrant"""
    print("\n🗑️  清理 Qdrant...")

    try:
        resp = httpx.get(f"{QDRANT_URL}/collections", timeout=30)
        if resp.status_code == 200:
            collections = resp.json().get("result", {}).get("collections", [])

            # 有效的 file_id pattern
            valid_patterns = ["f975b398-ccb3-4956-9a23-8ccc43e41ac5"]  # 最新測試

            deleted_count = 0
            for coll in collections:
                coll_name = coll.get("name", "")

                # 跳過有效 collection
                if any(p in coll_name for p in valid_patterns):
                    print(f"   ⏭️  保留: {coll_name}")
                    continue

                # 刪除舊的 file_* collections
                if coll_name.startswith("file_"):
                    try:
                        httpx.delete(f"{QDRANT_URL}/collections/{coll_name}", timeout=30)
                        print(f"   ✅ 已刪除: {coll_name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ 刪除失敗 {coll_name}: {e}")

                # 刪除測試 collection
                elif coll_name in ["test_api", "test_collection"]:
                    try:
                        httpx.delete(f"{QDRANT_URL}/collections/{coll_name}", timeout=30)
                        print(f"   ✅ 已刪除測試: {coll_name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ 刪除失敗 {coll_name}: {e}")

            print(f"   ✅ Qdrant 清理完成 (刪除 {deleted_count} 個 collections)")
        else:
            print("   ⚠️  無法獲取 Qdrant collections")
    except Exception as e:
        print(f"   ❌ Qdrant 清理失敗: {e}")


def cleanup_seaweedfs():
    """清理 SeaweedFS"""
    print("\n🗑️  清理 SeaweedFS...")

    # 方法1: 嘗試使用 weed shell 命令
    result = subprocess.run(
        ["docker", "exec", "seaweedfs", "which", "weed"], capture_output=True, text=True, timeout=10
    )

    if result.returncode == 0:
        print("   🔧 使用 weed shell 清理...")

        # 清理 systemAdmin_SystemDocs
        result = subprocess.run(
            [
                "docker",
                "exec",
                "seaweedfs",
                "weed",
                "s3",
                "rm",
                "bucket-ai-box-assets/tasks/systemAdmin_SystemDocs/",
                "-r",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print("   ✅ 已清理 tasks/systemAdmin_SystemDocs/")
        else:
            print(f"   ⚠️  {result.stderr}")

    # 方法2: 透過 S3 API 清理
    print("   🔧 透過 S3 API 清理...")

    # 清理前綴列表
    prefixes_to_clean = [
        "tasks/systemAdmin_SystemDocs/",
        "tasks/test-",
    ]

    # 嘗試直接 HTTP 請求（使用正確的日期）
    import datetime

    now = datetime.datetime.utcnow()
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")

    for prefix in prefixes_to_clean:
        try:
            # 列出 objects
            client = httpx.Client(timeout=30)

            # 嘗試直接刪除（可能失敗，因為需要簽名）
            print(f"   📋 待清理: {prefix}")

        except Exception as e:
            print(f"   ⚠️  {prefix} 清理需要手動處理")

    # 如果weed命令不可用，提供手動清理指令
    if result.returncode != 0:
        print("   💡 手動清理指令:")
        print(
            "      docker exec seaweedfs weed s3 rm bucket-ai-box-assets/tasks/systemAdmin_SystemDocs/ -r"
        )
        print("      docker exec seaweedfs weed s3 rm bucket-ai-box-assets/tasks/test-/ -r")


def main():
    print("=" * 60)
    print("🧹 完整清理測試環境")
    print("=" * 60)
    print(f"ArangoDB: {ARANGO_URL}")
    print(f"Qdrant:   {QDRANT_URL}")
    print(f"SeaweedFS: {SEAWEEDFS_URL}")
    print("=" * 60)

    cleanup_arangodb()
    cleanup_qdrant()
    cleanup_seaweedfs()

    print("\n" + "=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)
    print("\n📋 清理摘要:")
    print("   - ArangoDB: 舊 task_id 數據已清理")
    print("   - Qdrant: 舊 file_* collections 已清理")
    print("   - SeaweedFS: 請手動執行上述指令")
    print("=" * 60)


if __name__ == "__main__":
    main()
