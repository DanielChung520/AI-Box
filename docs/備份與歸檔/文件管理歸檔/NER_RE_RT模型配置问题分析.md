# NER/RE/RT模型配置问题分析

**创建日期**: 2026-01-01
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-01

---

## 📋 问题概述

当前NER/RE/RT服务的模型配置**未使用ArangoDB system_configs**，而是直接从环境变量（`.env`文件）和`config.json`读取，**不符合系统参数配置策略**。

---

## 🔍 当前实现分析

### 1. NER Service (`genai/api/services/ner_service.py`)

**当前配置来源**：

```python
# NERService.__init__()
self.config = get_config_section("text_analysis", "ner", default={}) or {}
import os

self.model_name = os.getenv("OLLAMA_NER_MODEL") or self.config.get(
    "model_name", "gpt-oss:20b"
)
```

**优先级**：
1. 环境变量 `OLLAMA_NER_MODEL`（`.env`文件）
2. `config.json` → `text_analysis.ner.model_name`
3. 硬编码默认值 `"gpt-oss:20b"`

**问题**：
- ❌ 未使用ArangoDB `system_configs`
- ❌ 不符合系统参数配置策略

### 2. RE Service (`genai/api/services/re_service.py`)

**当前配置来源**：

```python
# REService.__init__()
self.config = get_config_section("text_analysis", "re", default={}) or {}
import os

self.model_name = (
    os.getenv("OLLAMA_NER_MODEL")
    or os.getenv("OLLAMA_RE_MODEL")
    or self.config.get("model_name", "llama3.1:8b")
)
```

**优先级**：
1. 环境变量 `OLLAMA_NER_MODEL`（`.env`文件）
2. 环境变量 `OLLAMA_RE_MODEL`（`.env`文件）
3. `config.json` → `text_analysis.re.model_name`
4. 硬编码默认值 `"llama3.1:8b"`

**问题**：
- ❌ 未使用ArangoDB `system_configs`
- ❌ 不符合系统参数配置策略

### 3. RT Service (`genai/api/services/rt_service.py`)

**当前配置来源**：

```python
# RTService.__init__()
self.config = get_config_section("text_analysis", "rt", default={}) or {}
import os

self.model_name = (
    os.getenv("OLLAMA_NER_MODEL")
    or os.getenv("OLLAMA_RT_MODEL")
    or self.config.get("model_name", "llama3.1:8b")
)
```

**优先级**：
1. 环境变量 `OLLAMA_NER_MODEL`（`.env`文件）
2. 环境变量 `OLLAMA_RT_MODEL`（`.env`文件）
3. `config.json` → `text_analysis.rt.model_name`
4. 硬编码默认值 `"llama3.1:8b"`

**问题**：
- ❌ 未使用ArangoDB `system_configs`
- ❌ 不符合系统参数配置策略

---

## 📐 系统参数配置策略

根据`docs/系统设计文档/核心组件/系統管理/部署架构.md`中的**系统参数配置策略**：

### 配置分层

1. **`.env`文件**（基础服务启动参数）
   - 数据库连接信息
   - 服务端口
   - API密钥（敏感信息）
   - **不应该包含业务参数**

2. **ArangoDB `system_configs`**（运行时系统参数）
   - 业务参数（如模型配置、处理参数等）
   - 可以在运行时动态修改
   - 持久化存储

### 业务参数分类

NER/RE/RT模型配置属于**业务参数**，应该存储在ArangoDB `system_configs`中，而不是`.env`文件中。

---

## ✅ 应该的实现方式

### 配置优先级（推荐）

1. **ArangoDB `system_configs`**（优先）
   - Scope: `kg_extraction`
   - 参数名：
     - `ner_model`: NER模型名称
     - `re_model`: RE模型名称
     - `rt_model`: RT模型名称

2. **`.env`文件**（向后兼容）
   - `OLLAMA_NER_MODEL`
   - `OLLAMA_RE_MODEL`
   - `OLLAMA_RT_MODEL`

3. **`config.json`**（向后兼容）
   - `text_analysis.ner.model_name`
   - `text_analysis.re.model_name`
   - `text_analysis.rt.model_name`

4. **硬编码默认值**（最后fallback）
   - NER: `"mistral-nemo:12b"`（或其他合适的默认值）
   - RE: `"mistral-nemo:12b"`
   - RT: `"mistral-nemo:12b"`

### 实现示例

