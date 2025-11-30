# ArangoDB SDK 封裝

**創建日期**: 2025-10-25
**創建人**: Daniel Chung
**最後修改日期**: 2025-11-25 22:58 (UTC+8)

---

## 概述

本模組提供 ArangoDB 圖資料庫的 Python SDK 封裝，支持文檔存儲和圖查詢功能。

## 功能特性

- 連接管理和資料庫操作
- 文檔集合 CRUD 操作
- 圖結構管理（頂點和邊）
- 圖遍歷和關係查詢
- AQL 查詢支持
- 知識圖譜建模支持

## 安裝依賴

```bash
pip install python-arango
```

## 使用方法

### 1. 初始化客戶端

```python
from databases.arangodb import ArangoDBClient

client = ArangoDBClient(
    host="localhost",
    port=8529,
    username="root",
    password="ai_box_arangodb_password",
    database="ai_box_kg"
)
```

### 2. 文檔集合操作

```python
from databases.arangodb import ArangoCollection

# 創建或獲取集合
collection = client.get_or_create_collection("entities")
arango_collection = ArangoCollection(collection)

# 插入文檔
arango_collection.insert({
    "_key": "entity1",
    "name": "Python",
    "type": "programming_language",
    "description": "A high-level programming language"
})

# 獲取文檔
entity = arango_collection.get("entity1")

# 更新文檔
arango_collection.update({
    "_key": "entity1",
    "description": "Updated description"
})

# 查找文檔
results = arango_collection.find(
    filters={"type": "programming_language"},
    limit=10
)

# 刪除文檔
arango_collection.delete("entity1")
```

### 3. 圖操作

```python
from databases.arangodb import ArangoGraph

# 創建或獲取圖
graph = client.get_or_create_graph(
    name="knowledge_graph",
    edge_definitions=[{
        "edge_collection": "relations",
        "from_vertex_collections": ["entities"],
        "to_vertex_collections": ["entities"]
    }]
)
arango_graph = ArangoGraph(graph)

# 創建頂點集合
arango_graph.create_vertex_collection("entities")

# 插入頂點
arango_graph.insert_vertex("entities", {
    "_key": "python",
    "name": "Python",
    "type": "language"
})

arango_graph.insert_vertex("entities", {
    "_key": "django",
    "name": "Django",
    "type": "framework"
})

# 插入邊（關係）
arango_graph.insert_edge(
    collection="relations",
    edge={
        "_key": "python_django",
        "type": "used_by",
        "weight": 1.0
    },
    from_vertex="entities/python",
    to_vertex="entities/django"
)

# 圖遍歷
result = arango_graph.traverse(
    start_vertex="entities/python",
    direction="outbound",
    max_depth=2
)

# 獲取鄰居
neighbors = arango_graph.get_neighbors(
    vertex_id="entities/python",
    direction="outbound"
)

# 最短路徑
path = arango_graph.get_shortest_path(
    start_vertex="entities/python",
    end_vertex="entities/django"
)
```

### 4. AQL 查詢

```python
# 執行 AQL 查詢
result = client.execute_aql(
    query="""
        FOR entity IN entities
        FILTER entity.type == @type
        RETURN entity
    """,
    bind_vars={"type": "programming_language"}
)

# 圖查詢示例
result = client.execute_aql(
    query="""
        FOR v, e, p IN 1..2 OUTBOUND 'entities/python' relations
        RETURN {
            vertex: v,
            edge: e,
            path: p
        }
    """
)
```

### 5. 知識圖譜建模示例

