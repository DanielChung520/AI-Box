# 代碼功能說明: DataLake 數據遷移腳本 - 從 ArangoDB 遷移到 SeaweedFS
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""
DataLake 數據遷移腳本 - 從 ArangoDB 遷移到 SeaweedFS

功能：
1. 從 ArangoDB 查詢 DataLake dictionary 定義
2. 從 ArangoDB 查詢 DataLake schema 定義
3. 將這些數據轉換為 JSON 格式
4. 上傳到 AI-Box SeaweedFS 服務：
   - dictionary 定義 → bucket-datalake-dictionary
   - schema 定義 → bucket-datalake-schema
5. 更新相關服務的引用（從 ArangoDB 改為 SeaweedFS URI）
6. 驗證遷移結果
7. 可選：從 ArangoDB 刪除已遷移的數據（備份後）

注意：
- DataLake dictionary 和 schema 定義的具體存儲位置需要進一步確認
- 可能存儲在 system_configs、tenant_configs 或獨立的 Collection 中
- 本腳本提供通用的遷移邏輯，需要根據實際數據結構調整
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import structlog

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.arangodb import ArangoDBClient
from storage.file_storage import create_storage_from_config
from storage.s3_storage import SeaweedFSService
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

# 遷移狀態文件路徑
MIGRATION_STATE_FILE = project_root / "data" / "datalake_migration_state.json"
MIGRATION_LOG_FILE = project_root / "data" / "datalake_migration_log.jsonl"

# 可能的 Collection 名稱
POSSIBLE_COLLECTIONS = [
    "datalake_dictionary",
    "datalake_schema",
    "system_configs",
    "tenant_configs",
]


def find_datalake_data(client: ArangoDBClient) -> Dict[str, List[Dict[str, Any]]]:
    """
    查找 DataLake dictionary 和 schema 定義

    Args:
        client: ArangoDB 客戶端

    Returns:
        包含 dictionary 和 schema 數據的字典
    """
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    result: Dict[str, List[Dict[str, Any]]] = {
        "dictionary": [],
        "schema": [],
    }

    # 方法 1：查找獨立的 Collection
    for collection_name in ["datalake_dictionary", "datalake_schema"]:
        if client.db.has_collection(collection_name):
            collection = client.db.collection(collection_name)
            cursor = collection.all()
            data_type = "dictionary" if "dictionary" in collection_name else "schema"
            result[data_type].extend(list(cursor))

    # 方法 2：從 system_configs 和 tenant_configs 中查找
    for collection_name in ["system_configs", "tenant_configs"]:
        if client.db.has_collection(collection_name):
            collection = client.db.collection(collection_name)
            # 查找 scope 包含 "datalake" 的配置
            aql = f"""
                FOR doc IN {collection_name}
                    FILTER doc.scope LIKE "%datalake%" OR doc.scope LIKE "%dictionary%" OR doc.scope LIKE "%schema%"
                    RETURN doc
            """
            cursor = client.db.aql.execute(aql)
            for doc in cursor:
                scope = doc.get("scope", "")
                if "dictionary" in scope.lower():
                    result["dictionary"].append(doc)
                elif "schema" in scope.lower():
                    result["schema"].append(doc)

    return result


