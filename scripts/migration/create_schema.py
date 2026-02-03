# 代碼功能說明: ArangoDB Schema 建立腳本 - 為檔案系統轉結構遷移建立必要的 Collections 和索引
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""ArangoDB Schema 建立腳本

用於建立檔案系統轉結構遷移所需的 Collections 和索引。
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

from database.arangodb import ArangoDBClient

logger = structlog.get_logger(__name__)

# Collection 名稱定義
ONTOLOGIES_COLLECTION = "ontologies"
SYSTEM_CONFIGS_COLLECTION = "system_configs"
TENANT_CONFIGS_COLLECTION = "tenant_configs"
USER_CONFIGS_COLLECTION = "user_configs"
AGENT_DISPLAY_CONFIGS_COLLECTION = "agent_display_configs"


def create_collections(client: ArangoDBClient) -> None:
    """建立所有需要的 Collections"""
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    collections = [
        (ONTOLOGIES_COLLECTION, "document"),
        (SYSTEM_CONFIGS_COLLECTION, "document"),
        (TENANT_CONFIGS_COLLECTION, "document"),
        (USER_CONFIGS_COLLECTION, "document"),
        (AGENT_DISPLAY_CONFIGS_COLLECTION, "document"),
    ]

    for name, collection_type in collections:
        try:
            if not client.db.has_collection(name):
                client.db.create_collection(name)
                logger.info("collection_created", name=name, type=collection_type)
            else:
                logger.info("collection_exists", name=name)
        except Exception as exc:
            logger.error("collection_create_failed", name=name, error=str(exc))
            raise


def create_indexes(client: ArangoDBClient) -> None:
    """建立所有需要的索引"""
    if client.db is None:
        raise RuntimeError("ArangoDB client is not connected")

    # ontologies collection 索引
    ontologies_indexes = [
        {
            "name": "idx_ontologies_tenant_type_name",
            "fields": ["tenant_id", "type", "name"],
            "type": "persistent",
        },
        {
            "name": "idx_ontologies_tenant_type_name_version",
            "fields": ["tenant_id", "type", "name", "version"],
            "type": "persistent",
        },
        {
            "name": "idx_ontologies_type_name_default",
            "fields": ["type", "name", "default_version"],
            "type": "persistent",
        },
        {
            "name": "idx_ontologies_is_active",
            "fields": ["is_active"],
            "type": "persistent",
        },
    ]

    # system_configs collection 索引
    system_configs_indexes = [
        {
            "name": "idx_system_configs_scope_active",
            "fields": ["scope", "is_active"],
            "type": "persistent",
        },
    ]

    # tenant_configs collection 索引
    tenant_configs_indexes = [
        {
            "name": "idx_tenant_configs_tenant_scope_active",
            "fields": ["tenant_id", "scope", "is_active"],
            "type": "persistent",
        },
    ]

    # user_configs collection 索引
    user_configs_indexes = [
        {
            "name": "idx_user_configs_tenant_user_scope_active",
            "fields": ["tenant_id", "user_id", "scope", "is_active"],
            "type": "persistent",
        },
    ]

    # agent_display_configs collection 索引
    agent_display_configs_indexes = [
        {
            "name": "idx_agent_display_configs_tenant_type_active",
            "fields": ["tenant_id", "config_type", "is_active"],
            "type": "persistent",
        },
        {
            "name": "idx_agent_display_configs_category",
            "fields": ["tenant_id", "config_type", "category_id", "is_active"],
            "type": "persistent",
        },
        {
            "name": "idx_agent_display_configs_agent",
            "fields": ["tenant_id", "config_type", "agent_id", "is_active"],
            "type": "persistent",
        },
    ]

    index_configs = [
        (ONTOLOGIES_COLLECTION, ontologies_indexes),
        (SYSTEM_CONFIGS_COLLECTION, system_configs_indexes),
        (TENANT_CONFIGS_COLLECTION, tenant_configs_indexes),
        (USER_CONFIGS_COLLECTION, user_configs_indexes),
        (AGENT_DISPLAY_CONFIGS_COLLECTION, agent_display_configs_indexes),
    ]

    for collection_name, indexes in index_configs:
        try:
            collection = client.db.collection(collection_name)
            for idx_config in indexes:
                idx_name = idx_config["name"]
                existing_indexes = [idx["name"] for idx in collection.indexes() if "name" in idx]
                if idx_name not in existing_indexes:
                    # 使用 ArangoDB 的索引創建方法
                    collection.add_hash_index(
                        fields=idx_config["fields"],
                        unique=False,
                        name=idx_name,
                    )
                    logger.info(
                        "index_created",
                        collection=collection_name,
                        index=idx_name,
                        fields=idx_config["fields"],
                    )
                else:
                    logger.info("index_exists", collection=collection_name, index=idx_name)
        except Exception as exc:
            logger.error("index_create_failed", collection=collection_name, error=str(exc))
            raise


def main() -> None:
    """主函數"""
    logger.info("starting_schema_creation")
    try:
        client = ArangoDBClient()
        create_collections(client)
        create_indexes(client)
        logger.info("schema_creation_completed")
    except Exception as exc:
        logger.error("schema_creation_failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
