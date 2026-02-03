# LLM Provider 模型列表（完整版）

**版本**: 1.0
**創建日期**: 2026-01-24
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-24 22:41 UTC+8

---

## 📋 概述

本文檔提供所有 LLM Provider 的完整模型列表，用於：
- 系統初始化時批量導入模型
- 定期更新模型列表（新增、更新、標記已棄用）
- 參考各 Provider 的官方模型文檔

**更新頻率建議**：每月檢查一次，或當 Provider 發布新模型時立即更新。

---

## 🔄 更新指南

### 如何更新模型列表

1. **檢查 Provider 官方文檔**：
   - OpenAI: https://platform.openai.com/docs/models
   - Google Gemini: https://ai.google.dev/models/gemini
   - Anthropic Claude: https://docs.anthropic.com/claude/docs/models-overview
   - 其他 Provider 的官方文檔

2. **更新遷移腳本**：
   - 編輯 `services/api/services/migrations/migrate_llm_models.py`
   - 在 `LLM_MODELS_DATA` 列表中添加或更新模型數據

3. **運行遷移腳本**：
   ```bash
   python -m services.api.services.migrations.migrate_llm_models
   ```

4. **更新本文檔**：
   - 更新對應 Provider 的模型列表
   - 更新「最後修改日期」
   - 在「更新記錄」中添加更新說明

---

## 🤖 Provider 模型列表

### 1. Auto（自動選擇）

| Model ID | Name | Provider | Status | Description |
|----------|------|----------|--------|-------------|
| `auto` | Auto | auto | Active | 自動選擇最佳模型 |

**能力**: Chat

**備註**: 特殊模型，用於自動路由到最佳模型。

---

### 2. OpenAI (ChatGPT)

**官方文檔**: https://platform.openai.com/docs/models

**Base URL**: `https://api.openai.com/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `gpt-4o` | GPT-4o | Active | 128K | ~1.8T | Chat, Completion, Code, Multimodal, Vision, Function Calling, Streaming | 2024-05-13 | ✅ 默認模型 |
| `gpt-4-turbo` | GPT-4 Turbo | Active | 128K | ~1.8T | Chat, Completion, Code, Vision, Function Calling, Streaming | 2023-11-06 | - |
| `gpt-4` | GPT-4 | Active | 8K | ~1.8T | Chat, Completion, Code, Vision, Function Calling | 2023-03-14 | - |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | Active | 16K | ~175B | Chat, Completion, Function Calling, Streaming | 2022-11-30 | - |
| `gpt-4o-mini` | GPT-4o Mini | Active | 128K | - | Chat, Completion, Code, Vision, Function Calling, Streaming | 2024-09-12 | 輕量版本 |
| `o1-preview` | O1 Preview | Beta | 200K | - | Chat, Completion, Reasoning | 2024-09-12 | 推理模型 |
| `o1-mini` | O1 Mini | Beta | 128K | - | Chat, Completion, Reasoning | 2024-09-12 | 輕量推理模型 |

**已棄用模型**（不建議使用）:
- `gpt-3.5-turbo-0301` (已棄用)
- `gpt-4-0314` (已棄用)
- `gpt-4-32k` (已棄用)

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 3. Google (Gemini)

**官方文檔**: https://ai.google.dev/models/gemini

**Base URL**: `https://generativelanguage.googleapis.com/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `gemini-3-pro-preview` | Gemini 3 Pro (Preview) | Active | 2M | ~540B | Chat, Completion, Multimodal, Vision, Function Calling, Streaming | 2024-12-11 | ✅ 默認模型 |
| `gemini-2.0-flash-exp` | Gemini 2.0 Flash (Experimental) | Beta | 1M | - | Chat, Completion, Multimodal, Vision, Function Calling, Streaming | 2024-12-11 | 實驗版本 |
| `gemini-1.5-pro` | Gemini 1.5 Pro | Active | 2M | ~540B | Chat, Completion, Multimodal, Vision, Function Calling, Streaming | 2024-02-15 | - |
| `gemini-1.5-flash` | Gemini 1.5 Flash | Active | 1M | ~8B | Chat, Completion, Multimodal, Vision, Function Calling, Streaming | 2024-05-14 | 快速版本 |
| `gemini-pro` | Gemini Pro | Active | 32K | ~540B | Chat, Completion, Vision, Function Calling | 2023-12-06 | - |
| `gemini-ultra` | Gemini Ultra | Active | 2M | ~1.5T | Chat, Completion, Multimodal, Vision, Reasoning, Function Calling | 2024-02-15 | - |

**更新記錄**:
- 2026-01-24: 初始列表創建，添加 Gemini 3 Pro Preview

---

### 4. Anthropic (Claude)

**官方文檔**: https://docs.anthropic.com/claude/docs/models-overview