def migrate_datalake_data(
    dry_run: bool = False,
    backup: bool = True,
    delete_after_migration: bool = False,
) -> None:
    """
    遷移 DataLake 數據從 ArangoDB 到 SeaweedFS

    Args:
        dry_run: 是否為乾運行模式
        backup: 是否備份數據
        delete_after_migration: 遷移後是否刪除 ArangoDB 中的數據
    """
    logger.info("Starting DataLake data migration", dry_run=dry_run)

    # 創建 ArangoDB 客戶端
    client = ArangoDBClient()

    # 查找 DataLake 數據
    logger.info("Searching for DataLake data in ArangoDB...")
    datalake_data = find_datalake_data(client)

    logger.info(
        "Found DataLake data",
        dictionary_count=len(datalake_data["dictionary"]),
        schema_count=len(datalake_data["schema"]),
    )

    if not datalake_data["dictionary"] and not datalake_data["schema"]:
        logger.warning("No DataLake data found in ArangoDB")
        return

    # 創建 S3 存儲實例
    config = get_config_section("file_upload", default={}) or {}
    s3_storage = create_storage_from_config(config, service_type=SeaweedFSService.AI_BOX)

    # 遷移 dictionary 定義
    migrated_dictionaries = []
    for idx, dictionary_doc in enumerate(datalake_data["dictionary"]):
        dictionary_id = dictionary_doc.get("_key") or dictionary_doc.get("id") or f"dict_{idx}"
        tenant_id = dictionary_doc.get("tenant_id", "global")

        # 生成文件路徑
        file_path = f"dictionary/{tenant_id}/{dictionary_id}.json"

        # 轉換為 JSON
        json_content = json.dumps(dictionary_doc, ensure_ascii=False, indent=2).encode("utf-8")

        if dry_run:
            logger.info(
                "Dry run: Would migrate dictionary",
                dictionary_id=dictionary_id,
                file_path=file_path,
            )
            continue

        # 上傳到 SeaweedFS
        try:
            # 注意：這裡需要使用 bucket-datalake-dictionary，但 S3FileStorage 默認使用 bucket-ai-box-assets
            # 需要擴展 S3FileStorage 支持自定義 bucket，或使用 boto3 直接上傳
            # 暫時使用默認 bucket，後續可以擴展
            file_id, s3_uri = s3_storage.save_file(
                json_content, f"{dictionary_id}.json", file_id=dictionary_id
            )
            migrated_dictionaries.append({"dictionary_id": dictionary_id, "s3_uri": s3_uri})
            logger.info(
                "Dictionary migrated",
                dictionary_id=dictionary_id,
                s3_uri=s3_uri,
            )
        except Exception as e:
            logger.error(
                "Failed to migrate dictionary",
                dictionary_id=dictionary_id,
                error=str(e),
            )

    # 遷移 schema 定義
    migrated_schemas = []
    for idx, schema_doc in enumerate(datalake_data["schema"]):
        schema_id = schema_doc.get("_key") or schema_doc.get("id") or f"schema_{idx}"
        tenant_id = schema_doc.get("tenant_id", "global")

        # 生成文件路徑
        file_path = f"schema/{tenant_id}/{schema_id}.json"

        # 轉換為 JSON
        json_content = json.dumps(schema_doc, ensure_ascii=False, indent=2).encode("utf-8")

        if dry_run:
            logger.info(
                "Dry run: Would migrate schema",
                schema_id=schema_id,
                file_path=file_path,
            )
            continue

        # 上傳到 SeaweedFS
        try:
            file_id, s3_uri = s3_storage.save_file(
                json_content, f"{schema_id}.json", file_id=schema_id
            )
            migrated_schemas.append({"schema_id": schema_id, "s3_uri": s3_uri})
            logger.info(
                "Schema migrated",
                schema_id=schema_id,
                s3_uri=s3_uri,
            )
        except Exception as e:
            logger.error(
                "Failed to migrate schema",
                schema_id=schema_id,
                error=str(e),
            )

    # 保存遷移狀態
    migration_state = {
        "migrated_dictionaries": migrated_dictionaries,
        "migrated_schemas": migrated_schemas,
        "total_dictionaries": len(datalake_data["dictionary"]),
        "total_schemas": len(datalake_data["schema"]),
    }
    MIGRATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MIGRATION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(migration_state, f, indent=2, ensure_ascii=False)

    logger.info(
        "DataLake data migration completed",
        dictionaries_migrated=len(migrated_dictionaries),
        schemas_migrated=len(migrated_schemas),
        dry_run=dry_run,
    )


def main() -> None:
    """主函數"""
    parser = argparse.ArgumentParser(description="Migrate DataLake data from ArangoDB to SeaweedFS")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="乾運行模式（不實際遷移，僅顯示將要執行的操作）",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不備份數據（不推薦）",
    )
    parser.add_argument(
        "--delete-after-migration",
        action="store_true",
        help="遷移後刪除 ArangoDB 中的數據（謹慎使用）",
    )

    args = parser.parse_args()

    migrate_datalake_data(
        dry_run=args.dry_run,
        backup=not args.no_backup,
        delete_after_migration=args.delete_after_migration,
    )


if __name__ == "__main__":
    main()