```python
# 創建知識圖譜結構
graph = client.get_or_create_graph(
    name="knowledge_graph",
    edge_definitions=[{
        "edge_collection": "relations",
        "from_vertex_collections": ["entities"],
        "to_vertex_collections": ["entities"]
    }]
)

arango_graph = ArangoGraph(graph)

# 創建實體和關係
arango_graph.insert_vertex("entities", {
    "_key": "person1",
    "name": "Alice",
    "type": "Person"
})

arango_graph.insert_vertex("entities", {
    "_key": "company1",
    "name": "Tech Corp",
    "type": "Company"
})

arango_graph.insert_edge(
    collection="relations",
    edge={
        "_key": "works_at_1",
        "type": "works_at",
        "position": "Engineer",
        "since": "2020-01-01"
    },
    from_vertex="entities/person1",
    to_vertex="entities/company1"
)
```

## 環境變數

- `ARANGODB_HOST`: ArangoDB 服務器地址（默認: localhost）
- `ARANGODB_PORT`: ArangoDB 服務器端口（默認: 8529）
- `ARANGODB_USERNAME`: 用戶名（默認: root）
- `ARANGODB_PASSWORD`: 密碼（默認: ai_box_arangodb_password）
- `ARANGODB_DATABASE`: 資料庫名稱（默認: ai_box_kg）

## 設定載入與連線池

- 非敏感配置集中在 `config/config.json` → `datastores.arangodb`，由 `databases/arangodb/settings.py` 載入。
- `load_arangodb_settings()` 會自動尋找 `config/config.json`，若不存在則回退至樣板。
- `ArangoDBClient` 支援以下進階選項：
  - `request_timeout`：HTTP 請求逾時（秒）
  - `retry.enabled/max_attempts/backoff_factor`：使用 `tenacity` 的連線重試策略
  - `pool.connections/max_size/timeout`：`DefaultHTTPClient` 連線池大小
  - `tls.enabled/verify/ca_file`：TLS 驗證與 CA 憑證

```python
from databases.arangodb import ArangoDBClient, load_arangodb_settings

settings = load_arangodb_settings()
client = ArangoDBClient(settings=settings)
```

若需要指定自訂 config 路徑，可呼叫 `load_arangodb_settings("path/to/config.json")`。

## Docker 部署

ArangoDB 已配置在 `docker-compose.yml` 中：

```yaml
arangodb:
  image: arangodb:3.12
  ports:
    - "8529:8529"
  environment:
    - ARANGO_ROOT_PASSWORD=ai_box_arangodb_password
    - ARANGO_DATABASE=ai_box_kg
```

啟動服務：

```bash
docker-compose up -d arangodb
```

## 測試

```python
# 健康檢查
status = client.heartbeat()
print(status)  # {'status': 'healthy', 'database': 'ai_box_kg'}

# 列出集合
collections = client.list_collections()
print(collections)  # ['entities', 'relations', ...]

# 統計文檔
count = arango_collection.count()
print(f"Collection contains {count} documents")
```

## 知識圖譜查詢封裝

```python
from databases.arangodb import queries

neighbors = queries.fetch_neighbors(client, "entities/agent_planning", limit=5)
subgraph = queries.fetch_subgraph(client, "entities/agent_planning", max_depth=2)
filtered = queries.filter_entities(client, filters={"type": ["agent"]}, limit=10)
```

## 種子資料與腳本

- `datasets/arangodb/schema.yml`：欄位與索引定義。
- `datasets/arangodb/seed_data.json`：預設 Agent/Task/Resource/ Dataset 節點。
- `docs/datasets/arangodb-kg-schema.md`：完整記錄與 migration 規範。
- `scripts/arangodb_seed.py --reset`：清空並匯入資料（可搭配 `--dry-run`）。
- `scripts/arangodb_query_demo.py --vertex entities/agent_planning`：驗證常用查詢。

## 注意事項

1. 文檔必須包含 `_key` 字段（或由系統自動生成）
2. 頂點和邊的 ID 格式為 `collection/_key`
3. 圖遍歷操作可能消耗較多資源，注意設置合理的深度限制
4. AQL 查詢支持複雜的圖查詢邏輯
5. 知識圖譜建模需要預先設計好實體和關係的 Schema

---

**最後更新**: 2025-11-25 22:58 (UTC+8)
