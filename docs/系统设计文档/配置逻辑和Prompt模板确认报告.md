# 配置逻辑和 Prompt 模板确认报告

**分析日期**: 2026-01-04  
**目的**: 确认 AI-Box 上传文件代码的配置优先级逻辑和 Prompt 模板

---

## 🔍 当前配置优先级逻辑（有问题）

### 代码位置

- `genai/api/services/ner_service.py` (第 437-510 行)
- `genai/api/services/re_service.py` (第 454-530 行)
- `genai/api/services/rt_service.py` (第 505-585 行)

### 当前逻辑（错误）

**model_type 优先级**：
1. **優先級1**: 從 ArangoDB system_configs 讀取 ✅
2. **優先級2**: 從環境變量讀取（**允許覆蓋 ArangoDB 配置**）❌ **问题！**
3. **優先級3**: 從 config.json 讀取（向後兼容）

**model_name 优先级**：
1. **優先級1**: 從 ArangoDB system_configs 讀取 ✅
2. **優先級2**: 從環境變量讀取（**如果环境变量存在就覆盖**）❌ **问题！**
3. **優先級3**: 從 config.json 讀取（向後兼容）
4. **優先級4**: 使用硬編碼默認值

### 问题代码示例

```python
# ner_service.py 第 467-498 行
# 優先級2: 從環境變量讀取 model_type（允許覆蓋 ArangoDB 配置）
env_model_type = os.getenv("NER_MODEL_TYPE")
if env_model_type:
    model_type = env_model_type  # ❌ 无条件覆盖

# 優先級2: 從環境變量讀取（只在 model_type 匹配時覆蓋）
if self.model_type == "ollama":
    env_model_name = os.getenv("OLLAMA_NER_MODEL")
    if env_model_name:
        model_name = env_model_name  # ❌ 如果环境变量存在就覆盖
```

**问题**：
- 环境变量会**无条件覆盖** ArangoDB 配置
- 用户期望：**优先使用 ArangoDB，只有 ArangoDB 无效时才 fallback 到 .env**

---

## ✅ 正确的逻辑应该是

### 用户期望的优先级顺序

1. **優先級1**: 從 ArangoDB system_configs 讀取
   - 如果 ArangoDB 配置存在且有效（model_type 和 model_name 都存在）
   - **直接使用 ArangoDB 配置，不再检查环境变量**

2. **優先級2**: 從環境變量讀取（fallback）
   - 只有在 ArangoDB 配置不存在或无效时，才使用环境变量

3. **優先級3**: 從 config.json 讀取（向後兼容）

4. **優先級4**: 使用硬編碼默認值

### 正确的代码逻辑应该是

```python
# 優先級1: 從 ArangoDB system_configs 讀取
model_type = None
model_name = None
try:
    config_service = ConfigStoreService()
    kg_config = config_service.get_config("kg_extraction", tenant_id=None)
    if kg_config and kg_config.config_data:
        model_type = kg_config.config_data.get("ner_model_type")
        model_name = kg_config.config_data.get("ner_model")
        if model_type and model_name:
            # ✅ ArangoDB 配置有效，直接使用，不再检查环境变量
            self.model_type = model_type
            self.model_name = model_name
            # 继续到模型初始化步骤
except Exception as e:
    logger.debug("從 ArangoDB 讀取配置失敗，使用 fallback 方式")

# 優先級2: 從環境變量讀取（fallback - 只有在 ArangoDB 无效时）
if not model_type or not model_name:
    env_model_type = os.getenv("NER_MODEL_TYPE")
    env_model_name = os.getenv("OLLAMA_NER_MODEL")
    if env_model_type:
        model_type = env_model_type
    if env_model_name:
        model_name = env_model_name

# 優先級3: 從 config.json 讀取（向後兼容）
if not model_type:
    model_type = self.config.get("model_type", "ollama")
if not model_name:
    model_name = self.config.get("model_name")

# 優先級4: 使用硬編碼默認值
self.model_type = model_type or "ollama"
self.model_name = model_name or "mistral-nemo:12b"
```

---

## 📋 Prompt 模板确认

### 1. NER (Named Entity Recognition) Prompt 模板

**位置**: `genai/api/services/ner_service.py` 第 123-164 行

**类**: `OllamaNERModel`

**模板内容**：
```
你是一個專業的命名實體識別（NER）助手。請仔細閱讀以下文本，識別並提取所有命名實體。

重要規則：
1. **必須識別盡可能多的實體**：不要遺漏任何重要的實體，包括人名、組織名、地點、日期、金額、產品、設備、技術等。
2. **僅返回一個 JSON 數組**：不要包含任何解釋、註釋或額外文字。
3. **嚴格遵守 JSON 格式**：確保輸出是有效的 JSON 數組。
4. **處理中文文本**：特別注意識別中文實體，包括公司名稱、產品名稱、技術術語等。
5. **處理亂碼字符**：如果文本中包含特殊字符或亂碼，請忽略這些字符，專注於識別有效的實體。

Few-Shot 示例：
[包含 3 個示例]

待分析的文本內容：
{text}

請返回 JSON 數組格式的實體列表：
```

**模型参数**：
- `temperature`: 0.0
- `max_tokens`: 2048
- `format`: "json"
- `num_ctx`: 32768
- `top_p`: 0.9
- `top_k`: 40

### 2. RE (Relation Extraction) Prompt 模板

