# 根本原因已找到！

**日期**: 2026-01-28
**問題**: Agent 實例無法獲取，導致 Agent 結果為空

---

## 根本原因

### ⚠️ 關鍵發現

**測試結果**（`test_actual_api_flow.py`）:
```
[3] Agent 執行...
  Agent info: name=Knowledge Architect Agent (v1.5), is_internal=False
  ❌ 無法獲取 Agent 實例
```

**問題**: `is_internal=False`，導致 Agent 實例無法獲取！

---

## 問題分析

### 問題流程

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

## 修復方案

### 修復 1: 從 metadata 讀取 is_internal

**位置**: `agents/services/registry/registry.py` 第 512-538 行和第 656-692 行

**修改**:
- 從 `sys_agent.metadata.get("is_internal", True)` 讀取 `is_internal`
- 如果不存在，默認為 `True`（System Agent 默認為內部）

**代碼**:
```python
# 從 metadata 中讀取 is_internal，如果不存在則默認為 True（System Agent 默認為內部）
metadata = sys_agent.metadata or {}
is_internal = metadata.get("is_internal", True)  # System Agent 默認為內部
```

---

## 驗證步驟

### 1. 重新運行測試

**命令**:
```bash
python3 test_actual_api_flow.py
```

**預期結果**:
- ✅ `is_internal=True`
- ✅ Agent 實例可以獲取
- ✅ Agent 執行成功
- ✅ `agent_tool_results` 不為空
- ✅ `messages_for_llm` 包含 Agent 結果
- ✅ LLM 正確回答

### 2. 檢查實際 API 調用

**命令**:
```bash
python3 test_chat_api_endpoint.py
```

**預期結果**:
- ✅ API 端點返回 200 狀態碼
- ✅ LLM 響應包含文件數量
- ✅ LLM 不返回拒絕性回答

---

## 相關文件

- `agents/services/registry/registry.py` - Agent Registry 邏輯
- `agents/builtin/__init__.py` - Agent 註冊邏輯
- `test_actual_api_flow.py` - 實際 API 流程測試

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
