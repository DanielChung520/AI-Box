#!/usr/bin/env python3
# 代碼功能說明: 測試文件上傳、向量化和圖譜提取
# 創建日期: 2026-01-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-03

"""測試文件上傳、向量化和圖譜提取"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

API_BASE = "http://localhost:8000/api/v1"


def login(username: str = "daniel@test.com", password: str = "test123") -> Optional[str]:
    """登錄獲取 access token"""
    print(f"\n🔐 登錄用戶: {username}")
    url = f"{API_BASE}/auth/login"
    data = {"username": username, "password": password}
    
    try:
        response = requests.post(url, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            # API 返回格式: {"success": true, "data": {"access_token": "..."}}
            if result.get("success"):
                token = result.get("data", {}).get("access_token")
            else:
                token = result.get("access_token")  # 兼容其他格式
            if token:
                print(f"✅ 登錄成功")
                return token
            else:
                print(f"❌ 無法獲取 access_token")
                print(f"   響應: {result}")
                return None
        else:
            print(f"❌ 登錄失敗: HTTP {response.status_code}")
            print(f"   錯誤: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登錄錯誤: {e}")
        return None


def upload_file(file_path: Path, token: str, task_id: Optional[str] = None) -> Optional[dict]:
    """上傳文件"""
    print(f"\n📤 上傳文件: {file_path.name}")
    print(f"   文件大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    url = f"{API_BASE}/files/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 準備 multipart/form-data
    with open(file_path, "rb") as f:
        files = {"files": (file_path.name, f, "application/pdf")}
        data = {}
        if task_id:
            data["task_id"] = task_id
        
        try:
            print(f"   上傳中...")
            response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    uploaded = result.get("data", {}).get("uploaded", [])
                    if uploaded:
                        file_info = uploaded[0]
                        print(f"✅ 文件上傳成功")
                        print(f"   File ID: {file_info.get('file_id')}")
                        print(f"   文件名: {file_info.get('filename')}")
                        print(f"   文件類型: {file_info.get('file_type')}")
                        print(f"   文件大小: {file_info.get('file_size')} bytes")
                        return file_info
                else:
                    print(f"❌ 上傳失敗: {result.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"❌ 上傳失敗: HTTP {response.status_code}")
                print(f"   錯誤: {response.text}")
                return None
        except Exception as e:
            print(f"❌ 上傳錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None


def check_processing_status(file_id: str, token: str) -> dict:
    """檢查處理狀態"""
    url = f"{API_BASE}/files/{file_id}/processing-status"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            return {}
    except Exception as e:
        print(f"⚠️  查詢狀態錯誤: {e}")
        return {}


def monitor_processing(file_id: str, token: str, max_wait: int = 600) -> bool:
    """監控處理進度"""
    print(f"\n📊 監控處理進度 (最多等待 {max_wait} 秒)...")
    start_time = time.time()
    last_progress = -1
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"\n⏱️  超時: 已等待 {max_wait} 秒")
            return False
        
        status = check_processing_status(file_id, token)
        overall_status = status.get("overall_status", "unknown")
        overall_progress = status.get("overall_progress", 0)
        
        # 只在進度變化時打印
        if overall_progress != last_progress:
            print(f"   進度: {overall_progress}% | 狀態: {overall_status} | 已用時: {elapsed:.0f}秒")
            last_progress = overall_progress
        
        # 檢查各階段狀態
        chunking = status.get("chunking", {})
        vectorization = status.get("vectorization", {})
        storage = status.get("storage", {})
        kg_extraction = status.get("kg_extraction", {})
        
        if overall_status == "completed":
            print(f"\n✅ 處理完成！")
            print(f"   總用時: {elapsed:.1f} 秒")
            print(f"\n📊 處理結果:")
            print(f"   分塊階段:")
            print(f"     - 狀態: {chunking.get('status', 'unknown')}")
            print(f"     - 進度: {chunking.get('progress', 0)}%")
            print(f"     - 分塊數: {chunking.get('chunk_count', 0)}")
            print(f"   向量化階段:")
            print(f"     - 狀態: {vectorization.get('status', 'unknown')}")
            print(f"     - 進度: {vectorization.get('progress', 0)}%")
            print(f"   存儲階段:")
            print(f"     - 狀態: {storage.get('status', 'unknown')}")
            print(f"     - 進度: {storage.get('progress', 0)}%")
            print(f"     - 向量數: {storage.get('vector_count', 0)}")
            print(f"   圖譜提取階段:")
            print(f"     - 狀態: {kg_extraction.get('status', 'unknown')}")
            print(f"     - 進度: {kg_extraction.get('progress', 0)}%")
            print(f"     - 實體數 (NER): {kg_extraction.get('entities_count', 0)}")
            print(f"     - 關係數 (RE): {kg_extraction.get('relations_count', 0)}")
            print(f"     - 三元組數 (RT): {kg_extraction.get('triples_count', 0)}")
            return True
        elif overall_status == "failed":
            print(f"\n❌ 處理失敗")
            message = status.get("message", "Unknown error")
            print(f"   錯誤信息: {message}")
            return False
        
        time.sleep(5)  # 每 5 秒檢查一次


def get_kg_stats(file_id: str, token: str) -> Optional[dict]:
    """獲取圖譜統計信息"""
    url = f"{API_BASE}/files/{file_id}/kg/stats"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            return None
    except Exception as e:
        print(f"⚠️  獲取圖譜統計錯誤: {e}")
        return None


def main():
    file_path = Path("docs/亮能環科.pdf")
    task_id = None
    
    if not file_path.exists():
        print(f"❌ 錯誤：文件不存在: {file_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("文件上傳、向量化和圖譜提取測試")
    print("=" * 60)
    
    # 1. 登錄
    token = login()
    if not token:
        print("❌ 無法登錄，退出")
        sys.exit(1)
    
    # 2. 上傳文件
    file_info = upload_file(file_path, token, task_id)
    if not file_info:
        print("❌ 文件上傳失敗，退出")
        sys.exit(1)
    
    file_id = file_info.get("file_id")
    if not file_id:
        print("❌ 無法獲取 File ID，退出")
        sys.exit(1)
    
    # 3. 監控處理進度
    success = monitor_processing(file_id, token, max_wait=600)
    
    # 4. 獲取圖譜統計（如果處理完成）
    if success:
        print(f"\n📈 獲取圖譜統計信息...")
        kg_stats = get_kg_stats(file_id, token)
        if kg_stats:
            print(f"✅ 圖譜統計:")
            print(f"   實體總數: {kg_stats.get('total_entities', 0)}")
            print(f"   關係總數: {kg_stats.get('total_relations', 0)}")
            print(f"   三元組總數: {kg_stats.get('total_triples', 0)}")
            print(f"   實體類型分佈:")
            for entity_type, count in kg_stats.get('entity_type_distribution', {}).items():
                print(f"     - {entity_type}: {count}")
            print(f"   關係類型分佈:")
            for relation_type, count in kg_stats.get('relation_type_distribution', {}).items():
                print(f"     - {relation_type}: {count}")
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
    print(f"File ID: {file_id}")
    if task_id:
        print(f"Task ID: {task_id}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
