#!/usr/bin/env python3
# 代碼功能說明: 修復文件權限設置
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""修復文件權限設置，將 owner_id 和 authorized_users 設置為正確的值"""

import sys
from pathlib import Path
from typing import Dict, Any

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 嘗試載入 .env 文件
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

import structlog
from database.arangodb import ArangoDBClient
from services.api.models.file_access_control import FileAccessLevel

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "file_metadata"


def fix_file_permissions(
    dry_run: bool = True,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """修復文件權限設置

    Args:
        dry_run: 是否為乾運行（只檢查不修改）
        batch_size: 批量處理大小

    Returns:
        修復統計信息
    """
    client = ArangoDBClient()
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    collection = client.db.collection(COLLECTION_NAME)

    stats = {
        "total_files": 0,
        "systemadmin_fixed": 0,
        "daniel_fixed": 0,
        "other_fixed": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": [],
    }

    try:
        # 查詢所有文件
        if client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        aql = f"""
        FOR doc IN {COLLECTION_NAME}
            RETURN doc
        """
        cursor = client.db.aql.execute(aql)

        files_to_process: list = []
        for doc in cursor:
            files_to_process.append(doc)
            stats["total_files"] += 1

        logger.info(
            "Found files to fix",
            count=len(files_to_process),
            dry_run=dry_run,
        )

        # 批量處理
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i : i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} files)")

            for doc in batch:
                try:
                    file_id = doc.get("_key") or doc.get("file_id")
                    if not file_id:
                        stats["errors"] += 1
                        stats["error_details"].append(f"文件缺少 _key 或 file_id: {doc}")
                        continue

                    user_id = doc.get("user_id")
                    if not user_id:
                        stats["errors"] += 1
                        stats["error_details"].append(f"文件 {file_id} 缺少 user_id")
                        continue

                    # 獲取當前的 access_control
                    access_control = doc.get("access_control", {})
                    if not isinstance(access_control, dict):
                        access_control = {}

                    # 根據 user_id 設置權限
                    if user_id == "systemAdmin":
                        # SystemAdmin 的文件
                        new_access_control = {
                            "access_level": FileAccessLevel.PRIVATE.value,
                            "owner_id": "systemAdmin",
                            "authorized_users": ["systemAdmin"],
                            "authorized_security_groups": None,
                            "authorized_organizations": ["SystemGroup"],
                            "data_classification": "internal",  # 使用小寫（API 標準）
                            "sensitivity_labels": ["high"],  # 自定義標籤
                            "owner_tenant_id": access_control.get("owner_tenant_id"),
                            "access_log_enabled": access_control.get("access_log_enabled", True),
                            "access_expires_at": access_control.get("access_expires_at"),
                        }
                        stats["systemadmin_fixed"] += 1
                    else:
                        # 其他用戶的文件（主要是 daniel@test.com）
                        new_access_control = {
                            "access_level": FileAccessLevel.PRIVATE.value,
                            "owner_id": user_id,
                            "authorized_users": [user_id],
                            "authorized_security_groups": None,
                            "authorized_organizations": ["develop"],
                            "data_classification": "confidential",  # 使用小寫（API 標準）
                            "sensitivity_labels": ["low"],  # 自定義標籤
                            "owner_tenant_id": access_control.get("owner_tenant_id"),
                            "access_log_enabled": access_control.get("access_log_enabled", True),
                            "access_expires_at": access_control.get("access_expires_at"),
                        }
                        if user_id == "daniel@test.com":
                            stats["daniel_fixed"] += 1
                        else:
                            stats["other_fixed"] += 1

                    # 檢查是否需要更新
                    needs_update = False
                    current_owner = access_control.get("owner_id")
                    current_orgs = access_control.get("authorized_organizations")
                    current_dc = access_control.get("data_classification")
                    current_labels = access_control.get("sensitivity_labels")

                    if (
                        current_owner != new_access_control["owner_id"]
                        or current_orgs != new_access_control["authorized_organizations"]
                        or current_dc != new_access_control["data_classification"]
                        or current_labels != new_access_control["sensitivity_labels"]
                    ):
                        needs_update = True

                    if not needs_update:
                        stats["skipped"] += 1
                        logger.debug(f"文件 {file_id} 權限已正確，跳過")
                        continue

                    if dry_run:
                        # 乾運行模式：只記錄統計
                        logger.debug(f"[DRY RUN] 將更新文件 {file_id} 的權限")
                    else:
                        # 更新文件權限
                        update_data = {
                            "access_control": new_access_control,
                            "data_classification": new_access_control["data_classification"],
                            "sensitivity_labels": new_access_control["sensitivity_labels"],
                            "updated_at": doc.get("updated_at"),  # 保持原有時間
                        }

                        # 更新文檔
                        doc.update(update_data)
                        collection.update(doc)
                        logger.info(f"成功更新文件 {file_id} 的權限")

                except Exception as e:
                    stats["errors"] += 1
                    file_id = doc.get("_key") or doc.get("file_id", "unknown")
                    error_msg = f"文件 {file_id}: {str(e)}"
                    stats["error_details"].append(error_msg)
                    logger.error(error_msg, exc_info=True)

        logger.info(
            "Permission fix completed",
            total=stats["total_files"],
            systemadmin_fixed=stats["systemadmin_fixed"],
            daniel_fixed=stats["daniel_fixed"],
            other_fixed=stats["other_fixed"],
            skipped=stats["skipped"],
            errors=stats["errors"],
            dry_run=dry_run,
        )

        return stats

    except Exception as e:
        logger.error("Permission fix failed", error=str(e), exc_info=True)
        raise


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="修復文件權限設置")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="乾運行模式（只檢查不修改，默認啟用）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="執行修復（禁用乾運行模式）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量處理大小（默認：100）",
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode (no changes will be made)")
    else:
        logger.warning("Running in EXECUTE mode (changes will be made)")

    try:
        stats = fix_file_permissions(
            dry_run=dry_run,
            batch_size=args.batch_size,
        )

        print("\n" + "=" * 60)
        print("權限修復統計")
        print("=" * 60)
        print(f"總文件數: {stats['total_files']}")
        print(f"SystemAdmin 文件修復: {stats['systemadmin_fixed']}")
        print(f"daniel@test.com 文件修復: {stats['daniel_fixed']}")
        print(f"其他用戶文件修復: {stats['other_fixed']}")
        print(f"已跳過: {stats['skipped']}")
        print(f"錯誤數: {stats['errors']}")
        print("=" * 60)

        if stats["error_details"]:
            print("\n錯誤詳情（前10個）:")
            for error in stats["error_details"][:10]:
                print(f"  - {error}")
            if len(stats["error_details"]) > 10:
                print(f"  ... 還有 {len(stats['error_details']) - 10} 個錯誤")

        if dry_run:
            print("\n這是乾運行模式，沒有實際修改數據。")
            print("要執行實際修復，請使用 --execute 參數。")

    except Exception as e:
        logger.error("Permission fix script failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

