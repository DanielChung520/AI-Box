#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼功能說明: SeaweedFS 清理腳本
創建日期: 2026-01-20
創建人: Daniel Chung

功能:
- 清除 tasks/SystemDoc/ 目錄下的測試文件
- 清除 tasks/ 下所有測試文件
- 清除指定 bucket 中的文件

使用方法:
    python3 scripts/cleanup_seaweedfs.py [--prefix PREFIX] [--bucket BUCKET] [--dry-run]

示例:
    # 清除 SystemDoc 任務下的文件（預設）
    python3 scripts/cleanup_seaweedfs.py

    # 清除所有 tasks/ 目錄下的文件
    python3 scripts/cleanup_seaweedfs.py --prefix tasks/

    # 僅預覽不實際刪除
    python3 scripts/cleanup_seaweedfs.py --dry-run
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import structlog

# 添加項目根目錄
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = structlog.get_logger(__name__)

# SeaweedFS 配置（從 .env 讀取）
SEAWEEDFS_FILER_HOST = (
    os.getenv("AI_BOX_SEAWEEDFS_FILER_ENDPOINT", "http://localhost:8888")
    .replace("http://", "")
    .replace("https://", "")
)
SEAWEEDFS_FILER_PORT = 8888
SEAWEEDFS_ACCESS_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin")
SEAWEEDFS_SECRET_KEY = os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123")
SEAWEEDFS_BUCKET = os.getenv("AI_BOX_SEAWEEDFS_BUCKET", "bucket-ai-box-assets")


def get_filer_url():
    """獲取 Filer URL"""
    return f"http://{SEAWEEDFS_FILER_HOST}"


def get_auth_header():
    """獲取 Basic Auth Header"""
    import base64

    credentials = f"{SEAWEEDFS_ACCESS_KEY}:{SEAWEEDFS_SECRET_KEY}"
    return "Basic " + base64.b64encode(credentials.encode()).decode()


def list_directory(path: str = "/") -> list:
    """列出目錄內容"""
    filer_url = get_filer_url()
    url = f"{filer_url}{path}?format=json"

    headers = {"Authorization": get_auth_header()}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("entries", [])
    except urllib.error.HTTPError as e:
        logger.error(f"無法列出目錄 {path}: {e.code} {e.reason}")
        return []
    except Exception as e:
        logger.error(f"列出目錄 {path} 失敗: {e}")
        return []


def delete_file(full_path: str) -> bool:
    """刪除文件"""
    filer_url = get_filer_url()
    url = f"{filer_url}{full_path}"

    headers = {"Authorization": get_auth_header()}
    req = urllib.request.Request(url, headers=headers, method="DELETE")

    try:
        with urllib.request.urlopen(req):
            return True
    except urllib.error.HTTPError as e:
        logger.error(f"刪除文件失敗 {full_path}: {e.code} {e.reason}")
        return False
    except Exception as e:
        logger.error(f"刪除文件 {full_path} 失敗: {e}")
        return False


def delete_directory_recursive(path: str, dry_run: bool = False) -> tuple:
    """
    遞歸刪除目錄內容

    Returns:
        (deleted_count, error_count)
    """
    deleted = 0
    errors = 0

    entries = list_directory(path)

    for entry in entries:
        full_path = entry.get("FullPath", "")
        is_dir = entry.get("IsDir", False)

        if is_dir:
            # 遞歸處理子目錄
            sub_deleted, sub_errors = delete_directory_recursive(full_path, dry_run)
            deleted += sub_deleted
            errors += sub_errors

            # 刪除空目錄
            if not dry_run:
                # SeaweedFS filer 會自動刪除空目錄
                pass
        else:
            # 刪除文件
            if dry_run:
                logger.info(f"[DRY-RUN] 將刪除: {full_path}")
                deleted += 1
            else:
                if delete_file(full_path):
                    logger.info(f"已刪除: {full_path}")
                    deleted += 1
                else:
                    errors += 1

    return deleted, errors


