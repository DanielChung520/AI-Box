#!/usr/bin/env python3
# 代碼功能說明: 批量處理系統設計文檔，進行知識圖譜提取
# 創建日期: 2025-12-31
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""批量上傳系統設計文檔並進行知識圖譜提取"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# 加載環境變數
load_dotenv(project_root / ".env")

from database.arangodb.client import ArangoDBClient

# API 配置
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_USERNAME = "test"
TEST_PASSWORD = "test"

# 文檔目錄
DOCS_DIR = project_root / "docs/系统设计文档"

# 進度文件（用於斷點續傳）
PROGRESS_FILE = project_root / "scripts/kg_extract_progress.json"
RESULT_FILE = project_root / "scripts/kg_extract_all_results.json"


def get_auth_token() -> str:
    """獲取 JWT 認證 token"""
    print("🔐 登錄獲取認證 token...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=10,
    )

    if response.status_code != 200:
        raise Exception(f"登錄失敗: {response.status_code} - {response.text}")

    data = response.json()
    if not data.get("success"):
        raise Exception(f"登錄失敗: {data.get('message', 'Unknown error')}")

    token = data["data"]["access_token"]
    print("✅ 登錄成功")
    return token


def upload_file(file_path: Path, token: str) -> Optional[str]:
    """上傳文件並返回 file_id"""
    try:
        with open(file_path, "rb") as f:
            files = {"files": (file_path.name, f, "text/markdown")}
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.post(
                f"{API_BASE_URL}/files/upload",
                files=files,
                headers=headers,
                timeout=120,
            )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        if not data.get("success"):
            raise Exception(data.get("message", "Unknown error"))

        uploaded_files = data["data"]["uploaded"]
        if not uploaded_files:
            raise Exception("未返回文件信息")

        return uploaded_files[0]["file_id"]
    except Exception as e:
        print(f"      ❌ 上傳失敗: {e}")
        return None


def wait_for_processing(file_id: str, token: str, timeout: int = 600) -> bool:
    """等待文件處理完成"""
    start_time = time.time()
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            return False

        try:
            response = requests.get(
                f"{API_BASE_URL}/files/{file_id}/processing-status",
                headers=headers,
                timeout=10,
            )

            if response.status_code != 200:
                time.sleep(5)
                continue

            data = response.json()
            if not data.get("success"):
                time.sleep(5)
                continue

            status_data = data["data"]
            kg_status = status_data.get("kg_extraction", {})
            kg_status_value = kg_status.get("status", "")
            kg_progress = kg_status.get("progress", 0)

            if kg_status_value == "completed":
                return True
            elif kg_status_value == "failed":
                return False

            time.sleep(5)
        except Exception:
            time.sleep(5)


def verify_kg_extraction(file_id: str) -> Dict[str, Any]:
    """驗證知識圖譜提取結果"""
    client = ArangoDBClient()
    db = client.db

    entities_col = db.collection("entities")
    entities = list(entities_col.find({"file_id": file_id}))

    relations_col = db.collection("relations")
    relations = list(relations_col.find({"file_id": file_id}))

    entity_types = {}
    for entity in entities:
        entity_type = entity.get("type", "UNKNOWN")
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    return {
        "file_id": file_id,
        "entities_count": len(entities),
        "relations_count": len(relations),
        "entity_types": entity_types,
    }


def load_progress() -> Dict[str, Any]:
    """加載進度文件"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": [], "failed": []}


def save_progress(progress: Dict[str, Any]) -> None:
    """保存進度文件"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def find_all_markdown_files() -> List[Path]:
    """查找所有 Markdown 文件"""
    md_files = []
    for md_file in DOCS_DIR.rglob("*.md"):
        # 排除某些文件
        if md_file.name.startswith(".") or md_file.name.lower() == "readme.md":
            continue
        md_files.append(md_file)

    # 按文件大小排序（從小到大）
    md_files.sort(key=lambda p: p.stat().st_size)
    return md_files


def main():
    """主函數"""
    print("=" * 60)
    print("批量處理系統設計文檔 - 知識圖譜提取")
    print("=" * 60)

    # 查找所有文件
    all_files = find_all_markdown_files()
    print(f"\n📁 找到 {len(all_files)} 個 Markdown 文件")

    # 加載進度
    progress = load_progress()
    processed_file_ids = {item["file_path"] for item in progress.get("processed", [])}
    failed_files = {item["file_path"] for item in progress.get("failed", [])}

    # 過濾已處理的文件
    remaining_files = [
        f
        for f in all_files
        if str(f.relative_to(project_root)) not in processed_file_ids
        and str(f.relative_to(project_root)) not in failed_files
    ]

    if not remaining_files:
        print("✅ 所有文件都已處理完成！")
        return 0

    print(f"📋 待處理文件: {len(remaining_files)} 個")
    print(f"   已處理: {len(processed_file_ids)} 個")
    print(f"   失敗: {len(failed_files)} 個")

    # 獲取認證 token
    try:
        token = get_auth_token()
    except Exception as e:
        print(f"❌ 無法獲取認證 token: {e}")
        return 1

    # 處理文件
    results = {
        "processed": progress.get("processed", []),
        "failed": progress.get("failed", []),
        "total": len(all_files),
    }

    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(remaining_files, 1):
        file_relative = str(file_path.relative_to(project_root))
        print(f"\n[{i}/{len(remaining_files)}] 處理: {file_path.name}")
        print(f"   路徑: {file_relative}")
        print(f"   大小: {file_path.stat().st_size / 1024:.2f} KB")

        try:
            # 上傳文件
            file_id = upload_file(file_path, token)
            if not file_id:
                results["failed"].append(
                    {
                        "file_path": file_relative,
                        "error": "上傳失敗",
                        "timestamp": time.time(),
                    }
                )
                fail_count += 1
                save_progress(results)
                continue

            print(f"   ✅ 上傳成功，file_id: {file_id}")

            # 等待處理完成
            print("   ⏳ 等待處理完成...")
            if wait_for_processing(file_id, token, timeout=600):
                print("   ✅ 處理完成")

                # 驗證結果
                verification = verify_kg_extraction(file_id)
                results["processed"].append(
                    {
                        "file_path": file_relative,
                        "file_id": file_id,
                        "entities_count": verification["entities_count"],
                        "relations_count": verification["relations_count"],
                        "entity_types": verification["entity_types"],
                        "timestamp": time.time(),
                    }
                )
                success_count += 1
            else:
                print("   ❌ 處理超時或失敗")
                results["failed"].append(
                    {
                        "file_path": file_relative,
                        "file_id": file_id,
                        "error": "處理超時或失敗",
                        "timestamp": time.time(),
                    }
                )
                fail_count += 1

            # 保存進度
            save_progress(results)

        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
            results["failed"].append(
                {
                    "file_path": file_relative,
                    "error": str(e),
                    "timestamp": time.time(),
                }
            )
            fail_count += 1
            save_progress(results)

    # 保存最終結果
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 輸出總結
    print("\n" + "=" * 60)
    print("處理完成！")
    print("=" * 60)
    print(f"總文件數: {len(all_files)}")
    print(f"成功處理: {success_count + len(processed_file_ids)} 個")
    print(f"失敗: {fail_count + len(failed_files)} 個")
    print(f"進度文件: {PROGRESS_FILE}")
    print(f"結果文件: {RESULT_FILE}")
    print("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
