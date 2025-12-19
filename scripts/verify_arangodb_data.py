#!/usr/bin/env python3
# 代碼功能說明: ArangoDB 數據驗證腳本
# 創建日期: 2025-12-19
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-19

"""ArangoDB 數據驗證腳本 - 驗證所有 collections 的數據完整性"""

import sys
from pathlib import Path
from typing import Any, Dict

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加載 .env 文件
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

print("=" * 60)
print("ArangoDB 數據驗證")
print("=" * 60 + "\n")

try:
    from database.arangodb import ArangoDBClient

    client = ArangoDBClient()

    if client.db is None:
        print("❌ 錯誤: ArangoDB 客戶端未連接")
        sys.exit(1)

    # Collections 列表
    collections_to_verify = [
        "file_metadata",
        "upload_progress",
        "processing_status",
        "entities",
        "relations",
        "audit_logs",
    ]

    print(f"驗證 Collections: {', '.join(collections_to_verify)}\n")

    results: Dict[str, Dict[str, Any]] = {}

    for collection_name in collections_to_verify:
        print(f"檢查 Collection: {collection_name}")
        try:
            if client.db.has_collection(collection_name):
                collection = client.db.collection(collection_name)
                count = collection.count()
                results[collection_name] = {"exists": True, "count": count, "status": "✅"}
                print(f"  ✅ 存在: {count} 個文檔")

                # 獲取示例文檔（如果有）
                if count > 0:
                    try:
                        sample = collection.random()
                        if sample:
                            print(f"  📄 示例文檔鍵: {sample.get('_key', 'N/A')}")
                    except Exception:
                        pass
            else:
                results[collection_name] = {"exists": False, "count": 0, "status": "❌"}
                print("  ❌ 不存在")
        except Exception as e:
            results[collection_name] = {
                "exists": False,
                "count": 0,
                "status": "⚠️",
                "error": str(e),
            }
            print(f"  ⚠️  錯誤: {e}")
        print()

    # 驗證多租戶隔離（檢查是否有 tenant_id 字段）
    print("驗證多租戶隔離...")
    tenant_collections = ["file_metadata", "upload_progress", "processing_status"]
    for coll_name in tenant_collections:
        if coll_name in results and results[coll_name]["exists"]:
            try:
                collection = client.db.collection(coll_name)
                # 查詢是否有 tenant_id 字段的文檔
                aql = f"FOR doc IN {coll_name} FILTER doc.tenant_id != null LIMIT 1 RETURN doc.tenant_id"
                cursor = client.db.aql.execute(aql) if client.db.aql else None
                if cursor:
                    has_tenant_id = len(list(cursor)) > 0
                    print(
                        f"  {coll_name}: {'✅ 支持多租戶' if has_tenant_id else '⚠️  未找到 tenant_id 字段'}"
                    )
            except Exception:
                print(f"  {coll_name}: ⚠️  無法驗證多租戶")
    print()

    # 總結
    print("=" * 60)
    print("驗證總結")
    print("=" * 60)
    total_collections = len(collections_to_verify)
    existing_collections = sum(1 for r in results.values() if r["exists"])
    total_documents = sum(r["count"] for r in results.values() if r["exists"])

    print(f"Collections 總數: {total_collections}")
    print(f"存在的 Collections: {existing_collections}")
    print(f"總文檔數: {total_documents}")
    print()

    for coll_name, result in results.items():
        status = result["status"]
        if result["exists"]:
            print(f"{status} {coll_name}: {result['count']} 個文檔")
        else:
            error_msg = f" ({result.get('error', '')})" if result.get("error") else ""
            print(f"{status} {coll_name}: 不存在{error_msg}")

except Exception as e:
    print(f"❌ 驗證失敗: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("驗證完成")
print("=" * 60)
