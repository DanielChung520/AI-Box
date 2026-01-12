#!/usr/bin/env python3
# 代碼功能說明: 通過 API 更新 KG 提取模型配置
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""通過 API 更新 KG 提取模型配置為 Gemini 最新模型"""

import sys
from pathlib import Path

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


def login(username: str = "daniel@test.com", password: str = "test123") -> str:
    """登錄獲取 access token"""
    url = f"{API_BASE}/auth/login"
    data = {"username": username, "password": password}

    response = requests.post(url, json=data, timeout=60)
    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            token = result.get("data", {}).get("access_token")
        else:
            token = result.get("access_token")

        if token:
            return token
        else:
            raise ValueError("無法獲取 access_token")
    else:
        raise ValueError(f"登錄失敗: {response.status_code} - {response.text}")


def update_kg_config(token: str, model_name: str = "gemini-2.5-flash"):
    """更新 KG 提取模型配置"""
    # 先獲取當前配置
    url = f"{API_BASE}/config/kg_extraction"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"❌ 獲取配置失敗: {response.status_code}")
        print(response.text)
        return False

    current_config = response.json().get("data", {})
    config_data = current_config.get("config_data", {})

    # 更新模型配置
    config_data["ner_model_type"] = "gemini"
    config_data["ner_model"] = model_name
    config_data["re_model_type"] = "gemini"
    config_data["re_model"] = model_name
    config_data["rt_model_type"] = "gemini"
    config_data["rt_model"] = model_name

    # 更新配置
    update_url = f"{API_BASE}/config/kg_extraction"
    update_data = {"config_data": config_data, "is_active": True}

    response = requests.put(update_url, headers=headers, json=update_data, timeout=10)
    if response.status_code == 200:
        print("✅ 配置更新成功")
        print(f"  NER: gemini - {model_name}")
        print(f"  RE: gemini - {model_name}")
        print(f"  RT: gemini - {model_name}")
        return True
    else:
        print(f"❌ 更新配置失敗: {response.status_code}")
        print(response.text)
        return False


def main():
    model_name = sys.argv[1] if len(sys.argv) > 1 else "gemini-2.5-flash"

    print("=" * 60)
    print("通過 API 更新 KG 提取模型配置")
    print("=" * 60)
    print(f"模型名稱: {model_name}")
    print()

    try:
        # 登錄
        print("正在登錄...")
        token = login()
        print("✅ 登錄成功")
        print()

        # 更新配置
        print("正在更新配置...")
        if update_kg_config(token, model_name):
            print()
            print("=" * 60)
            print("更新完成")
            print("=" * 60)
            print()
            print("⚠️  請重啟 RQ Worker 以應用新配置:")
            print("  ./scripts/start_services.sh restart rq_worker")
            return 0
        else:
            print()
            print("=" * 60)
            print("更新失敗")
            print("=" * 60)
            return 1
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
