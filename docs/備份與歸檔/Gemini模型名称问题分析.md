# Gemini 模型名称问题分析

**创建日期**: 2026-01-04
**问题**: `404 models/gemini-pro is not found`

---

## 🔍 问题分析

### 当前状态

1. ✅ **环境变量覆盖问题已修复**
   - 模型配置正确：`Model type: gemini`, `Model name: gemini-pro`
   - 不再使用错误的 `mistral-nemo:12b`

2. ❌ **新的问题：模型名称不可用**

   ```
   Gemini generate error: 404 models/gemini-pro is not found for API version v1beta,
   or is not supported for generateContent.
   ```

### 原因

`gemini-pro` 模型名称已被弃用或不可用。从 Gemini API 查询结果来看，可用的模型包括：

**推荐的模型**：

- `gemini-2.5-flash` - 速度快，适合批量处理
- `gemini-pro-latest` - 最新版本的 Pro 模型
- `gemini-2.5-pro` - 2.5 版本的 Pro 模型

**不可用的模型**：

- `gemini-pro` ❌ (已弃用)

---

## ✅ 解决方案

### 方案 1：使用 gemini-2.5-flash（推荐）

**优点**：

- 速度快，适合批量处理
- 成本较低
- 支持 `generateContent`

**更新配置**：

```python
# 通过 API 或直接更新 ArangoDB
ner_model: gemini-2.5-flash
re_model: gemini-2.5-flash
rt_model: gemini-2.5-flash
```

### 方案 2：使用 gemini-pro-latest

**优点**：

- 最新版本的 Pro 模型
- 性能更好

**更新配置**：

```python
ner_model: gemini-pro-latest
re_model: gemini-pro-latest
rt_model: gemini-pro-latest
```

---

## 🔧 更新步骤

### 方法 1：通过 API 更新（推荐）

使用 `update_kg_model_to_gemini_latest.py` 脚本：

```bash
# 使用 gemini-2.5-flash（推荐）
python update_kg_model_to_gemini_latest.py gemini-2.5-flash

# 或使用 gemini-pro-latest
python update_kg_model_to_gemini_latest.py gemini-pro-latest
```

### 方法 2：直接更新 ArangoDB

```python
from services.api.services.config_store_service import ConfigStoreService
from services.api.models.config import ConfigUpdate

service = ConfigStoreService()
kg_config = service.get_config("kg_extraction", tenant_id=None)

config_data = kg_config.config_data.copy()
config_data["ner_model"] = "gemini-2.5-flash"
config_data["re_model"] = "gemini-2.5-flash"
config_data["rt_model"] = "gemini-2.5-flash"

update = ConfigUpdate(config_data=config_data, is_active=True)
service.update_config("kg_extraction", update, tenant_id=None)
```

### 方法 3：通过 ArangoDB Web UI

1. 访问 ArangoDB Web UI
2. 进入 `system_configs` collection
3. 找到 `_key: kg_extraction` 的文档
4. 更新 `config_data` 字段：

   ```json
   {
     "ner_model": "gemini-2.5-flash",
     "re_model": "gemini-2.5-flash",
     "rt_model": "gemini-2.5-flash"
   }
   ```

---

## 📊 可用模型列表

从 Gemini API 查询到的可用模型（支持 `generateContent`）：

```
- models/gemini-2.5-flash          ✅ 推荐（速度快）
- models/gemini-2.5-pro            ✅ 推荐（性能好）
- models/gemini-pro-latest          ✅ 推荐（最新 Pro）
- models/gemini-2.0-flash
- models/gemini-2.0-flash-001
- models/gemini-flash-latest
- models/gemini-3-pro-preview
- models/gemini-3-flash-preview
```

---

## 🧪 验证步骤

1. **更新配置**（使用上述任一方法）

2. **重启 RQ Worker**：

   ```bash
   ./scripts/start_services.sh restart rq_worker
   ```

3. **运行诊断脚本**：

   ```bash
   python diagnose_kg_extraction.py
   ```

   应该看到：

   ```
   Model type: gemini
   Model name: gemini-2.5-flash  ✅
   ```

4. **重新测试图谱提取**：

   ```bash
   python test_regenerate_kg_gemini.py 149aee1a-89da-4b07-a83c-634fb29246e2
   ```

5. **检查结果**：
   - ✅ 不再出现 `404 models/gemini-pro is not found` 错误
   - ✅ 能够成功提取实体、关系、三元组
   - ✅ `entities_count > 0`, `relations_count > 0`, `triples_count > 0`

---

## 📝 总结

**问题根源**：

- `gemini-pro` 模型名称已被弃用，不再可用

**解决方案**：

- 更新为 `gemini-2.5-flash`（推荐）或 `gemini-pro-latest`

**下一步**：

1. 更新 ArangoDB 配置中的模型名称
2. 重启 RQ Worker
3. 重新测试图谱提取
