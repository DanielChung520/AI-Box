# Data-Agent 數據查詢服務

## 概述

Data-Agent 是 Tiptop 數據湖系統的核心服務，負責接受 BPA（如 MM-Agent）提供的自然語言查詢，依 metadata schema（`schema_registry.json`）進行 Text-to-SQL，透過 DuckDB 對資料湖執行查詢，並做基礎驗證後回傳給 BPA。目標是將 Datalake 資料架構抽象化，便於未來切換不同 schema，讓 BPA 專注業務流程。

**現況與待修訂**：詳見 [Data-Agent-規格書.md](Data-Agent-規格書.md) 第 9 章「待修訂」。

## 目錄結構

```
.docs-docs/Data-Agent/
├── README.md                          # 本文件
├── Data-Agent-規格書.md               # 服務規格說明
├── Data-Agent-TextToSql-優化調整報告.md # 優化歷程
├── Data-Agent-意圖語義分析架構.md      # 意圖分析架構
├── CodeDictionary-回退指南.md         # 代碼字典使用指南
├── ENVIRONMENT.md                     # 環境配置說明
└── testing/
    ├── DA-NL-Query-Test-19場景測試腳本.py
    └── code_dictionary_test.py
```

## 模型配置

### LLM 模型優先級（Text-to-SQL）

> ⚠️ **注意**：雲端模型（qwen3-coder:480b-cloud、gpt-oss:120b）需要 Ollama Connect 認證，請確保已登入。

| 優先級 | 模型 | 類型 | 說明 |
|--------|------|------|------|
| 1 | `mistral-nemo:12b` | Ollama 本地 | ⭐ **首選** (6.6 GB) |
| 2 | `qwen3:32b` | Ollama 本地 | 備用 (18.8 GB) |
| 3 | `llama3:8b` | Ollama 本地 | 最終備用 (4.3 GB) |
| 4 | `qwen3-coder:480b-cloud` | Ollama 雲端 | 需要認證 |
| 5 | `gpt-oss:120b` | Ollama 雲端 | 需要認證 |

### Embedding 模型（意圖分析 RAG）

| 優先級 | 模型 | 說明 |
|--------|------|------|
| 1 | `qwen3-embedding:latest` | ⭐ **首選** (Ollama) |
| 2 | `sentence-transformers/all-MiniLM-L6-v2` | Fallback (HuggingFace 內建) |

## 配置檔案

### 1. DataAgentConfig.json

位置：`datalake-system/data_agent/DataAgentConfig.json`

```json
{
  "llm": {
    "model_priority": ["qwen3:32b", "mistral-nemo:12b", "qwen3-coder:480b-cloud", "gpt-oss:120b"]
  },
  "embedding": {
    "model": "qwen3-embedding:latest",
    "fallback": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "text_to_sql": {
    "model": "qwen3:32b",
    "temperature": 0.3,
    "max_tokens": 2000
  }
}
```

### 2. .env 環境變數

位置：`datalake-system/data_agent/.env`

```bash
# Text-to-SQL 模型
DATA_AGENT_TEXT_TO_SQL_MODEL=qwen3:32b

# Embedding 模型
DATA_AGENT_EMBEDDING_MODEL=qwen3-embedding:latest
DATA_AGENT_EMBEDDING_FALLBACK=sentence-transformers/all-MiniLM-L6-v2

# Ollama 預設模型
OLLAMA_DEFAULT_MODEL=qwen3:32b

# LLM 優先級
DATA_AGENT_MODEL_PRIORITY=qwen3:32b,mistral-nemo:12b,qwen3-coder:480b-cloud,gpt-oss:120b
```

## 服務 API

### 端口

| 服務 | 端口 | 狀態 |
|------|------|------|
| Data-Agent | 8004 | ✅ 運行中 |

### Endpoints

| Method | Endpoint | 功能 |
|--------|----------|------|
| GET | `/health` | 健康檢查 |
| POST | `/execute` | 執行查詢 |

### 請求範例

```bash
# Text-to-SQL
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test",
    "user_id": "user123",
    "task_type": "data_query",
    "task_data": {
      "action": "text_to_sql",
      "natural_language": "W01 各料號的庫存"
    }
  }'

# 執行 SQL
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "exec",
    "task_data": {
      "action": "execute_sql_on_datalake",
      "sql_query_datalake": "SELECT img01, SUM(img10) FROM img_file WHERE img02 = 'W01' GROUP BY img01"
    }
  }'
```

## 查詢流程

```
用戶輸入 → 步驟 1: 意圖分析 → 步驟 2: 類型確認 
         → 步驟 3: LLM 生成 SQL → 步驟 4: 執行 SQL → 步驟 5: 顯示結果
```

| 步驟 | 輸出 |
|------|------|
| 1. 意圖分析 | 查詢意圖、資料表、聚合方式 |
| 2. 類型確認 | text_to_sql / query_datalake |
| 3. SQL 生成 | 置信度、耗時、SQL 語句 |
| 4. SQL 執行 | 執行耗時、返回筆數 |
| 5. 結果顯示 | 數據表格、統計指標 |

## 代碼字典

位置：`datalake-system/data_agent/code_dictionary.json`

| 代碼類型 | 範例 | 說明 |
|---------|------|------|
| 倉庫 | W01 → 原料倉 | 倉庫代碼映射 |
| 料號 | 10-0001 | 格式：`^\d{2}-\d{4}$` |
| 程式 | AXMT520 | 程式代碼映射 |
| 表格別名 | inag_t → tlf_file | 表格別名映射 |

## 常見問題

### Q: Text-to-SQL 返回 404 錯誤？

A: 模型配置問題。檢查 `OLLAMA_DEFAULT_MODEL` 是否為 `qwen3:32b`

### Q: 查詢結果為空？

A: 可能原因：
- SQL 語句無效（檢查 conversion_log）
- 資料庫無符合資料
- LLM 輸出格式錯誤

### Q: 如何切換模型？

A: 修改 `data_agent/.env` 中的 `DATA_AGENT_TEXT_TO_SQL_MODEL`

## 相關文件

- [架構說明](Data-Agent-意圖語義分析架構.md)
- [規格書](Data-Agent-規格書.md)
- [TextToSql 優化報告](Data-Agent-TextToSql-優化調整報告.md)
- [代碼字典指南](CodeDictionary-回退指南.md)
- [環境配置](ENVIRONMENT.md)
