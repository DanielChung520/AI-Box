# 代碼功能說明: 清理測試數據和存儲
# 創建日期: 2026-01-22
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

"""清理測試數據和存儲 - 支持按 task_id 清理"""

import argparse
import os
from pathlib import Path

# 先加載 .env 文件（在導入其他模組之前）
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"

if env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(env_file, override=True)
    print(f"✅ 已加載 .env 文件: {env_file}")
else:
    print(f"⚠️  未找到 .env 文件: {env_file}")

# SeaweedFS
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Qdrant
from qdrant_client import QdrantClient

# ArangoDB
from database.arangodb import ArangoDBClient

# 配置
ARANGO_DB = os.getenv("ARANGO_DB", "ai_box_kg")
ARANGO_HOST = os.getenv("ARANGODB_HOST", "localhost")
ARANGO_PORT = int(os.getenv("ARANGODB_PORT", "8529"))
ARANGO_USER = os.getenv("ARANGODB_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGODB_PASSWORD", "ai_box_arangodb_password")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

SEAWEEDFS_ENDPOINT = os.getenv("AI_BOX_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8333")
SEAWEEDFS_BUCKET = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
SEAWEEDFS_ACCESS_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123")

# 從 endpoint 解析 host 和 port
try:
    SEAWEEDFS_HOST = SEAWEEDFS_ENDPOINT.replace("http://", "").split(":")[0]
    SEAWEEDFS_PORT = int(SEAWEEDFS_ENDPOINT.replace("http://", "").split(":")[1])
except:
    SEAWEEDFS_HOST = "localhost"
    SEAWEEDFS_PORT = 8333


def cleanup_arangodb(task_ids: list = None):
    """清理 ArangoDB 集合

    Args:
        task_ids: 可選，按 task_id 清理（只清理相關的 user_tasks 和 file_metadata）
                 如果為 None，則清空所有集合
    """
    print("🗑️  清理 ArangoDB...")

    client = ArangoDBClient()
    db = client.db

    if db is None:
        print("  ❌ 無法連接到 ArangoDB")
        return False

    if task_ids:
        print(f"  按任務清理: {len(task_ids)} 個 task_id")

    # 始終清理 entities 和 relations（知識圖譜數據）
    collections_to_clear = ["entities", "relations"]

    # 如果沒有指定 task_ids，則清空所有集合
    if not task_ids:
        collections_to_clear.extend(
            [
                "file_metadata",
                "user_tasks",
                "folder_metadata",
            ]
        )
        print("  清空模式: 將清空所有集合")
    else:
        # 如果有指定 task_ids，也要清理 file_metadata 和 user_tasks
        collections_to_clear.extend(
            [
                "file_metadata",
                "user_tasks",
            ]
        )
        print("  按任務清理模式: 將清理相關集合")

    for collection_name in collections_to_clear:
        try:
            if db.has_collection(collection_name):
                collection = db.collection(collection_name)

                if task_ids and collection_name in ["file_metadata", "user_tasks"]:
                    # 按任務清理模式：只刪除相關的文檔
                    query = f"FOR doc IN {collection_name} "
                    if collection_name == "user_tasks":
                        query += f"FILTER doc._key IN @task_ids RETURN doc"
                    elif collection_name == "file_metadata":
                        query += f"FILTER doc.task_id IN @task_ids RETURN doc"

                    cursor = db.aql.execute(query, bind_vars={"task_ids": task_ids})
                    deleted_count = 0

                    for doc in cursor:
                        try:
                            if isinstance(doc, dict) and "_key" in doc:
                                collection.delete(doc["_key"])
                                deleted_count += 1
                        except Exception as e:
                            print(f"    ❌ 刪除失敗: {e}")

                    print(f"  ✅ {collection_name}: 已刪除 {deleted_count} 個相關文檔")

                else:
                    # 清空模式：清空整個集合
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
                                        import json

                                        doc_dict = json.loads(doc)
                                        if "_key" in doc_dict:
                                            collection.delete(doc_dict["_key"])
                                            count += 1
                                except Exception:
                                    pass
                            print(f"  ✅ {collection_name}: 已刪除 {count} 個文檔")
                        except Exception as e:
                            print(f"  ❌ {collection_name}: {e}")
            else:
                print(f"  ✅ {collection_name}: 集合不存在（跳過）")
        except Exception as e:
            print(f"  ❌ {collection_name}: {e}")

    return True


