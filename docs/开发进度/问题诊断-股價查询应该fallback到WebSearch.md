# 问题诊断：股價查询应该 fallback 到 WebSearch

**创建日期**: 2025-12-30
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-30

---

## 📋 问题描述

**用户查询**："幫我看台灣華電網今天的股價"

**AI 实际回复**：
> 抱歉，我目前無法直接查詢或顯示實時股價。以下提供幾種常見且可靠的方式，讓您可以快速取得「台灣華電（Hua Nan Power / Taiwan Power Company）」今天的股價資訊：
> 並給一些查詢建議

**用户期望**：找不到，应该尝试上网查（若有上网权利）

---

## 🔍 问题分析

### 当前流程

1. **Layer 0 (Cheap Gating)**：
   - 检测到 `"股價"` 在 `tool_indicators` 中
   - `_is_direct_answer_candidate()` 返回 `False`
   - 进入 Layer 1

2. **Layer 1 (Fast Answer Layer)**：
   - 高级 LLM 判断需要实时数据
   - 返回 `{"needs_system_action": true}`
   - 进入 Layer 2/3

3. **Layer 2/3 (Decision Engine)**：
   - Router LLM 识别需要工具：`needs_tools=True`
   - Capability Matcher 匹配工具（可能没有 `stock_price_tool`）
   - 如果没有匹配的工具，或工具返回空结果，系统直接返回 "无法查询"

4. **问题**：
   - 没有 fallback 机制：当主要工具不存在或返回空结果时，应该尝试 WebSearch
   - 聊天路由中的 WebSearch 只在关键词匹配时触发，不会作为 fallback

---

## 🎯 解决方案

### 方案 1：在 Decision Engine 中添加 WebSearch Fallback（推荐）

在 `DecisionEngine.decide()` 中：

- 如果 `needs_tools=True` 但没有匹配的工具
- 或者工具返回空结果
- 且 `allowed_tools` 包含 `web_search`
- 则自动添加 `web_search` 到 `suggested_tools`

### 方案 2：在聊天路由中添加 Fallback 逻辑

在 `chat_product_stream` 中：

- 当 Task Analyzer 返回 `needs_tools=True` 但没有找到合适的工具
- 或者工具执行失败/返回空结果
- 且 `allowed_tools` 包含 `web_search`
- 则自动调用 WebSearch

### 方案 3：在 Layer 1 中智能判断

在 `_try_direct_answer()` 的 System Prompt 中：

- 明确告诉 LLM：如果问题需要实时数据但无法直接回答，应该返回 `needs_system_action: true`
- 但不应该直接说"无法查询"，而应该让系统尝试工具和 WebSearch

---

## 📝 推荐实施方案

### 实施步骤

1. **修改 Decision Engine**：
   - 当 `needs_tools=True` 但 `suggested_tools` 为空时
   - 检查是否有 `web_search` 权限
   - 如果有，自动添加 `web_search` 到 `suggested_tools`

2. **修改聊天路由**：
   - 当 Task Analyzer 返回 `needs_tools=True` 但 `suggested_tools` 为空时
   - 检查 `allowed_tools` 是否包含 `web_search`
   - 如果包含，自动触发 WebSearch

3. **优化 Layer 1 System Prompt**：
   - 明确说明：需要实时数据的问题应该返回 `needs_system_action: true`
   - 不要直接回答"无法查询"

---

## 🔧 代码修改点

### 1. Decision Engine (`agents/task_analyzer/decision_engine.py`)

```python
# 在选择工具后，如果没有匹配的工具，检查是否可以 fallback 到 WebSearch
if router_decision.needs_tools and not chosen_tools:
    # 检查是否有 web_search 权限（从 system_constraints 或 context 中获取）
    if self._has_web_search_permission(context):
        chosen_tools.append("web_search")
```

### 2. 聊天路由 (`api/routers/chat.py`)

```python
# 在 Task Analyzer 分析后
if analysis_result.decision_result and analysis_result.decision_result.needs_tools:
    suggested_tools = analysis_result.decision_result.chosen_tools or analysis_result.suggested_tools
    if not suggested_tools and "web_search" in allowed_tools:
        # Fallback 到 WebSearch
        suggested_tools = ["web_search"]
        # 触发 WebSearch...
```

---

## 🧪 测试用例

### 测试用例 1：股價查询（没有专门的股票工具）

**查询**："幫我看台灣華電網今天的股價"

**预期流程**：

1. Layer 0 → 不是 Direct Answer Candidate（有 `"股價"`）
2. Layer 1 → 需要系统行动
3. Layer 2/3 → `needs_tools=True`，但没有匹配的股票工具
4. **Fallback** → 自动添加 `web_search` 到 `suggested_tools`
5. 执行 WebSearch → 返回搜索结果
6. LLM 基于搜索结果回答

### 测试用例 2：天气查询（没有专门的天气工具）

**查询**："今天台北的天气怎么样？"

**预期流程**：

1. Layer 0 → 不是 Direct Answer Candidate（有 `"天氣"`）
2. Layer 1 → 需要系统行动
3. Layer 2/3 → `needs_tools=True`，但没有匹配的天气工具
4. **Fallback** → 自动添加 `web_search` 到 `suggested_tools`
5. 执行 WebSearch → 返回搜索结果
6. LLM 基于搜索结果回答

---

**最后更新日期**: 2025-12-30
**维护人**: Daniel Chung
