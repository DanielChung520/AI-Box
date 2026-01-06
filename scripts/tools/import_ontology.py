#!/usr/bin/env python3
# 代碼功能說明: 將 Ontology JSON 文件導入到 ArangoDB（系統級）
# 創建日期: 2025-12-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""將 Ontology JSON 文件導入到 ArangoDB

使用方法:
    python import_ontology.py data/ontology/domain-ai-box.json
    python import_ontology.py data/ontology/major-ai-box-system-architecture.json
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from database.arangodb.client import ArangoDBClient
from services.api.models.ontology import OntologyCreate
from services.api.services.ontology_store_service import OntologyStoreService


def extract_name_and_type(ontology_name: str, filename: str) -> tuple[str, str]:
    """從 ontology_name 和文件名提取 name 和 type"""
    filename_lower = filename.lower()
    if filename_lower.startswith("domain-"):
        type_val = "domain"
        name_val = ontology_name.replace("_Domain_Ontology", "")
    elif filename_lower.startswith("major-"):
        type_val = "major"
        name_val = ontology_name.replace("_Major_Ontology", "")
    elif filename_lower.startswith("base"):
        type_val = "base"
        name_val = ontology_name
    else:
        raise ValueError(f"無法從文件名推斷類型: {filename}")
    return name_val, type_val


def import_ontology(json_file_path: Path) -> str:
    """導入 Ontology JSON 文件到 ArangoDB"""
    # 載入 JSON
    print(f"📖 載入文件: {json_file_path}")
    with open(json_file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    
    # 提取信息
    ontology_name = json_data.get("ontology_name", "")
    filename = json_file_path.name
    name, type_val = extract_name_and_type(ontology_name, filename)
    
    # 處理 inherits_from
    inherits_from = json_data.get("inherits_from", [])
    if isinstance(inherits_from, str):
        inherits_from = [inherits_from]
    
    # 處理 compatible_domains
    compatible_domains = json_data.get("compatible_domains", [])
    if not compatible_domains and type_val == "major":
        # 如果是 major 類型且沒有指定，根據文件名推斷
        if "ai-box" in filename.lower() or "ai_box" in filename.lower():
            compatible_domains = ["domain-ai-box.json"]
    
    print(f"✅ JSON 數據解析成功")
    print(f"   Ontology 名稱: {ontology_name}")
    print(f"   類型: {type_val}")
    print(f"   名稱: {name}")
    print(f"   版本: {json_data.get('version', '1.0')}")
    print(f"   實體類數量: {len(json_data.get('entity_classes', []))}")
    print(f"   關係屬性數量: {len(json_data.get('object_properties', []))}")
    
    # 創建 OntologyCreate
    ontology_create = OntologyCreate(
        type=type_val,
        name=name,
        version=json_data.get("version", "1.0"),
        default_version=True,
        ontology_name=ontology_name,
        description=json_data.get("description"),
        author=json_data.get("author"),
        last_modified=json_data.get("last_modified"),
        inherits_from=inherits_from,
        compatible_domains=compatible_domains,
        tags=json_data.get("tags", []),
        use_cases=json_data.get("use_cases", []),
        entity_classes=json_data.get("entity_classes", []),
        object_properties=json_data.get("object_properties", []),
        metadata=json_data.get("metadata", {}),
        tenant_id=None,  # None 表示系統級（全局共享）
        data_classification="INTERNAL",
        sensitivity_labels=None,
    )
    
    # 連接 ArangoDB
    print(f"\n🔌 連接 ArangoDB...")
    client = ArangoDBClient()
    store_service = OntologyStoreService(client)
    print("✅ ArangoDB 連接成功")
    
    # 保存 Ontology
    print(f"\n💾 保存 Ontology 到 ArangoDB（系統級）...")
    ontology_id = store_service.save_ontology(
        ontology_create,
        tenant_id=None,  # 系統級
        changed_by="system",
    )
    print(f"✅ Ontology 保存成功！")
    print(f"   Ontology ID: {ontology_id}")
    print(f"   租戶 ID: null (系統級)")
    
    return ontology_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python import_ontology.py <json_file>")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"❌ 錯誤：文件不存在: {json_file}")
        sys.exit(1)
    
    try:
        import_ontology(json_file)
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
