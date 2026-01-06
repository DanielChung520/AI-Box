# GraphRAG 模型参数配置建议

**创建日期**: 2026-01-03
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-03

---

## 📋 概述

本文档提供 GraphRAG 知识图谱提取任务的模型参数配置建议，基于 ChatGPT 的建议和实际测试经验。

---

## 🎯 推荐参数配置

### 基础配置（推荐）

```python
{
    "temperature": 0.0,      # 保守，确保稳定性
    "top_p": 0.9,            # 核采样参数
    "top_k": 40,             # Top-K 采样
    "max_tokens": 512,       # 每个 chunk 的最大输出 token 数
    "num_ctx": 32768         # Context window（Ollama 专用）
}
```

### 参数说明

#### 1. temperature (0.0 - 0.2)

**推荐值**: `0.0`

**理由**:
- GraphRAG 提取任务需要**确定性输出**，而非创造性
- `temperature=0.0` 确保相同输入产生相同输出
- 提高三元组提取的**一致性和可重复性**

**不同场景**:
- **提取任务**: `0.0` (推荐)
- **质量评估**: `0.1 - 0.2` (如果需要一定灵活性)

#### 2. top_p (0.9)

**推荐值**: `0.9`

**理由**:
- 平衡确定性和灵活性
- 避免过于保守（top_p=1.0）或过于随机（top_p<0.8）

#### 3. top_k (40)

**推荐值**: `40`

**理由**:
- 限制候选 token 数量，提高效率
- 对于知识图谱提取，40 个候选 token 通常足够

#### 4. max_tokens (512)

**推荐值**: `512`

**理由**:
- 单个 chunk 的三元组数量通常有限
- 512 tokens 足够表达 10-20 个三元组
- 避免过长输出导致解析错误

**注意**: 如果 chunk 较大或预期三元组较多，可以增加到 `1024`

#### 5. num_ctx (32768)

**推荐值**: `32768` (Ollama 专用)

**理由**:
- 确保有足够的上下文窗口处理长文本
- 32k 是当前 Ollama 模型的标准配置

---

## 🔧 不同模型的参数调整

### Ollama 模型 (Mistral-NeMo:12B)

```python
{
    "temperature": 0.0,
    "top_p": 0.9,
    "top_k": 40,
    "num_ctx": 32768,
    "format": "json"  # 强制 JSON 输出
}
```

### Gemini 模型

```python
{
    "temperature": 0.0,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 512
}
```

### OpenAI GPT-4

```python
{
    "temperature": 0.0,
    "top_p": 0.9,
    "max_tokens": 512,
    "response_format": {"type": "json_object"}  # 强制 JSON 输出
}
```

---

## 📊 Chunk Size 建议

### 推荐 Chunk Size

- **最小**: 200 tokens
- **推荐**: 300-500 tokens
- **最大**: 800 tokens

### 理由

1. **太小 (<200 tokens)**:
   - 上下文不足，难以提取完整三元组
   - 实体和关系可能被截断

2. **适中 (300-500 tokens)**:
   - ✅ 有足够上下文提取完整三元组
   - ✅ 不会超出模型上下文窗口
   - ✅ 处理效率高

3. **太大 (>800 tokens)**:
   - ❌ 可能超出 max_tokens 限制
   - ❌ 输出质量可能下降
   - ❌ 处理时间增加

---

## ⚙️ 实现建议

### 1. 配置化设计

**不推荐硬编码**，建议在服务层支持参数配置：

```python
# services/api/services/kg_extraction_service.py
class KGExtractionService:
    def __init__(self, ...):
        # 从配置读取参数
        self.model_params = {
            "temperature": config.get("kg.temperature", 0.0),
            "top_p": config.get("kg.top_p", 0.9),
            "top_k": config.get("kg.top_k", 40),
            "max_tokens": config.get("kg.max_tokens", 512),
        }
```

### 2. 环境变量配置

```bash
# .env
KG_EXTRACTION_TEMPERATURE=0.0
KG_EXTRACTION_TOP_P=0.9
KG_EXTRACTION_TOP_K=40
KG_EXTRACTION_MAX_TOKENS=512
```

### 3. ArangoDB 配置存储

```python
# 存储在 system_configs 中
{
    "scope": "genai.kg_extraction",
    "config_data": {
        "model_params": {
            "temperature": 0.0,
            "top_p": 0.9,
            "top_k": 40,
            "max_tokens": 512
        },
        "chunk_size": {
            "min": 200,
            "recommended": 400,
            "max": 800
        }
    }
}
```

---

## 🎯 性能优化建议

### 1. 批量处理

- 使用 `asyncio.gather()` 并行处理多个 chunks
- 控制并发数（建议 4-8 个并发）

### 2. 缓存策略

- 缓存相同文本的提取结果
- 使用文本哈希作为缓存键

### 3. 错误处理

- 设置合理的超时时间（建议 30-60 秒）
- 实现重试机制（最多 3 次）
- 记录失败日志用于后续分析

---

## 📝 总结

**核心原则**:
1. ✅ **确定性优先**: `temperature=0.0` 确保稳定性
2. ✅ **适度限制**: `max_tokens=512` 避免过长输出
3. ✅ **可配置化**: 不硬编码，支持运行时调整
4. ✅ **模型适配**: 不同模型使用对应的参数格式

**实施建议**:
- ✅ 立即采用推荐参数
- ✅ 在服务层实现配置化
- ✅ 通过 A/B 测试优化参数
- ✅ 根据实际效果调整

