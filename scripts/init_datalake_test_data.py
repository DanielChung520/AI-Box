# 代碼功能說明: 初始化 Datalake 測試數據（500+ 筆）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""初始化 Datalake 測試數據腳本 - 生成 523 筆測試數據"""

import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from storage.s3_storage import S3FileStorage, SeaweedFSService
except ImportError as e:
    print(f"❌ 無法導入 S3FileStorage: {e}")
    print("請確保已安裝所需依賴：pip install boto3")
    sys.exit(1)


def get_timestamp(days_ago=0):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat() + "Z"


def create_test_parts_data():
    categories = ["電子元件", "機械零件", "包裝材料", "化學原料", "金屬材料"]
    suppliers = ["供應商 A", "供應商 B", "供應商 C", "供應商 D", "供應商 E"]
    units = ["PCS", "BOX", "KG", "M", "L"]
    part_numbers = [
        "ABC-123",
        "ABC-124",
        "ABC-125",
        "ABC-126",
        "ABC-127",
        "ABC-128",
        "ABC-129",
        "ABC-130",
        "ABC-131",
        "ABC-132",
    ]
    part_names = [
        "電子元件 A",
        "電子元件 B",
        "機械零件 C",
        "包裝材料 D",
        "電子元件 E",
        "化學原料 F",
        "金屬材料 G",
        "電子元件 H",
        "機械零件 I",
        "包裝材料 J",
    ]
    specifications = [
        "10x10x5mm",
        "15x15x8mm",
        "20x20x10mm",
        "30x30x20cm",
        "5x5x3mm",
        "100ml",
        "50x50x25mm",
        "12x12x6mm",
        "25x25x12mm",
        "40x40x30cm",
    ]
    parts = {}
    for i, part_number in enumerate(part_numbers):
        parts[part_number] = {
            "part_number": part_number,
            "name": part_names[i],
            "specification": specifications[i],
            "unit": units[i % len(units)],
            "supplier": suppliers[i % len(suppliers)],
            "category": categories[i % len(categories)],
            "safety_stock": random.randint(50, 200),
            "unit_price": round(random.uniform(5.0, 100.0), 2),
            "currency": "TWD",
            "created_at": get_timestamp(days_ago=30),
            "updated_at": get_timestamp(),
        }
    return parts


def create_test_stock_data(parts_data):
    locations = ["倉庫 A-01", "倉庫 A-02", "倉庫 B-01", "倉庫 B-02", "倉庫 C-01"]
    stock = {}
    for part_number, part_info in parts_data.items():
        safety_stock = part_info["safety_stock"]
        if random.random() < 0.3:
            current_stock = random.randint(0, int(safety_stock * 0.5))
            status = "shortage"
        elif random.random() < 0.5:
            current_stock = random.randint(int(safety_stock * 0.5), int(safety_stock * 0.8))
            status = "low"
        else:
            current_stock = random.randint(int(safety_stock * 1.0), int(safety_stock * 2.0))
            status = "normal"
        stock[part_number] = {
            "part_number": part_number,
            "current_stock": current_stock,
            "location": random.choice(locations),
            "status": status,
            "last_updated": get_timestamp(),
            "last_counted": get_timestamp(days_ago=random.randint(1, 30)),
        }
    return stock


def create_stock_history_data(part_number, current_stock, safety_stock, count=50):
    history = []
    locations = ["倉庫 A-01", "倉庫 A-02", "倉庫 B-01", "倉庫 B-02", "倉庫 C-01"]
    operations = ["入庫", "出庫", "盤點", "調整", "移庫"]
    stock_value = current_stock
    for i in range(count):
        days_ago = count - i
        operation = random.choice(operations)
        change = 0  # 初始化 change
        if operation == "入庫":
            change = random.randint(10, 100)
            stock_value += change
        elif operation == "出庫":
            max_change = min(50, max(1, stock_value))  # 確保至少為 1
            change = random.randint(1, max_change) if max_change >= 1 else 0
            stock_value = max(0, stock_value - change)
        elif operation == "盤點":
            change = random.randint(-20, 20)
            stock_value = max(0, stock_value + change)
        elif operation == "調整":
            change = random.randint(-10, 10)
            stock_value = max(0, stock_value + change)
        # 移庫操作 change 保持為 0
        if stock_value < safety_stock * 0.5:
            status = "shortage"
        elif stock_value < safety_stock * 0.8:
            status = "low"
        else:
            status = "normal"
        history.append(
            {
                "part_number": part_number,
                "timestamp": get_timestamp(days_ago=days_ago),
                "stock_value": stock_value,
                "location": random.choice(locations),
                "operation": operation,
                "change": change,
                "status": status,
                "operator": f"操作員{random.randint(1, 5)}",
                "notes": f"{operation}操作記錄",
            }
        )
    return history


def create_dictionary_data():
    return {
        "dictionary_id": "warehouse",
        "name": "倉庫數據字典",
        "version": "1.0.0",
        "description": "倉庫管理系統數據字典",
        "tables": {
            "parts": {"description": "物料表", "primary_key": "part_number"},
            "stock": {"description": "庫存表", "primary_key": "part_number"},
            "stock_history": {"description": "庫存歷史記錄表", "primary_key": "timestamp"},
        },
        "created_at": get_timestamp(),
        "updated_at": get_timestamp(),
    }


def create_part_schema():
    return {
        "schema_id": "part_schema",
        "name": "物料 Schema",
        "version": "1.0.0",
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "part_number": {"type": "string"},
                "name": {"type": "string"},
                "safety_stock": {"type": "integer", "minimum": 0},
            },
            "required": ["part_number", "name", "safety_stock"],
        },
        "created_at": get_timestamp(),
        "updated_at": get_timestamp(),
    }


