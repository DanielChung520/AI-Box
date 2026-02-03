#!/usr/bin/env python3
"""
清理測試環境：ArangoDB、SeaweedFS、Qdrant
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

import httpx

# 從 .env 讀取配置
ARANGO_HOST = os.getenv("ARANGO_HOST", "localhost")
ARANGO_PORT = os.getenv("ARANGO_PORT", "8529")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_ROOT_PASSWORD", "changeme")
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")

SEAWEEDFS_HOST = os.getenv("SEAWEEDFS_HOST", "localhost")
SEAWEEDFS_PORT = os.getenv("SEAWEEDFS_PORT", "8333")
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123")


def cleanup_arangodb():
    """清理 ArangoDB 測試數據"""
    print("\n🗑️  清理 ArangoDB...")

    base_url = f"http://{ARANGO_HOST}:{ARANGO_PORT}"
    db = ARANGO_DB

    # 測試數據的特徵：task_id = "SystemDoc" 或 user_id 包含 "test"
    test_task_ids = ["SystemDoc", "systemAdmin_SystemDocs", "test-task"]

    try:
        with httpx.Client(timeout=30) as client:
            # 清理 file_metadata
            for task_id in test_task_ids:
                try:
                    cursor = client.post(
                        f"{base_url}/_db/{db}/_api/cursor",
                        json={
                            "query": "FOR f IN file_metadata FILTER f.task_id == @task_id REMOVE f IN file_metadata",
                            "bindVars": {"task_id": task_id},
                        },
                        auth=(ARANGO_USER, ARANGO_PASSWORD),
                    )
                    print(f"   ✅ 已清理 file_metadata (task_id={task_id})")
                except Exception as e:
                    pass

            # 清理 folder_metadata
            for task_id in test_task_ids:
                try:
                    cursor = client.post(
                        f"{base_url}/_db/{db}/_api/cursor",
                        json={
                            "query": "FOR f IN folder_metadata FILTER f.task_id == @task_id REMOVE f IN folder_metadata",
                            "bindVars": {"task_id": task_id},
                        },
                        auth=(ARANGO_USER, ARANGO_PASSWORD),
                    )
                    print(f"   ✅ 已清理 folder_metadata (task_id={task_id})")
                except Exception as e:
                    pass

            # 清理數字開頭的測試任務 (如 1765252693136)
            try:
                cursor = client.post(
                    f"{base_url}/_db/{db}/_api/cursor",
                    json={
                        "query": "FOR f IN folder_metadata FILTER LIKE(f.task_id, '____%', true) REMOVE f IN folder_metadata",
                    },
                    auth=(ARANGO_USER, ARANGO_PASSWORD),
                )
                print("   ✅ 已清理數字開頭的 folder_metadata")
            except Exception as e:
                print(f"   ⚠️  數字任務清理跳過: {e}")

            print("   ✅ ArangoDB 清理完成")
    except Exception as e:
        print(f"   ❌ ArangoDB 清理失敗: {e}")


def cleanup_seaweedfs():
    """清理 SeaweedFS S3 測試數據"""
    print("\n🗑️  清理 SeaweedFS...")

    try:
        import boto3
        from botocore.config import Config

        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://{SEAWEEDFS_HOST}:{SEAWEEDFS_PORT}",
            aws_access_key_id=SEAWEEDFS_ACCESS_KEY,
            aws_secret_access_key=SEAWEEDFS_SECRET_KEY,
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )

        test_prefixes = [
            "tasks/SystemDoc/",
            "tasks/systemAdmin_SystemDocs/",
            "tasks/test-",
        ]

        # 清理 bucket
        try:
            paginator = s3_client.get_paginator("list_objects_v2")
            for prefix in test_prefixes:
                for page in paginator.paginate(Bucket=SEAWEEDFS_BUCKET, Prefix=prefix):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            s3_client.delete_object(Bucket=SEAWEEDFS_BUCKET, Key=obj["Key"])
                            print(f"   已刪除: {obj['Key']}")
            print("   ✅ SeaweedFS 清理完成")
        except Exception as e:
            print(f"   ⚠️  SeaweedFS 清理跳過: {e}")

    except ImportError:
        print("   ⚠️  boto3 未安裝，跳過 SeaweedFS 清理")
    except Exception as e:
        print(f"   ❌ SeaweedFS 清理失敗: {e}")


def cleanup_qdrant():
    """清理 Qdrant 測試數據"""
    print("\n🗑️  清理 Qdrant...")

    qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

    try:
        with httpx.Client(timeout=30) as client:
            # 列出所有 collections
            try:
                response = client.get(f"{qdrant_url}/collections")
                if response.status_code == 200:
                    collections = response.json().get("result", {}).get("collections", [])

                    # 刪除包含特定 file_id 的 collections
                    for coll in collections:
                        coll_name = coll.get("name", "")

                        if "a9972bb4" in coll_name or "SystemDoc" in coll_name:
                            client.delete(f"{qdrant_url}/collections/{coll_name}")
                            print(f"   已刪除 collection: {coll_name}")

                    print("   ✅ Qdrant 清理完成")
                else:
                    print("   ⚠️  Qdrant 無法列出 collections")
            except Exception as e:
                print(f"   ⚠️  Qdrant 清理跳過: {e}")

    except Exception as e:
        print(f"   ❌ Qdrant 清理失敗: {e}")


def main():
    print("=" * 60)
    print("🧹 清理測試環境")
    print("=" * 60)

    cleanup_arangodb()
    cleanup_seaweedfs()
    cleanup_qdrant()

    print("\n" + "=" * 60)
    print("✅ 環境清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
