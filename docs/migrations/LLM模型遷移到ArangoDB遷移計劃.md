# LLM 模型遷移到 ArangoDB 遷移計劃

**版本**: 1.0
**創建日期**: 2025-12-20
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-20

---

## 📋 概述

將前端硬編碼的 LLM 模型列表遷移到後台管理，使用 ArangoDB 存儲模型信息，實現模型的集中管理和動態配置。

### 目標

1. **集中管理**: 將模型定義從前端代碼遷移到後台數據庫
2. **動態配置**: 支持通過 API 動態添加、更新、刪除模型
3. **擴展性**: 支持添加更多模型提供商和模型類型
4. **向後兼容**: 保持現有前端功能正常運行

---

## 🗄️ ArangoDB Collection 設計

### Collection 名稱

```
llm_models
```

### 數據結構

```json
{
  "_key": "gpt-4-turbo",           // 使用 model_id 作為 _key
  "_id": "llm_models/gpt-4-turbo",
  "model_id": "gpt-4-turbo",       // 模型唯一標識符
  "name": "GPT-4 Turbo",            // 顯示名稱
  "provider": "chatgpt",            // 提供商 (enum)
  "description": "GPT-4 Turbo - 快速響應版本",
  "capabilities": [                 // 模型能力列表
    "chat",
    "completion",
    "code",
    "vision",
    "function_calling",
    "streaming"
  ],
  "status": "active",               // 狀態: active/deprecated/maintenance/coming_soon/beta
  "context_window": 128000,         // 上下文窗口大小 (tokens)
  "max_output_tokens": 4096,        // 最大輸出 tokens
  "parameters": "~1.8T",            // 參數規模
  "release_date": "2023-11-06",     // 發布日期 (ISO 8601)
  "license": "proprietary",         // 許可證類型
  "languages": ["en", "zh"],        // 支持語言列表
  "icon": "fa-robot",               // FontAwesome 圖標類名
  "color": "text-green-400",        // 主題顏色
  "order": 40,                      // 排序順序
  "is_default": false,              // 是否為提供商默認模型
  "metadata": {},                   // 額外元數據
  "created_at": "2025-12-20T00:00:00Z",
  "updated_at": "2025-12-20T00:00:00Z"
}
```

### 索引設計

```javascript
// 唯一索引
{
  "type": "persistent",
  "fields": ["model_id"],
  "unique": true
}

// 查詢索引
{
  "type": "persistent",
  "fields": ["provider"]
}

{
  "type": "persistent",
  "fields": ["status"]
}

{
  "type": "persistent",
  "fields": ["capabilities[*]"]  // 數組索引
}

{
  "type": "persistent",
  "fields": ["order"]
}

{
  "type": "persistent",
  "fields": ["is_default"]
}
```

---

## 📦 數據模型定義

### Pydantic 模型

文件位置: `services/api/models/llm_model.py`

主要類別:

- `LLMProvider` (Enum): 提供商枚舉
- `ModelCapability` (Enum): 模型能力枚舉
- `ModelStatus` (Enum): 模型狀態枚舉
- `LLMModelBase`: 基礎模型
- `LLMModelCreate`: 創建請求模型
- `LLMModelUpdate`: 更新請求模型
- `LLMModel`: 響應模型（包含 ArangoDB 字段）
- `LLMModelQuery`: 查詢參數模型

---

## 🔧 服務層實現

### LLM Model Service

文件位置: `services/api/services/llm_model_service.py`

主要方法:

- `create(model: LLMModelCreate) -> LLMModel`: 創建模型
- `get_by_id(model_id: str) -> Optional[LLMModel]`: 根據 ID 獲取模型
- `get_all(query: Optional[LLMModelQuery]) -> List[LLMModel]`: 獲取所有模型（支持篩選）
- `update(model_id: str, update: LLMModelUpdate) -> Optional[LLMModel]`: 更新模型
- `delete(model_id: str) -> bool`: 刪除模型
- `get_by_provider(provider: LLMProvider) -> List[LLMModel]`: 根據提供商獲取模型列表

---

## 🚀 API 路由設計

### 端點定義

文件位置: `api/routers/llm_models.py` (需要創建)

#### 1. 獲取模型列表

```http
GET /api/v1/models
```

**查詢參數**:

- `provider` (optional): 提供商篩選
- `status` (optional): 狀態篩選
- `capability` (optional): 能力篩選
- `search` (optional): 搜索關鍵詞（名稱、描述）
- `limit` (optional, default: 100): 返回數量限制
- `offset` (optional, default: 0): 偏移量