**Base URL**: `https://api.anthropic.com/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `claude-3.5-sonnet` | Claude 3.5 Sonnet | Active | 200K | ~250B | Chat, Completion, Code, Vision, Reasoning, Function Calling, Streaming | 2024-06-20 | ✅ 默認模型 |
| `claude-3-opus` | Claude 3 Opus | Active | 200K | ~400B | Chat, Completion, Code, Vision, Reasoning, Function Calling | 2024-03-04 | - |
| `claude-3-sonnet` | Claude 3 Sonnet | Active | 200K | ~250B | Chat, Completion, Code, Vision, Function Calling | 2024-03-04 | - |
| `claude-3-haiku` | Claude 3 Haiku | Active | 200K | ~80B | Chat, Completion, Vision, Function Calling, Streaming | 2024-03-04 | 快速版本 |
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet (2024-10-22) | Active | 200K | ~250B | Chat, Completion, Code, Vision, Reasoning, Function Calling, Streaming | 2024-10-22 | 特定版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 5. 阿里巴巴 (Qwen)

**官方文檔**: https://help.aliyun.com/zh/model-studio/

**Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `qwen-plus` | Qwen Plus | Active | 32K | - | Chat, Completion, Code, Streaming | - | ✅ 默認模型 |
| `qwen-turbo` | Qwen Turbo | Active | 8K | - | Chat, Completion, Streaming | - | 快速版本 |
| `qwen-2.5-72b-instruct` | Qwen 2.5 72B Instruct | Active | 32K | 72B | Chat, Completion, Code, Function Calling, Streaming | - | - |
| `qwen-max` | Qwen Max | Active | 8K | - | Chat, Completion, Code, Streaming | - | 旗艦版本 |
| `qwen-max-longcontext` | Qwen Max LongContext | Active | 200K | - | Chat, Completion, Code, Streaming | - | 長上下文版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 6. xAI (Grok)

**官方文檔**: https://docs.x.ai/

**Base URL**: `https://api.x.ai/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `grok-2` | Grok-2 | Active | 131K | ~314B | Chat, Completion, Reasoning, Streaming | 2024-11-11 | ✅ 默認模型 |
| `grok-beta` | Grok Beta | Beta | 131K | ~314B | Chat, Completion, Streaming | 2024-03-28 | - |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 7. Mistral AI

**官方文檔**: https://docs.mistral.ai/

**Base URL**: `https://api.mistral.ai/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `mistral-large` | Mistral Large | Active | 128K | ~123B | Chat, Completion, Code, Function Calling, Streaming | 2024-02-26 | - |
| `mistral-medium` | Mistral Medium | Active | 32K | ~50B | Chat, Completion, Code, Streaming | 2024-01-23 | - |
| `mistral-small` | Mistral Small | Active | 32K | ~24B | Chat, Completion, Streaming | 2023-09-27 | - |
| `mistral-tiny` | Mistral Tiny | Active | 32K | ~7B | Chat, Completion, Streaming | 2023-09-27 | 輕量版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 8. DeepSeek

**官方文檔**: https://platform.deepseek.com/docs

**Base URL**: `https://api.deepseek.com/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `deepseek-chat` | DeepSeek Chat | Active | 64K | ~67B | Chat, Completion, Code, Streaming | 2024-01-29 | - |
| `deepseek-coder` | DeepSeek Coder | Active | 16K | ~33B | Chat, Code, Completion | 2024-01-29 | 代碼專用 |
| `deepseek-chat-v3` | DeepSeek Chat V3 | Active | 64K | ~67B | Chat, Completion, Code, Streaming | 2024-12-10 | 最新版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 9. Databricks (DBRX)

**官方文檔**: https://docs.databricks.com/en/machine-learning/foundation-models/index.html

**Base URL**: `https://workspace.cloud.databricks.com/serving-endpoints`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `dbrx` | DBRX | Active | 32K | 132B | Chat, Completion, Code, Streaming | 2024-03-27 | - |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 10. Cohere

**官方文檔**: https://docs.cohere.com/docs/models

**Base URL**: `https://api.cohere.ai/v1`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `command-r-plus` | Command R+ | Active | 128K | ~104B | Chat, Completion, Function Calling, Streaming | 2024-03-11 | - |
| `command-r` | Command R | Active | 128K | ~35B | Chat, Completion, Function Calling, Streaming | 2024-03-11 | - |
| `command` | Command | Active | 4K | ~6B | Chat, Completion, Streaming | 2023-10-26 | - |

**更新記錄**:
- 2026-01-24: 初始列表創建（待補充更多模型）

---

### 11. Perplexity

**官方文檔**: https://docs.perplexity.ai/

**Base URL**: `https://api.perplexity.ai`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `llama-3.1-sonar-large-128k-online` | Llama 3.1 Sonar Large 128K Online | Active | 128K | - | Chat, Completion, Streaming | - | 在線搜索版本 |
| `llama-3.1-sonar-small-128k-online` | Llama 3.1 Sonar Small 128K Online | Active | 128K | - | Chat, Completion, Streaming | - | 在線搜索版本（小） |