**位置**: `genai/api/services/re_service.py` 第 140-167 行

**类**: `OllamaREModel`

**模板内容**：
```
你是一個專業的知識圖譜構建助手。請從以下文本中抽取實體之間的關係。

重要規則：
1. 僅返回一個 JSON 數組。
2. 不要解釋你的答案。
3. 識別 API 文檔中的邏輯關係，例如：
   - API 端點 BELONGS_TO 模塊
   - 參數 PART_OF API
   - 錯誤碼 RETURNED_BY API
   - 實體 HAS_PROPERTY 屬性
4. 忽略純 JSON 示例數據，專注於描述性文本中的關係。
5. 嚴格遵守以下 JSON 格式。

文本內容：
{text}

{entities_section}

預期的 JSON 格式示例：
[
  {
    "subject": {"text": "GET /api/v1/users", "label": "API_ENDPOINT"},
    "relation": "RETURNED_BY",
    "object": {"text": "404 Not Found", "label": "STATUS_CODE"},
    "confidence": 0.95,
    "context": "如果用戶不存在，接口將返回 404"
  }
]
```

**模型参数**：
- `format`: "json"
- `num_ctx`: 32768

### 3. RT (Relation Type Classification) Prompt 模板

**位置**: `genai/api/services/rt_service.py` 第 94-114 行

**类**: `OllamaRTModel`

**模板内容**：
```
請對以下關係文本進行分類，識別其關係類型，並以 JSON 格式返回結果。

關係文本：{relation_text}
{context_section}

可選的關係類型包括：
{relation_types_list}

請返回 JSON 格式，包含以下字段：
- type: 關係類型名稱
- confidence: 置信度（0-1之間的浮點數）
```

### 4. 图谱提取（三元组提取）Prompt 模板

**位置**: `kag/ontology/Prompt-Template.json`

**模板名称**: `Knowledge_Graph_Extraction_Multi_Layer`

**主要结构**：
1. **功能分層說明**：
   - Extraction Layer (抽取層)
   - Judgment Layer (裁決層)
   - Schema Layer (格式層)

2. **核心實體類型 (Entity Classes)**: `[INJECT_ENTITY_LIST]`

3. **關係類型約束 (Relationship Types)**: `[INJECT_RELATIONSHIP_LIST]`

4. **OWL Domain/Range 規則**

5. **GraphRAG 裁決規則 (Judgment Layer)**：
   - 證據充分性
   - 置信度評估
   - 核心節點識別
   - 保守原則
   - 禁止創造

6. **上下文一致性要求**

7. **輸出格式 (JSON Schema)**: `[INJECT_JSON_SCHEMA]`

8. **待分析文本片段**: `[TEXT_CHUNK]`

**模型参数建议**：
- `temperature`: 0.0
- `top_p`: 0.9
- `top_k`: 40
- `max_tokens`: 512

---

## 🎯 测试计划确认

### 测试目标

比对三个模型的图谱生成性能：
1. **mistral-nemo:12b** (作为基准)
2. **gpt-oss:120b-cloud**
3. **qwen3-next:latest**

### 测试指标

- **时间**：图谱生成时间
- **数量**：NER/RE/RT 数量
- **向量**：统一使用 `nomic-embed-text:latest`（系统默认）

### 测试方法

1. **通过 ArangoDB 配置切换模型**（推荐）
   - 使用 `update_kg_model_direct.py` 脚本更新配置
   - 不需要修改 `.env` 文件
   - 更灵活、可追溯

2. **测试步骤**：
   ```bash
   # 1. 更新为 mistral-nemo:12b（基准）
   python update_kg_model_direct.py mistral-nemo:12b
   # 重启 RQ Worker
   python test_regenerate_kg_gptoss.py <file_id>
   
   # 2. 更新为 gpt-oss:120b-cloud
   python update_kg_model_direct.py gpt-oss:120b-cloud
   # 重启 RQ Worker
   python test_regenerate_kg_gptoss.py <file_id>
   
   # 3. 更新为 qwen3-next:latest
   python update_kg_model_direct.py qwen3-next:latest
   # 重启 RQ Worker
   python test_regenerate_kg_gptoss.py <file_id>
   ```

---

## 📝 总结

### 当前问题

1. ❌ **配置优先级错误**：环境变量会覆盖 ArangoDB 配置
2. ❌ **不符合用户期望**：用户期望 ArangoDB 优先，环境变量作为 fallback

### 正确的逻辑

1. ✅ **ArangoDB 配置优先**
2. ✅ **环境变量作为 fallback**（只有在 ArangoDB 无效时）
3. ✅ **通过 ArangoDB 灵活配置，不需要修改 .env**

### Prompt 模板位置

1. **NER**: `genai/api/services/ner_service.py` - `OllamaNERModel._prompt_template`
2. **RE**: `genai/api/services/re_service.py` - `OllamaREModel._prompt_template`
3. **RT**: `genai/api/services/rt_service.py` - `OllamaRTModel._prompt_template`
4. **图谱提取**: `kag/ontology/Prompt-Template.json` - `Knowledge_Graph_Extraction_Multi_Layer`

### 建议

1. **修复配置优先级逻辑**：让 ArangoDB 配置优先，环境变量作为 fallback
2. **使用 ArangoDB 配置进行测试**：不需要修改 `.env` 文件
3. **创建测试脚本**：方便切换模型进行对比测试

