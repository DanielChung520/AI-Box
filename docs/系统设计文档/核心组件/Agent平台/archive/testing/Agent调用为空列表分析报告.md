# Agent 調用為空列表的深度分析報告

**創建日期**: 2026-01-11
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-11 19:55

---

## 問題描述

所有測試場景的 `actual_agents` 為空列表 `[]`，導致 Agent 調用失敗。

## 代碼流程分析

### 1. analyzer.py 中的流程

**關鍵代碼**（analyzer.py 303-305 行）：

```python
suggested_agents = []
if decision_result.chosen_agent:
    suggested_agents.append(decision_result.chosen_agent)
```

**說明**：`suggested_agents` 只有在 `decision_result.chosen_agent` 不為 None 時才會有值。

**流程**：

1. 第 231-233 行：調用 `capability_matcher.match_agents(router_output, enhanced_context)` 獲取 `agent_candidates`
2. 第 248-251 行：記錄日誌 `agent_candidates` 數量
3. 第 252-258 行：調用 `decision_engine.decide(..., agent_candidates, ...)`
4. 第 259-263 行：記錄日誌 `decision_result.chosen_agent`
5. 第 303-305 行：從 `decision_result.chosen_agent` 構建 `suggested_agents`

### 2. CapabilityMatcher.match_agents() 的邏輯

**關鍵代碼**（capability_matcher.py 299 行）：

```python
user_query = context.get("task", "") or context.get("query", "") if context else ""
is_file_editing = self._is_file_editing_task(user_query)
```

**問題**：如果 `context` 中沒有 `"task"` 或 `"query"` 字段，`user_query` 會為空字符串。

**影響**：

- 如果 `user_query` 為空，`is_file_editing` 判斷會失敗
- 如果 `is_file_editing=False`，代碼會使用 `AgentDiscovery`（第 399-406 行）
- `AgentDiscovery.discover_agents()` 會過濾 System Agents
- System Agent（md-editor, xls-editor 等）會被過濾掉
- 最終 `agent_candidates` 可能為空

### 3. DecisionEngine.decide() 的選擇邏輯

**關鍵代碼**（decision_engine.py 340 行）：

```python
user_query = context.get("task", "") or context.get("query", "") if context else ""
is_file_editing = self._is_file_editing_task(user_query)
specific_agent_id = self._select_agent_by_file_extension(user_query)
```

**同樣的問題**：如果 `context` 中沒有 `"task"` 或 `"query"` 字段，`user_query` 會為空字符串。

**選擇邏輯**（decision_engine.py 363-430 行）：

1. 方案1：根據文件擴展名精確匹配（需要 `specific_agent_id and agent_candidates`）
2. 方案2：如果是文件編輯任務，優先選擇 document-editing-agent（需要 `not chosen_agent and is_file_editing and agent_candidates`）
3. 方案3：從 `agent_candidates` 中選擇評分最高的（需要 `router_decision.needs_agent and agent_candidates`）

**關鍵問題**：如果 `agent_candidates` 為空，所有方案都不會執行，`chosen_agent` 會保持為 None。

## 可能的原因

### 1. context 中沒有 'task' 字段（最可能的原因）

**問題**：

- `analyzer.py` 中構建 `enhanced_context` 時可能沒有包含 `"task"` 字段
- `CapabilityMatcher.match_agents()` 從 `context.get("task")` 獲取 `user_query`，如果 `context` 中沒有 `"task"`，`user_query` 為空
- 如果 `user_query` 為空，`is_file_editing` 判斷失敗
- 使用 `AgentDiscovery`，過濾掉 System Agents
- `agent_candidates` 為空

**檢查點**：

- analyzer.py 第 218-228 行：`enhanced_context` 的構建
- 確認是否包含 `"task"` 字段

### 2. Agent Registry 中沒有註冊相應的 Agent

**問題**：

- md-editor, xls-editor 等 System Agent 可能沒有註冊
- 或者這些 Agent 的 `agent_type` 不是 `"document_editing"`
- 或者這些 Agent 的 `status` 不是 `ONLINE`

**檢查點**：

- Agent Registry 中的 Agent 註冊狀態
- System Agent 的 agent_type 和 status

### 3. DecisionEngine 選擇邏輯沒有被觸發

**問題**：

- 如果 `agent_candidates` 為空，所有選擇方案都不會執行
- `chosen_agent` 保持為 None
- `suggested_agents` 為空列表

**檢查點**：

- `agent_candidates` 是否為空？
- 如果 `agent_candidates` 不為空，為什麼沒有選擇到 Agent？

## 建議的調試步驟

### 1. 檢查 context 傳遞

**檢查 analyzer.py 中的 enhanced_context 構建**（第 218-228 行）：

- 確認是否包含 `"task"` 字段
- 如果沒有，需要添加

### 2. 添加調試日誌

**在 CapabilityMatcher.match_agents() 中添加日誌**：

- 記錄 `user_query` 的值
- 記錄 `is_file_editing` 的判斷結果
- 記錄 `agent_candidates` 的數量和內容

**在 DecisionEngine.decide() 中添加日誌**：

- 記錄收到的 `agent_candidates` 數量
- 記錄文件擴展名匹配的結果（`specific_agent_id`）
- 記錄每個選擇方案的執行情況
- 記錄 `chosen_agent` 的最終值

### 3. 檢查 Agent Registry

**檢查 System Agent 的註冊狀態**：

- 確認 md-editor, xls-editor 等 System Agent 是否已註冊
- 確認這些 Agent 的 agent_type 是否為 `"document_editing"`
- 確認這些 Agent 的 status 是否為 `ONLINE`

## 發現的問題

### ✅ 已確認：context 傳遞正確

**analyzer.py 第 228-229 行**：