def cleanup_task_files(
    task_id: str = "SystemDoc", bucket: str = None, dry_run: bool = False
) -> dict:
    """
    清理指定任務的文件

    Args:
        task_id: 任務 ID
        bucket: bucket 名稱（可選）
        dry_run: 是否僅預覽

    Returns:
        清理結果統計
    """
    filer_url = get_filer_url()

    # 構建路徑
    if bucket:
        base_path = f"/{bucket}/tasks/{task_id}/"
    else:
        base_path = f"/tasks/{task_id}/"

    logger.info("=" * 60)
    logger.info("清理 SeaweedFS 文件")
    logger.info("=" * 60)
    logger.info(f"路徑: {base_path}")
    logger.info(f"模式: {'預覽（dry-run）' if dry_run else '實際刪除'}")
    logger.info("=" * 60)

    # 檢查路徑是否存在
    entries = list_directory(base_path)

    if not entries:
        logger.info(f"路徑不存在或為空: {base_path}")
        return {"deleted": 0, "errors": 0, "path": base_path}

    # 遞歸刪除
    deleted, errors = delete_directory_recursive(base_path, dry_run)

    logger.info("=" * 60)
    logger.info("清理完成")
    logger.info(f"  路徑: {base_path}")
    logger.info(f"  已刪除: {deleted} 個文件")
    logger.info(f"  失敗: {errors} 個文件")
    logger.info("=" * 60)

    return {"deleted": deleted, "errors": errors, "path": base_path}


def cleanup_all_test_files(dry_run: bool = False) -> dict:
    """
    清理所有測試相關的文件
    - tasks/SystemDoc/
    - tasks/*/ (其他任務目錄)
    """
    filer_url = get_filer_url()

    logger.info("=" * 60)
    logger.info("清理所有測試文件")
    logger.info("=" * 60)

    total_deleted = 0
    total_errors = 0

    # 列出所有 tasks 目錄
    tasks_path = "/tasks/"
    entries = list_directory(tasks_path)

    for entry in entries:
        full_path = entry.get("FullPath", "")
        is_dir = entry.get("IsDir", False)

        if is_dir and full_path.startswith("tasks/"):
            task_name = full_path.replace("tasks/", "").rstrip("/")

            # 跳過非測試任務
            if task_name in ["systemAdmin_SystemDocs"]:
                logger.info(f"跳過系統任務: {task_name}")
                continue

            logger.info(f"\n處理任務: {task_name}")
            deleted, errors = cleanup_task_files(task_name, dry_run=dry_run)
            total_deleted += deleted
            total_errors += errors

    logger.info("=" * 60)
    logger.info("全部清理完成")
    logger.info(f"  總共刪除: {total_deleted} 個文件")
    logger.info(f"  總共失敗: {total_errors} 個文件")
    logger.info("=" * 60)

    return {"deleted": total_deleted, "errors": total_errors}


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="SeaweedFS 文件清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 清除 SystemDoc 任務下的文件
  python3 scripts/cleanup_seaweedfs.py

  # 清除所有 tasks/ 目錄下的文件
  python3 scripts/cleanup_seaweedfs.py --all

  # 僅預覽不刪除
  python3 scripts/cleanup_seaweedfs.py --dry-run

  # 清除指定任務
  python3 scripts/cleanup_seaweedfs.py --task-id test-task
        """,
    )

    parser.add_argument(
        "--task-id",
        default="SystemDoc",
        help="要清理的任務 ID（默認: SystemDoc）",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Bucket 名稱（可選，例如: bucket-ai-box-assets）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="清理所有 tasks/ 目錄下的文件",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="僅預覽，不實際刪除",
    )

    args = parser.parse_args()

    if args.all:
        result = cleanup_all_test_files(dry_run=args.dry_run)
    else:
        result = cleanup_task_files(
            task_id=args.task_id,
            bucket=args.bucket,
            dry_run=args.dry_run,
        )

    # 返回退出碼
    sys.exit(0 if result["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
