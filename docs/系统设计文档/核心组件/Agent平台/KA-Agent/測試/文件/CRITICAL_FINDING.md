# 關鍵發現報告

**日期**: 2026-01-28
**問題**: Agent 實例無法獲取

---

## 關鍵發現

### ⚠️ 問題定位成功！

**測試結果**（`test_actual_api_flow.py`）:
```
[3] Agent 執行...
  ⚠️ Agent 不是內部 Agent 或不存在
  ⚠️ agent_tool_results 為空，沒有 Agent 結果
  ✅ messages_for_llm 構建完成
    Total messages: 1
    [0] user: 告訴我你的知識庫或文件區有多少文件？...
```

**結論**: **Agent 實例無法獲取，導致 Agent 結果為空！**

---

## 問題分析

### 問題點

1. **Task Analysis 成功**：
   - ✅ 成功選擇了 `ka-agent`
   - ✅ `chosen_agent_id = "ka-agent"`

2. **Agent 信息獲取成功**：
   - ✅ `agent_info` 存在
   - ❌ 但 `agent_info.endpoints.is_internal` 可能為 `False` 或 `None`

3. **Agent 實例獲取失敗**：
   - ❌ `registry.get_agent(chosen_agent_id)` 返回 `None`
   - ❌ 導致 Agent 無法執行

4. **結果**：
   - ❌ `agent_tool_results` 為空
   - ❌ `messages_for_llm` 沒有 Agent 結果
   - ❌ LLM 返回拒絕性回答

---

## 根本原因

### 可能的原因

1. **Agent 註冊問題**：
   - Agent 可能沒有正確註冊到 Registry
   - Agent 的 `is_internal` 標記可能不正確

2. **Agent 實例存儲問題**：
   - Agent 實例可能沒有正確存儲到 Registry
   - `registry.get_agent()` 可能無法找到實例

3. **Agent 狀態問題**：
   - Agent 狀態可能不是 `online`
   - Agent 可能被標記為 `offline`

---

## 需要檢查的地方

### 1. Agent 註冊邏輯

**文件**: `agents/builtin/__init__.py`

**檢查**:
- Agent 是否正確註冊
- `is_internal=True` 是否正確設置
- Agent 實例是否正確存儲

### 2. Agent Registry 邏輯

**文件**: `agents/services/registry/registry.py`

**檢查**:
- `get_agent()` 方法是否正確實現
- Agent 實例存儲邏輯是否正確
- `is_internal` 檢查邏輯是否正確

### 3. Agent 狀態檢查

**文件**: `api/routers/chat.py` 第 1811 行

**檢查**:
- `agent_info.status.value == "online"` 檢查是否過於嚴格
- Agent 狀態是否正確更新

---

## 解決方案

### 方案 1: 檢查 Agent 註冊

**步驟**:
1. 檢查 `agents/builtin/__init__.py` 中的 Agent 註冊邏輯
2. 確認 `is_internal=True` 是否正確設置
3. 確認 Agent 實例是否正確存儲

### 方案 2: 檢查 Agent Registry

**步驟**:
1. 檢查 `agents/services/registry/registry.py` 中的 `get_agent()` 方法
2. 確認 Agent 實例存儲邏輯
3. 添加調試日誌

### 方案 3: 檢查 Agent 狀態

**步驟**:
1. 檢查 Agent 狀態是否為 `online`
2. 如果狀態檢查過於嚴格，考慮放寬條件
3. 確保 Agent heartbeat 機制正常工作

---

## 測試腳本

### 已創建的測試腳本

1. ✅ `test_agent_result_flow.py` - 6/6 通過（證明流程正確）
2. ⚠️ `test_actual_api_flow.py` - 發現問題：Agent 實例無法獲取
3. `test_messages_structure.py` - 待運行
4. `test_llm_instruction_effectiveness.py` - 待運行

---

## 下一步行動

### 1. 檢查 Agent 註冊和獲取邏輯

**命令**:
```bash
# 檢查 Agent 註冊邏輯
grep -n "is_internal" agents/builtin/__init__.py

# 檢查 Agent Registry 邏輯
grep -n "get_agent\|get_agent_info" agents/services/registry/registry.py
```

### 2. 添加調試日誌

**位置**: `api/routers/chat.py` 第 1823-1850 行

**添加**:
- Agent 信息獲取的詳細日誌
- Agent 實例獲取的詳細日誌
- `is_internal` 檢查的詳細日誌

### 3. 修復 Agent 實例獲取問題

**根據檢查結果**:
- 修復 Agent 註冊邏輯
- 修復 Agent 實例存儲邏輯
- 修復 Agent 狀態檢查邏輯

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
