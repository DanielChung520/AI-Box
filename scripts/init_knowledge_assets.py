# 代碼功能說明: 初始化 ArangoDB 知識資產集合與索引
# 創建日期: 2026-01-25
# 創建人: Daniel Chung

from database.arangodb.client import ArangoDBClient


def initialize_knowledge_assets():
    """創建 knowledge_assets 集合並配置索引"""
    client = ArangoDBClient()

    if client.db is None:
        print("❌ 無法連接到 ArangoDB")
        return

    collection_name = "knowledge_assets"

    # 確保集合存在
    if not client.db.has_collection(collection_name):
        print(f"🏗️ 正在創建集合: {collection_name}")
        client.db.create_collection(collection_name)
    else:
        print(f"✅ 集合 {collection_name} 已存在")

    collection = client.db.collection(collection_name)

    # 配置索引 (根據 Ch 13.1 規格)
    indexes = [
        {
            "type": "persistent",
            "fields": ["ka_id", "version"],
            "unique": True,
            "name": "idx_ka_id_version",
        },
        {
            "type": "persistent",
            "fields": ["tenant_id", "lifecycle_state"],
            "name": "idx_tenant_lifecycle",
        },
        {"type": "persistent", "fields": ["file_refs[*]"], "name": "idx_file_refs"},
        {"type": "persistent", "fields": ["security_group"], "name": "idx_security_group"},
        {"type": "persistent", "fields": ["lifecycle_state"], "name": "idx_lifecycle_state"},
        {"type": "persistent", "fields": ["domain"], "name": "idx_domain"},
        {"type": "persistent", "fields": ["major"], "name": "idx_major"},
        {"type": "persistent", "fields": ["is_active"], "name": "idx_is_active"},
        {
            "type": "persistent",
            "fields": ["tenant_id", "domain", "is_active"],
            "name": "idx_tenant_domain_active",
        },
    ]

    existing_indexes = collection.indexes()
    existing_names = [idx["name"] for idx in existing_indexes]

    for idx_cfg in indexes:
        name = idx_cfg["name"]
        if name not in existing_names:
            print(f"⚙️ 正在創建索引: {name}")
            collection.add_index(idx_cfg)
        else:
            print(f"✅ 索引 {name} 已存在")


if __name__ == "__main__":
    initialize_knowledge_assets()
