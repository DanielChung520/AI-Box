# LLM 模型列表

**版本**: 1.0  
**創建日期**: 2025-12-20  
**創建人**: Daniel Chung  
**最後修改日期**: 2025-12-20

---

## 📋 概述

本文檔列出了系統中所有可用的 LLM 模型。模型分為兩類：

1. **數據庫模型**: 存儲在 ArangoDB 中的預定義模型（全域配置）
2. **動態發現模型**: 從 Ollama 服務器（本地和遠程）自動發現的模型

---

## 🔄 模型來源

### 數據庫模型 (Database Models)

這些模型存儲在 ArangoDB 的 `llm_models` collection 中，由系統管理員維護。

### 動態發現模型 (Discovered Models)

這些模型通過查詢配置的 Ollama 服務器節點自動發現，格式為：`ollama:{host}:{port}:{model_name}`

---

## 📋 完整模型列表（含 Active 狀態）

以下列表包含所有可用的模型，並標記 Active 狀態：

- ✅ **Active**: 模型可用（雲端模型已配置 API Key，或本地 Ollama 模型）
- ⚠️ **Inactive**: 模型不可用（雲端模型未配置 API Key）
- 🟢 **Local**: 本地模型（Ollama，無需 API Key）

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
| `ollama:localhost:11434:*` | [動態發現] | ollama | Active | 🟢 | - | 本地模型（需 Ollama 服務運行） |
| `ollama:ai.sunlyc.com:443:*` | [動態發現] | ollama | Active | 🟢 | - | 遠端模型（ai.sunlyc.com） |

**說明**:
- ✅ **Active**: 模型已配置且可用
- ⚠️ **Inactive**: 需要配置 Provider API Key 後才能使用
- 🟢 **Local**: 本地 Ollama 模型，無需 API Key（但需要 Ollama 服務運行）

**備註**: 
- 所有雲端模型的 Active 狀態取決於是否已配置對應 Provider 的 API Key
- Ollama 模型的 Active 狀態取決於 Ollama 服務是否運行以及模型是否已下載
- 實際的 Active 狀態會根據系統配置動態變化

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
| Ollama | 動態發現（本地+遠端） | - | Ollama 服務運行且模型已拉取（本地 localhost:11434，遠端 ai.sunlyc.com:443） |

**總計**: 
- **數據庫模型**: 26 個（預定義模型）
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

**本地模型（無需 API Key）**:
- Ollama 模型: 只需要 Ollama 服務運行，無需 API Key
  - 模型格式: `ollama:{host}:{port}:{model_name}`
  - 示例: `ollama:localhost:11434:llama3.1:8b`
  - 系統會自動發現所有配置節點上的可用模型

**檢查 Active 狀態**:
- 通過 `GET /api/v1/models/providers/{provider}/api-key` 查詢 Provider 是否已配置 API Key
- 對於 Ollama 模型，Active 狀態取決於模型是否已被下載到對應的 Ollama 服務器

---

## 🔄 更新記錄

### 2025-12-20

- ✅ 初始版本創建
- ✅ 包含所有主要 Provider 的模型
- ✅ 支持 Ollama 動態模型發現
- ✅ 支持 Provider API Key 加密存儲

---

## 📚 相關文檔

- [LLM模型遷移到ArangoDB遷移計劃](./migrations/LLM模型遷移到ArangoDB遷移計劃.md)
- [API 文檔](../api/routers/llm_models.py)

---

**文檔版本**: 1.0  
**最後更新**: 2025-12-20  
**維護者**: Daniel Chung

