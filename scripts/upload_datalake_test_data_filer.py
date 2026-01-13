# 代碼功能說明: 使用 Filer API 上傳本地測試數據到 SeaweedFS Datalake
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""使用 Filer API 上傳本地測試數據到 SeaweedFS Datalake

由於 S3 API 連接問題，此腳本使用 Filer API 直接上傳數據。
本地數據由 init_datalake_test_data.py 生成在 scripts/datalake_test_data/ 目錄。

使用方法：
    python scripts/upload_datalake_test_data_filer.py
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


def upload_local_data_via_filer():
    """使用 Filer API 從本地文件上傳數據到 SeaweedFS"""
    local_data_dir = project_root / "scripts" / "datalake_test_data"

    if not local_data_dir.exists():
        print(f"❌ 本地數據目錄不存在: {local_data_dir}")
        print("   請先運行腳本生成本地測試數據")
        return False

    print("🚀 開始使用 Filer API 上傳本地測試數據到 SeaweedFS Datalake...")
    print("=" * 60)

    # 獲取環境變數
    filer_endpoint = os.getenv("DATALAKE_SEAWEEDFS_FILER_ENDPOINT", "http://localhost:8889")

    if not filer_endpoint:
        print("❌ 錯誤：未設置 DATALAKE_SEAWEEDFS_FILER_ENDPOINT 環境變數")
        return False

    print(f"✅ Filer API 端點: {filer_endpoint}")

    # Bucket 配置
    assets_bucket = "bucket-datalake-assets"
    dictionary_bucket = "bucket-datalake-dictionary"
    schema_bucket = "bucket-datalake-schema"

    success_count = 0
    error_count = 0

    # 創建 HTTP 客戶端
    client = httpx.Client(timeout=30.0)

    # 1. 上傳物料數據
    print("\n📦 上傳物料數據...")
    parts_dir = local_data_dir / "parts"
    if parts_dir.exists():
        for part_file in parts_dir.glob("*.json"):
            try:
                with open(part_file, "r", encoding="utf-8") as f:
                    content = f.read()
                url = f"{filer_endpoint}/{assets_bucket}/parts/{part_file.name}"
                response = client.put(
                    url,
                    content=content.encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in [200, 201, 204]:
                    print(f"  ✅ {part_file.name}")
                    success_count += 1
                else:
                    print(f"  ⚠️  {part_file.name}: HTTP {response.status_code}")
                    error_count += 1
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
                url = f"{filer_endpoint}/{assets_bucket}/stock/{stock_file.name}"
                response = client.put(
                    url,
                    content=content.encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in [200, 201, 204]:
                    print(f"  ✅ {stock_file.name}")
                    success_count += 1
                else:
                    print(f"  ⚠️  {stock_file.name}: HTTP {response.status_code}")
                    error_count += 1
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
                url = f"{filer_endpoint}/{assets_bucket}/stock_history/{history_file.name}"
                response = client.put(
                    url,
                    content=content.encode("utf-8"),
                    headers={"Content-Type": "application/x-ndjson"},
                )
                if response.status_code in [200, 201, 204]:
                    line_count = len(content.strip().split("\n"))
                    print(f"  ✅ {history_file.name}: {line_count} 筆記錄")
                    success_count += line_count
                else:
                    print(f"  ⚠️  {history_file.name}: HTTP {response.status_code}")
                    error_count += 50
            except Exception as e:
                print(f"  ❌ {history_file.name}: {e}")
                error_count += 50

    # 4. 上傳數據字典
    print("\n📚 上傳數據字典...")
    dict_file = local_data_dir / "dictionary" / "warehouse.json"
    if dict_file.exists():
        try:
            with open(dict_file, "r", encoding="utf-8") as f:
                content = f.read()
            url = f"{filer_endpoint}/{dictionary_bucket}/warehouse.json"
            response = client.put(
                url,
                content=content.encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code in [200, 201, 204]:
                print("  ✅ warehouse.json")
                success_count += 1
            else:
                print(f"  ⚠️  warehouse.json: HTTP {response.status_code}")
                error_count += 1
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
                url = f"{filer_endpoint}/{schema_bucket}/{schema_file.name}"
                response = client.put(
                    url,
                    content=content.encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in [200, 201, 204]:
                    print(f"  ✅ {schema_file.name}")
                    success_count += 1
                else:
                    print(f"  ⚠️  {schema_file.name}: HTTP {response.status_code}")
                    error_count += 1
            except Exception as e:
                print(f"  ❌ {schema_file.name}: {e}")
                error_count += 1

    client.close()

    # 總結
    print("\n" + "=" * 60)
    print(f"✅ 成功上傳: {success_count} 筆數據")
    if error_count > 0:
        print(f"❌ 失敗: {error_count} 筆數據")
    print("=" * 60)

    return error_count == 0


if __name__ == "__main__":
    success = upload_local_data_via_filer()
    sys.exit(0 if success else 1)
