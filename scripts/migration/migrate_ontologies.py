# 代碼功能說明: Ontology 數據遷移腳本 - 從文件系統遷移到 ArangoDB
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Ontology 數據遷移腳本"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.ontology import OntologyCreate
from services.api.services.ontology_store_service import get_ontology_store_service

logger = structlog.get_logger(__name__)
ONTOLOGY_DIR = project_root / "kag" / "ontology"


def load_ontology_file(file_path: Path):
    """載入 Ontology JSON 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_ontology_info(file_name: str, data):
    """從 JSON 數據中提取 Ontology 信息"""
    ontology_type = "base"
    if file_name.startswith("domain-"):
        ontology_type = "domain"
    elif file_name.startswith("major-"):
        ontology_type = "major"

    return {
        "type": ontology_type,
        "name": data.get("ontology_name", file_name.replace(".json", "")),
        "version": data.get("version", "1.0"),
        "ontology_name": data.get("ontology_name", ""),
        "description": data.get("description", ""),
        "author": data.get("author", "Daniel Chung"),
        "last_modified": data.get("last_modified", ""),
        "inherits_from": data.get("inherits_from", []),
        "compatible_domains": data.get("compatible_domains", []),
        "tags": data.get("tags", []),
        "use_cases": data.get("use_cases", []),
        "entity_classes": data.get("entity_classes", []),
        "object_properties": data.get("object_properties", []),
    }


def migrate_ontology_file(file_path: Path, service, tenant_id=None):
    """遷移單個 Ontology 文件"""
    file_name = file_path.name
    if file_name in ["ontology_list.json", "Prompt-Template.json"]:
        return True

    data = load_ontology_file(file_path)
    info = extract_ontology_info(file_name, data)
    default_version = info["type"] == "base" or file_name in [
        "domain-enterprise.json",
        "domain-administration.json",
    ]

    ontology_create = OntologyCreate(
        type=info["type"],
        name=info["name"],
        version=info["version"],
        default_version=default_version,
        ontology_name=info["ontology_name"],
        description=info.get("description"),
        author=info.get("author"),
        last_modified=info.get("last_modified"),
        inherits_from=info.get("inherits_from", []),
        compatible_domains=info.get("compatible_domains", []),
        tags=info.get("tags", []),
        use_cases=info.get("use_cases", []),
        entity_classes=info.get("entity_classes", []),
        object_properties=info.get("object_properties", []),
        tenant_id=tenant_id,
    )

    service.save_ontology(ontology_create, tenant_id=tenant_id)
    return True


def main():
    """主函數"""
    from scripts.migration.create_schema import create_collections, create_indexes

    client = ArangoDBClient()
    create_collections(client)
    create_indexes(client)

    service = get_ontology_store_service()
    ontology_files = list(ONTOLOGY_DIR.glob("*.json"))

    for file_path in ontology_files:
        if file_path.name not in ["ontology_list.json", "Prompt-Template.json"]:
            migrate_ontology_file(file_path, service, tenant_id=None)
            print(f"Migrated: {file_path.name}")

    print("Migration completed!")


if __name__ == "__main__":
    main()
