# LLM 模型列表

**版本**: 1.3
**創建日期**: 2025-12-20
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-24

---

## 📋 概述

本文檔列出了系統中所有可用的 LLM 模型。模型分為兩類：

1. **數據庫模型**: 存儲在 ArangoDB 中的預定義模型（全域配置）
2. **動態發現模型**: 從 Ollama 服務器（本地和遠程）自動發現的模型

---

## 🔐 模型激活邏輯（重要）

**重要更新（2026-01-27）**：前端模型選擇列表現在只顯示**已激活的模型**。

### 激活條件

模型必須滿足以下條件才會在前端顯示：

1. **雲端模型（需要 API Key）**：
   - 必須在 ArangoDB 中配置對應 Provider 的 API Key
   - 通過 `llm_provider_config_service` 檢查 API Key 是否存在
   - 只有已配置 API Key 的 Provider 的模型才會顯示

2. **Ollama 模型（本地/遠程）**：
   - 默認激活（不需要 API Key）
   - 需要 Ollama 服務運行且模型已下載

3. **Auto 模型**：
   - 默認激活（自動選擇最佳模型）

### 實現位置

- **API 端點**：
  - `/api/v1/models`（`llm_models.py`）：過濾 `is_active=False` 的模型
  - `/api/v1/chat/models`（`chat.py`）：檢查 Provider API Key 配置並過濾未激活模型

- **服務層**：
  - `llm_model_service.get_all_with_discovery()`：設置 `is_active` 狀態
  - `genai_model_registry_service.list_models()`：返回所有模型（由 API 層過濾）

### 模型狀態字段

- `is_active`: 布爾值，表示模型是否可用
  - `True`: 模型已激活，會在前端顯示
  - `False`: 模型未激活，不會在前端顯示

### 注意事項

- 如果 Provider 未配置 API Key，該 Provider 的所有模型都不會在前端顯示
- 配置 API Key 後，需要刷新前端頁面才能看到新激活的模型
- Ollama 模型的激活狀態取決於 Ollama 服務是否運行以及模型是否已下載

---

## 🔄 模型來源

### 數據庫模型 (Database Models)

這些模型存儲在 ArangoDB 的 `llm_models` collection 中，由系統管理員維護。

### 動態發現模型 (Discovered Models)

這些模型通過查詢配置的 Ollama 服務器節點自動發現，格式為：`ollama:{host}:{port}:{model_name}`

---

## 🤖 Auto 模式（自動選擇）

### 模型選擇邏輯

當用戶選擇「自動」模式時，系統按以下優先級選擇模型：

1. **收藏模型優先**（未來迭代）
   - 如果用戶有收藏的模型，會在收藏列表中優先選擇
   - 目前收藏功能已實現，模型調用邏輯待後續迭代開發

2. **任務分類路由**（當前實現）
   - 使用 `TaskClassifier` 對用戶輸入進行分類
   - 根據任務類型（QUERY, EXECUTION, REVIEW, PLANNING, COMPLEX）選擇最佳模型
   - 任務分類結果包含 `task_type`, `confidence`, `reasoning` 字段

3. **Provider 允許列表**
   - 根據 `policy_gate.get_allowed_providers()` 獲取允許的 Provider
   - 過濾不允許的 Provider

4. **故障轉移**
   - 如果首選 Provider 失敗，自動切換到備用 Provider
   - 最終 fallback 到本地 Ollama

### 實現位置

- **任務分類**: `agents/task_analyzer/classifier.py`
- **路由邏輯**: `api/routers/chat.py` (Auto 模式分支)
- **故障轉移**: `llm/moe/failover.py`

---

## 🛡️ 錯誤處理與用戶友好消息

### 錯誤翻譯機制

系統將技術性錯誤轉換為用戶友好的錯誤消息，避免暴露內部實現細節。

### 錯誤類型與翻譯