**響應**:

```json
{
  "success": true,
  "data": {
    "models": [
      {
        "_key": "gpt-4-turbo",
        "model_id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "chatgpt",
        ...
      }
    ],
    "total": 50
  }
}
```

#### 2. 獲取單個模型

```http
GET /api/v1/models/{model_id}
```

**響應**:

```json
{
  "success": true,
  "data": {
    "model": { ... }
  }
}
```

#### 3. 創建模型（管理員）

```http
POST /api/v1/models
```

**請求體**:

```json
{
  "model_id": "new-model",
  "name": "New Model",
  "provider": "chatgpt",
  ...
}
```

#### 4. 更新模型（管理員）

```http
PUT /api/v1/models/{model_id}
```

#### 5. 刪除模型（管理員）

```http
DELETE /api/v1/models/{model_id}
```

---

## 📝 模型列表數據

### 當前前端硬編碼模型

從 `ai-bot/src/components/ChatInput.tsx` 提取的模型:

1. **Auto** (`auto`) - 自動選擇
2. **SmartQ IEE** (`smartq-iee`) - SmartQ
3. **SmartQ HCI** (`smartq-hci`) - SmartQ
4. **GPT-4 Turbo** (`gpt-4-turbo`) - OpenAI
5. **GPT-4** (`gpt-4`) - OpenAI
6. **GPT-3.5 Turbo** (`gpt-3.5-turbo`) - OpenAI
7. **Gemini Pro** (`gemini-pro`) - Google
8. **Gemini Ultra** (`gemini-ultra`) - Google
9. **Qwen Turbo** (`qwen-turbo`) - Alibaba
10. **Qwen Plus** (`qwen-plus`) - Alibaba
11. **Grok Beta** (`grok-beta`) - xAI
12. **Llama 2** (`llama2`) - Ollama
13. **Qwen3 Coder 30B** (`qwen3-coder:30b`) - Ollama
14. **GPT-OSS 20B** (`gpt-oss:20b`) - Ollama

### 擴展模型列表

#### OpenAI (ChatGPT)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `gpt-4o` | GPT-4o | 128K | ~1.8T | Active |
| `gpt-4-turbo` | GPT-4 Turbo | 128K | ~1.8T | Active |
| `gpt-4` | GPT-4 | 8K | ~1.8T | Active |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | 16K | ~175B | Active |

#### Google (Gemini)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `gemini-2.0-flash-exp` | Gemini 2.0 Flash (Experimental) | 1M | - | Beta |
| `gemini-1.5-pro` | Gemini 1.5 Pro | 2M | ~540B | Active |
| `gemini-pro` | Gemini Pro | 32K | ~540B | Active |
| `gemini-ultra` | Gemini Ultra | 2M | ~1.5T | Active |

#### Anthropic (Claude)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `claude-3.5-sonnet` | Claude 3.5 Sonnet | 200K | ~250B | Active |
| `claude-3-opus` | Claude 3 Opus | 200K | ~400B | Active |
| `claude-3-sonnet` | Claude 3 Sonnet | 200K | ~250B | Active |
| `claude-3-haiku` | Claude 3 Haiku | 200K | ~80B | Active |

#### 阿里巴巴 (Qwen)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `qwen-2.5-72b-instruct` | Qwen 2.5 72B Instruct | 32K | 72B | Active |
| `qwen-plus` | Qwen Plus | 32K | - | Active |
| `qwen-turbo` | Qwen Turbo | 8K | - | Active |

#### xAI (Grok)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `grok-2` | Grok-2 | 131K | ~314B | Active |
| `grok-beta` | Grok Beta | 131K | ~314B | Beta |

#### Ollama (本地部署)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `llama3.1:405b` | Llama 3.1 405B | 131K | 405B | Active |
| `llama3.1:70b` | Llama 3.1 70B | 131K | 70B | Active |
| `qwen3-coder:30b` | Qwen3 Coder 30B | 32K | 30B | Active |
| `gpt-oss:20b` | GPT-OSS 20B | 8K | 20B | Active |
| `llama2` | Llama 2 | 4K | 70B | Deprecated |

#### Mistral AI

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `mistral-large` | Mistral Large | 128K | ~123B | Active |
| `mistral-medium` | Mistral Medium | 32K | ~50B | Active |
| `mistral-small` | Mistral Small | 32K | ~24B | Active |

#### DeepSeek

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `deepseek-chat` | DeepSeek Chat | 64K | ~67B | Active |
| `deepseek-coder` | DeepSeek Coder | 16K | ~33B | Active |

#### Databricks (DBRX)

