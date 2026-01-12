# 代碼功能說明: 實時監控批量處理進度（通過API查詢）
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""實時監控批量處理進度

通過API直接查詢每個文件的處理狀態，提供實時進度監控。
支持從進度文件讀取文件列表，然後實時查詢每個文件的處理狀態。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import structlog

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = structlog.get_logger(__name__)

# API 配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
STATUS_ENDPOINT = f"{API_BASE_URL}{API_PREFIX}/files/{{file_id}}/processing-status"
LOGIN_ENDPOINT = f"{API_BASE_URL}{API_PREFIX}/auth/login"

# 默認配置
DEFAULT_USERNAME = os.getenv("TEST_USERNAME", "daniel@test.com")
DEFAULT_PASSWORD = os.getenv("TEST_PASSWORD", "1234")
DEFAULT_REFRESH_INTERVAL = 3  # 秒


def get_auth_token(
    username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD
) -> Optional[str]:
    """獲取認證 Token"""
    try:
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"].get("access_token")
        return None
    except Exception as e:
        logger.error("認證失敗", error=str(e))
        return None


def get_processing_status(file_id: str, token: str) -> Optional[Dict[str, Any]]:
    """查詢文件處理狀態"""
    try:
        url = STATUS_ENDPOINT.format(file_id=file_id)
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        return None
    except Exception as e:
        logger.debug("查詢狀態失敗", file_id=file_id, error=str(e))
        return None


def load_progress_file(progress_file: str) -> Dict[str, Any]:
    """加載進度文件"""
    if not os.path.exists(progress_file):
        return {}

    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("加載進度文件失敗", error=str(e))
        return {}


def format_status(status: str) -> str:
    """格式化狀態顯示"""
    status_map = {
        "completed": "✅ 完成",
        "partial_completed": "⚠️  部分完成",
        "processing": "🔄 處理中",
        "pending": "⏳ 等待中",
        "failed": "❌ 失敗",
        "uploaded": "📤 已上傳",
    }
    return status_map.get(status, status)