| 錯誤類型 | 錯誤代碼 | 用戶看到的消息 |
|---------|---------|--------------|
| API Key 無效 | `API_INVALID` | 哎呀，發生了一些小狀況！🔐 API 授權出現問題，請通知管理員（錯誤代碼：API_INVALID）😅 |
| 網路錯誤 | `NETWORK_ERROR` | 哎呀，發生了一些小狀況！🌐 網路連線有點不穩，請稍後再試或通知管理員（錯誤代碼：NETWORK_ERROR）😅 |
| 超出限制 | `LIMIT_EXCEEDED` | 哎呀，發生了一些小狀況！😓 AI 模型服務超出使用限制，請通知管理員（錯誤代碼：LIMIT_EXCEEDED）😅 |
| 服務不可用 | `SERVICE_UNAVAILABLE` | 哎呀，發生了一些小狀況！🔧 AI 服務正在休息中，請稍後再試或通知管理員（錯誤代碼：SERVICE_UNAVAILABLE）😅 |
| 模型不存在 | `MODEL_NOT_FOUND` | 哎呀，發生了一些小狀況！🤔 指定的 AI 模型不存在，請通知管理員（錯誤代碼：MODEL_NOT_FOUND）😅 |
| 模型不在允許列表 | `MODEL_NOT_ALLOWED` | 哎呀，發生了一些小狀況！🤷 您選擇的 AI 模型超出使用限制或未被管理員允許，請嘗試其他模型（錯誤代碼：MODEL_NOT_ALLOWED）😅 |
| 內容被過濾 | `CONTENT_FILTERED` | 哎呀，發生了一些小狀況！🛡️ 您的請求被安全過濾攔截，請調整問題內容後再試（錯誤代碼：CONTENT_FILTERED）😅 |
| 上下文過長 | `CONTEXT_TOO_LONG` | 哎呀，發生了一些小狀況！📝 對話內容太長了，請嘗試縮短對話或開啟新對話（錯誤代碼：CONTEXT_TOO_LONG）😅 |
| 其他錯誤 | 原始代碼 | 哎呀，發生了一些小狀況，我感到很抱歉！請通知管理員（錯誤代碼：XXX）😅 |

### 實現位置

- **錯誤翻譯函數**: `api/routers/chat.py` → `translate_error_to_user_message()`
- **錯誤關鍵詞匹配**: 包含 API Key、網路、超出限制、服務不可用等關鍵詞
- **前端錯誤顯示**: `ai-bot/src/pages/Home.tsx` - 移除 "Chat failed:" 前綴

### 注意事項

- 錯誤消息包含 Emoji 和調皮的結尾（😅），提升用戶體驗
- 錯誤代碼便於管理員追蹤問題
- 原始錯誤會記錄到日誌，不會暴露給用戶

---

## 🔄 Fallback 模型（最終備用）

### 默認 Fallback 模型

當所有 Provider 都失敗時，系統會嘗試使用本地 Ollama 的 **qwen3-next:latest** 作為最終 fallback：

| 場景 | Fallback 模型 | 位置 |
|------|--------------|------|
| 非流式生成 (`_failover_generate`) | `qwen3-next:latest` | `llm/moe/moe_manager.py` |
| 流式生成 (`_failover_chat_stream`) | `qwen3-next:latest` | `llm/moe/moe_manager.py` |

### Fallback 順序

1. 雲端 Provider（根據配置）
   - Gemini → Qwen → ChatGPT
2. 本地 Ollama（最終 fallback）
   - localhost:11434 → qwen3-next:latest

### 實現位置

- `llm/moe/moe_manager.py` - `LAST_RESORT_MODEL = "qwen3-next:latest"`

---

## ⚠️ 已知 Bug 修復

### TaskClassificationResult 屬性名稱（2026-01-22）

**問題**: 錯誤使用 `task_classification.type` 導致 `'TaskClassificationResult' object has no attribute 'type'`

**修復**: 正確屬性名稱為 `task_classification.task_type`

**修復位置**: `api/routers/chat.py`

```python
# 錯誤
task_classification.type.value

# 正確
task_classification.task_type.value
```

---

## 📋 完整模型列表（含 Active 狀態）

