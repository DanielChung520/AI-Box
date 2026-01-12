#!/usr/bin/env python3
import time

import requests

API_BASE = "http://localhost:8000/api/v1"
FILE_ID = "5bcb96d4-fcca-475d-a557-a52c08371298"

# 登录
login_url = f"{API_BASE}/auth/login"
login_data = {"username": "daniel@test.com", "password": "test123"}
login_resp = requests.post(login_url, json=login_data, timeout=30)
token = login_resp.json().get("data", {}).get("access_token")
headers = {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("监控处理进度")
print("=" * 60)

for i in range(120):  # 最多监控 10 分钟
    status_url = f"{API_BASE}/files/{FILE_ID}/processing-status"
    status_resp = requests.get(status_url, headers=headers, timeout=10)
    status_data = status_resp.json().get("data", {})

    overall_status = status_data.get("status", "unknown")
    overall_progress = status_data.get("progress", 0)

    chunking = status_data.get("chunking", {})
    vectorization = status_data.get("vectorization", {})
    storage = status_data.get("storage", {})
    kg_extraction = status_data.get("kg_extraction", {})

    print(f"\n[{i*5}秒] 总体: {overall_status} ({overall_progress}%)")
    print(
        f"  分块: {chunking.get('status', 'unknown')} ({chunking.get('progress', 0)}%) - {chunking.get('chunk_count', 0)} 块"
    )
    print(f"  向量化: {vectorization.get('status', 'unknown')} ({vectorization.get('progress', 0)}%)")
    print(
        f"  存储: {storage.get('status', 'unknown')} ({storage.get('progress', 0)}%) - {storage.get('vector_count', 0)} 向量"
    )
    print(
        f"  圖譜: {kg_extraction.get('status', 'unknown')} ({kg_extraction.get('progress', 0)}%) - NER:{kg_extraction.get('entities_count', 0)} RE:{kg_extraction.get('relations_count', 0)} RT:{kg_extraction.get('triples_count', 0)}"
    )

    if overall_status == "completed":
        print("\n✅ 处理完成！")
        break
    elif overall_status == "failed":
        print(f"\n❌ 处理失败: {status_data.get('message', 'Unknown error')}")
        break

    time.sleep(5)

print("\n" + "=" * 60)