```python
# NERService.__init__()
from services.api.services.config_store_service import ConfigStoreService

def __init__(self):
    # 优先级1: 从ArangoDB system_configs读取
    config_service = ConfigStoreService()
    kg_config = config_service.get_config("kg_extraction", tenant_id=None)
    
    if kg_config and kg_config.config_data:
        ner_model = kg_config.config_data.get("ner_model")
        if ner_model:
            self.model_name = ner_model
        else:
            # 优先级2: 从.env文件读取（向后兼容）
            import os
            self.model_name = os.getenv("OLLAMA_NER_MODEL") or self._get_default_model()
    else:
        # 向后兼容：从.env或config.json读取
        import os
        self.config = get_config_section("text_analysis", "ner", default={}) or {}
        self.model_name = (
            os.getenv("OLLAMA_NER_MODEL")
            or self.config.get("model_name")
            or self._get_default_model()
        )
    
    # 初始化模型...
```

---

## 🔧 实施建议

### 步骤1: 添加默认配置到ConfigInitializer

在`services/api/services/config_initializer.py`的`DEFAULT_SYSTEM_CONFIGS`中添加：

```python
DEFAULT_SYSTEM_CONFIGS: Dict[str, Dict[str, Any]] = {
    # ... 现有配置 ...
    "kg_extraction": {
        "enabled": True,
        "mode": "all_chunks",
        "min_confidence": 0.5,
        "batch_size": 10,
        "ner_model": "mistral-nemo:12b",  # 新增
        "re_model": "mistral-nemo:12b",   # 新增
        "rt_model": "mistral-nemo:12b",   # 新增
    },
}
```

### 步骤2: 修改NER/RE/RT服务

为每个服务添加配置读取逻辑：
1. 优先从`ConfigStoreService`读取
2. 回退到环境变量（向后兼容）
3. 回退到`config.json`（向后兼容）
4. 最后使用硬编码默认值

### 步骤3: 创建辅助函数

可以创建一个辅助函数来统一读取模型配置：

```python
def get_kg_model_config(model_type: str) -> str:
    """
    获取KG提取模型配置（NER/RE/RT）
    
    Args:
        model_type: 模型类型（"ner", "re", "rt"）
    
    Returns:
        模型名称
    """
    from services.api.services.config_store_service import ConfigStoreService
    import os
    
    config_service = ConfigStoreService()
    kg_config = config_service.get_config("kg_extraction", tenant_id=None)
    
    if kg_config and kg_config.config_data:
        model_key = f"{model_type}_model"
        model_name = kg_config.config_data.get(model_key)
        if model_name:
            return model_name
    
    # 向后兼容：从环境变量读取
    env_var_map = {
        "ner": "OLLAMA_NER_MODEL",
        "re": "OLLAMA_RE_MODEL",
        "rt": "OLLAMA_RT_MODEL",
    }
    env_var = env_var_map.get(model_type)
    if env_var:
        model_name = os.getenv(env_var)
        if model_name:
            return model_name
    
    # 最后fallback：使用默认值
    default_models = {
        "ner": "mistral-nemo:12b",
        "re": "mistral-nemo:12b",
        "rt": "mistral-nemo:12b",
    }
    return default_models.get(model_type, "mistral-nemo:12b")
```

---

## 📊 对比表格

| 配置来源 | 当前实现 | 应该实现 |
|---------|---------|---------|
| **ArangoDB system_configs** | ❌ 未使用 | ✅ 优先使用 |
| **.env文件** | ✅ 优先使用 | ✅ 向后兼容（第二优先级） |
| **config.json** | ✅ 第二优先级 | ✅ 向后兼容（第三优先级） |
| **硬编码默认值** | ✅ 最后fallback | ✅ 最后fallback |

---

## 🎯 优势

### 迁移到ArangoDB system_configs后的优势

1. **符合系统参数配置策略**
   - 业务参数存储在`system_configs`中
   - `.env`文件只包含基础服务启动参数

2. **动态配置**
   - 可以在运行时修改模型配置
   - 不需要重启服务

3. **统一管理**
   - 所有KG提取相关配置集中管理
   - 便于系统管理员配置和维护

4. **多租户支持**
   - 未来可以支持租户级别的模型配置
   - 不同租户可以使用不同的模型

5. **向后兼容**
   - 保留`.env`和`config.json`的支持
   - 不会破坏现有配置

---

## 📝 参考文档

1. `docs/系统设计文档/核心组件/系統管理/部署架构.md` - 系统参数配置策略
2. `services/api/services/config_initializer.py` - 配置初始化服务
3. `services/api/services/config_store_service.py` - 配置存储服务
4. `genai/api/services/ner_service.py` - NER服务实现
5. `genai/api/services/re_service.py` - RE服务实现
6. `genai/api/services/rt_service.py` - RT服务实现

---

**最后更新日期**: 2026-01-01

