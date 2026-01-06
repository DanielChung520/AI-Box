#!/usr/bin/env python3
# 代碼功能說明: 測試企業級AI驅動開發架構設計PDF並進行圖譜提取
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""測試企業級AI驅動開發架構設計PDF並進行圖譜提取

測試流程：
1. 上傳 PDF 文件
2. 等待向量化完成
3. 設置 KG 模型為 mistral-nemo:12b
4. 觸發圖譜提取
5. 監控進度並顯示結果
"""

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
    if host == '0.0.0.0':
        host = 'localhost'
    base_url = f"http://{host}:{port}"
api_prefix = os.getenv('API_PREFIX', '/api/v1')

print(f"API 服務地址: {base_url}{api_prefix}")

# 測試文件
test_file = project_root / 'docs' / '企業級AI驅動開發架構設計_完整版.pdf'
model_name = "mistral-nemo:12b"

if not test_file.exists():
    print(f"❌ 錯誤：文件不存在: {test_file}")
    sys.exit(1)

file_size_mb = test_file.stat().st_size / (1024 * 1024)
print("=" * 80)
print("📤 測試企業級AI驅動開發架構設計PDF")
print("=" * 80)
print(f"文件: {test_file.name}")
print(f"大小: {file_size_mb:.2f} MB")
print(f"KG 模型: {model_name}")
print()

# 登入
print("🔐 登入系統...")
login_data = {'username': 'daniel@test.com', 'password': '1234'}

try:
    with httpx.Client(timeout=600.0) as client:
        # 登入
        login_resp = client.post(
            f'{base_url}{api_prefix}/auth/login',
            json=login_data,
            timeout=30.0
        )
        if login_resp.status_code != 200:
            print(f"❌ 登入失敗: {login_resp.status_code}")
            print(login_resp.text)
            sys.exit(1)
        
        token = login_resp.json()['data']['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ 登入成功")
        print()
        
        # 步驟 1: 上傳文件
        print("=" * 80)
        print("步驟 1: 上傳文件並等待向量化")
        print("=" * 80)
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
                    print("⏳ 等待向量化處理...")
                    print()
                    
                    # 等待向量化完成
                    max_wait = 900  # 最多等待15分鐘
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
                            
                            chunking = status.get('chunking', {})
                            vectorization = status.get('vectorization', {})
                            storage = status.get('storage', {})
                            
                            print(
                                f"   [{waited:4d}s] "
                                f"狀態: {overall_status:12s} | "
                                f"進度: {overall_progress:3d}% | "
                                f"分塊: {chunking.get('chunk_count', 0):4d} | "
                                f"向量: {storage.get('vector_count', 0):6d}"
                            )
                            
                            if overall_status == 'completed':
                                print()
                                print("✅ 向量化處理完成！")
                                print(f"   分塊數量: {chunking.get('chunk_count', 0)}")
                                print(f"   向量數量: {storage.get('vector_count', 0)}")
                                print()
                                break
                            elif overall_status == 'failed':
                                print()
                                print("❌ 向量化處理失敗")
                                print(status.get('message', '未知錯誤'))
                                sys.exit(1)
                        else:
                            print(f"   ⚠️  無法查詢狀態: {status_resp.status_code}")
                    
                    if waited >= max_wait:
                        print()
                        print("⚠️  向量化處理超時（15分鐘），請手動查詢狀態")
                        print(f"FILE_ID={file_id}")
                        sys.exit(1)
                    
                    # 步驟 2: 設置 KG 模型
                    print()
                    print("=" * 80)
                    print(f"步驟 2: 設置 KG 模型為 {model_name}")
                    print("=" * 80)
                    
                    # 先獲取當前配置
                    config_resp = client.get(
                        f'{base_url}{api_prefix}/config/kg_extraction',
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if config_resp.status_code == 200:
                        current_config = config_resp.json().get('data', {})
                        config_data = current_config.get('config_data', {})
                        
                        print("當前配置:")
                        print(f"  NER: {config_data.get('ner_model_type')} - {config_data.get('ner_model')}")
                        print(f"  RE: {config_data.get('re_model_type')} - {config_data.get('re_model')}")
                        print(f"  RT: {config_data.get('rt_model_type')} - {config_data.get('rt_model')}")
                        print()
                        
                        # 更新為 mistral-nemo:12b
                        config_data['ner_model_type'] = 'ollama'
                        config_data['ner_model'] = model_name
                        config_data['re_model_type'] = 'ollama'
                        config_data['re_model'] = model_name
                        config_data['rt_model_type'] = 'ollama'
                        config_data['rt_model'] = model_name
                        
                        # 更新配置
                        update_resp = client.put(
                            f'{base_url}{api_prefix}/config/kg_extraction',
                            headers=headers,
                            json={
                                'config_data': config_data,
                                'is_active': True
                            },
                            timeout=30.0
                        )
                        
                        if update_resp.status_code == 200:
                            print("✅ 模型配置已更新")
                            print(f"  NER: ollama - {model_name}")
                            print(f"  RE: ollama - {model_name}")
                            print(f"  RT: ollama - {model_name}")
                            print()
                            print("⚠️  請確保 RQ Worker 已重啟以應用新配置")
                            print()
                        else:
                            print(f"❌ 更新配置失敗: {update_resp.status_code}")
                            print(update_resp.text)
                            sys.exit(1)
                    else:
                        print(f"❌ 獲取配置失敗: {config_resp.status_code}")
                        print(config_resp.text)
                        sys.exit(1)
                    
                    # 步驟 3: 觸發圖譜提取
                    print("=" * 80)
                    print("步驟 3: 觸發圖譜提取")
                    print("=" * 80)
                    print("🔄 觸發圖譜提取...")
                    
                    regenerate_resp = client.post(
                        f'{base_url}{api_prefix}/files/{file_id}/regenerate',
                        headers=headers,
                        json={
                            'type': 'graph',
                            'options': {}
                        },
                        timeout=30.0
                    )
                    
                    if regenerate_resp.status_code == 200:
                        print("✅ 圖譜提取任務已提交")
                        print()
                        print("⏳ 等待圖譜提取完成...")
                        print()
                        
                        # 等待圖譜提取完成
                        max_wait = 1800  # 最多等待30分鐘
                        check_interval = 15  # 每15秒檢查一次
                        waited = 0
                        last_entities = 0
                        last_relations = 0
                        last_triples = 0
                        
                        while waited < max_wait:
                            time.sleep(check_interval)
                            waited += check_interval
                            
                            # 查詢處理狀態
                            status_resp = client.get(
                                f'{base_url}{api_prefix}/files/{file_id}/processing-status',
                                headers=headers,
                                timeout=30.0
                            )
                            
                            if status_resp.status_code == 200:
                                status = status_resp.json().get('data', {})
                                kg_extraction = status.get('kg_extraction', {})
                                
                                kg_status = kg_extraction.get('status', 'unknown')
                                kg_progress = kg_extraction.get('progress', 0)
                                
                                # 查詢圖譜統計
                                stats_resp = client.get(
                                    f'{base_url}{api_prefix}/kg/stats',
                                    headers=headers,
                                    params={'file_id': file_id},
                                    timeout=30.0
                                )
                                
                                entities = 0
                                relations = 0
                                triples = 0
                                
                                if stats_resp.status_code == 200:
                                    stats = stats_resp.json().get('data', {})
                                    entities = stats.get('entities', 0)
                                    relations = stats.get('relations', 0)
                                    triples = stats.get('triples', 0)
                                
                                # 只在有變化時顯示
                                if (entities != last_entities or
                                    relations != last_relations or
                                    triples != last_triples or
                                    waited % 60 == 0):  # 每60秒至少顯示一次
                                    
                                    print(
                                        f"   [{waited:4d}s] "
                                        f"狀態: {kg_status:12s} | "
                                        f"進度: {kg_progress:3d}% | "
                                        f"實體: {entities:4d} | "
                                        f"關係: {relations:4d} | "
                                        f"三元組: {triples:4d}"
                                    )
                                    
                                    last_entities = entities
                                    last_relations = relations
                                    last_triples = triples
                                
                                if kg_status == 'completed':
                                    print()
                                    print("=" * 80)
                                    print("✅ 圖譜提取完成！")
                                    print("=" * 80)
                                    
                                    # 顯示最終統計
                                    if stats_resp.status_code == 200:
                                        stats = stats_resp.json().get('data', {})
                                        print(f"實體數量: {stats.get('entities', 0)}")
                                        print(f"關係數量: {stats.get('relations', 0)}")
                                        print(f"三元組數量: {stats.get('triples', 0)}")
                                        print()
                                    
                                    # 顯示處理時間
                                    timing = status.get('metadata', {}).get('timing_records', {})
                                    if timing:
                                        print("處理時間記錄:")
                                        for stage, duration in timing.items():
                                            if isinstance(duration, (int, float)):
                                                print(f"  {stage}: {duration:.2f} 秒")
                                        print()
                                    
                                    print(f"文件 ID: {file_id}")
                                    print()
                                    break
                                elif kg_status == 'failed':
                                    print()
                                    print("❌ 圖譜提取失敗")
                                    print(kg_extraction.get('message', '未知錯誤'))
                                    sys.exit(1)
                            
                            if waited >= max_wait:
                                print()
                                print("⚠️  圖譜提取超時（30分鐘），請手動查詢狀態")
                                print(f"FILE_ID={file_id}")
                                break
                    else:
                        print(f"❌ 觸發圖譜提取失敗: {regenerate_resp.status_code}")
                        print(regenerate_resp.text)
                        sys.exit(1)
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

