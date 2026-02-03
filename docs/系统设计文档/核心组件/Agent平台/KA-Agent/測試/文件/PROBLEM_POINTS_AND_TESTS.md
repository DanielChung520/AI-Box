# 問題點定義與獨立測試計劃

**日期**: 2026-01-28
**目標**: 定義可能的問題點，並創建獨立測試腳本逐一驗證

---

## 可能的問題點

### 問題點 1: Agent 結果格式不正確 ⚠️

**描述**: Agent 返回的結果格式可能不符合預期

**可能原因**:
- `agent_response.result` 不是字典格式
- 缺少必需的字段（`success`, `results`, `total`, `metadata`）
- `metadata.file_count` 不存在或為 0

**測試腳本**: `test_agent_result_flow.py` - 測試 1

**驗證方法**:
- 檢查 Agent 結果的類型
- 檢查必需字段是否存在
- 檢查文件數量是否正確

---

### 問題點 2: Agent 結果格式化失敗 ⚠️

**描述**: `_format_agent_result_for_llm` 函數可能無法正確格式化 Agent 結果

**可能原因**:
- Agent 結果格式不符合預期
- 格式化邏輯有 bug
- 缺少關鍵信息（文件數量、檢索結果等）

**測試腳本**: `test_agent_result_flow.py` - 測試 2

**驗證方法**:
- 調用 `_format_agent_result_for_llm` 函數
- 檢查格式化結果是否包含文件數量
- 檢查格式化結果是否包含重要指令

---

### 問題點 3: Agent 結果消息構建失敗 ⚠️

**描述**: Agent 結果消息（`agent_result_message`）可能構建不正確

**可能原因**:
- 消息格式不正確（缺少 `role` 或 `content`）
- 消息內容為空
- 消息結構不符合 LLM 的期望

**測試腳本**: `test_agent_result_flow.py` - 測試 3

**驗證方法**:
- 檢查消息的 `role` 是否為 `system`
- 檢查消息的 `content` 是否不為空
- 檢查消息內容是否包含 Agent 結果

---

### 問題點 4: Agent 結果沒有注入到 messages_for_llm ⚠️⚠️ 關鍵問題

**描述**: Agent 結果可能沒有被正確添加到 `messages_for_llm`

**可能原因**:
- `agent_tool_results` 為空
- `agent_tool_results` 中的消息格式不正確
- `messages_for_llm.insert(0, ...)` 沒有執行
- Agent 結果被其他消息覆蓋

**測試腳本**: 
- `test_agent_result_flow.py` - 測試 4
- `test_messages_structure.py` - 完整流程測試

**驗證方法**:
- 檢查 `messages_for_llm` 的第一個消息是否是 Agent 結果
- 檢查 `messages_for_llm` 的數量是否正確
- 檢查 Agent 結果是否在用戶消息之前

---

### 問題點 5: messages_for_llm 結構不正確 ⚠️⚠️ 關鍵問題

**描述**: `messages_for_llm` 的最終結構可能不符合 LLM 的期望

**可能原因**:
- 消息順序不正確（Agent 結果不在最前面）
- 消息格式不正確（缺少 `role` 或 `content`）
- 消息內容被截斷或損壞

**測試腳本**: `test_messages_structure.py`

**驗證方法**:
- 檢查 `messages_for_llm` 的完整結構
- 檢查每個消息的格式
- 檢查消息的順序
- 保存 `messages_for_llm` 到文件進行詳細分析

---

### 問題點 6: LLM 指令無效 ⚠️⚠️ 關鍵問題

**描述**: LLM 可能沒有正確理解或遵守 Agent 結果中的指令

**可能原因**:
- 指令格式不夠明確
- 指令不夠強烈
- LLM 模型本身的限制（安全策略、訓練數據等）
- 指令被其他消息覆蓋或忽略

**測試腳本**: `test_llm_instruction_effectiveness.py`

**驗證方法**:
- 測試不同的指令格式
- 對比有指令 vs 無指令的響應
- 找出最有效的指令格式

---

### 問題點 7: LLM 響應生成失敗 ⚠️

