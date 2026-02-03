# 根本原因分析報告

**日期**: 2026-01-28
**問題**: LLM 返回拒絕性回答，即使 Agent 執行成功

---

## 關鍵發現

### ✅ Agent 執行成功

從 `logs/agent.log` 可以看到：

1. **KA-Agent 被正確觸發**：
   ```
   Decision Engine: Knowledge query detected, selected KA-Agent: ka-agent (score: 0.66)
   ```

2. **KA-Agent 執行成功**：
   ```
   [KA-Agent] ✅ 流程執行完成: task_id=chat_92cb0d80-2a4f-4de5-8aa7-843d708964ad, 
   category=RETRIEVAL, success=True, flow_latency_ms=118, total_latency_ms=1590, result_count=10
   ```

3. **找到 5 個文件**：
   ```
   [KA-Agent] 📊 文件過濾結果: task_id=chat_92cb0d80-2a4f-4de5-8aa7-843d708964ad, 
   total_files=5, domain=None, major=None
   ```

4. **檢索到 10 個結果**：
   ```
   [KA-Agent] ✅ 檢索流程完成: task_id=chat_92cb0d80-2a4f-4de5-8aa7-843d708964ad, 
   final_results_count=10, rerank_latency_ms=0, retrieval_total_latency_ms=118
   ```

### ⚠️ 問題：Agent 結果可能沒有正確傳遞給 LLM

從代碼分析：

1. **Agent 結果被添加到 `agent_tool_results`**（第 1911-1917 行）：
   ```python
   agent_tool_results.append({
       "tool_name": "agent_execute",
       "result": agent_response.result,
       "message": agent_result_message,
   })
   ```

2. **`messages_for_llm` 的構建邏輯**（第 2140-2147 行）：
   ```python
   base_system = system_messages[:1] if system_messages else []
   messages_for_llm = base_system + memory_result.injection_messages + windowed_history
   ```

3. **問題**：`agent_tool_results` 中的 Agent 結果**沒有被添加到 `messages_for_llm`**！

---

## 根本原因

### 問題 1: Agent 結果沒有注入到 `messages_for_llm`

**位置**: `api/routers/chat.py` 第 2140-2147 行

**當前代碼**:
```python
base_system = system_messages[:1] if system_messages else []
messages_for_llm = base_system + memory_result.injection_messages + windowed_history
```

**問題**:
- `agent_tool_results` 被收集了，但沒有被添加到 `messages_for_llm`
- LLM 沒有收到 Agent 執行結果
- LLM 只能基於自己的訓練數據回答，因此返回拒絕性回答

**預期行為**:
- Agent 結果應該被格式化後添加到 `messages_for_llm` 的開頭（作為 system message）
- 這樣 LLM 才能基於 Agent 結果生成正確的回答

---

## 解決方案

### 修復步驟

1. **在構建 `messages_for_llm` 時，添加 Agent 結果**：

   ```python
   # 構建 messages_for_llm
   base_system = system_messages[:1] if system_messages else []
   
   # 添加 Agent 執行結果（如果有的話）
   agent_result_messages = []
   if agent_tool_results:
       for tool_result in agent_tool_results:
           if "message" in tool_result:
               agent_result_messages.append(tool_result["message"])
   
   messages_for_llm = (
       base_system 
       + agent_result_messages  # 添加 Agent 結果
       + memory_result.injection_messages 
       + windowed_history
   )
   ```

2. **確保 Agent 結果在正確的位置**：
   - Agent 結果應該在 system messages 之後、memory injection 之前
   - 這樣 LLM 能夠優先看到 Agent 執行結果

---

## 驗證步驟

修復後，需要驗證：

1. **Agent 結果是否被添加到 `messages_for_llm`**：
   - 檢查日誌中的 `messages_count`
   - 確認 Agent 結果消息存在

2. **LLM 是否收到 Agent 結果**：
   - 檢查 LLM 響應是否包含文件數量信息
   - 確認不再返回拒絕性回答

3. **API 端點是否正常響應**：
   - 運行 `test_chat_api_endpoint.py`
   - 確認返回 200 狀態碼

---

## 相關代碼位置

- **Agent 結果收集**: `api/routers/chat.py` 第 1897-1927 行
- **`messages_for_llm` 構建**: `api/routers/chat.py` 第 2140-2147 行
- **Agent 結果格式化**: `api/routers/chat.py` 第 482-548 行（`_format_agent_result_for_llm` 函數）

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