```python
enhanced_context["task"] = request.task
enhanced_context["query"] = request.task
```

`enhanced_context` 已正確包含 `"task"` 和 `"query"` 字段。

### ❌ 問題 1：缺少 agent_candidates 日誌

**analyzer.py 第 235-238 行**：

- 只記錄了 `tool_candidates` 的日誌
- **沒有記錄 `agent_candidates` 的日誌！**
- 需要添加：`logger.info(f"Layer 3: Capability Matcher found {len(agent_candidates)} agent candidates: {[c.candidate_id for c in agent_candidates[:5]]}")`

### ❌ 問題 2：DecisionEngine.decide() 的 context 參數

**analyzer.py 第 252-258 行**：

```python
decision_result = self.decision_engine.decide(
    router_output,
    agent_candidates,
    tool_candidates,
    model_candidates,
    request.context,  # ❌ 應該是 enhanced_context
)
```

**問題**：

- 傳遞的是 `request.context` 而不是 `enhanced_context`
- `DecisionEngine.decide()` 第 340 行從 `context.get("task")` 獲取 `user_query`
- 如果 `request.context` 中沒有 `"task"` 字段，`user_query` 會為空
- 導致 `is_file_editing` 判斷失敗，文件擴展名匹配失敗

### ✅ 已確認：System Agent 註冊狀態

**系統規格書要求**（`文件編輯-Agent-系統規格書-v2.0.md`）：
根據系統規格書，應註冊以下 6 個 System Agent：

1. `document-editing-agent` - 文件編輯服務（通用）
2. `md-editor` - Markdown 編輯器
3. `xls-editor` - Excel 編輯器
4. `md-to-pdf` - Markdown 轉 PDF
5. `xls-to-pdf` - Excel 轉 PDF
6. `pdf-to-md` - PDF 轉 Markdown

**代碼確認**（`agents/builtin/__init__.py`）：

| Agent ID | Agent 類型 | 狀態 | 註冊位置 | 說明 | 代碼位置 |
|----------|-----------|------|---------|------|---------|
| `document-editing-agent` | `document_editing` | ONLINE | System Agent Registry + Agent Registry | 文件編輯服務（通用） | 第 342-421 行 |
| `md-editor` | `document_editing` | ONLINE | System Agent Registry + Agent Registry | Markdown 編輯器（v2.0） | 第 525-584 行 |
| `xls-editor` | `document_editing` | ONLINE | System Agent Registry + Agent Registry | Excel 編輯器（v2.0） | 第 588-605 行 |
| `md-to-pdf` | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | Markdown 轉 PDF（v2.0） | 第 608-624 行 |
| `xls-to-pdf` | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | Excel 轉 PDF（v2.0） | 第 627-643 行 |
| `pdf-to-md` | `document_conversion` | ONLINE | System Agent Registry + Agent Registry | PDF 轉 Markdown（v2.0） | 第 646-662 行 |

**註冊流程**：

1. 所有 System Agent 都通過 `register_builtin_agents()` 函數註冊（第 282-671 行）
2. 註冊流程：先註冊到 System Agent Registry（ArangoDB），再註冊到 Agent Registry（內存）
3. 註冊時會設置 `is_system_agent=True` 和 `status=ONLINE`
4. 註冊時機：系統啟動時通過 `api/main.py` 調用 `register_builtin_agents()`

**結論**：✅ **System Agent 註冊狀態正常，所有 6 個 Agent 都已正確註冊，符合系統規格書要求，不需要重複檢查。**

## 建議的修復

### 修復 1：添加 agent_candidates 日誌

在 analyzer.py 第 234 行之後添加：

```python
logger.info(
    f"Layer 3: Capability Matcher found {len(agent_candidates)} agent candidates: "
    f"{[c.candidate_id for c in agent_candidates[:5]]}"
)
```

### 修復 2：將 DecisionEngine.decide() 的 context 參數改為 enhanced_context

在 analyzer.py 第 252-258 行，將 `request.context` 改為 `enhanced_context`：

```python
decision_result = self.decision_engine.decide(
    router_output,
    agent_candidates,
    tool_candidates,
    model_candidates,
    enhanced_context,  # ✅ 改為 enhanced_context
)
```

### 修復 3：添加詳細調試日誌

在 CapabilityMatcher.match_agents() 和 DecisionEngine.decide() 中添加詳細的調試日誌，追蹤整個 Agent 選擇流程。

## ✅ 測試執行結果

### 測試執行（2026-01-11 19:43）

**測試場景數**：3（限制）
**測試結果**：

- ✅ 意圖類型識別：100% 正確（所有場景 `actual_intent_type=execution`）
- ✅ needs_agent 判斷：100% 正確（所有場景 `actual_needs_agent=True`）
- ❌ Agent 調用：0% 成功（所有場景 `actual_agents=[]`）

**關鍵發現**：

1. RouterLLM 的意圖識別正確（intent_type=execution, needs_agent=True）
2. 但 DecisionEngine 沒有選擇到 Agent
3. 可能原因：`agent_candidates` 為空，或者選擇邏輯沒有滿足條件

**日誌檢查**：

- 測試日誌中未看到 "Layer 3: Capability Matcher found X agent candidates" 的輸出
- 需要檢查實際運行時的日誌，確認 `agent_candidates` 的數量

## 📋 後續行動

1. ✅ **已修復**：添加 agent_candidates 日誌記錄
2. ✅ **已修復**：修復 DecisionEngine.decide() 的 context 參數
3. ✅ **已確認**：System Agent 註冊狀態正常
4. ⏳ **待執行**：運行完整測試，查看 agent_candidates 日誌輸出
5. ⏳ **待分析**：根據日誌進一步分析為什麼 agent_candidates 為空

---
