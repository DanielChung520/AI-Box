# 代碼功能說明: 準備庫管員Agent測試數據
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""準備庫管員Agent測試數據並上傳到SeaweedFS Datalake"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

from botocore.exceptions import ClientError
from dotenv import load_dotenv

from storage.s3_storage import S3FileStorage, SeaweedFSService

# 顯式加載 .env 文件
env_path = ai_box_root / ".env"
load_dotenv(dotenv_path=env_path)


# 測試數據定義
TEST_DATA = {
    "parts": {
        "ABC-123": {
            "part_number": "ABC-123",
            "name": "電子元件 A",
            "specification": "10x10x5mm",
            "unit": "PCS",
            "supplier": "供應商 A",
            "category": "電子元件",
            "safety_stock": 100,
            "unit_price": 50.0,
            "currency": "TWD",
            "description": "高品質電子元件，適用於各種電子設備",
        },
        "XYZ-456": {
            "part_number": "XYZ-456",
            "name": "機械零件 B",
            "specification": "20x15x10mm",
            "unit": "PCS",
            "supplier": "供應商 B",
            "category": "機械零件",
            "safety_stock": 50,
            "unit_price": 120.0,
            "currency": "TWD",
            "description": "精密機械零件，用於工業設備",
        },
    },
    "stock": {
        "ABC-123": {
            "part_number": "ABC-123",
            "current_stock": 50,
            "location": "倉庫 A-01",
            "last_updated": "2026-01-13T10:00:00Z",
            "reserved_quantity": 0,
            "available_stock": 50,
        },
        "XYZ-456": {
            "part_number": "XYZ-456",
            "current_stock": 30,
            "location": "倉庫 B-02",
            "last_updated": "2026-01-13T10:00:00Z",
            "reserved_quantity": 0,
            "available_stock": 30,
        },
    },
}


async def upload_test_data():
    """上傳測試數據到SeaweedFS Datalake"""

    # 初始化S3存儲
    endpoint = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8334")
    access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY", "admin")
    secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY", "admin123")
    use_ssl = os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"

    storage = S3FileStorage(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        use_ssl=use_ssl,
        service_type=SeaweedFSService.DATALAKE,
    )

    bucket = "bucket-datalake-assets"
    uploaded_count = 0
    failed_count = 0

    print("=" * 60)
    print("準備庫管員Agent測試數據")
    print("=" * 60)
    print(f"Datalake端點: {endpoint}")
    print(f"Bucket: {bucket}")
    print()

    # 確保bucket存在
    try:
        storage.s3_client.head_bucket(Bucket=bucket)
        print(f"✅ Bucket存在: {bucket}")
    except ClientError:
        try:
            storage.s3_client.create_bucket(Bucket=bucket)
            print(f"✅ Bucket已創建: {bucket}")
        except Exception as e:
            print(f"⚠️  Bucket創建失敗: {e}，繼續嘗試上傳...")

    print()

    # 上傳物料信息
    print("📦 上傳物料信息...")
    for part_number, part_data in TEST_DATA["parts"].items():
        key = f"parts/{part_number}.json"
        try:
            content = json.dumps(part_data, ensure_ascii=False, indent=2)
            storage.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print(f"  ✅ {key}")
            uploaded_count += 1
        except Exception as e:
            print(f"  ❌ {key}: {e}")
            failed_count += 1

    print()

    # 上傳庫存信息
    print("📊 上傳庫存信息...")
    for part_number, stock_data in TEST_DATA["stock"].items():
        key = f"stock/{part_number}.json"
        try:
            content = json.dumps(stock_data, ensure_ascii=False, indent=2)
            storage.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print(f"  ✅ {key}")
            uploaded_count += 1
        except Exception as e:
            print(f"  ❌ {key}: {e}")
            failed_count += 1

    print()
    print("=" * 60)
    print("上傳完成")
    print("=" * 60)
    print(f"成功: {uploaded_count} 個文件")
    print(f"失敗: {failed_count} 個文件")
    print()

    # 驗證上傳的數據
    print("🔍 驗證上傳的數據...")
    verification_passed = 0
    verification_failed = 0

    for part_number in TEST_DATA["parts"].keys():
        # 驗證物料信息
        part_key = f"parts/{part_number}.json"
        try:
            response = storage.s3_client.get_object(Bucket=bucket, Key=part_key)
            content = response["Body"].read()
            data = json.loads(content.decode("utf-8"))
            if data.get("part_number") == part_number:
                print(f"  ✅ 驗證物料: {part_number}")
                verification_passed += 1
            else:
                print(f"  ❌ 驗證物料: {part_number} (數據不匹配)")
                verification_failed += 1
        except Exception as e:
            print(f"  ❌ 驗證物料: {part_number} ({e})")
            verification_failed += 1

        # 驗證庫存信息
        stock_key = f"stock/{part_number}.json"
        try:
            response = storage.s3_client.get_object(Bucket=bucket, Key=stock_key)
            content = response["Body"].read()
            data = json.loads(content.decode("utf-8"))
            if data.get("part_number") == part_number:
                print(f"  ✅ 驗證庫存: {part_number}")
                verification_passed += 1
            else:
                print(f"  ❌ 驗證庫存: {part_number} (數據不匹配)")
                verification_failed += 1
        except Exception as e:
            print(f"  ❌ 驗證庫存: {part_number} ({e})")
            verification_failed += 1

    print()
    print("=" * 60)
    print("驗證完成")
    print("=" * 60)
    print(f"通過: {verification_passed} 個文件")
    print(f"失敗: {verification_failed} 個文件")
    print()

    if failed_count == 0 and verification_failed == 0:
        print("✅ 所有測試數據準備完成！")
        return True
    else:
        print("⚠️  部分測試數據準備失敗，請檢查錯誤信息")
        return False


if __name__ == "__main__":
    success = asyncio.run(upload_test_data())
    sys.exit(0 if success else 1)