| Model ID | Name | Context Window | Parameters | Status |
|----------|------|----------------|------------|--------|
| `dbrx` | DBRX | 32K | 132B | Active |

#### SmartQ (自定義)

| Model ID | Name | Description | Status |
|----------|------|-------------|--------|
| `smartq-iee` | SmartQ IEE | SmartQ IEE 專用模型 | Active |
| `smartq-hci` | SmartQ HCI | SmartQ HCI 專用模型 | Active |

---

## 🔄 遷移步驟

### 階段 1: 後台準備（已完成 ✅）

- [x] 創建數據模型 (`services/api/models/llm_model.py`)
- [x] 創建服務類 (`services/api/services/llm_model_service.py`)
- [x] 設計 Collection 結構和索引

### 階段 2: 數據遷移

1. **執行遷移腳本**

   ```bash
   python -m services.api.services.migrations.migrate_llm_models
   ```

2. **驗證數據**
   - 檢查所有模型是否成功創建
   - 驗證索引是否正確創建
   - 測試查詢功能

### 階段 3: API 實現

1. **創建 API 路由**
   - 文件: `api/routers/llm_models.py`
   - 實現所有端點
   - 添加權限檢查（管理員功能）

2. **註冊路由**
   - 在 `api/main.py` 中註冊新路由

3. **測試 API**
   - 使用 Postman 或 curl 測試所有端點
   - 驗證響應格式和錯誤處理

### 階段 4: 前端遷移

1. **創建 API 客戶端函數**
   - 文件: `ai-bot/src/lib/api.ts`
   - 添加 `getModels()` 函數

2. **更新 ChatInput 組件**
   - 文件: `ai-bot/src/components/ChatInput.tsx`
   - 移除硬編碼的 `llmModels` 數組
   - 從 API 獲取模型列表
   - 添加加載狀態和錯誤處理

3. **測試前端功能**
   - 驗證模型選單正常顯示
   - 測試模型選擇功能
   - 測試收藏功能

### 階段 5: 向後兼容和文檔

1. **向後兼容處理**
   - 如果 API 失敗，使用默認模型列表 fallback
   - 確保現有功能不受影響

2. **更新文檔**
   - API 文檔
   - 開發文檔
   - 遷移記錄

---

## 🧪 測試計劃

### 單元測試

- [ ] `LLMModelService.create()` 測試
- [ ] `LLMModelService.get_by_id()` 測試
- [ ] `LLMModelService.get_all()` 測試（含篩選）
- [ ] `LLMModelService.update()` 測試
- [ ] `LLMModelService.delete()` 測試

### 集成測試

- [ ] API 端點測試
- [ ] 前端組件測試
- [ ] 端到端測試

### 性能測試

- [ ] 大量模型列表查詢性能
- [ ] 索引查詢性能

---

## ⚠️ 風險與注意事項

### 風險

1. **數據遷移風險**
   - 遷移過程中可能出現數據不一致
   - **緩解**: 先備份現有數據，遷移後驗證

2. **前端兼容性風險**
   - 前端可能依賴硬編碼的模型列表
   - **緩解**: 實現 fallback 機制，API 失敗時使用默認列表

3. **性能風險**
   - 每次加載都需要查詢數據庫
   - **緩解**: 實現前端緩存，定期刷新

### 注意事項

1. **模型 ID 唯一性**: 確保 `model_id` 全局唯一
2. **向後兼容**: 保持現有 `model_id` 不變
3. **權限控制**: 創建/更新/刪除操作需要管理員權限
4. **數據驗證**: 嚴格驗證輸入數據，避免無效數據

---

## 📅 時間表

| 階段 | 任務 | 預計時間 | 狀態 |
|------|------|----------|------|
| 階段 1 | 後台準備 | 1-2 天 | ✅ 已完成 |
| 階段 2 | 數據遷移 | 0.5 天 | ⏸️ 待執行 |
| 階段 3 | API 實現 | 1-2 天 | ⏸️ 待執行 |
| 階段 4 | 前端遷移 | 1-2 天 | ⏸️ 待執行 |
| 階段 5 | 測試和文檔 | 1 天 | ⏸️ 待執行 |
| **總計** | | **4-7 天** | |

---

## 📚 相關文檔

- [ArangoDB 文檔](https://www.arangodb.com/docs/)
- [Pydantic 文檔](https://docs.pydantic.dev/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [前端 API 客戶端文檔](./../../ai-bot/src/lib/api.ts)

---

**計劃版本**: 1.0
**最後更新**: 2025-12-20
**維護者**: Daniel Chung
