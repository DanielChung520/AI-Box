#!/usr/bin/env python3
# 代碼功能說明: 文件訪問控制數據遷移腳本
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""
為現有文件自動生成默認 access_control（PRIVATE, INTERNAL），
並遷移 data_classification 和 sensitivity_labels 到 access_control。

使用方法:
    python -m services.api.services.migrations.migrate_file_access_control --dry-run
    python -m services.api.services.migrations.migrate_file_access_control --execute
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import structlog  # noqa: E402

from database.arangodb import ArangoDBClient  # noqa: E402
from services.api.models.data_classification import DataClassification  # noqa: E402
from services.api.services.file_metadata_service import FileMetadataService  # noqa: E402

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "file_metadata"


def migrate_file_access_control(
    dry_run: bool = True,
    batch_size: int = 100,
    tenant_id: Optional[str] = None,
) -> Dict[str, int]:
    """遷移文件訪問控制數據

    Args:
        dry_run: 是否為乾運行（只檢查不修改）
        batch_size: 批量處理大小
        tenant_id: 租戶ID（可選，用於多租戶環境）

    Returns:
        遷移統計信息
    """
    client = ArangoDBClient()
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    FileMetadataService(client=client)
    collection = client.db.collection(COLLECTION_NAME)

    stats = {
        "total_files": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        # 查詢所有沒有 access_control 的文件
        if client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        aql = f"""
        FOR doc IN {COLLECTION_NAME}
            FILTER doc.access_control == null OR doc.access_control == undefined
            RETURN doc
        """
        cursor = client.db.aql.execute(aql)

        files_to_migrate: list = []
        for doc in cursor:
            files_to_migrate.append(doc)
            stats["total_files"] += 1

        logger.info(
            "Found files to migrate",
            count=len(files_to_migrate),
            dry_run=dry_run,
        )

        # 批量處理
        for i in range(0, len(files_to_migrate), batch_size):
            batch = files_to_migrate[i : i + batch_size]
            logger.info(
                "Processing batch",
                batch_start=i,
                batch_end=min(i + batch_size, len(files_to_migrate)),
                total=len(files_to_migrate),
            )

            for doc in batch:
                try:
                    file_id = doc.get("_key") or doc.get("file_id")
                    if not file_id:
                        logger.warning("File missing _key or file_id", doc=doc)
                        stats["skipped"] += 1
                        continue

                    user_id = doc.get("user_id")
                    if not user_id:
                        logger.warning("File missing user_id", file_id=file_id)
                        stats["skipped"] += 1
                        continue

                    # 獲取現有的 data_classification 和 sensitivity_labels
                    existing_classification = doc.get("data_classification")
                    existing_labels = doc.get("sensitivity_labels", [])

                    # 生成默認 access_control
                    default_acl = FileMetadataService.get_default_access_control(
                        user_id=user_id, tenant_id=tenant_id
                    )

                    # 如果存在 data_classification，使用它；否則使用默認值
                    if existing_classification:
                        default_acl.data_classification = existing_classification
                    else:
                        default_acl.data_classification = DataClassification.INTERNAL.value

                    # 如果存在 sensitivity_labels，使用它們
                    if existing_labels:
                        default_acl.sensitivity_labels = existing_labels

                    # 更新文檔
                    if not dry_run:
                        update_data = {
                            "_key": file_id,
                            "access_control": default_acl.model_dump(),
                            # 同步更新頂層字段（如果不存在）
                            "data_classification": default_acl.data_classification,
                            "sensitivity_labels": default_acl.sensitivity_labels,
                        }
                        collection.update(update_data)
                        stats["migrated"] += 1
                        logger.debug(
                            "Migrated file access control",
                            file_id=file_id,
                            access_level=default_acl.access_level,
                            data_classification=default_acl.data_classification,
                        )
                    else:
                        stats["migrated"] += 1
                        logger.debug(
                            "Would migrate file access control (dry run)",
                            file_id=file_id,
                            access_level=default_acl.access_level,
                            data_classification=default_acl.data_classification,
                        )

                except Exception as e:
                    logger.error(
                        "Failed to migrate file access control",
                        file_id=doc.get("_key"),
                        error=str(e),
                        exc_info=True,
                    )
                    stats["errors"] += 1

        logger.info(
            "Migration completed",
            stats=stats,
            dry_run=dry_run,
        )

        return stats

    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        raise


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="遷移文件訪問控制數據")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="乾運行模式（只檢查不修改，默認啟用）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="執行遷移（禁用乾運行模式）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批量處理大小（默認：100）",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        default=None,
        help="租戶ID（可選）",
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode (no changes will be made)")
    else:
        logger.warning("Running in EXECUTE mode (changes will be made)")

    try:
        stats = migrate_file_access_control(
            dry_run=dry_run,
            batch_size=args.batch_size,
            tenant_id=args.tenant_id,
        )

        print("\n" + "=" * 60)
        print("遷移統計")
        print("=" * 60)
        print(f"總文件數: {stats['total_files']}")
        print(f"已遷移: {stats['migrated']}")
        print(f"已跳過: {stats['skipped']}")
        print(f"錯誤數: {stats['errors']}")
        print("=" * 60)

        if dry_run:
            print("\n這是乾運行模式，沒有實際修改數據。")
            print("要執行實際遷移，請使用 --execute 參數。")

    except Exception as e:
        logger.error("Migration script failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