**更新記錄**:
- 2026-01-24: 初始列表創建（待補充更多模型）

---

### 12. 智譜 AI (ChatGLM)

**官方文檔**: https://open.bigmodel.cn/

**Base URL**: `https://open.bigmodel.cn/api/paas/v4`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `glm-4` | GLM-4 | Active | 128K | - | Chat, Completion, Code, Function Calling, Streaming | 2024-01-16 | ✅ 默認模型 |
| `glm-4v` | GLM-4V | Active | 128K | - | Chat, Completion, Multimodal, Vision, Streaming | 2024-01-16 | 視覺版本 |
| `glm-3-turbo` | GLM-3 Turbo | Active | 32K | - | Chat, Completion, Streaming | 2023-11-06 | 快速版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 13. 字節跳動火山引擎 (Volcano Engine / Doubao)

**官方文檔**: https://www.volcengine.com/docs/82379

**Base URL**: `https://ark.cn-beijing.volces.com/api/v3`

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `doubao-pro-4k` | 豆包 Pro 4K | Active | 4K | - | Chat, Completion, Code, Function Calling, Streaming | - | ✅ 默認模型 |
| `doubao-pro-32k` | 豆包 Pro 32K | Active | 32K | - | Chat, Completion, Code, Function Calling, Streaming | - | - |
| `doubao-lite-4k` | 豆包 Lite 4K | Active | 4K | - | Chat, Completion, Streaming | - | 輕量版本 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 14. Ollama (本地部署)

**官方文檔**: https://ollama.ai/library

**Base URL**: 動態配置（本地或遠程 Ollama 服務器）

**模型格式**: `ollama:{host}:{port}:{model_name}`

**常見模型**:
- `gpt-oss:120b-cloud` - GPT-OSS 120B 雲端託管版本
- `gpt-oss:20b` - GPT-OSS 20B 本地版本
- `qwen3-next:latest` - Qwen 3 Next（Fallback 模型）
- `llama3.1:8b` - Llama 3.1 8B
- `llama3.2-vision:90b` - Llama 3.2 Vision 90B

**備註**: Ollama 模型通過動態發現機制自動檢測，無需手動添加到數據庫。

**更新記錄**:
- 2026-01-24: 初始列表創建

---

### 15. SmartQ (自定義)

**Base URL**: 自定義配置

| Model ID | Name | Status | Context Window | Parameters | Capabilities | Release Date | Notes |
|----------|------|--------|----------------|------------|--------------|--------------|-------|
| `smartq-iee` | SmartQ IEE | Active | - | - | Chat, Completion | - | IEE 專用模型 |
| `smartq-hci` | SmartQ HCI | Active | - | - | Chat, Completion | - | HCI 專用模型 |

**更新記錄**:
- 2026-01-24: 初始列表創建

---

## 📊 統計信息

### 按 Provider 分類統計

| Provider | 模型數量 | 默認模型 | 需要 API Key |
|----------|---------|---------|-------------|
| Auto | 1 | auto | ❌ |
| OpenAI | 7 | gpt-4o | ✅ |
| Google | 6 | gemini-3-pro-preview | ✅ |
| Anthropic | 5 | claude-3.5-sonnet | ✅ |
| 阿里巴巴 | 5 | qwen-plus | ✅ |
| xAI | 2 | grok-2 | ✅ |
| Mistral AI | 4 | - | ✅ |
| DeepSeek | 3 | - | ✅ |
| Databricks | 1 | - | ✅ |
| Cohere | 3 | - | ✅ |
| Perplexity | 2 | - | ✅ |
| 智譜 AI | 3 | glm-4 | ✅ |
| 火山引擎 | 3 | doubao-pro-4k | ✅ |
| Ollama | 動態發現 | - | ❌ |
| SmartQ | 2 | - | ✅ |

**總計**: 約 47 個預定義模型（不含 Ollama 動態發現模型）

---

## 🔄 更新記錄

### 2026-01-24
- ✅ 創建初始完整版模型列表文檔
- ✅ 添加所有主要 Provider 的模型
- ✅ 包含模型詳細信息（Context Window、Parameters、Capabilities 等）
- ✅ 添加更新指南和統計信息

---

## 📚 相關文檔

- [LLM 模型列表](./LLM模型列表.md) - 系統使用的模型列表（含 Active 狀態）
- [LLM 模型遷移計劃](../開發過程文件/migrations/LLM模型遷移到ArangoDB遷移計劃.md) - 遷移腳本和計劃
- [遷移腳本](../../services/api/services/migrations/migrate_llm_models.py) - 實際的遷移腳本

---

**文檔版本**: 1.0
**最後更新**: 2026-01-24 22:41 UTC+8
**維護者**: Daniel Chung