def create_stock_schema():
    return {
        "schema_id": "stock_schema",
        "name": "庫存 Schema",
        "version": "1.0.0",
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "part_number": {"type": "string"},
                "current_stock": {"type": "integer", "minimum": 0},
                "status": {"type": "string", "enum": ["normal", "low", "shortage"]},
            },
            "required": ["part_number", "current_stock", "status"],
        },
        "created_at": get_timestamp(),
        "updated_at": get_timestamp(),
    }


def init_datalake_test_data():
    print("🚀 開始初始化 Datalake 測試數據（500+ 筆）...")
    print("=" * 60)
    endpoint = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT")
    access_key = os.getenv("DATALAKE_SEAWEEDFS_S3_ACCESS_KEY")
    secret_key = os.getenv("DATALAKE_SEAWEEDFS_S3_SECRET_KEY")
    use_ssl = os.getenv("DATALAKE_SEAWEEDFS_USE_SSL", "false").lower() == "true"
    if not endpoint:
        print("❌ 錯誤：未設置 DATALAKE_SEAWEEDFS_S3_ENDPOINT 環境變數")
        return False
    try:
        storage = S3FileStorage(
            endpoint=endpoint,
            access_key=access_key or "",
            secret_key=secret_key or "",
            use_ssl=use_ssl,
            service_type=SeaweedFSService.DATALAKE,
        )
        print(f"✅ 成功連接到 SeaweedFS Datalake: {endpoint}")
    except Exception as e:
        print(f"❌ 無法連接到 SeaweedFS Datalake: {e}")
        return False
    assets_bucket = "bucket-datalake-assets"
    dictionary_bucket = "bucket-datalake-dictionary"
    schema_bucket = "bucket-datalake-schema"
    success_count = 0
    error_count = 0
    print("\n📦 創建物料數據（10 個料號）...")
    parts_data = create_test_parts_data()
    for part_number, part_data in parts_data.items():
        try:
            key = f"parts/{part_number}.json"
            content = json.dumps(part_data, ensure_ascii=False, indent=2)
            storage.s3_client.put_object(
                Bucket=assets_bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print(f"  ✅ {part_number}: {part_data['name']}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 創建物料數據失敗 {part_number}: {e}")
            error_count += 1
    print("\n📊 創建庫存數據（10 個料號）...")
    stock_data = create_test_stock_data(parts_data)
    for part_number, stock_info in stock_data.items():
        try:
            key = f"stock/{part_number}.json"
            content = json.dumps(stock_info, ensure_ascii=False, indent=2)
            storage.s3_client.put_object(
                Bucket=assets_bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            status_icon = {"normal": "✅", "low": "⚠️", "shortage": "❌"}.get(
                stock_info["status"], "❓"
            )
            print(
                f"  {status_icon} {part_number}: 庫存 {stock_info['current_stock']} ({stock_info['status']})"
            )
            success_count += 1
        except Exception as e:
            print(f"  ❌ 創建庫存數據失敗 {part_number}: {e}")
            error_count += 1
    print("\n📜 創建庫存歷史記錄（每個料號 50 筆，共 500 筆）...")
    for part_number, stock_info in stock_data.items():
        part_info = parts_data[part_number]
        history_data = create_stock_history_data(
            part_number=part_number,
            current_stock=stock_info["current_stock"],
            safety_stock=part_info["safety_stock"],
            count=50,
        )
        try:
            key = f"stock_history/{part_number}.jsonl"
            content = "\n".join([json.dumps(record, ensure_ascii=False) for record in history_data])
            storage.s3_client.put_object(
                Bucket=assets_bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print(f"  ✅ {part_number}: 50 筆歷史記錄")
            success_count += 50
        except Exception as e:
            print(f"  ❌ 創建歷史記錄失敗 {part_number}: {e}")
            error_count += 50
    print("\n📚 創建數據字典...")
    try:
        dictionary_data = create_dictionary_data()
        key = "warehouse.json"
        content = json.dumps(dictionary_data, ensure_ascii=False, indent=2)
        storage.s3_client.put_object(
            Bucket=dictionary_bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
        )
        print(f"  ✅ 數據字典: {key}")
        success_count += 1
    except Exception as e:
        print(f"  ❌ 創建數據字典失敗: {e}")
        error_count += 1
    print("\n📋 創建 Schema 定義...")
    schemas = {
        "part_schema.json": create_part_schema(),
        "stock_schema.json": create_stock_schema(),
    }
    for schema_file, schema_data in schemas.items():
        try:
            content = json.dumps(schema_data, ensure_ascii=False, indent=2)
            storage.s3_client.put_object(
                Bucket=schema_bucket,
                Key=schema_file,
                Body=content.encode("utf-8"),
                ContentType="application/json",
            )
            print(f"  ✅ Schema: {schema_file}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ 創建 Schema 失敗 {schema_file}: {e}")
            error_count += 1
    print("\n" + "=" * 60)
    print(f"✅ 成功創建: {success_count} 筆數據")
    if error_count > 0:
        print(f"❌ 失敗: {error_count} 筆數據")
    print("📊 數據分布:")
    print("   - 物料數據: 10 筆")
    print("   - 庫存數據: 10 筆")
    print("   - 庫存歷史: 500 筆")
    print("   - 數據字典: 1 筆")
    print("   - Schema 定義: 2 筆")
    print(f"   - 總計: {success_count} 筆")
    print("=" * 60)
    return error_count == 0


if __name__ == "__main__":
    success = init_datalake_test_data()
    sys.exit(0 if success else 1)
