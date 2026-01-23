#!/usr/bin/env python3
"""
清理測試環境：ArangoDB、SeaweedFS、Qdrant
"""


import httpx


def cleanup_arangodb():
    """清理 ArangoDB 測試數據"""
    print("\n🗑️  清理 ArangoDB...")

    base_url = "http://localhost:8529"
    db = "ai_box_kg"

    # 測試數據的特徵：task_id = "SystemDoc" 或 user_id 包含 "test"
    test_task_ids = ["SystemDoc", "systemAdmin_SystemDocs", "test-task"]

    try:
        with httpx.Client(timeout=30) as client:
            # 清理 file_metadata
            for task_id in test_task_ids:
                try:
                    # 查找並刪除該任務的 file_metadata
                    cursor = client.post(
                        f"{base_url}/_db/{db}/_api/cursor",
                        json={
                            "query": "FOR f IN file_metadata FILTER f.task_id == @task_id REMOVE f IN file_metadata",
                            "bindVars": {"task_id": task_id},
                        },
                    )
                    print(f"   已清理 file_metadata (task_id={task_id})")
                except Exception as e:
                    pass

            # 清理 entities (通過 file_id)
            for task_id in test_task_ids:
                try:
                    cursor = client.post(
                        f"{base_url}/_db/{db}/_api/cursor",
                        json={
                            "query": """
                            FOR f IN file_metadata FILTER f.task_id == @task_id
                            FOR e IN entities FILTER e.file_id == f._key
                            REMOVE e IN entities
                            """,
                            "bindVars": {"task_id": task_id},
                        },
                    )
                    print(f"   已清理 entities (task_id={task_id})")
                except Exception as e:
                    pass

            # 清理 relations (通過 file_id)
            for task_id in test_task_ids:
                try:
                    cursor = client.post(
                        f"{base_url}/_db/{db}/_api/cursor",
                        json={
                            "query": """
                            FOR f IN file_metadata FILTER f.task_id == @task_id
                            FOR r IN relations FILTER r.file_id == f._key
                            REMOVE r IN relations
                            """,
                            "bindVars": {"task_id": task_id},
                        },
                    )
                    print(f"   已清理 relations (task_id={task_id})")
                except Exception as e:
                    pass

            print("   ✅ ArangoDB 清理完成")
    except Exception as e:
        print(f"   ❌ ArangoDB 清理失敗: {e}")


def cleanup_seaweedfs():
    """清理 SeaweedFS S3 測試數據"""
    print("\n🗑️  清理 SeaweedFS...")

    s3_endpoint = "http://localhost:8333"
    test_prefixes = [
        "tasks/SystemDoc/",
        "tasks/systemAdmin_SystemDocs/",
        "tasks/test-",
    ]

    try:
        import boto3
        from botocore.config import Config

        s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id="admin",
            aws_secret_access_key="admin",
            region_name="us-east-1",
            config=Config(signature_version="s3v4"),
        )

        # 清理 bucket-ai-box-assets
        try:
            paginator = s3_client.get_paginator("list_objects_v2")
            for prefix in test_prefixes:
                for page in paginator.paginate(Bucket="bucket-ai-box-assets", Prefix=prefix):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            s3_client.delete_object(Bucket="bucket-ai-box-assets", Key=obj["Key"])
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

    qdrant_url = "http://localhost:6333"

    try:
        with httpx.Client(timeout=30) as client:
            # 列出所有 collections
            try:
                response = client.get(f"{qdrant_url}/collections")
                if response.status_code == 200:
                    collections = response.json().get("result", {}).get("collections", [])

                    # 刪除包含 file_id 的 collections
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