以下列表包含所有可用的模型，並標記 Active 狀態：

- ✅ **Active**: 模型可用（雲端模型已配置 API Key，或本地 Ollama 模型）**會在前端顯示**
- ⚠️ **Inactive**: 模型不可用（雲端模型未配置 API Key）**不會在前端顯示**
- 🟢 **Local**: 本地模型（Ollama，無需 API Key）**會在前端顯示**

**重要**：前端模型選擇列表只顯示 Active 狀態的模型。未配置 API Key 的雲端模型不會出現在前端列表中。

### 所有模型列表

| Model ID | Name | Provider | Status | Active | Context Window | Notes |
|----------|------|----------|--------|--------|----------------|-------|
| `auto` | Auto | auto | Active | ✅ | - | 自動選擇最佳模型 |
| `smartq-iee` | SmartQ IEE | smartq | Active | ⚠️ | - | 需要配置 API Key |
| `smartq-hci` | SmartQ HCI | smartq | Active | ⚠️ | - | 需要配置 API Key |
| `gpt-4o` | GPT-4o | chatgpt | Active | ⚠️ | 128K | 需要配置 API Key (OpenAI) |
| `gpt-4-turbo` | GPT-4 Turbo | chatgpt | Active | ⚠️ | 128K | 需要配置 API Key (OpenAI) |
| `gpt-4` | GPT-4 | chatgpt | Active | ⚠️ | 8K | 需要配置 API Key (OpenAI) |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | chatgpt | Active | ⚠️ | 16K | 需要配置 API Key (OpenAI) |
| `gemini-2.0-flash-exp` | Gemini 2.0 Flash (Experimental) | gemini | Beta | ⚠️ | 1M | 需要配置 API Key (Google) |
| `gemini-1.5-pro` | Gemini 1.5 Pro | gemini | Active | ⚠️ | 2M | 需要配置 API Key (Google) |
| `gemini-pro` | Gemini Pro | gemini | Active | ⚠️ | 32K | 需要配置 API Key (Google) |
| `gemini-ultra` | Gemini Ultra | gemini | Active | ⚠️ | 2M | 需要配置 API Key (Google) |
| `claude-3.5-sonnet` | Claude 3.5 Sonnet | anthropic | Active | ⚠️ | 200K | 需要配置 API Key (Anthropic) |
| `claude-3-opus` | Claude 3 Opus | anthropic | Active | ⚠️ | 200K | 需要配置 API Key (Anthropic) |
| `claude-3-sonnet` | Claude 3 Sonnet | anthropic | Active | ⚠️ | 200K | 需要配置 API Key (Anthropic) |
| `claude-3-haiku` | Claude 3 Haiku | anthropic | Active | ⚠️ | 200K | 需要配置 API Key (Anthropic) |
| `qwen-2.5-72b-instruct` | Qwen 2.5 72B Instruct | qwen | Active | ⚠️ | 32K | 需要配置 API Key (Alibaba) |
| `qwen-plus` | Qwen Plus | qwen | Active | ⚠️ | 32K | 需要配置 API Key (Alibaba) |
| `qwen-turbo` | Qwen Turbo | qwen | Active | ⚠️ | 8K | 需要配置 API Key (Alibaba) |
| `grok-2` | Grok-2 | grok | Active | ⚠️ | 131K | 需要配置 API Key (xAI) |
| `grok-beta` | Grok Beta | grok | Beta | ⚠️ | 131K | 需要配置 API Key (xAI) |
| `mistral-large` | Mistral Large | mistral | Active | ⚠️ | 128K | 需要配置 API Key (Mistral AI) |
| `mistral-medium` | Mistral Medium | mistral | Active | ⚠️ | 32K | 需要配置 API Key (Mistral AI) |
| `mistral-small` | Mistral Small | mistral | Active | ⚠️ | 32K | 需要配置 API Key (Mistral AI) |
| `deepseek-chat` | DeepSeek Chat | deepseek | Active | ⚠️ | 64K | 需要配置 API Key (DeepSeek) |
| `deepseek-coder` | DeepSeek Coder | deepseek | Active | ⚠️ | 16K | 需要配置 API Key (DeepSeek) |
| `dbrx` | DBRX | databricks | Active | ⚠️ | 32K | 需要配置 API Key (Databricks) |
| `glm-4` | GLM-4 | chatglm | Active | ⚠️ | 128K | 需要配置 API Key (智譜 AI) |
| `glm-4v` | GLM-4V | chatglm | Active | ⚠️ | 128K | 需要配置 API Key (智譜 AI) |
| `glm-3-turbo` | GLM-3 Turbo | chatglm | Active | ⚠️ | 32K | 需要配置 API Key (智譜 AI) |
| `doubao-pro-4k` | 豆包 Pro 4K | volcano | Active | ⚠️ | 4K | 需要配置 API Key (火山引擎) |
| `doubao-pro-32k` | 豆包 Pro 32K | volcano | Active | ⚠️ | 32K | 需要配置 API Key (火山引擎) |
| `doubao-lite-4k` | 豆包 Lite 4K | volcano | Active | ⚠️ | 4K | 需要配置 API Key (火山引擎) |
| `ollama:localhost:11434:*` | [動態發現] | ollama | Active | 🟢 | - | 本地模型（需 Ollama 服務運行） |
| `ollama:ai.sunlyc.com:443:*` | [動態發現] | ollama | Active | 🟢 | - | 遠端模型（ai.sunlyc.com） |

