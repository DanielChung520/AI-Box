# 问题诊断：HCI 查询无响应

**创建日期**: 2025-12-30
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-30

---

## 📋 问题描述

用户查询："HCI 是哪家公司？"，AI 没有任何响应。

---

## 🔍 日志分析

### 关键日志信息

```
2025-12-30 22:45:47 [info] user_text='HCI 是哪家公司？'
2025-12-30 22:45:47 [info] web_search_intent_check matched_keywords=[] needs_search=False
2025-12-30 22:45:47 [info] moe_chat_stream_start model=gemini-2.0-flash-exp provider=gemini
2025-12-30 22:45:47 [warning] Client initialization failed for gemini: Google Generative AI SDK is not installed
2025-12-30 22:45:47 [info] Failing over from gemini to qwen
2025-12-30 22:45:47 [debug] Provider qwen: no API key configured
2025-12-30 22:45:47 [info] Failing over from gemini to chatgpt
2025-12-30 22:45:47 [debug] Provider chatgpt: no API key configured
2025-12-30 22:45:47 [info] All fallback providers failed, attempting final fallback to local gpt-oss:20b
2025-12-30 22:46:29 [info] Successfully used final fallback to local gpt-oss:20b
2025-12-30 22:46:29 [info] moe_chat_stream_completed chunk_count=0 content_length=0
```

### 问题分析

1. **请求流程**：
   - 请求进入 `/api/v1/chat/stream` 端点
   - 使用 `TaskClassifier` 进行分类（不是 Task Analyzer）
   - 调用 `LLMMoEManager.chat()` 进行模型调用

2. **LLM 调用链**：
   - 首选：`gemini-2.0-flash-exp` → 失败（SDK 未安装）
   - Fallback 1：`qwen` → 失败（无 API Key）
   - Fallback 2：`chatgpt` → 失败（无 API Key）
   - Final Fallback：`gpt-oss:20b`（本地模型）→ **成功连接，但返回空内容**

3. **关键问题**：
   - ❌ **没有使用 Task Analyzer**：请求没有经过我们新实现的 Layer 1 (Fast Answer Layer)
   - ❌ **本地模型返回空内容**：`chunk_count=0 content_length=0`
   - ❌ **所有高级 LLM 都失败**：没有配置 API Key

---

## 🎯 根本原因

### 原因 1：聊天路由未集成 Task Analyzer

**当前实现**（`api/routers/chat.py`）：

```python
# 使用的是 TaskClassifier（简单分类器）
classifier = get_task_classifier()
task_classification = classifier.classify(last_user_text, context={...})

# 然后直接调用 MoE Manager
result = await moe.chat(messages_for_llm, task_classification=task_classification, ...)
```

**问题**：

- 没有调用 `TaskAnalyzer.analyze()`
- 没有经过 Layer 0 (Cheap Gating)
- 没有经过 Layer 1 (Fast Answer Layer)
- 没有经过 Layer 2/3 (Intent Analysis + Decision Engine)

### 原因 2：本地模型返回空内容

**现象**：

- `gpt-oss:20b` 连接成功
- 但 `chunk_count=0 content_length=0`，说明模型没有返回任何内容

**可能原因**：

- 模型调用超时
- 模型响应格式问题
- 流式响应处理问题
- 模型本身的问题

---

## 📊 代码流程对比

### 当前实际流程（聊天路由）

```
用户请求 "HCI 是哪家公司？"
  ↓
/api/v1/chat/stream
  ↓
TaskClassifier.classify()  ← 简单分类器
  ↓
LLMMoEManager.chat()  ← 直接调用模型
  ↓
gemini → qwen → chatgpt → gpt-oss:20b (Fallback)
  ↓
返回空内容 (chunk_count=0)
```

### 预期流程（Task Analyzer 4层架构）

```
用户请求 "HCI 是哪家公司？"
  ↓
Layer 0: Cheap Gating
  ↓ (匹配 factoid pattern: "是哪家公司")
Layer 1: Fast Answer Layer
  ↓ (使用高级 LLM 直接回答)
返回答案：HCI 是哪家公司...
```

---

## 🔧 解决方案

### 方案 1：集成 Task Analyzer 到聊天路由（推荐）

**需要修改**：`api/routers/chat.py`

**修改点**：

1. 在聊天路由中调用 `TaskAnalyzer.analyze()`
2. 检查是否返回 Layer 1 直接答案
3. 如果是直接答案，直接返回
4. 如果需要系统行动，再进入原有的 MoE 流程

**实现示例**：

```python
# 在 chat_product_stream 或 _process_chat_request 中
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest

# 创建 Task Analyzer 实例（或使用单例）
task_analyzer = TaskAnalyzer()

# 分析请求
analysis_result = await task_analyzer.analyze(
    TaskAnalysisRequest(
        task=last_user_text,
        context={
            "user_id": current_user.user_id,
            "session_id": session_id,
            "task_id": task_id,
        },
    )
)

# 检查是否是 Layer 1 直接回答
if analysis_result.analysis_details.get("direct_answer"):
    # 直接返回答案，不进入 MoE 流程
    response_content = analysis_result.analysis_details.get("response", "")
    # 返回响应...
    return

# 如果需要系统行动，继续原有的 MoE 流程
# ...
```

### 方案 2：修复本地模型返回空内容的问题

**需要检查**：

1. 本地模型 `gpt-oss:20b` 是否正常运行
2. 模型调用是否超时
3. 流式响应处理是否正确
4. 模型响应格式是否符合预期

---

## 📝 立即行动项

### 优先级 1（必须修复）

1. **集成 Task Analyzer 到聊天路由**
   - 修改 `api/routers/chat.py`
   - 在聊天流程开始前调用 `TaskAnalyzer.analyze()`
   - 检查 Layer 1 直接答案并返回

### 优先级 2（需要调查）

2. **调查本地模型返回空内容的原因**
   - 检查 Ollama 服务状态
   - 检查模型 `gpt-oss:20b` 是否正常运行
   - 检查流式响应处理逻辑

---

## 🧪 测试建议

### 测试 1：验证 Layer 0 逻辑

```python
# 测试 _is_direct_answer_candidate
query = "HCI 是哪家公司？"
is_candidate = analyzer._is_direct_answer_candidate(query)
# 应该返回 True（匹配 factoid pattern）
```

### 测试 2：验证 Layer 1 逻辑（需要 API Key）

```python
# 测试 _try_direct_answer（需要配置 OpenAI 或 Gemini API Key）
request = TaskAnalysisRequest(task="HCI 是哪家公司？")
result = await analyzer._try_direct_answer(request, task_id)
# 应该返回 TaskAnalysisResult，包含 direct_answer=True
```

### 测试 3：验证完整流程（需要 API Key）

```python
# 测试完整 analyze 流程
request = TaskAnalysisRequest(task="HCI 是哪家公司？")
result = await analyzer.analyze(request)
# 应该返回 Layer 1 直接答案
```

---

**最后更新日期**: 2025-12-30
**维护人**: Daniel Chung
