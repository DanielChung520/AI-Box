#!/usr/bin/env python3
# 代碼功能說明: 通過 API 將 tools_registry.json 中的工具同步到 ArangoDB
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""通過 API 將 tools_registry.json 中的工具同步到 ArangoDB"""

import json
from pathlib import Path

import requests

# API 配置
API_BASE_URL = "http://localhost:8000/api/v1"
TOOLS_REGISTRY_ENDPOINT = f"{API_BASE_URL}/tools/registry"


def load_tools_from_json():
    """從 JSON 文件載入工具列表"""
    json_path = Path("tools/tools_registry.json")
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("tools", [])


def get_auth_token():
    """獲取認證 token（如果需要）"""
    # 如果 API 需要認證，可以在這裡添加獲取 token 的邏輯
    # 目前先返回 None，如果 API 需要認證會返回 401
    return None


def sync_tools_via_api():
    """通過 API 同步工具"""
    print("=" * 60)
    print("通過 API 同步工具到 ArangoDB")
    print("=" * 60)
    print()

    # 載入工具列表
    print("📂 載入 JSON 文件...")
    tools = load_tools_from_json()
    print(f"✅ 找到 {len(tools)} 個工具")
    print()

    # 檢查現有工具
    print("🔍 檢查現有工具...")
    try:
        response = requests.get(TOOLS_REGISTRY_ENDPOINT, params={"is_active": None})
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                existing_tools = data["data"].get("tools", [])
                existing_names = {tool["name"] for tool in existing_tools}
                print(f"✅ ArangoDB 中現有 {len(existing_tools)} 個工具")
            else:
                existing_names = set()
                print("⚠️  無法獲取現有工具列表")
        else:
            existing_names = set()
            print(f"⚠️  無法獲取現有工具列表 (HTTP {response.status_code})")
    except Exception as e:
        print(f"⚠️  無法獲取現有工具列表: {e}")
        existing_names = set()
    print()

    # 同步工具
    print("📤 開始同步工具...")
    print()

    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    token = get_auth_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for i, tool_data in enumerate(tools, 1):
        tool_name = tool_data.get("name", "unknown")
        print(f"[{i}/{len(tools)}] {tool_name}...", end=" ")

        try:
            # 準備請求數據
            request_data = {
                "name": tool_data["name"],
                "version": tool_data["version"],
                "category": tool_data["category"],
                "description": tool_data["description"],
                "purpose": tool_data["purpose"],
                "use_cases": tool_data.get("use_cases", []),
                "input_parameters": tool_data.get("input_parameters", {}),
                "output_fields": tool_data.get("output_fields", {}),
                "example_scenarios": tool_data.get("example_scenarios", []),
            }

            if tool_name in existing_names:
                # 更新現有工具（移除 name 字段，因為 update API 不需要）
                update_data = {k: v for k, v in request_data.items() if k != "name"}
                update_data["is_active"] = True  # 確保工具是啟用的
                update_url = f"{TOOLS_REGISTRY_ENDPOINT}/{tool_name}"
                response = requests.put(update_url, json=update_data, headers=headers)
                if response.status_code == 200:
                    try:
                        resp_data = response.json()
                        if resp_data.get("success"):
                            updated_count += 1
                            print("✅ 更新")
                        else:
                            error_msg = resp_data.get("message", "Update failed")
                            print(f"❌ {error_msg}")
                            error_count += 1
                    except Exception:
                        updated_count += 1
                        print("✅ 更新")
                else:
                    try:
                        error_msg = response.json().get("detail", f"HTTP {response.status_code}")
                        print(f"❌ {error_msg}")
                    except Exception:
                        print(f"❌ HTTP {response.status_code}")
                    error_count += 1
            else:
                # 創建新工具
                response = requests.post(
                    TOOLS_REGISTRY_ENDPOINT, json=request_data, headers=headers
                )
                if response.status_code in [200, 201]:
                    # 檢查響應內容確認是否成功
                    try:
                        resp_data = response.json()
                        if resp_data.get("success"):
                            created_count += 1
                            print("✅ 創建")
                        else:
                            error_msg = resp_data.get("message", "Unknown error")
                            print(f"❌ {error_msg}")
                            error_count += 1
                    except Exception:
                        # 如果響應不是 JSON，但狀態碼是 200/201，認為成功
                        created_count += 1
                        print("✅ 創建")
                elif response.status_code == 400:
                    try:
                        error_msg = response.json().get("detail", "Bad Request")
                        if "already exists" in error_msg.lower():
                            skipped_count += 1
                            print("⏭️  已存在")
                        else:
                            print(f"❌ {error_msg}")
                            error_count += 1
                    except Exception:
                        print(f"❌ HTTP {response.status_code}")
                        error_count += 1
                else:
                    try:
                        error_msg = response.json().get("detail", f"HTTP {response.status_code}")
                        print(f"❌ {error_msg}")
                    except Exception:
                        print(f"❌ HTTP {response.status_code}")
                    error_count += 1

        except Exception as e:
            print(f"❌ {e}")
            error_count += 1

    # 顯示統計
    print()
    print("=" * 60)
    print("同步完成")
    print("=" * 60)
    print(f"✅ 創建: {created_count}")
    print(f"🔄 更新: {updated_count}")
    print(f"⏭️  跳過: {skipped_count}")
    print(f"❌ 錯誤: {error_count}")
    print(f"📊 總計: {len(tools)}")
    print()

    # 驗證同步結果
    print("🔍 驗證同步結果...")
    try:
        response = requests.get(TOOLS_REGISTRY_ENDPOINT, params={"is_active": True})
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                final_tools = data["data"].get("tools", [])
                print(f"✅ ArangoDB 中現有 {len(final_tools)} 個啟用的工具")
            else:
                print("⚠️  無法驗證同步結果")
        else:
            print(f"⚠️  無法驗證同步結果 (HTTP {response.status_code})")
    except Exception as e:
        print(f"⚠️  無法驗證: {e}")


if __name__ == "__main__":
    try:
        sync_tools_via_api()
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 發生錯誤: {e}")
        import traceback

        traceback.print_exc()