**說明**:

- ✅ **Active**: 模型已配置且可用，**會在前端模型選擇列表中顯示**
- ⚠️ **Inactive**: 需要配置 Provider API Key 後才能使用，**不會在前端模型選擇列表中顯示**
- 🟢 **Local**: 本地 Ollama 模型，無需 API Key（但需要 Ollama 服務運行），**會在前端模型選擇列表中顯示**

**備註**:

- 所有雲端模型的 Active 狀態取決於是否已配置對應 Provider 的 API Key
- Ollama 模型的 Active 狀態取決於 Ollama 服務是否運行以及模型是否已下載
- 實際的 Active 狀態會根據系統配置動態變化
- **前端只顯示 Active 狀態的模型**，未激活的模型不會出現在模型選擇列表中

---

## 📊 模型列表

### Auto（自動選擇）

| Model ID | Name | Provider | Status | Description |
|----------|------|----------|--------|-------------|
| `auto` | Auto | auto | Active | 自動選擇最佳模型 |

---

### SmartQ（自定義）

| Model ID | Name | Provider | Status | Description | Capabilities |
|----------|------|----------|--------|-------------|--------------|
| `smartq-iee` | SmartQ IEE | smartq | Active | SmartQ IEE 專用模型 | Chat, Completion |
| `smartq-hci` | SmartQ HCI | smartq | Active | SmartQ HCI 專用模型 | Chat, Completion |

---

### OpenAI (ChatGPT)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `gpt-4o` | GPT-4o | chatgpt | Active | 128K | ~1.8T | Chat, Completion, Code, Multimodal, Vision, Function Calling, Streaming |
| `gpt-4-turbo` | GPT-4 Turbo | chatgpt | Active | 128K | ~1.8T | Chat, Completion, Code, Vision, Function Calling, Streaming |
| `gpt-4` | GPT-4 | chatgpt | Active | 8K | ~1.8T | Chat, Completion, Code, Vision, Function Calling |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | chatgpt | Active | 16K | ~175B | Chat, Completion, Function Calling, Streaming |

**默認模型**: `gpt-4o`

---

### Google (Gemini)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `gemini-2.0-flash-exp` | Gemini 2.0 Flash (Experimental) | gemini | Beta | 1M | - | Chat, Completion, Multimodal, Vision, Function Calling, Streaming |
| `gemini-1.5-pro` | Gemini 1.5 Pro | gemini | Active | 2M | ~540B | Chat, Completion, Multimodal, Vision, Function Calling, Streaming |
| `gemini-pro` | Gemini Pro | gemini | Active | 32K | ~540B | Chat, Completion, Vision, Function Calling |
| `gemini-ultra` | Gemini Ultra | gemini | Active | 2M | ~1.5T | Chat, Completion, Multimodal, Vision, Reasoning, Function Calling |

