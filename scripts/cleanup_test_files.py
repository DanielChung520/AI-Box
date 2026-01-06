#!/usr/bin/env python3
# 代碼功能說明: 清理測試文件腳本
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""清理測試文件腳本

清理與測試相關的文件數據：
1. 文件名包含 "生质能源" 或 "測試" 的文件
2. 或指定文件 ID 列表

使用方法:
    # 清理特定文件名的文件
    python scripts/cleanup_test_files.py --filename-pattern "生质能源"

    # 清理指定文件 ID
    python scripts/cleanup_test_files.py --file-ids file_id1 file_id2

    # 清理所有測試文件（交互式確認）
    python scripts/cleanup_test_files.py --clean-all-test-files
"""

import argparse
import requests
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

API_BASE = "http://localhost:8000/api/v1"


def login(username: str = "daniel@test.com", password: str = "test123") -> Optional[str]:
    """登錄獲取 token"""
    url = f"{API_BASE}/auth/login"
    data = {"username": username, "password": password}
    try:
        response = requests.post(url, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            token = result.get("data", {}).get("access_token") or result.get("access_token")
            return token
    except Exception as e:
        print(f"[錯誤] 登錄失敗: {e}")
    return None


def list_files(token: str, filename_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出文件（使用系統 API）"""
    url = f"{API_BASE}/files/tree"
    headers = {"Authorization": f"Bearer {token}"}
    params = {}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        if response.status_code == 200:
            result = response.json()
            files = result.get("data", {}).get("files", [])

            if filename_pattern:
                # 過濾文件名包含模式的文件
                files = [
                    f for f in files if filename_pattern.lower() in f.get("filename", "").lower()
                ]

            return files
    except Exception as e:
        print(f"[錯誤] 列出文件失敗: {e}")

    return []


def delete_file(file_id: str, token: str) -> bool:
    """刪除文件（使用系統 API）"""
    url = f"{API_BASE}/files/{file_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.delete(url, headers=headers, timeout=60)
        if response.status_code == 200:
            return True
        else:
            print(f"[錯誤] 刪除文件失敗: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[錯誤] 刪除請求失敗: {e}")
        return False


def cleanup_files(
    file_ids: Optional[List[str]] = None,
    filename_pattern: Optional[str] = None,
    clean_all_test: bool = False,
) -> None:
    """清理文件

    Args:
        file_ids: 文件 ID 列表（可選）
        filename_pattern: 文件名模式（可選）
        clean_all_test: 是否清理所有測試文件
    """
    print("[清理] 開始清理測試文件...")

    # 登錄
    token = login()
    if not token:
        print("[錯誤] 無法登錄，清理中止")
        sys.exit(1)

    files_to_delete = []

    if file_ids:
        # 直接使用提供的文件 ID
        files_to_delete = [{"file_id": fid} for fid in file_ids]
    elif filename_pattern:
        # 根據文件名模式查找
        print(f"[查找] 搜索文件名包含 '{filename_pattern}' 的文件...")
        files = list_files(token, filename_pattern)
        files_to_delete = files
    elif clean_all_test:
        # 清理所有測試相關文件
        test_patterns = ["生质能源", "測試", "test", "測試文件"]
        all_files = list_files(token)
        files_to_delete = [
            f
            for f in all_files
            if any(pattern in f.get("filename", "").lower() for pattern in test_patterns)
        ]
    else:
        print("[錯誤] 請指定清理方式：--file-ids, --filename-pattern 或 --clean-all-test-files")
        sys.exit(1)

    if not files_to_delete:
        print("[信息] 未找到需要清理的文件")
        return

    print(f"[信息] 找到 {len(files_to_delete)} 個文件需要清理:")
    for f in files_to_delete:
        file_id = f.get("file_id") or f.get("id")
        filename = f.get("filename") or f.get("name", "Unknown")
        print(f"  - {file_id}: {filename}")

    # 確認
    if not clean_all_test and not file_ids:
        confirm = input("\n是否確認刪除這些文件？(yes/no): ")
        if confirm.lower() != "yes":
            print("[取消] 清理已取消")
            return

    # 執行刪除
    deleted_count = 0
    failed_count = 0

    for f in files_to_delete:
        file_id = f.get("file_id") or f.get("id")
        filename = f.get("filename") or f.get("name", "Unknown")

        print(f"[刪除] {file_id} ({filename})...")
        if delete_file(file_id, token):
            deleted_count += 1
            print("  ✅ 刪除成功")
        else:
            failed_count += 1
            print("  ❌ 刪除失敗")

    print(f"\n[完成] 清理完成：成功 {deleted_count} 個，失敗 {failed_count} 個")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="清理測試文件腳本")
    parser.add_argument("--file-ids", nargs="+", help="文件 ID 列表")
    parser.add_argument("--filename-pattern", help="文件名模式（部分匹配）")
    parser.add_argument(
        "--clean-all-test-files",
        action="store_true",
        help="清理所有測試相關文件（交互式確認）",
    )

    args = parser.parse_args()

    if not any([args.file_ids, args.filename_pattern, args.clean_all_test_files]):
        parser.print_help()
        sys.exit(1)

    cleanup_files(
        file_ids=args.file_ids,
        filename_pattern=args.filename_pattern,
        clean_all_test=args.clean_all_test_files,
    )


if __name__ == "__main__":
    main()
