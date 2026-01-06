#!/usr/bin/env python3
# 代碼功能說明: 通過 API 導入 Ontology 到 ArangoDB（系統級）
# 創建日期: 2025-12-31
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""通過 API 導入 Ontology JSON 文件到 ArangoDB

使用方法:
    python data/ontology/import_via_api.py
"""

import json
import requests
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"

def import_via_api(json_file, type_name):
    """通過 API 導入 Ontology"""
    print(f"\n{'='*60}")
    print(f"導入 {type_name}")
    print(f"{'='*60}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        api_data = json.load(f)
    
    print(f"📄 文件: {json_file}")
    print(f"   Ontology 名稱: {api_data.get('ontology_name')}")
    print(f"   類型: {api_data.get('type')}")
    print(f"   名稱: {api_data.get('name')}")
    print(f"   版本: {api_data.get('version')}")
    
    # 發送請求
    url = f"{API_BASE}/ontology"
    params = {"tenant_id": ""}  # 空字符串表示系統級
    
    try:
        print(f"\n🔌 連接 API: {url}")
        response = requests.post(url, json=api_data, params=params, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ 導入成功！")
            print(f"   Ontology ID: {result.get('id')}")
            return True
        else:
            print(f"❌ 導入失敗: HTTP {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   錯誤詳情: {error_detail}")
            except:
                print(f"   錯誤信息: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"⚠️  API 服務未運行或無法連接")
        print(f"   請確保 API 服務在 http://localhost:8000 運行")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 當前腳本目錄
    script_dir = Path(__file__).parent
    
    domain_file = script_dir / "domain-ai-box-api.json"
    major_file = script_dir / "major-ai-box-system-architecture-api.json"
    
    if not domain_file.exists():
        print(f"❌ 文件不存在: {domain_file}")
        exit(1)
    
    # 先導入 Domain Layer
    success1 = import_via_api(domain_file, "Domain Layer")
    
    # 如果 Domain Layer 成功，再導入 Major Layer
    if success1:
        if major_file.exists():
            import_via_api(major_file, "Major Layer")
        else:
            print(f"\n⚠️  Major Layer 文件不存在: {major_file}")
    else:
        print("\n⚠️  由於 Domain Layer 導入失敗，跳過 Major Layer")
    
    print("\n" + "="*60)
    print("導入流程完成！")
    print("="*60)
