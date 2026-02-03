# 修復總結

**日期**: 2026-01-28
**問題**: LLM 返回拒絕性回答，即使 Agent 執行成功

---

## 根本原因

從代碼分析和日誌檢查發現：

1. ✅ **Agent 執行成功**：KA-Agent 正確執行並返回結果（5 個文件，10 個檢索結果）
2. ✅ **Agent 結果已添加到 `messages_for_llm`**：代碼第 2168-2171 行已實現
3. ⚠️ **問題**：Agent 結果的格式化或傳遞可能有問題

---

## 已實施的修復

### 1. 增強 Agent 結果處理邏輯

**位置**: `api/routers/chat.py` 第 1897-1922 行

**修改內容**:
- 添加了對 `agent_response.result` 類型的檢查
- 確保結果是字典格式（`model_dump()` 的結果）
- 添加了詳細的調試日誌

**代碼**:
```python
# 注意：agent_response.result 已經是 model_dump() 的結果（字典）
agent_result_dict = agent_response.result
if not isinstance(agent_result_dict, dict):
    # 如果是其他類型，嘗試轉換
    if hasattr(agent_result_dict, "model_dump"):
        agent_result_dict = agent_result_dict.model_dump()
    else:
        agent_result_dict = {"success": False, "error": "Invalid result format"}

agent_result_text = _format_agent_result_for_llm(
    agent_id=chosen_agent_id,
    agent_result=agent_result_dict,
)

logger.debug(
    f"Agent result formatted: agent_id={chosen_agent_id}, "
    f"result_type={type(agent_response.result)}, "
    f"formatted_length={len(agent_result_text)}, "
    f"result_keys={list(agent_result_dict.keys()) if isinstance(agent_result_dict, dict) else 'N/A'}"
)
```

### 2. 增強 Agent 結果注入日誌

**位置**: `api/routers/chat.py` 第 2168-2182 行

**修改內容**:
- 添加了詳細的日誌，記錄 Agent 結果的注入過程
- 記錄 `messages_for_llm` 的數量變化
- 記錄每個 Agent 結果消息的內容長度

**代碼**:
```python
# 將 Agent 工具結果消息插入到 messages_for_llm 開頭（優先級最高）
if agent_tool_results:
    logger.info(
        f"Adding {len(agent_tool_results)} agent tool results to messages_for_llm: "
        f"request_id={request_id}"
    )
    for tool_result_item in agent_tool_results:
        if "message" in tool_result_item:
            messages_for_llm.insert(0, tool_result_item["message"])
            logger.debug(
                f"Agent tool result message added: "
                f"role={tool_result_item['message'].get('role')}, "
                f"content_length={len(tool_result_item['message'].get('content', ''))}"
            )
    logger.info(
        f"messages_for_llm after adding agent results: count={len(messages_for_llm)}, "
        f"request_id={request_id}"
    )
```

---

## 預期效果

修復後，應該能夠：

1. **正確處理 Agent 結果**：
   - 確保 Agent 結果是字典格式
   - 正確格式化為 LLM 友好的格式
   - 包含文件數量信息（5 個文件）

2. **正確注入到 LLM 上下文**：
   - Agent 結果被添加到 `messages_for_llm` 的開頭
   - LLM 能夠看到 Agent 執行結果
   - LLM 能夠基於 Agent 結果生成正確的回答

3. **詳細的日誌追蹤**：
   - 記錄 Agent 結果的格式化過程
   - 記錄 Agent 結果的注入過程
   - 方便問題定位和調試

---

## 驗證步驟

修復後，需要驗證：

1. **重啟 FastAPI 服務**：
   ```bash
   # 確保修改生效
   ```

2. **運行測試**：
   ```bash
   python3 test_chat_api_endpoint.py
   ```

3. **檢查日誌**：
   - 查看 `logs/fastapi.log` 中的 Agent 結果格式化日誌
   - 查看 `logs/fastapi.log` 中的 Agent 結果注入日誌
   - 確認 `messages_for_llm` 包含 Agent 結果

4. **驗證 LLM 響應**：
   - LLM 應該能夠回答文件數量（5 個文件）
   - LLM 不應該返回拒絕性回答

---

## 下一步

1. **重啟 FastAPI 服務**
2. **運行測試腳本驗證修復**
3. **檢查日誌確認 Agent 結果正確傳遞**
4. **如果問題仍然存在，進一步調查 LLM 響應生成邏輯**

---

**報告版本**: v1.0
**生成時間**: 2026-01-28