**默認模型**: `gemini-1.5-pro`

---

### Anthropic (Claude)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `claude-3.5-sonnet` | Claude 3.5 Sonnet | anthropic | Active | 200K | ~250B | Chat, Completion, Code, Vision, Reasoning, Function Calling, Streaming |
| `claude-3-opus` | Claude 3 Opus | anthropic | Active | 200K | ~400B | Chat, Completion, Code, Vision, Reasoning, Function Calling |
| `claude-3-sonnet` | Claude 3 Sonnet | anthropic | Active | 200K | ~250B | Chat, Completion, Code, Vision, Function Calling |
| `claude-3-haiku` | Claude 3 Haiku | anthropic | Active | 200K | ~80B | Chat, Completion, Vision, Function Calling, Streaming |

**默認模型**: `claude-3.5-sonnet`

---

### 阿里巴巴 (Qwen)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `qwen-2.5-72b-instruct` | Qwen 2.5 72B Instruct | qwen | Active | 32K | 72B | Chat, Completion, Code, Function Calling, Streaming |
| `qwen-plus` | Qwen Plus | qwen | Active | 32K | - | Chat, Completion, Code, Streaming |
| `qwen-turbo` | Qwen Turbo | qwen | Active | 8K | - | Chat, Completion, Streaming |

**默認模型**: `qwen-plus`

---

### xAI (Grok)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `grok-2` | Grok-2 | grok | Active | 131K | ~314B | Chat, Completion, Reasoning, Streaming |
| `grok-beta` | Grok Beta | grok | Beta | 131K | ~314B | Chat, Completion, Streaming |

**默認模型**: `grok-2`

---

### Mistral AI

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `mistral-large` | Mistral Large | mistral | Active | 128K | ~123B | Chat, Completion, Code, Function Calling, Streaming |
| `mistral-medium` | Mistral Medium | mistral | Active | 32K | ~50B | Chat, Completion, Code, Streaming |
| `mistral-small` | Mistral Small | mistral | Active | 32K | ~24B | Chat, Completion, Streaming |

---

### DeepSeek

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `deepseek-chat` | DeepSeek Chat | deepseek | Active | 64K | ~67B | Chat, Completion, Code, Streaming |
| `deepseek-coder` | DeepSeek Coder | deepseek | Active | 16K | ~33B | Chat, Code, Completion |

---

### Databricks (DBRX)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `dbrx` | DBRX | databricks | Active | 32K | 132B | Chat, Completion, Code, Streaming |

---

### 智譜 AI (ChatGLM)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `glm-4` | GLM-4 | chatglm | Active | 128K | - | Chat, Completion, Code, Function Calling, Streaming |
| `glm-4v` | GLM-4V | chatglm | Active | 128K | - | Chat, Completion, Multimodal, Vision, Streaming |
| `glm-3-turbo` | GLM-3 Turbo | chatglm | Active | 32K | - | Chat, Completion, Streaming |

**默認模型**: `glm-4`

---

### 字節跳動火山引擎 (Volcano Engine / Doubao)

| Model ID | Name | Provider | Status | Context Window | Parameters | Capabilities |
|----------|------|----------|--------|----------------|------------|--------------|
| `doubao-pro-4k` | 豆包 Pro 4K | volcano | Active | 4K | - | Chat, Completion, Code, Function Calling, Streaming |
| `doubao-pro-32k` | 豆包 Pro 32K | volcano | Active | 32K | - | Chat, Completion, Code, Function Calling, Streaming |
| `doubao-lite-4k` | 豆包 Lite 4K | volcano | Active | 4K | - | Chat, Completion, Streaming |

**默認模型**: `doubao-pro-4k`

---

## 🔍 Ollama 模型（動態發現）

Ollama 模型會根據配置的服務器節點自動發現。模型 ID 格式為：`ollama:{host}:{port}:{model_name}`