**描述**: LLM 可能無法正確生成響應，即使收到了 Agent 結果

**可能原因**:
- `moe.chat` 調用失敗
- LLM 返回的響應格式不正確
- 響應內容提取失敗

**測試腳本**: `test_agent_result_flow.py` - 測試 5

**驗證方法**:
- 檢查 `moe.chat` 是否成功調用
- 檢查響應是否包含文件數量
- 檢查響應是否包含拒絕性回答

---

## 測試腳本列表

### 1. `test_agent_result_flow.py` - 完整流程測試

**功能**: 測試 Agent 結果流程的各個環節

**測試內容**:
- 測試 1: Agent 結果格式驗證
- 測試 2: Agent 結果格式化
- 測試 3: Agent 結果消息構建
- 測試 4: messages_for_llm 構建
- 測試 5: LLM 響應生成（帶 Agent 結果）
- 測試 6: 對比（有 Agent 結果 vs 無 Agent 結果）

**使用方法**:
```bash
python3 test_agent_result_flow.py
```

---

### 2. `test_messages_structure.py` - messages_for_llm 結構測試

**功能**: 測試 messages_for_llm 的實際結構（使用真實的 Agent 執行）

**測試內容**:
- 執行真實的 KA-Agent
- 格式化 Agent 結果
- 構建 messages_for_llm
- 詳細檢查 messages_for_llm 結構
- 保存結果到文件

**使用方法**:
```bash
python3 test_messages_structure.py
```

**輸出**: `logs/test_messages_structure.json`

---

### 3. `test_llm_instruction_effectiveness.py` - LLM 指令有效性測試

**功能**: 測試不同指令格式的有效性

**測試內容**:
- 格式 1: 當前格式（帶有「重要指令」）
- 格式 2: 更強烈的指令格式
- 格式 3: 簡化的指令格式
- 格式 4: 無指令格式（對照組）

**使用方法**:
```bash
python3 test_llm_instruction_effectiveness.py
```

---

## 測試執行順序

### 推薦順序

1. **第一步**: 運行 `test_agent_result_flow.py`
   - 快速驗證各個環節是否正常
   - 找出第一個失敗的測試

2. **第二步**: 運行 `test_messages_structure.py`
   - 使用真實的 Agent 執行
   - 檢查實際的 messages_for_llm 結構
   - 保存結果用於詳細分析

3. **第三步**: 運行 `test_llm_instruction_effectiveness.py`
   - 如果前兩步都通過，但 LLM 仍然返回拒絕性回答
   - 測試不同的指令格式
   - 找出最有效的格式

---

## 問題定位流程

### 流程圖

```
開始
  ↓
運行 test_agent_result_flow.py
  ↓
所有測試通過？
  ├─ 是 → 運行 test_messages_structure.py
  │        ↓
  │      結構正確？
  │        ├─ 是 → 運行 test_llm_instruction_effectiveness.py
  │        │        ↓
  │        │       找到有效格式？
  │        │        ├─ 是 → 更新指令格式
  │        │        └─ 否 → 檢查 LLM 模型限制
  │        │
  │        └─ 否 → 修復 messages_for_llm 構建邏輯
  │
  └─ 否 → 修復第一個失敗的測試對應的問題
```

---

## 預期結果

### 如果所有測試通過

**說明**: Agent 結果流程正常，問題可能在：
- LLM 模型本身的限制
- 指令格式需要優化
- 需要更強烈的指令

**解決方案**:
- 使用 `test_llm_instruction_effectiveness.py` 找出最有效的指令格式
- 更新 `_format_agent_result_for_llm` 函數使用最有效的格式

### 如果測試失敗

**說明**: 找到了具體的問題點

**解決方案**:
- 根據失敗的測試，修復對應的問題
- 重新運行測試驗證修復

---

## 測試報告

測試完成後，會生成以下報告：
- `test_agent_result_flow.py` 的輸出（控制台）
- `logs/test_messages_structure.json`（messages_for_llm 結構）
- `test_llm_instruction_effectiveness.py` 的輸出（控制台）

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
