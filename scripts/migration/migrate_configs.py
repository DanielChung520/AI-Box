# 代碼功能說明: Config 數據遷移腳本 - 從 config/config.json 遷移到 ArangoDB
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Config 數據遷移腳本"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.config import ConfigCreate
from services.api.services.config_store_service import get_config_store_service

logger = structlog.get_logger(__name__)
CONFIG_FILE = project_root / "config" / "config.json"


def migrate_genai_policy_config(service, config_data):
    """遷移 genai.policy 配置"""
    genai_config = config_data.get("genai", {})
    policy_config = genai_config.get("policy", {})
    if policy_config:
        config_create = ConfigCreate(
            scope="genai.policy",
            config_data=policy_config,
            metadata={"description": "GenAI Policy Configuration", "version": "1.0"},
            tenant_id=None,
        )
        service.save_config(config_create, tenant_id=None)
        logger.info("config_migrated", scope="genai.policy")


def migrate_genai_model_registry_config(service, config_data):
    """遷移 genai.model_registry 配置"""
    genai_config = config_data.get("genai", {})
    model_registry_config = genai_config.get("model_registry", {})
    if model_registry_config:
        config_create = ConfigCreate(
            scope="genai.model_registry",
            config_data=model_registry_config,
            metadata={"description": "GenAI Model Registry Configuration", "version": "1.0"},
            tenant_id=None,
        )
        service.save_config(config_create, tenant_id=None)
        logger.info("config_migrated", scope="genai.model_registry")


def main():
    """主函數"""
    from scripts.migration.create_schema import create_collections, create_indexes

    client = ArangoDBClient()
    create_collections(client)
    create_indexes(client)

    service = get_config_store_service()

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    migrate_genai_policy_config(service, config_data)
    migrate_genai_model_registry_config(service, config_data)

    print("Config migration completed!")


if __name__ == "__main__":
    main()