### 配置的 Ollama 節點

系統會查詢以下 Ollama 服務器節點（根據配置）：

- **本地節點**: `localhost:11434` (默認)
- **遠程節點**: `ai.sunlyc.com:443` (HTTPS)
  - API 端點: `https://ai.sunlyc.com/v1/models` (OpenAI 兼容格式)
  - 或 `https://ai.sunlyc.com/api/tags` (Ollama 原生格式)

### 能力自動識別

系統會根據模型名稱自動識別能力：

- **Vision**: 模型名稱包含 `vl` 或 `vision`
- **Embedding**: 模型名稱包含 `embed`
- **Code**: 模型名稱包含 `code` 或 `coder`

### 遠端 Ollama 服務器模型列表 (ai.sunlyc.com)

根據 [ai.sunlyc.com/v1/models](https://ai.sunlyc.com/v1/models) 的實際查詢，遠端服務器上可用的模型：

| Model ID (示例) | Model Name | Provider | Source | Size | Description |
|-----------------|------------|----------|--------|------|-------------|
| `ollama:ai.sunlyc.com:443:llama3_gx10_locality_lora:latest` | llama3_gx10_locality_lora:latest | ollama | ollama_discovered | - | 自定義 LoRA 模型 |
| `ollama:ai.sunlyc.com:443:gx10_qlora2-llama3:latest` | gx10_qlora2-llama3:latest | ollama | ollama_discovered | - | QLoRA 2 微調模型 |
| `ollama:ai.sunlyc.com:443:gx10_split_qlora-llama3:latest` | gx10_split_qlora-llama3:latest | ollama | ollama_discovered | - | Split QLoRA 模型 |
| `ollama:ai.sunlyc.com:443:gx10_full_ft-llama3:latest` | gx10_full_ft-llama3:latest | ollama | ollama_discovered | - | 全量微調模型 |
| `ollama:ai.sunlyc.com:443:gx10_lora-llama3:latest` | gx10_lora-llama3:latest | ollama | ollama_discovered | - | LoRA 微調模型 |
| `ollama:ai.sunlyc.com:443:gx10_qlora-llama3:latest` | gx10_qlora-llama3:latest | ollama | ollama_discovered | - | QLoRA 微調模型 |
| `ollama:ai.sunlyc.com:443:gx10_full-llama3:latest` | gx10_full-llama3:latest | ollama | ollama_discovered | - | 全量訓練模型 |
| `ollama:ai.sunlyc.com:443:gx10_3-llama3:latest` | gx10_3-llama3:latest | ollama | ollama_discovered | - | 自定義模型 v3 |
| `ollama:ai.sunlyc.com:443:llama3:8b` | llama3:8b | ollama | ollama_discovered | 4.7 GB | Llama 3 8B 基礎模型 |
| `ollama:ai.sunlyc.com:443:gx10_2-llama3:latest` | gx10_2-llama3:latest | ollama | ollama_discovered | - | 自定義模型 v2 |
| `ollama:ai.sunlyc.com:443:gx10-llama3:latest` | gx10-llama3:latest | ollama | ollama_discovered | - | 自定義模型 |
| `ollama:ai.sunlyc.com:443:deepseek-ocr:latest` | deepseek-ocr:latest | ollama | ollama_discovered | 6.7 GB | DeepSeek OCR 模型 |
| `ollama:ai.sunlyc.com:443:qwen3:32b` | qwen3:32b | ollama | ollama_discovered | 20 GB | Qwen 3 32B 模型 |
| `ollama:ai.sunlyc.com:443:llama3.2-vision:90b` | llama3.2-vision:90b | ollama | ollama_discovered | 54 GB | Llama 3.2 Vision 90B |
| `ollama:ai.sunlyc.com:443:gpt-oss:120b` | gpt-oss:120b | ollama | ollama_discovered | 65 GB | GPT-OSS 120B 模型 |

**總計**: 遠端服務器有 **15 個模型**（根據 2025-12-20 查詢結果）

**注意**:

- 遠端服務器支持 Ollama 原生 API 格式（`/api/tags`）
- 系統同時支持兩種格式（Ollama 原生 `/api/tags` 和 OpenAI 兼容 `/v1/models`），會自動適配
- 所有模型都會在 API 查詢時動態發現並列出
- 模型大小信息來自 `/api/tags` 端點返回的實際數據

### 本地 Ollama 模型（示例）

| Model ID (示例) | Model Name | Provider | Source | Description |
|-----------------|------------|----------|--------|-------------|
| `ollama:localhost:11434:*` | [動態發現] | ollama | ollama_discovered | 本地模型（根據實際下載的模型列表） |

---

## 📝 模型能力說明

### ModelCapability 枚舉值

- **chat**: 對話能力
- **completion**: 文本補全
- **embedding**: 向量嵌入
- **code**: 代碼生成
- **multimodal**: 多模態（圖像、音頻等）
- **reasoning**: 推理能力
- **function_calling**: 函數調用
- **streaming**: 流式輸出
- **vision**: 視覺理解

---

## 🎯 模型狀態說明

### ModelStatus 枚舉值

- **active**: 啟用（正常使用）
- **deprecated**: 已棄用（不建議使用）
- **maintenance**: 維護中（暫時不可用）
- **coming_soon**: 即將推出
- **beta**: 測試版

---

## 🔐 Provider API Key 配置

每個 Provider 可以配置全局 API Key（加密存儲）：

### 支持的 Provider

- OpenAI (chatgpt)
- Anthropic (anthropic)
- Google (gemini)
- 阿里巴巴 (qwen)
- xAI (grok)
- Mistral AI (mistral)
- DeepSeek (deepseek)
- Databricks (databricks)
- Cohere (cohere)
- Perplexity (perplexity)
- 智譜 AI (chatglm)
- 字節跳動火山引擎 (volcano)

### API Key 管理

- **設置**: `POST /api/v1/models/providers/{provider}/api-key`
- **查詢狀態**: `GET /api/v1/models/providers/{provider}/api-key`（不返回實際 key）
- **刪除**: `DELETE /api/v1/models/providers/{provider}/api-key`

**注意**: API Key 使用 AES-256-GCM 加密存儲，永遠不會在 API 響應中返回明文。

---

## 📊 統計信息

### 按 Provider 分類

| Provider | 模型數量 | 默認模型 | Active 要求 |
|----------|---------|---------|-------------|
| Auto | 1 | auto | - |
| SmartQ | 2 | - | 需要 API Key |
| OpenAI | 4 | gpt-4o | 需要 API Key |
| Google | 4 | gemini-1.5-pro | 需要 API Key |
| Anthropic | 4 | claude-3.5-sonnet | 需要 API Key |
| 阿里巴巴 | 3 | qwen-plus | 需要 API Key |
| xAI | 2 | grok-2 | 需要 API Key |
| Mistral AI | 3 | - | 需要 API Key |
| DeepSeek | 2 | - | 需要 API Key |
| Databricks | 1 | - | 需要 API Key |
| 智譜 AI (ChatGLM) | 3 | glm-4 | 需要 API Key |
| 火山引擎 (Volcano) | 3 | doubao-pro-4k | 需要 API Key |
| Ollama | 動態發現（本地+遠端） | - | Ollama 服務運行且模型已拉取（本地 localhost:11434，遠端 ai.sunlyc.com:443） |

**總計**:

- **數據庫模型**: 32 個（預定義模型，包含 ChatGLM 和火山引擎）
- **本地 Ollama 模型**: 動態發現（根據本地 Ollama 服務實際下載的模型）
- **遠端 Ollama 模型**: 15 個（ai.sunlyc.com，見上方詳細列表）
- **總模型數**: 數據庫模型 + 本地 Ollama 模型 + 遠端 Ollama 模型（動態統計）

### Active 狀態說明

**雲端模型（需要 API Key）**:

- OpenAI (chatgpt): 需要配置 `chatgpt` Provider API Key
- Google (gemini): 需要配置 `gemini` Provider API Key
- Anthropic (anthropic): 需要配置 `anthropic` Provider API Key
- 阿里巴巴 (qwen): 需要配置 `qwen` Provider API Key
- xAI (grok): 需要配置 `grok` Provider API Key
- Mistral AI (mistral): 需要配置 `mistral` Provider API Key
- DeepSeek (deepseek): 需要配置 `deepseek` Provider API Key
- Databricks (databricks): 需要配置 `databricks` Provider API Key
- SmartQ (smartq): 需要配置 `smartq` Provider API Key
- 智譜 AI (chatglm): 需要配置 `chatglm` Provider API Key
- 火山引擎 (volcano): 需要配置 `volcano` Provider API Key

**重要**：未配置 API Key 的 Provider 的所有模型**不會在前端模型選擇列表中顯示**。

**本地模型（無需 API Key）**:

- Ollama 模型: 只需要 Ollama 服務運行，無需 API Key
  - 模型格式: `ollama:{host}:{port}:{model_name}`
  - 示例: `ollama:localhost:11434:llama3.1:8b`
  - 系統會自動發現所有配置節點上的可用模型
  - **會在前端模型選擇列表中顯示**（如果 Ollama 服務運行且模型已下載）

**檢查 Active 狀態**:

- 通過 `GET /api/v1/models/providers/{provider}/api-key` 查詢 Provider 是否已配置 API Key
- 對於 Ollama 模型，Active 狀態取決於模型是否已被下載到對應的 Ollama 服務器
- **前端模型選擇列表只顯示 Active 狀態的模型**

---

## 🔄 更新記錄

### 2026-01-22

- ✅ **Auto 模式文檔**：添加 Auto 模式模型選擇邏輯說明
- ✅ **錯誤處理文檔**：添加用戶友好錯誤消息機制（包含 Emoji）
- ✅ **Fallback 模型**：更新默認 Fallback 模型為 `qwen3-next:latest`
- ✅ **Bug 修復**：記錄 `task_classification.type` → `task_classification.task_type` 修復
- ✅ **前端優化**：移除 "Chat failed:" 前綴

### 2026-01-24

- ✅ **新增完整版模型列表文檔**：創建 [LLM Provider 模型列表（完整版）](./LLM-Provider-模型列表-完整版.md)，包含所有 Provider 的詳細模型信息和更新指南
- ✅ 添加文檔鏈接：在相關文檔中添加指向完整版模型列表的鏈接

### 2026-01-27

- ✅ **重要更新**：前端模型選擇列表現在只顯示已激活的模型
- ✅ 修復後端 API：`/api/v1/models` 和 `/api/v1/chat/models` 端點現在會過濾掉未激活的模型
- ✅ 添加模型激活邏輯說明：詳細說明哪些模型會在前端顯示
- ✅ 更新文檔：明確說明 Active 狀態與前端顯示的關係

### 2025-12-30

- ✅ 添加智譜 AI (ChatGLM) 模型：GLM-4, GLM-4V, GLM-3 Turbo
- ✅ 添加字節跳動火山引擎 (Volcano Engine) 模型：豆包 Pro 4K, 豆包 Pro 32K, 豆包 Lite 4K
- ✅ 更新 Provider 列表和統計信息

### 2025-12-20

- ✅ 初始版本創建
- ✅ 包含所有主要 Provider 的模型
- ✅ 支持 Ollama 動態模型發現
- ✅ 支持 Provider API Key 加密存儲

---

## 📚 相關文檔

- [LLM Provider 模型列表（完整版）](./LLM-Provider-模型列表-完整版.md) - **📖 完整模型列表，包含所有 Provider 的詳細模型信息，用於定期更新**
- [LLM模型遷移到ArangoDB遷移計劃](./migrations/LLM模型遷移到ArangoDB遷移計劃.md)
- [API 文檔](../api/routers/llm_models.py)
- [MoE 系統文檔](./MoE系统.md)

---

**文檔版本**: 1.3
**最後更新**: 2026-01-24
**維護者**: Daniel Chung
