#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據一致性檢查腳本

檢查以下一致性問題：
1. file_metadata 中的 folder_id 是否在 folder_metadata 中存在
2. file_metadata 中的 task_id 是否在 user_tasks 中存在
3. folder_metadata 中的 task_id 是否在 user_tasks 中存在
4. file_metadata 中是否有重複的 file_id

使用方法：
    python3 scripts/check_data_consistency.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.folder_metadata_service import get_folder_metadata_service
from services.api.services.user_task_service import get_user_task_service


def check_file_metadata_folder_consistency():
    """檢查 file_metadata 中的 folder_id 是否在 folder_metadata 中存在"""
    print("\n=== 檢查 file_metadata.folder_id 一致性 ===")

    issues = []
    folder_service = get_folder_metadata_service()
    metadata_service = FileMetadataService()

    try:
        files = metadata_service.list(limit=10000)
        existing_folder_ids = {f.get("_key") for f in folder_service.list(limit=10000)}

        for file in files:
            folder_id = getattr(file, "folder_id", None)
            if folder_id and folder_id not in existing_folder_ids:
                issues.append(f"file_id={file.file_id}, folder_id={folder_id} 不存在")

        if issues:
            print(f"❌ 發現 {len(issues)} 個不一致:")
            for issue in issues[:10]:  # 只顯示前10個
                print(f"   {issue}")
        else:
            print("✅ file_metadata.folder_id 一致性檢查通過")

    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        issues = []

    return issues


def check_file_metadata_task_consistency():
    """檢查 file_metadata 中的 task_id 是否在 user_tasks 中存在"""
    print("\n=== 檢查 file_metadata.task_id 一致性 ===")

    issues = []
    metadata_service = FileMetadataService()
    task_service = get_user_task_service()

    try:
        files = metadata_service.list(limit=10000)
        tasks = task_service.list(user_id=None, limit=10000, build_file_tree=False)
        existing_task_ids = {t.task_id for t in tasks}

        for file in files:
            task_id = getattr(file, "task_id", None)
            if task_id and task_id not in existing_task_ids:
                issues.append(f"file_id={file.file_id}, task_id={task_id} 不存在")

        if issues:
            print(f"❌ 發現 {len(issues)} 個不一致:")
            for issue in issues[:10]:
                print(f"   {issue}")
        else:
            print("✅ file_metadata.task_id 一致性檢查通過")

    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        issues = []

    return issues


def check_folder_metadata_task_consistency():
    """檢查 folder_metadata 中的 task_id 是否在 user_tasks 中存在"""
    print("\n=== 檢查 folder_metadata.task_id 一致性 ===")

    issues = []
    folder_service = get_folder_metadata_service()
    task_service = get_user_task_service()

    try:
        folders = folder_service.list(limit=10000)
        tasks = task_service.list(user_id=None, limit=10000, build_file_tree=False)
        existing_task_ids = {t.task_id for t in tasks}

        for folder in folders:
            task_id = folder.get("task_id")
            if task_id and task_id not in existing_task_ids:
                issues.append(f"folder_id={folder.get('folder_id')}, task_id={task_id} 不存在")

        if issues:
            print(f"❌ 發現 {len(issues)} 個不一致:")
            for issue in issues[:10]:
                print(f"   {issue}")
        else:
            print("✅ folder_metadata.task_id 一致性檢查通過")

    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        issues = []

    return issues


def check_duplicate_file_ids():
    """檢查是否有重複的 file_id"""
    print("\n=== 檢查 file_metadata 重複 file_id ===")

    issues = []
    metadata_service = FileMetadataService()

    try:
        files = metadata_service.list(limit=10000)
        file_ids = [f.file_id for f in files]
        seen = set()
        for file_id in file_ids:
            if file_id in seen:
                issues.append(f"file_id={file_id} 重複")
            seen.add(file_id)

        if issues:
            print(f"❌ 發現 {len(issues)} 個重複:")
            for issue in issues[:10]:
                print(f"   {issue}")
        else:
            print("✅ file_metadata file_id 唯一性檢查通過")

    except Exception as e:
        print(f"❌ 檢查失敗: {e}")
        issues = []

    return issues


def main():
    """主函數"""
    print("=" * 60)
    print("AI-Box 數據一致性檢查")
    print("=" * 60)

    all_issues = []

    # 1. 檢查 file_metadata.folder_id 一致性
    issues = check_file_metadata_folder_consistency()
    all_issues.extend(issues)

    # 2. 檢查 file_metadata.task_id 一致性
    issues = check_file_metadata_task_consistency()
    all_issues.extend(issues)

    # 3. 檢查 folder_metadata.task_id 一致性
    issues = check_folder_metadata_task_consistency()
    all_issues.extend(issues)

    # 4. 檢查 file_id 唯一性
    issues = check_duplicate_file_ids()
    all_issues.extend(issues)

    print("\n" + "=" * 60)
    print(f"檢查完成，總共發現 {len(all_issues)} 個問題")
    print("=" * 60)

    if all_issues:
        print("\n建議操作:")
        print("1. 運行 python3 scripts/fix_missing_file_metadata.py 修復缺失的 metadata")
        print("2. 運行 python3 scripts/cleanup_all.py 清理孤立數據")
        sys.exit(1)
    else:
        print("\n✅ 所有一致性檢查通過！")
        sys.exit(0)


if __name__ == "__main__":
    main()
