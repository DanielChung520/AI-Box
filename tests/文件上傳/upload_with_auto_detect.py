#!/usr/bin/env python3
# 代碼功能說明: 自動檢測 API 服務並上傳預製菜報告PDF
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""自動檢測 API 服務並上傳預製菜報告PDF"""

import sys
import time
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

import httpx

# 可能的 API 端口列表
possible_ports = [8000, 3000, 8001, 8080]
api_prefix = "/api/v1"

# 測試文件
test_file = project_root / "docs" / "东方伊厨-预制菜发展策略报告20250902.pdf"

if not test_file.exists():
    print(f"❌ 錯誤：文件不存在: {test_file}")
    sys.exit(1)

file_size_mb = test_file.stat().st_size / (1024 * 1024)

print("=" * 80)
print("🔍 自動檢測 API 服務")
print("=" * 80)
print(f"文件: {test_file.name}")
print(f"大小: {file_size_mb:.2f} MB")
print()

# 自動檢測可用的 API 服務
base_url = None
for port in possible_ports:
    test_url = f"http://localhost:{port}"
    print(f"測試 {test_url}...")

    try:
        with httpx.Client(timeout=5.0) as client:
            # 測試健康檢查或根路徑
            resp = client.get(f"{test_url}/health", timeout=5.0)
            if resp.status_code in [200, 404]:
                # 嘗試 API 端點
                try:
                    api_resp = client.get(f"{test_url}{api_prefix}/health", timeout=5.0)
                    if api_resp.status_code in [200, 404]:
                        base_url = test_url
                        print(f"  ✅ 找到 API 服務: {test_url}{api_prefix}")
                        break
                except:
                    # 嘗試登入端點是否存在
                    try:
                        login_resp = client.options(
                            f"{test_url}{api_prefix}/auth/login", timeout=5.0
                        )
                        if login_resp.status_code in [200, 204, 405]:
                            base_url = test_url
                            print(f"  ✅ 找到 API 服務: {test_url}{api_prefix}")
                            break
                    except:
                        pass
    except Exception as e:
        print(f"  ❌ 無法連接: {type(e).__name__}")

    print()

if not base_url:
    print("❌ 無法找到可用的 API 服務")
    print()
    print("💡 請確認：")
    print("   1. API 服務是否正在運行")
    print("   2. 執行以下命令啟動服務：")
    print("      $ cd /Users/daniel/GitHub/AI-Box")
    print("      $ ./scripts/start_services.sh fastapi")
    sys.exit(1)

print()
print("=" * 80)
print("📤 開始上傳文件")
print("=" * 80)
print(f"API 服務: {base_url}{api_prefix}")
print()

# 登入
print("🔐 登入系統...")
login_data = {"username": "daniel@test.com", "password": "1234"}

try:
    with httpx.Client(timeout=600.0) as client:
        # 登入（多次重試）
        max_retries = 3
        token = None

        for attempt in range(max_retries):
            try:
                login_resp = client.post(
                    f"{base_url}{api_prefix}/auth/login", json=login_data, timeout=30.0
                )

                if login_resp.status_code == 200:
                    result = login_resp.json()
                    token = result.get("data", {}).get("access_token")
                    if token:
                        print(f"  ✅ 登入成功（嘗試 {attempt + 1}/{max_retries}）")
                        break
                else:
                    print(f"  ⚠️  登入失敗（嘗試 {attempt + 1}/{max_retries}）: {login_resp.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
            except Exception as e:
                print(f"  ⚠️  登入錯誤（嘗試 {attempt + 1}/{max_retries}）: {type(e).__name__}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        if not token:
            print("❌ 登入失敗，無法繼續")
            sys.exit(1)

        headers = {"Authorization": f"Bearer {token}"}
        print()

        # 上傳文件
        print("📤 上傳文件（29MB，可能需要較長時間）...")
        start_time = time.time()

        with open(test_file, "rb") as f:
            files = {"files": (test_file.name, f, "application/pdf")}
            upload_resp = client.post(
                f"{base_url}{api_prefix}/files/upload", files=files, headers=headers, timeout=600.0
            )

            upload_time = time.time() - start_time

            if upload_resp.status_code == 200:
                result = upload_resp.json()
                uploaded = result.get("data", {}).get("uploaded", [])
                if uploaded:
                    file_id = uploaded[0]["file_id"]
                    print("✅ 文件上傳成功！")
                    print(f"   文件 ID: {file_id}")
                    print(f"   文件名: {uploaded[0]['filename']}")
                    print(f"   文件大小: {uploaded[0]['file_size'] / (1024*1024):.2f} MB")
                    print(f"   上傳耗時: {upload_time:.2f} 秒")
                    print()
                    print("⏳ 文件處理中（向量化），正在查詢處理狀態...")
                    print()

                    # 等待並查詢處理狀態
                    max_wait = 600  # 最多等待10分鐘
                    check_interval = 10  # 每10秒檢查一次
                    waited = 0
                    last_progress = -1

                    while waited < max_wait:
                        time.sleep(check_interval)
                        waited += check_interval

                        try:
                            status_resp = client.get(
                                f"{base_url}{api_prefix}/files/{file_id}/processing-status",
                                headers=headers,
                                timeout=30.0,
                            )

                            if status_resp.status_code == 200:
                                status = status_resp.json().get("data", {})
                                overall_status = status.get("overall_status", "unknown")
                                overall_progress = status.get("overall_progress", 0)

                                if overall_progress != last_progress:
                                    print(
                                        f"   狀態: {overall_status}, 進度: {overall_progress}% (已等待 {waited} 秒)"
                                    )
                                    last_progress = overall_progress

                                if overall_status == "completed":
                                    print()
                                    print("✅ 文件處理完成！")
                                    chunking = status.get("chunking", {})
                                    vectorization = status.get("vectorization", {})
                                    storage = status.get("storage", {})

                                    print(f"   分塊數量: {chunking.get('chunk_count', 0)}")
                                    print(f"   向量數量: {storage.get('vector_count', 0)}")
                                    print()
                                    print(f"FILE_ID={file_id}")
                                    print()
                                    print("=" * 80)
                                    print("✅ 階段二完成：文件上傳和向量化成功！")
                                    print("=" * 80)
                                    print()
                                    print("📋 下一步：驗證向量化質量")
                                    print(
                                        f"   $ python scripts/verify_vectorization_quality.py {file_id}"
                                    )
                                    break
                                elif overall_status == "failed":
                                    print()
                                    print("❌ 文件處理失敗")
                                    print(status.get("message", "未知錯誤"))
                                    sys.exit(1)
                            else:
                                if waited % 30 == 0:  # 每30秒打印一次
                                    print(f"   ⚠️  無法查詢狀態: {status_resp.status_code}")
                        except Exception as e:
                            if waited % 30 == 0:
                                print(f"   ⚠️  查詢狀態時出錯: {type(e).__name__}")

                    if waited >= max_wait:
                        print()
                        print("⚠️  處理超時（10分鐘），請手動查詢狀態")
                        print(f"FILE_ID={file_id}")
                else:
                    print("❌ 上傳失敗: 沒有返回文件ID")
                    print(result)
                    sys.exit(1)
            else:
                print(f"❌ 上傳失敗: {upload_resp.status_code}")
                print(upload_resp.text[:500])
                sys.exit(1)

except Exception as e:
    print(f"❌ 錯誤: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
