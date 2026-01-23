# SystemDocs 文件上傳測試記錄 v3.1

**創建日期**: 2026-01-20
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-20

---

## 第一階段：準備工作

### 執行日期

2026-01-20

### 環境確認結果

| 服務                 | 狀態           | 備註                  |
| -------------------- | -------------- | --------------------- |
| ArangoDB             | ✅ 運行中      | 端口 8529             |
| ChromaDB             | ⚠️ unhealthy | 端口 8001（服務正常） |
| SeaWeedFS (AI-Box)   | ✅ 運行中      | 端口 8333、8888       |
| SeaWeedFS (DataLake) | ✅ 運行中      | 端口 8334、8889       |
| Redis                | ✅ 運行中      | 端口 6379             |
| API Server           | ✅ 運行中      | 端口 8000             |
| RQ Worker            | ✅ 運行中      | PID 10220             |
| Ollama               | ✅ 運行中      | 端口 11434            |

**可用的 Ollama 模型**：

- `llama3.2:latest`
- `quentinz/bge-large-zh-v1.5:latest`
- `qwen3-next:latest`
- `glm-4.6:cloud`
- `glm-4.7:cloud`

### 數據清理結果

| 項目                           | 清理前  | 清理後   |
| ------------------------------ | ------- | -------- |
| SeaWeedFS bucket-ai-box-assets | 已清理  | 0 個檔案 |
| ArangoDB file_metadata         | 0 個    | 0 個     |
| ArangoDB processing_status     | 222 個  | 0 個     |
| ArangoDB entities              | 1251 個 | 0 個     |
| ArangoDB relations             | 937 個  | 0 個     |
| ArangoDB user_tasks (重複任務) | 2 個    | 1 個     |
| ChromaDB collections           | 0 個    | 0 個     |

### 額外清理（2026-01-20）

**發現問題**：

- `processing_status` 有 222 個舊記錄
- `user_tasks` 有 1 個重複任務（_key = systemAdmin_SystemDocs）
- `user_tasks/systemAdmin_systemAdmin_SystemDocs` 的 `fileTree` 有 104 個 children（舊的測試數據）
- `user_tasks` 中有 339 個 `unauthenticated` 用戶的任務（測試殘留數據）

**處理結果**：

- ✅ 清理 processing_status: 222 個記錄
- ✅ 清理重複的 user_tasks（_key = systemAdmin_SystemDocs）
- ✅ 清理 fileTree[0].children: 104 個項目
- ✅ 刪除 unauthenticated 用戶的任務: 339 個

**系統當前狀態**：

| 項目                                                    | 數量                            |
| ------------------------------------------------------- | ------------------------------- |
| file_metadata                                           | 0 個                            |
| processing_status                                       | 0 個                            |
| entities                                                | 0 個                            |
| relations                                               | 0 個                            |
| ChromaDB collections                                    | 0 個                            |
| SeaWeedFS bucket-ai-box-assets                          | 0 個                            |
| user_tasks[systemAdmin_systemAdmin_SystemDocs].fileTree | 已移除                          |
| user_tasks（總數）                                      | 1 個（只有 systemAdmin 的任務） |

**系統已完全清理完成，可以開始測試。**

### 清理命令

```bash
# SeaWeedFS
docker exec seaweedfs-ai-box-volume sh -c 'rm -f /var/lib/seaweedfs/bucket-ai-box-assets_*.*'
docker restart seaweedfs-ai-box-volume seaweedfs-ai-box-filer

# ArangoDB
python3 << 'EOF'
from arango import ArangoClient
client = ArangoClient(hosts='http://localhost:8529')
db = client.db('ai_box_kg', username='root', password='changeme')
for name in ['file_metadata', 'entities', 'relations']:
    coll = db.collection(name)
    for doc in coll:
        coll.delete(doc)
    print(f'{name}: 已清理')
EOF

# ChromaDB
python3 << 'EOF'
import chromadb
client = chromadb.HttpClient(host='localhost', port=8001)
for coll in client.list_collections():
    client.delete_collection(coll.name)
    print(f'刪除 collection: {coll.name}')
EOF
```

---

## 第二階段：單一文件測試

### 執行日期

2026-01-20

### 測試文件

- 文件名：`README.md`
- 路径：`docs/系统设计文档/README.md`
- 大小：18 KB
- file_id: `b37ac95e-c73a-4251-9201-b75c2fb69998`