def cleanup_qdrant(file_ids: list = None):
    """清理 Qdrant collections

    Args:
        file_ids: 可選，按 file_id 清理（只刪除相關的向量）
                  如果為 None，則刪除所有 collections
    """
    print("\n🗑️  清理 Qdrant...")

    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        if file_ids:
            print(f"  按文件清理: {len(file_ids)} 個 file_id")

            # 按文件清理模式：刪除指定 file_id 的向量
            collections = client.get_collections().collections
            deleted_count = 0

            for collection in collections:
                collection_name = collection.name
                if not collection_name.startswith("_"):
                    try:
                        # 查找並刪除相關點（通過 payload.file_id）
                        client.delete(
                            collection_name=collection_name,
                            points_selector={
                                "must": [{"key": "file_id", "match": {"any": file_ids}}]
                            },
                        )
                        print(f"  ✅ {collection_name}: 已刪除相關向量")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  ❌ {collection_name}: {e}")

            print(f"  ✅ Qdrant 清理完成（{deleted_count} 個 collections）")

        else:
            # 清空模式：刪除所有 collections
            print("  清空模式: 將刪除所有 collections")

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


def cleanup_seaweedfs(task_ids: list = None):
    """清理 SeaweedFS S3 buckets

    Args:
        task_ids: 可選，按 task_id 清理（只刪除 tasks/<task_id> 目錄）
                  如果為 None，則刪除 bucket 中所有文件
    """
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

        if task_ids:
            print(f"  按任務清理: {len(task_ids)} 個 task_id")
            deleted_count = 0

            # 按任務清理模式：只刪除 tasks/<task_id> 目錄
            for task_id in task_ids:
                try:
                    prefix = f"tasks/{task_id}/"

                    # 列出所有匹配前綴的對象
                    paginator = s3.get_paginator("list_objects_v2")

                    for page in paginator.paginate(Bucket=SEAWEEDFS_BUCKET, Prefix=prefix):
                        if "Contents" in page:
                            for obj in page["Contents"]:
                                try:
                                    s3.delete_object(Bucket=SEAWEEDFS_BUCKET, Key=obj["Key"])
                                    print(f"  🗑️  刪除: {obj['Key']}")
                                    deleted_count += 1
                                except Exception:
                                    pass

                except ClientError as e:
                    if e.response["Error"]["Code"] in ["NoSuchBucket", "NoSuchKey"]:
                        pass
                    else:
                        print(f"  ❌ task_id {task_id}: {e}")

            print(f"  ✅ SeaweedFS S3 已清理（{deleted_count} 個文件）")

        else:
            # 清空模式：刪除 bucket 中所有文件
            print("  清空模式: 將刪除 bucket 中所有文件")

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

    parser = argparse.ArgumentParser(description="AI-Box 測試數據清理工具")
    parser.add_argument("--force", action="store_true", help="跳過確認直接執行（危險！）")
    parser.add_argument("--task-ids", nargs="+", help="按 task_id 清理（可選，多個 task_id）")
    parser.add_argument("--file-ids", nargs="+", help="按 file_id 清理（可選，多個 file_id）")
    args = parser.parse_args()

    print("=" * 60)
    print("AI-Box 測試數據清理工具")
    print("=" * 60)

    # 確定清理模式
    task_ids = args.task_ids if args.task_ids else None

    if not args.force:
        if task_ids:
            # 按任務清理模式
            print(f"\n⚠️  警告：此操作將清除以下數據（按任務清理）:")
            print(f"  - ArangoDB: task_id 在 {task_ids} 中的 user_tasks 和 file_metadata")
            print(f"  - ArangoDB: 所有 entities 和 relations（知識圖譜）")
            print(f"  - Qdrant: file_id 在 {args.file_ids if args.file_ids else '相關'} 中的向量")
            print(f"  - SeaweedFS: tasks/<task_id> 目錄中的所有文件")
        else:
            # 清空模式
            print("\n⚠️  警告：此操作將清除以下數據（清空模式）:")
            print("  - ArangoDB: file_metadata, entities, relations, user_tasks, folder_metadata")
            print("  - Qdrant: 所有 collections")
            print("  - SeaweedFS S3: bucket-ai-box-assets 中的所有文件")
            print("  - 本地文件: data/tasks, data/uploads")

        confirm = input("\n確定要繼續嗎？(輸入 DELETE 確認): ")

        if confirm != "DELETE":
            print("\n❌ 已取消")
            return
    else:
        if task_ids:
            print("\n⚠️  強制模式：按任務清理")
        else:
            print("\n⚠️  強制模式：清空所有數據")

    print("\n" + "=" * 60)

    # 執行清理
    cleanup_arangodb(task_ids=task_ids)
    cleanup_qdrant(file_ids=args.file_ids)
    cleanup_seaweedfs(task_ids=task_ids)
    cleanup_local_files()

    print("\n" + "=" * 60)
    print("✅ 數據清理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
