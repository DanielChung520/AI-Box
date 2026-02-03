#!/usr/bin/env python3
"""立即刪除並驗證 user_tasks"""

import os
from dotenv import load_dotenv

load_dotenv()

import httpx

ARANGO_HOST = os.getenv("ARANGODB_HOST", "localhost")
ARANGO_PORT = os.getenv("ARANGODB_PORT", "8529")
ARANGO_USER = os.getenv("ARANGODB_USERNAME", "root")
ARANGO_PASSWORD = os.getenv("ARANGODB_PASSWORD", "ai_box_arangodb_password")
ARANGO_DB = os.getenv("ARANGODB_DATABASE", "ai_box_kg")

ARANGO_URL = f"http://{ARANGO_HOST}:{ARANGO_PORT}"

print("🔍 檢查 user_tasks 實際狀態...")
print()

with httpx.Client(timeout=30) as client:
    # 立即刪除所有記錄
    print("🗑️  立即刪除所有 user_tasks 記錄...")
    resp = client.post(
        f"{ARANGO_URL}/_db/{ARANGO_DB}/_api/cursor",
        json={"query": "FOR doc IN user_tasks REMOVE doc IN user_tasks"},
        auth=(ARANGO_USER, ARANGO_PASSWORD),
    )

    if resp.status_code == 200:
        deleted = resp.json().get("extra", {}).get("stats", {}).get("deleted", 0)
        print(f"   ✅ 已刪除: {deleted} 個記錄")

    print()
    print("立即驗證...")

    # 立即檢查
    resp = client.post(
        f"{ARANGO_URL}/_db/{ARANGO_DB}/_api/cursor",
        json={"query": "RETURN LENGTH(user_tasks)"},
        auth=(ARANGO_USER, ARANGO_PASSWORD),
    )

    if resp.status_code == 200:
        count = resp.json().get("result", [0])[0]
        print(f"📊 user_tasks 數量: {count}")

        if count == 0:
            print()
            print("✅ user_tasks 已完全清空！")
        else:
            print()
            print(f"⚠️ 仍舊 {count} 個記錄")
            print()

            # 列出最新的5 個記錄
            print("最新的 5 個記錄:")
            resp2 = client.post(
                f"{ARANGO_URL}/_db/{ARANGO_DB}/_api/cursor",
                json={"query": "FOR doc IN user_tasks SORT doc.created_at DESC LIMIT 5 RETURN doc"},
                auth=(ARANGO_USER, ARANGO_PASSWORD),
            )

            docs = resp2.json().get("result", [])
            for doc in docs:
                print(f"  _key: {doc.get('_key')[:40]}...")
                print(f"  task_id: {doc.get('task_id')}")
                print(f"  created_at: {doc.get('created_at')}")
                print()
    else:
        print(f"錯誤: {resp.status_code}")

print()
print("=" * 60)
print("執行完成！")
print("=" * 60)