def format_progress_bar(progress: int, width: int = 30) -> str:
    """格式化進度條"""
    filled = int(width * progress / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {progress}%"


def display_status_summary(
    files_data: Dict[str, Dict[str, Any]],
    status_map: Dict[str, Dict[str, Any]],
    refresh_count: int,
) -> None:
    """顯示狀態摘要"""
    total = len(files_data)
    completed = sum(1 for s in status_map.values() if s.get("overall_status") == "completed")
    partial = sum(1 for s in status_map.values() if s.get("overall_status") == "partial_completed")
    failed = sum(1 for s in status_map.values() if s.get("overall_status") == "failed")
    processing = sum(
        1
        for s in status_map.values()
        if s.get("overall_status") in ["processing", "pending", "uploaded"]
    )

    # 計算平均進度
    avg_progress = 0
    if status_map:
        total_progress = sum(s.get("overall_progress", 0) for s in status_map.values())
        avg_progress = total_progress / len(status_map)

    print("\n" + "=" * 80)
    print(f"批量處理進度監控 - {time.strftime('%Y-%m-%d %H:%M:%S')} (刷新次數: {refresh_count})")
    print("=" * 80)
    print(f"\n總文件數: {total}")
    print(
        f"  {format_status('completed')}: {completed} ({completed/total*100:.1f}%)"
        if total > 0
        else ""
    )
    print(
        f"  {format_status('partial_completed')}: {partial} ({partial/total*100:.1f}%)"
        if total > 0
        else ""
    )
    print(
        f"  {format_status('processing')}: {processing} ({processing/total*100:.1f}%)"
        if total > 0
        else ""
    )
    print(f"  {format_status('failed')}: {failed} ({failed/total*100:.1f}%)" if total > 0 else "")
    print(f"\n平均進度: {format_progress_bar(int(avg_progress))}")
    print("\n" + "-" * 80)


def display_file_details(
    files_data: Dict[str, Dict[str, Any]],
    status_map: Dict[str, Dict[str, Any]],
    max_display: int = 10,
) -> None:
    """顯示文件詳細狀態"""
    print("\n最近處理的文件:")
    print("-" * 80)

    # 按狀態和進度排序
    file_list = []
    for file_path, file_data in files_data.items():
        file_id = file_data.get("file_id")
        if not file_id:
            continue

        status_info = status_map.get(file_id, {})
        overall_status = status_info.get("overall_status", "unknown")
        overall_progress = status_info.get("overall_progress", 0)

        file_list.append(
            {
                "file_path": file_path,
                "file_id": file_id,
                "filename": Path(file_path).name,
                "status": overall_status,
                "progress": overall_progress,
                "status_info": status_info,
            }
        )

    # 排序：處理中 > 部分完成 > 完成 > 失敗
    status_priority = {
        "processing": 0,
        "pending": 0,
        "uploaded": 0,
        "partial_completed": 1,
        "completed": 2,
        "failed": 3,
    }
    file_list.sort(key=lambda x: (status_priority.get(x["status"], 99), -x["progress"]))

    # 顯示前 N 個
    for i, file_info in enumerate(file_list[:max_display], 1):
        filename = file_info["filename"][:50]
        status = format_status(file_info["status"])
        progress_bar = format_progress_bar(file_info["progress"], width=20)

        # 獲取詳細狀態信息
        status_info = file_info["status_info"]
        details = []
        if status_info.get("chunking"):
            chunking = status_info["chunking"]
            details.append(f"分塊: {chunking.get('progress', 0)}%")
        if status_info.get("vectorization"):
            vectorization = status_info["vectorization"]
            details.append(f"向量: {vectorization.get('progress', 0)}%")
        if status_info.get("kg_extraction"):
            kg = status_info["kg_extraction"]
            details.append(f"圖譜: {kg.get('progress', 0)}%")
            if kg.get("entities_count"):
                details.append(f"實體: {kg.get('entities_count')}")
            if kg.get("relations_count"):
                details.append(f"關係: {kg.get('relations_count')}")

        detail_str = " | ".join(details) if details else ""
        print(f"{i:2d}. {status} {progress_bar} {filename}")
        if detail_str:
            print(f"    {detail_str}")

    if len(file_list) > max_display:
        print(f"\n... 還有 {len(file_list) - max_display} 個文件未顯示")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="實時監控批量處理進度")
    parser.add_argument(
        "--progress-json",
        type=str,
        default="system_docs_processing_progress.json",
        help="進度文件路徑",
    )
    parser.add_argument(
        "--refresh-interval",
        type=int,
        default=DEFAULT_REFRESH_INTERVAL,
        help=f"刷新間隔（秒，默認: {DEFAULT_REFRESH_INTERVAL}）",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=DEFAULT_USERNAME,
        help="用戶名",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=DEFAULT_PASSWORD,
        help="密碼",
    )
    parser.add_argument(
        "--max-display",
        type=int,
        default=10,
        help="最多顯示的文件數（默認: 10）",
    )

    args = parser.parse_args()

    # 獲取認證 Token
    logger.info("正在認證", username=args.username)
    token = get_auth_token(args.username, args.password)
    if not token:
        logger.error("認證失敗，退出")
        sys.exit(1)

    # 加載進度文件
    progress = load_progress_file(args.progress_json)
    if not progress:
        logger.error("無法加載進度文件", file=args.progress_json)
        logger.info("等待進度文件創建...")
        while not os.path.exists(args.progress_json):
            time.sleep(1)
        progress = load_progress_file(args.progress_json)
        if not progress:
            logger.error("進度文件仍然無法加載")
            sys.exit(1)

    files_data = progress.get("files", {})
    if not files_data:
        logger.error("進度文件中沒有文件記錄")
        sys.exit(1)

    logger.info("開始監控", total_files=len(files_data), refresh_interval=args.refresh_interval)

    # 提取所有 file_id
    file_ids = []
    for file_data in files_data.values():
        file_id = file_data.get("file_id")
        if file_id:
            file_ids.append(file_id)

    if not file_ids:
        logger.error("沒有找到有效的 file_id")
        sys.exit(1)

    # 實時監控循環
    refresh_count = 0
    try:
        while True:
            refresh_count += 1
            status_map: Dict[str, Dict[str, Any]] = {}

            # 查詢所有文件的狀態
            for file_id in file_ids:
                status = get_processing_status(file_id, token)
                if status:
                    status_map[file_id] = status

            # 清屏並顯示狀態
            os.system("clear" if os.name != "nt" else "cls")
            display_status_summary(files_data, status_map, refresh_count)
            display_file_details(files_data, status_map, args.max_display)

            # 檢查是否全部完成
            all_done = all(
                s.get("overall_status") in ["completed", "partial_completed", "failed"]
                for s in status_map.values()
            )
            if all_done and len(status_map) == len(file_ids):
                print("\n" + "=" * 80)
                print("✅ 所有文件處理完成！")
                print("=" * 80)
                break

            print(f"\n下次刷新: {args.refresh_interval}秒後 (按 Ctrl+C 停止)")
            time.sleep(args.refresh_interval)

    except KeyboardInterrupt:
        print("\n\n監控已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
