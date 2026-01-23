# 代碼功能說明: 清理所有數據庫和存儲
# 創建日期: 2026-01-22
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-22

"""清理所有數據庫和存儲 - 恢復到乾淨狀態"""

import os

# SeaweedFS
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Qdrant
from qdrant_client import QdrantClient

# ArangoDB
from database.arangodb import ArangoDBClient

# 配置
ARANGO_DB = "ai_box_kg"
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = 6333
SEAWEEDFS_HOST = os.getenv("SEAWEEDFS_HOST", "localhost")
SEAWEEDFS_PORT = 8333
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123")


def cleanup_arangodb():
    """清理 ArangoDB 集合"""
    print("🗑️  清理 ArangoDB...")

    client = ArangoDBClient()
    db = client.db

    if db is None:
        print("  ❌ 無法連接到 ArangoDB")
        return False

    collections_to_clear = [
        "file_metadata",
        "entities",
        "relations",
        "user_tasks",
        "folder_metadata",
    ]

    for collection_name in collections_to_clear:
        try:
            if db.has_collection(collection_name):
                collection = db.collection(collection_name)

                # 使用 truncate 清空集合
                try:
                    collection.truncate()
                    print(f"  ✅ {collection_name}: 已清空集合")
                except Exception:
                    # 如果 truncate 失敗，嘗試遍歷刪除
                    try:
                        cursor = db.aql.execute(
                            f"FOR doc IN {collection_name} LIMIT 1000 RETURN doc"
                        )
                        count = 0
                        for doc in cursor:
                            try:
                                # 確保 doc 是字典並包含 _key
                                if isinstance(doc, dict) and "_key" in doc:
                                    collection.delete(doc["_key"])
                                    count += 1
                                elif isinstance(doc, str):
                                    # 如果返回的是字符串，嘗試解析為 JSON
                                    import json

                                    doc_dict = json.loads(doc)
                                    if "_key" in doc_dict:
                                        collection.delete(doc_dict["_key"])
                                        count += 1
                            except Exception as e:
                                pass
                        print(f"  ✅ {collection_name}: 已刪除 {count} 個文檔")
                    except Exception as e:
                        print(f"  ❌ {collection_name}: {e}")
            else:
                print(f"  ✅ {collection_name}: 集合不存在（跳過）")
        except Exception as e:
            print(f"  ❌ {collection_name}: {e}")

    return True


def cleanup_qdrant():
    """清理 Qdrant collections"""
    print("\n🗑️  清理 Qdrant...")

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # 獲取所有 collections
        collections = client.get_collections().collections

        for collection in collections:
            collection_name = collection.name

            # 刪除所有 collection（除了 system collections）
            if not collection_name.startswith("_"):
                try:
                    client.delete_collection(collection_name)
                    print(f"  ✅ 已刪除 collection: {collection_name}")
                except Exception as e:
                    print(f"  ❌ {collection_name}: {e}")

        print("  ✅ Qdrant 清理完成")
        return True
    except Exception as e:
        print(f"  ❌ Qdrant 連接失敗: {e}")
        return False


def cleanup_seaweedfs():
    """清理 SeaweedFS S3 buckets"""
    print("\n🗑️  清理 SeaweedFS S3...")

    try:
        # 連接 SeaweedFS S3
        session = boto3.Session()
        s3 = session.client(
            "s3",
            endpoint_url=f"http://{SEAWEEDFS_HOST}:{SEAWEEDFS_PORT}",
            aws_access_key_id=SEAWEEDFS_ACCESS_KEY,
            aws_secret_access_key=SEAWEEDFS_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )

        # 列出並刪除 bucket 中的所有對象
        try:
            paginator = s3.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=SEAWEEDFS_BUCKET):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        try:
                            s3.delete_object(Bucket=SEAWEEDFS_BUCKET, Key=obj["Key"])
                            print(f"  🗑️  刪除: {obj['Key']}")
                        except Exception:
                            pass

            print(f"  ✅ SeaweedFS S3 bucket ({SEAWEEDFS_BUCKET}) 已清理")

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchBucket":
                print(f"  ✅ Bucket ({SEAWEEDFS_BUCKET}) 不存在")
            elif e.response["Error"]["Code"] == "NoSuchKey":
                print(f"  ✅ Bucket ({SEAWEEDFS_BUCKET}) 已是空")
            else:
                raise

        return True
    except Exception as e:
        print(f"  ❌ SeaweedFS S3 錯誤: {e}")
        return False


def cleanup_local_files():
    """清理本地文件（如果有）"""
    print("\n🗑️  清理本地文件...")

    local_paths = [
        "data/tasks",
        "data/uploads",
    ]

    for path in local_paths:
        if os.path.exists(path):
            import shutil

            try:
                shutil.rmtree(path)
                print(f"  ✅ 已刪除: {path}")
            except Exception as e:
                print(f"  ❌ {path}: {e}")
        else:
            print(f"  ✅ {path}: 不存在")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="AI-Box 數據清理工具")
    parser.add_argument("--force", action="store_true", help="跳過確認直接執行（危險！）")
    args = parser.parse_args()

    print("=" * 60)
    print("AI-Box 數據清理工具")
    print("=" * 60)

    if not args.force:
        # 確認
        print("\n⚠️  警告：此操作將清除以下數據：")
        print("  - ArangoDB: file_metadata, entities, relations, user_tasks, folder_metadata")
        print("  - Qdrant: 所有 collections")
        print("  - SeaweedFS S3: bucket-ai-box-assets 中的所有文件")

        confirm = input("\n確定要繼續嗎？(輸入 DELETE 確認): ")

        if confirm != "DELETE":
            print("\n❌ 已取消")
            return
    else:
        print("\n⚠️  強制模式：直接清除所有數據")

    print("\n" + "=" * 60)

    # 執行清理
    cleanup_arangodb()
    cleanup_qdrant()
    cleanup_seaweedfs()
    cleanup_local_files()

    print("\n" + "=" * 60)
    print("✅ 數據清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
