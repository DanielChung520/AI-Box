# 代碼功能說明: 上傳本地測試數據到 SeaweedFS Datalake
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""上傳本地測試數據到 SeaweedFS Datalake

此腳本從本地文件讀取測試數據並上傳到 SeaweedFS Datalake。
本地數據由 init_datalake_test_data.py 生成在 scripts/datalake_test_data/ 目錄。

使用方法：
    python scripts/upload_datalake_test_data.py
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
    print("請確保已安裝所需依賴：pip install boto3")
    sys.exit(1)


def upload_local_data_to_seaweedfs():
    """從本地文件上傳數據到 SeaweedFS"""
    local_data_dir = project_root / "scripts" / "datalake_test_data"

    if not local_data_dir.exists():
        print(f"❌ 本地數據目錄不存在: {local_data_dir}")
        print("   請先運行腳本生成本地測試數據")
        return False

    print("🚀 開始上傳本地測試數據到 SeaweedFS Datalake...")
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

    # 確保 Buckets 存在
    print("\n📦 確保 Buckets 存在...")
    for bucket_name in [assets_bucket, dictionary_bucket, schema_bucket]:
        try:
            storage.s3_client.head_bucket(Bucket=bucket_name)
            print(f"  ✅ Bucket '{bucket_name}' 已存在")
        except Exception:
            try:
                storage.s3_client.create_bucket(Bucket=bucket_name)
                print(f"  ✅ Bucket '{bucket_name}' 已創建")
            except Exception as e:
                print(f"  ⚠️  無法創建 Bucket '{bucket_name}': {e}")

    success_count = 0
    error_count = 0

    # 1. 上傳物料數據
    print("\n📦 上傳物料數據...")
    parts_dir = local_data_dir / "parts"
    if parts_dir.exists():
        for part_file in parts_dir.glob("*.json"):
            try:
                with open(part_file, "r", encoding="utf-8") as f:
                    content = f.read()
                key = f"parts/{part_file.name}"
                storage.s3_client.put_object(
                    Bucket=assets_bucket,
                    Key=key,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                )
                print(f"  ✅ {part_file.name}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ {part_file.name}: {e}")
                error_count += 1

    # 2. 上傳庫存數據
    print("\n📊 上傳庫存數據...")
    stock_dir = local_data_dir / "stock"
    if stock_dir.exists():
        for stock_file in stock_dir.glob("*.json"):
            try:
                with open(stock_file, "r", encoding="utf-8") as f:
                    content = f.read()
                key = f"stock/{stock_file.name}"
                storage.s3_client.put_object(
                    Bucket=assets_bucket,
                    Key=key,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                )
                print(f"  ✅ {stock_file.name}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ {stock_file.name}: {e}")
                error_count += 1

    # 3. 上傳庫存歷史記錄
    print("\n📜 上傳庫存歷史記錄...")
    history_dir = local_data_dir / "stock_history"
    if history_dir.exists():
        for history_file in history_dir.glob("*.jsonl"):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    content = f.read()
                key = f"stock_history/{history_file.name}"
                storage.s3_client.put_object(
                    Bucket=assets_bucket,
                    Key=key,
                    Body=content.encode("utf-8"),
                    ContentType="application/x-ndjson",
                )
                # 計算記錄數
                line_count = len(content.strip().split("\n"))
                print(f"  ✅ {history_file.name}: {line_count} 筆記錄")
                success_count += line_count
            except Exception as e:
                print(f"  ❌ {history_file.name}: {e}")
                error_count += 50  # 估算

    # 4. 上傳數據字典
    print("\n📚 上傳數據字典...")
    dict_file = local_data_dir / "dictionary" / "warehouse.json"
    if dict_file.exists():
        try:
            with open(dict_file, "r", encoding="utf-8") as f:
                content = f.read()
            storage.s3_client.put_object(
                Bucket=dictionary_bucket,
                Key="warehouse.json",
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print("  ✅ warehouse.json")
            success_count += 1
        except Exception as e:
            print(f"  ❌ warehouse.json: {e}")
            error_count += 1

    # 5. 上傳 Schema 定義
    print("\n📋 上傳 Schema 定義...")
    schema_dir = local_data_dir / "schema"
    if schema_dir.exists():
        for schema_file in schema_dir.glob("*.json"):
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    content = f.read()
                storage.s3_client.put_object(
                    Bucket=schema_bucket,
                    Key=schema_file.name,
                    Body=content.encode("utf-8"),
                    ContentType="application/json",
                )
                print(f"  ✅ {schema_file.name}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ {schema_file.name}: {e}")
                error_count += 1

    # 總結
    print("\n" + "=" * 60)
    print(f"✅ 成功上傳: {success_count} 筆數據")
    if error_count > 0:
        print(f"❌ 失敗: {error_count} 筆數據")
    print("=" * 60)

    return error_count == 0


if __name__ == "__main__":
    success = upload_local_data_to_seaweedfs()
    sys.exit(0 if success else 1)
