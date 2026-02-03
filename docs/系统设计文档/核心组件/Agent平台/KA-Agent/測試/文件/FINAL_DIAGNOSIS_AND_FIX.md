# 最終診斷與修復報告

**日期**: 2026-01-28
**問題**: LLM 返回拒絕性回答，即使 Agent 執行成功

---

## 問題定位過程

### 步驟 1: 獨立測試驗證流程 ✅

**測試腳本**: `test_agent_result_flow.py`

**結果**: 6/6 測試通過

**關鍵發現**:
- ✅ 當 Agent 結果正確傳遞時，LLM 能夠正確回答
- ✅ 無 Agent 結果時，LLM 返回拒絕性回答
- ✅ 有 Agent 結果時，LLM 正確回答（包含文件數量，不包含拒絕性回答）

**結論**: **Agent 結果流程代碼邏輯正確！**

---

### 步驟 2: 實際 API 流程測試 ⚠️

**測試腳本**: `test_actual_api_flow.py`

**結果**: 發現問題

**關鍵發現**:
```
[3] Agent 執行...
  Agent info: name=Knowledge Architect Agent (v1.5), is_internal=False
  ❌ 無法獲取 Agent 實例
  ⚠️ agent_tool_results 為空，沒有 Agent 結果
```

**結論**: **問題在於 `is_internal=False`，導致 Agent 實例無法獲取！**

---

## 根本原因

### 問題分析

1. **Agent 註冊時**（`agents/builtin/__init__.py` 第 248 行）：
   - ✅ `is_internal=True` 正確設置
   - ✅ Agent 實例正確存儲到 `_agent_instances`

2. **從 System Agent Registry 加載時**（`agents/services/registry/registry.py` 第 678-682 行）：
   - ❌ `is_internal` 從 `endpoints_dict.get("is_internal", False)` 讀取
   - ❌ 如果 `endpoints_dict` 不存在或 `is_internal` 不在 `endpoints` 中，默認為 `False`
   - ❌ 導致 `is_internal=False`

3. **獲取 Agent 實例時**（`agents/services/registry/registry.py` 第 381-390 行）：
   - ❌ 因為 `is_internal=False`，不會從 `_agent_instances` 獲取實例
   - ❌ 嘗試獲取外部 Agent Client，但沒有 endpoint，返回 `None`

---

## 已實施的修復

### 修復 1: 從 metadata 讀取 is_internal

**位置**: `agents/services/registry/registry.py` 第 526-538 行

**修改前**:
```python
endpoints=AgentEndpoints(
    http=None,
    mcp=None,
    protocol=AgentServiceProtocolType.HTTP,
    is_internal=True,  # 硬編碼為 True
),
```

**修改後**:
```python
# 從 metadata 中讀取 is_internal，如果不存在則默認為 True（System Agent 默認為內部）
metadata = sys_agent.metadata or {}
is_internal = metadata.get("is_internal", True)  # System Agent 默認為內部

endpoints=AgentEndpoints(
    http=None,
    mcp=None,
    protocol=AgentServiceProtocolType.HTTP,
    is_internal=is_internal,
),
```

---

### 修復 2: 從 metadata 讀取 is_internal（get_all_agents）

**位置**: `agents/services/registry/registry.py` 第 656-692 行

**修改前**:
```python
is_internal=(
    endpoints_dict.get("is_internal", False)
    if endpoints_dict
    else False
),
```

**修改後**:
```python
# 從 metadata 中讀取 is_internal，如果不存在則默認為 True（System Agent 默認為內部）
metadata = sys_agent.metadata or {}
is_internal = metadata.get("is_internal", True)  # System Agent 默認為內部
endpoints_dict = metadata.get("endpoints", {}) if metadata else {}

endpoints=AgentEndpoints(
    ...
    is_internal=is_internal,
),
```

---

## 預期效果

修復後，應該能夠：

1. **正確識別內部 Agent**：
   - `is_internal=True` 從 metadata 正確讀取
   - 如果 metadata 中不存在，默認為 `True`（System Agent 默認為內部）

2. **正確獲取 Agent 實例**：
   - `registry.get_agent()` 能夠從 `_agent_instances` 獲取實例
   - Agent 能夠正常執行

3. **正確傳遞 Agent 結果**：
   - `agent_tool_results` 不為空
   - `messages_for_llm` 包含 Agent 結果
   - LLM 能夠基於 Agent 結果生成正確的回答

---

## 驗證步驟

### 1. 重新運行測試

**命令**:
```bash
# 測試實際 API 流程
python3 test_actual_api_flow.py

# 測試 API 端點
python3 test_chat_api_endpoint.py
```

**預期結果**:
- ✅ `is_internal=True`
- ✅ Agent 實例可以獲取
- ✅ Agent 執行成功
- ✅ `agent_tool_results` 不為空
- ✅ `messages_for_llm` 包含 Agent 結果
- ✅ LLM 正確回答（包含文件數量，不包含拒絕性回答）

### 2. 重啟 FastAPI 服務

**命令**:
```bash
# 確保修改生效
# 如果使用 uvicorn --reload，服務會自動重啟
```

### 3. 運行 P0 測試

**命令**:
```bash
python3 test_ka_agent_round4.py
```

**預期結果**:
- ✅ 所有測試用例通過
- ✅ LLM 正確回答文件數量
- ✅ LLM 不返回拒絕性回答

---

## 相關文件

### 測試腳本
- `test_agent_result_flow.py` - 完整流程測試（6/6 通過）
- `test_actual_api_flow.py` - 實際 API 流程測試（發現問題）
- `test_messages_structure.py` - messages_for_llm 結構測試
- `test_llm_instruction_effectiveness.py` - LLM 指令有效性測試

### 修復文件
- `agents/services/registry/registry.py` - 修復 `is_internal` 讀取邏輯

### 報告文件
- `PROBLEM_POINTS_AND_TESTS.md` - 問題點定義與測試計劃
- `TEST_EXECUTION_SUMMARY.md` - 測試執行總結
- `CRITICAL_FINDING.md` - 關鍵發現報告
- `ROOT_CAUSE_FOUND.md` - 根本原因報告
- `FINAL_DIAGNOSIS_AND_FIX.md` - 本報告

---

## 總結

### 問題定位

1. ✅ **獨立測試證明流程正確**：當 Agent 結果正確傳遞時，LLM 能夠正確回答
2. ✅ **實際 API 流程測試發現問題**：`is_internal=False`，導致 Agent 實例無法獲取
3. ✅ **根本原因已找到**：從 System Agent Registry 加載時，`is_internal` 讀取邏輯錯誤

### 修復實施

1. ✅ **修復 `is_internal` 讀取邏輯**：從 `metadata.is_internal` 讀取，默認為 `True`
2. ✅ **代碼已通過 linter 檢查**

### 下一步

1. **重啟 FastAPI 服務**
2. **運行測試驗證修復**
3. **檢查日誌確認 Agent 實例正確獲取**

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
