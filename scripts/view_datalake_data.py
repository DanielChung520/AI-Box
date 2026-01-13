# 代碼功能說明: 查看 SeaweedFS Datalake 中的測試數據
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""查看 SeaweedFS Datalake 中的測試數據

使用方法：
    python scripts/view_datalake_data.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from storage.s3_storage import S3FileStorage, SeaweedFSService
except ImportError as e:
    print(f"❌ 無法導入 S3FileStorage: {e}")
    sys.exit(1)


def view_datalake_data():
    """查看 Datalake 中的數據"""
    print("🔍 查看 SeaweedFS Datalake 測試數據...")
    print("=" * 60)

    # 獲取環境變數
    endpoint = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT")
    access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY", "")
    secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY", "")
    use_ssl = os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"

    if not endpoint:
        print("❌ 錯誤：未設置 DATALAKE_SEAWEEDFS_S3_ENDPOINT 環境變數")
        return False

    # 創建存儲實例
    try:
        storage = S3FileStorage(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            use_ssl=use_ssl,
            service_type=SeaweedFSService.DATALAKE,
        )
        print(f"✅ 成功連接到 SeaweedFS Datalake: {endpoint}")
    except Exception as e:
        print(f"❌ 無法連接到 SeaweedFS Datalake: {e}")
        return False

    # Bucket 配置
    assets_bucket = "bucket-datalake-assets"
    dictionary_bucket = "bucket-datalake-dictionary"
    schema_bucket = "bucket-datalake-schema"

    # 列出所有 Buckets
    print("\n📦 列出所有 Buckets...")
    try:
        response = storage.s3_client.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        print(f"   {buckets if buckets else '(無 Buckets)'}")
    except Exception as e:
        print(f"   ❌ 無法列出 Buckets: {e}")
        return False

    # 查看各 Bucket 中的文件
    buckets_to_check = [
        (assets_bucket, "assets"),
        (dictionary_bucket, "dictionary"),
        (schema_bucket, "schema"),
    ]

    total_files = 0
    for bucket_name, bucket_type in buckets_to_check:
        print(f"\n📁 {bucket_name} ({bucket_type}):")
        try:
            objects = storage.s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" in objects and objects["Contents"]:
                files = objects["Contents"]
                total_files += len(files)
                print(f"   ✅ 找到 {len(files)} 個文件")

                # 按前綴分組顯示
                prefixes = {}
                for obj in files:
                    key = obj["Key"]
                    prefix = key.split("/")[0] if "/" in key else "root"
                    if prefix not in prefixes:
                        prefixes[prefix] = []
                    prefixes[prefix].append(obj)

                for prefix, objs in sorted(prefixes.items()):
                    print(f"\n   📂 {prefix}/ ({len(objs)} 個文件):")
                    for obj in sorted(objs, key=lambda x: x["Key"])[:10]:
                        size_kb = obj["Size"] / 1024
                        print(f"      - {obj['Key']} ({size_kb:.1f} KB)")
                    if len(objs) > 10:
                        print(f"      ... 還有 {len(objs) - 10} 個文件")
            else:
                print("   📭 (空)")
        except Exception as e:
            if "NoSuchBucket" in str(e):
                print("   ⚠️  Bucket 不存在")
            else:
                print(f"   ❌ 錯誤: {e}")

    # 總結
    print("\n" + "=" * 60)
    if total_files > 0:
        print(f"✅ 總共找到 {total_files} 個文件")
    else:
        print("⚠️  沒有找到任何文件")
        print("   測試數據可能還沒有上傳到 SeaweedFS")
        print("   請執行: python scripts/upload_datalake_test_data.py")
    print("=" * 60)

    return total_files > 0


if __name__ == "__main__":
    success = view_datalake_data()
    sys.exit(0 if success else 1)
