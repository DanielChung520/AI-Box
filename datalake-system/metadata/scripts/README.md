# Schema Registry Scripts

本目錄包含 Schema Registry 的管理腳本，用於 HybridRRAG 架構。

---

## 腳本列表

| 腳本 | 說明 |
|------|------|
| `schemaUpload.py` | Schema 上傳腳本 |
| `schemaUpdate.py` | Schema 更新腳本 |
| `schemaRAG.py` | Schema RAG 查詢腳本 |

---

## 配置檔案

| 檔案 | 說明 |
|------|------|
| `../config/schema_rag_config.yaml` | 主配置檔案 |

---

## 使用方式

### 1. schemaUpload.py - 首次上傳

```bash
# 執行上傳
python schemaUpload.py -s ../tiptop_schema_registry.json

# 參數說明
-s, --schema    Schema Registry JSON 檔案路徑 (必填)
-c, --config    配置文件路徑 (預設: config/schema_rag_config.yaml)
```

**功能**：
- 解析 `tiptop_schema_registry.json`
- 向量化後上傳至 Qdrant
- 圖譜化後上傳至 ArangoDB

### 2. schemaUpdate.py - 增量更新

```bash
# 檢查變更（不執行更新）
python schemaUpdate.py -s ../tiptop_schema_registry.json -C

# 執行更新
python schemaUpdate.py -s ../tiptop_schema_registry.json
```

**功能**：
- 計算 JSON Hash 比對變更
- 增量更新 Qdrant（Upsert）
- 增量更新 ArangoDB
- 記錄更新狀態至 `schema_update_state.json`

### 3. schemaRAG.py - 查詢測試

```bash
# 混合檢索（預設）
python schemaRAG.py -q "料件 主檔"

# 只用向量檢索
python schemaRAG.py -q "料件 主檔" -s vector

# 只用圖譜檢索
python schemaRAG.py -q "料件 主檔" -s graph

# 指定系統
python schemaRAG.py -q "料件 主檔" -S tiptop

# 指定類型
python schemaRAG.py -q "料件 主檔" -t table
```

**參數說明**：
| 參數 | 說明 |
|------|------|
| `-q, --query` | 查詢語句 (必填) |
| `-s, --strategy` | 檢索策略: `vector`, `graph`, `hybrid` (預設: hybrid) |
| `-S, --system` | 系統 ID |
| `-t, --type` | 文檔類型: `table`, `concept`, `intent` |

---

## 配置說明

### config/schema_rag_config.yaml

```yaml
# Qdrant 配置
qdrant:
  host: "localhost"
  port: 6333
  collection_name: "schema_registry"
  vector_size: 1024

# ArangoDB 配置
arangodb:
  host: "localhost"
  port: 8529
  username: "root"
  password: ""
  database: "schema_registry_db"
  collection_prefix: "schema_"

# 檢索配置
retrieval:
  top_k: 10
  vector_weight: 0.6
  graph_weight: 0.4
```

---

## 資料庫結構

### Qdrant Collection

```
Collection: schema_registry
│
├── Point 1
│   └── payload: { type: "table", system_id: "tiptop", name: "ima_file", ... }
│
├── Point 2
│   └── payload: { type: "concept", system_id: "tiptop", name: "MATERIAL_CATEGORY", ... }
│
└── ...
```

### ArangoDB Collections

```
Database: schema_registry_db
│
├── Collection: schema_entities
│   ├── { _key: "ima_file_tiptop", type: "table", system_id: "tiptop", ... }
│   ├── { _key: "MATERIAL_CATEGORY_tiptop", type: "concept", system_id: "tiptop", ... }
│   └── ...
│
└── Collection: schema_relationships
    ├── { _from: "entities/ima_file_tiptop", _to: "entities/ima01_tiptop", type: "has_column", ... }
    └── ...
```

---

## 執行流程

### 首次部署

```bash
# 1. 上傳 Schema
python schemaUpload.py -s ../tiptop_schema_registry.json

# 2. 測試查詢
python schemaRAG.py -q "料件 主檔 庫存"
```

### 日常更新

```bash
# 檢查變更
python schemaUpdate.py -s ../tiptop_schema_registry.json -C

# 執行更新（若有變更）
python schemaUpdate.py -s ../tiptop_schema_registry.json
```

### 查詢驗證

```bash
# 測試各種查詢
python schemaRAG.py -q "料號 品名"
python schemaRAG.py -q "交易 類型"
python schemaRAG.py -q "庫存 位置"
```

---

## 依賴套件

```bash
pip install qdrant-client arango-python pyyaml
```

---

## 已知限制

1. **向量化**：目前使用簡化的 hash-based 向量，未來應替換為 Ollama/nomic-embed-text
2. **NER**：圖譜搜索目前使用關鍵字匹配，未來應加入 NER 實體識別
3. **權重調整**：向量/圖譜權重需根據實際效果調整

---

## 相關文檔

- [Schema Registry README](../README.md)
- [上傳功能架構說明](../../../../docs/系统设计文档/核心组件/文件上傳向量圖譜/上傳的功能架構說明-v4.0.md)
- [HybridRAG查詢處理示例](../../../../docs/系统设计文档/核心组件/文件上傳向量圖譜/HybridRAG查询处理示例.md)
