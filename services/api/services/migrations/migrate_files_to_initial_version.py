#!/usr/bin/env python3
"""
批量遷移所有文件記錄為初版（版本1.0，備註"遷移原文件"）

使用方法:
    python -m services.api.services.migrations.migrate_files_to_initial_version --dry-run
    python -m services.api.services.migrations.migrate_files_to_initial_version --execute
"""

import sys
from pathlib import Path
from typing import Any, Dict

import structlog

from database.arangodb import ArangoDBClient
from services.api.services.file_metadata_service import FileMetadataService

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 嘗試載入 .env 文件（如果 python-dotenv 可用）
try:
    from dotenv import load_dotenv

    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 不可用時跳過

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "file_metadata"


def migrate_files_to_initial_version(
    dry_run: bool = True,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """批量遷移所有文件記錄為初版

    Args:
        dry_run: 是否為乾運行（只檢查不修改）
        batch_size: 批量處理大小

    Returns:
        遷移統計信息
    """
    client = ArangoDBClient()
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    metadata_service = FileMetadataService(client=client)
    client.db.collection(COLLECTION_NAME)

    stats = {
        "total_files": 0,
        "updated": 0,
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
            "Found files to migrate",
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

                    # 檢查文件是否已經有版本和備註
                    custom_metadata = doc.get("custom_metadata", {})
                    if not isinstance(custom_metadata, dict):
                        custom_metadata = {}

                    has_version = custom_metadata.get("version") is not None
                    has_note = (
                        doc.get("description") == "遷移原文件"
                        or custom_metadata.get("note") == "遷移原文件"
                        or custom_metadata.get("备注") == "遷移原文件"
                    )

                    # 如果已經有版本和備註，跳過
                    if has_version and has_note:
                        stats["skipped"] += 1
                        logger.debug(f"文件 {file_id} 已更新，跳過")
                        continue

                    if dry_run:
                        # 乾運行模式：只記錄統計
                        stats["updated"] += 1
                        logger.debug(f"[DRY RUN] 將更新文件 {file_id}")
                    else:
                        # 準備更新數據
                        updated_custom_metadata = custom_metadata.copy()
                        updated_custom_metadata["version"] = "1.0"
                        updated_custom_metadata["note"] = "遷移原文件"
                        updated_custom_metadata["备注"] = "遷移原文件"

                        # 更新文件元數據
                        from services.api.models.file_metadata import FileMetadataUpdate

                        update_data = FileMetadataUpdate(
                            description="遷移原文件",
                            custom_metadata=updated_custom_metadata,
                        )

                        result = metadata_service.update(file_id, update_data)
                        if result:
                            stats["updated"] += 1
                            logger.info(f"成功更新文件 {file_id}")
                        else:
                            stats["errors"] += 1
                            error_msg = f"文件 {file_id}: 更新失敗"
                            stats["error_details"].append(error_msg)
                            logger.error(error_msg)

                except Exception as e:
                    stats["errors"] += 1
                    file_id = doc.get("_key") or doc.get("file_id", "unknown")
                    error_msg = f"文件 {file_id}: {str(e)}"
                    stats["error_details"].append(error_msg)
                    logger.error(error_msg, exc_info=True)

        logger.info(
            "Migration completed",
            total=stats["total_files"],
            updated=stats["updated"],
            skipped=stats["skipped"],
            errors=stats["errors"],
            dry_run=dry_run,
        )

        return stats

    except Exception as e:
        logger.error("Migration failed", error=str(e), exc_info=True)
        raise


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="批量遷移所有文件記錄為初版")
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

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode (no changes will be made)")
    else:
        logger.warning("Running in EXECUTE mode (changes will be made)")

    try:
        stats = migrate_files_to_initial_version(
            dry_run=dry_run,
            batch_size=args.batch_size,
        )

        print("\n" + "=" * 60)
        print("遷移統計")
        print("=" * 60)
        print(f"總文件數: {stats['total_files']}")
        print(f"已更新: {stats['updated']}")
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
            print("要執行實際遷移，請使用 --execute 參數。")

    except Exception as e:
        logger.error("Migration script failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