### 上傳結果

- ✅ 文件上傳成功
- ✅ 存儲到 SeaWeedFS: `s3://bucket-ai-box-assets/tasks/systemAdmin_SystemDocs/b37ac95e-...md`
- ✅ ArangoDB 元數據創建成功

### 處理結果

| 階段     | 狀態    | 說明                      |
| -------- | ------- | ------------------------- |
| 文件讀取 | ✅ 成功 | 從 S3 讀取 18850 bytes    |
| 分塊處理 | ❌ 失敗 | 依賴 LLM 服務             |
| 向量化   | ❌ 失敗 | 依賴 LLM 服務（文件摘要） |
| 知識圖譜 | ❌ 失敗 | 依賴 LLM 服務             |

### 失敗原因

**LLM 服務配置問題**：

| 服務             | 狀態      | 原因                             |
| ---------------- | --------- | -------------------------------- |
| OpenAI (ChatGPT) | ❌        | SDK 未安裝                       |
| Google Gemini    | ❌        | `gemini-pro` 模型已棄用（404） |
| Qwen             | ❌        | 需要 API key                     |
| Grok             | ❌        | 需要 API key                     |
| Ollama           | ⚠️ 可用 | 但代碼未正確 fallback            |

### 問題分析

1. **文件摘要生成失敗**：處理流程中需要使用 LLM 生成文件摘要用於 Ontology 選擇，但所有 LLM 服務都不可用
2. **缺少 Fallback 機制**：代碼嘗試了多種 LLM，但沒有正確 fallback 到 Ollama
3. **Gemini 模型過時**：`gemini-pro` 已被棄用，需要更新為新模型（如 `gemini-1.5-pro`）

### 嘗試的解決方案

1. ✅ 重啟 RQ Worker（設置 `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES`）
2. ❌ 同步執行處理腳本（LLM 服務不可用）

### 下一步行動

1. **修復 LLM Fallback 機制**：確保 Ollama 可以正確 fallback
2. **更新 Gemini 模型**：從 `gemini-pro` 更新為新模型
3. **安裝 OpenAI SDK**：或配置其他可用的 LLM 服務
4. **可選**：使用本地 Ollama 模型進行處理

### 測試狀態：待修復後重新執行

---

## 第三階段：批量文件測試（5 個文件）

### 執行日期

待執行

### 測試記錄

| 項目         | 數值        | 備註 |
| ------------ | ----------- | ---- |
| 總文件數     | 5 個        |      |
| 成功處理     | ___ 個      |      |
| 失敗處理     | ___ 個      |      |
| 並發任務數   | 5 個        |      |
| 總處理時間   | ___ 分鐘    |      |
| 平均處理時間 | ___ 秒/文件 |      |

### 詳細記錄

| 序號 | 文件名 | 大小  | 分塊 | 向量 | 實體 | 關係 | 狀態  | 處理時間 |
| ---- | ------ | ----- | ---- | ---- | ---- | ---- | ----- | -------- |
| 1    |        | ___KB | ___  | ___  | ___  | ___  | ✅/❌ | ___ 秒   |
| 2    |        | ___KB | ___  | ___  | ___  | ___  | ✅/❌ | ___ 秒   |
| 3    |        | ___KB | ___  | ___  | ___  | ___  | ✅/❌ | ___ 秒   |
| 4    |        | ___KB | ___  | ___  | ___  | ___  | ✅/❌ | ___ 秒   |
| 5    |        | ___KB | ___  | ___  | ___  | ___  | ✅/❌ | ___ 秒   |

---

## 第四階段：完整系統文檔處理

### 執行日期

待執行

### 執行摘要

| 項目         | 數值        |
| ------------ | ----------- |
| 總文件數     | ___ 個      |
| 成功處理     | ___ 個      |
| 失敗處理     | ___ 個      |
| 總處理時間   | ___ 分鐘    |
| 平均處理時間 | ___ 秒/文件 |

---

## 修改記錄

| 日期       | 版本 | 修改內容                       | 修改人       |
| ---------- | ---- | ------------------------------ | ------------ |
| 2026-01-20 | 3.1  | 初始版本，執行第一階段準備工作 | Daniel Chung |
|            |      |                                |              |

---

**最後更新日期**: 2026-01-20
