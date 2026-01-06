#!/usr/bin/env python3
# 代碼功能說明: 上傳預製菜報告PDF並觸發向量化處理
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""上傳預製菜報告PDF並觸發向量化處理"""

import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

import httpx
import os

# 從環境變數獲取配置
base_url = os.getenv('API_GATEWAY_BASE_URL')
if not base_url:
    host = os.getenv('API_GATEWAY_HOST', 'localhost')
    port = os.getenv('API_GATEWAY_PORT', '8000')
    # 如果 host 是 0.0.0.0，使用 localhost
    if host == '0.0.0.0':
        host = 'localhost'
    base_url = f"http://{host}:{port}"
api_prefix = os.getenv('API_PREFIX', '/api/v1')

print(f"API 服務地址: {base_url}{api_prefix}")

# 測試文件
test_file = project_root / 'docs' / '东方伊厨-预制菜发展策略报告20250902.pdf'

if not test_file.exists():
    print(f"❌ 錯誤：文件不存在: {test_file}")
    sys.exit(1)

file_size_mb = test_file.stat().st_size / (1024 * 1024)
print("=" * 80)
print("📤 上傳預製菜報告PDF")
print("=" * 80)
print(f"文件: {test_file.name}")
print(f"大小: {file_size_mb:.2f} MB")
print()

# 登入
print("🔐 登入系統...")
login_data = {'username': 'daniel@test.com', 'password': '1234'}

try:
    with httpx.Client(timeout=600.0) as client:
        # 登入
        login_resp = client.post(f'{base_url}{api_prefix}/auth/login', json=login_data, timeout=30.0)
        if login_resp.status_code != 200:
            print(f"❌ 登入失敗: {login_resp.status_code}")
            print(login_resp.text)
            sys.exit(1)
        
        token = login_resp.json()['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ 登入成功")
        print()
        
        # 上傳文件
        print("📤 上傳文件...")
        start_time = time.time()
        
        with open(test_file, 'rb') as f:
            files = {'files': (test_file.name, f, 'application/pdf')}
            upload_resp = client.post(
                f'{base_url}{api_prefix}/files/upload',
                files=files,
                headers=headers,
                timeout=600.0
            )
            
            upload_time = time.time() - start_time
            
            if upload_resp.status_code == 200:
                result = upload_resp.json()
                uploaded = result.get('data', {}).get('uploaded', [])
                if uploaded:
                    file_id = uploaded[0]['file_id']
                    print(f"✅ 文件上傳成功！")
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
                    
                    while waited < max_wait:
                        time.sleep(check_interval)
                        waited += check_interval
                        
                        status_resp = client.get(
                            f'{base_url}{api_prefix}/files/{file_id}/processing-status',
                            headers=headers,
                            timeout=30.0
                        )
                        
                        if status_resp.status_code == 200:
                            status = status_resp.json().get('data', {})
                            overall_status = status.get('overall_status', 'unknown')
                            overall_progress = status.get('overall_progress', 0)
                            
                            print(f"   狀態: {overall_status}, 進度: {overall_progress}% (已等待 {waited} 秒)")
                            
                            if overall_status == 'completed':
                                print()
                                print("✅ 文件處理完成！")
                                chunking = status.get('chunking', {})
                                vectorization = status.get('vectorization', {})
                                storage = status.get('storage', {})
                                
                                print(f"   分塊數量: {chunking.get('chunk_count', 0)}")
                                print(f"   向量數量: {storage.get('vector_count', 0)}")
                                print()
                                print(f"FILE_ID={file_id}")
                                break
                            elif overall_status == 'failed':
                                print()
                                print("❌ 文件處理失敗")
                                print(status.get('message', '未知錯誤'))
                                sys.exit(1)
                        else:
                            print(f"   ⚠️  無法查詢狀態: {status_resp.status_code}")
                    
                    if waited >= max_wait:
                        print()
                        print("⚠️  處理超時（10分鐘），請手動查詢狀態")
                        print(f"FILE_ID={file_id}")
                else:
                    print(f"❌ 上傳失敗: 沒有返回文件ID")
                    print(result)
                    sys.exit(1)
            else:
                print(f"❌ 上傳失敗: {upload_resp.status_code}")
                print(upload_resp.text)
                sys.exit(1)

except httpx.ConnectError:
    print("❌ 無法連接到 API 服務器")
    print(f"   請確認 API 服務正在運行: {base_url}")
    print()
    print("💡 建議：")
    print("   1. 檢查 API 服務是否啟動")
    print("   2. 或通過前端界面上傳文件")
    sys.exit(1)
except Exception as e:
    print(f"❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

