# AI-Box 重複回應問題診斷指南

**創建日期**: 2026-02-23
**問題描述**: AI 回覆會重複之前的內容，無論用戶輸入什麼

---

## 症狀

| # | 用戶輸入                 | 預期回應          | 實際回應          |
| - | ------------------------ | ----------------- | ----------------- |
| 1 | 查詢ZTLJ002_P的庫存      | ZTLJ002_P 庫存    | ZTLJ002_P 庫存 ✅ |
| 2 | 查詢9GG02701料號的庫存   | 9GG02701 庫存     | ZTLJ002_P 庫存 ❌ |
| 3 | 你好                     | 問候回覆          | ZTLJ002_P 庫存 ❌ |
| 4 | 查詢81105GG00131料號庫存 | 81105GG00131 庫存 | ZTLJ002_P 庫存 ❌ |

---

## 瀏覽器診斷步驟

### 1. 開啟開發者工具

按 **F12** 或 **Ctrl+Shift+I** (Mac: **Cmd+Option+I**)

### 2. 切換到 Network 標籤

### 3. 過濾請求

在左侧 Filter 输入：`/api/v1/chat/`

### 4. 發送測試請求

1. 刷新页面
2. 输入：「查詢ZTLJ002_P的庫存」发送
3. 找到 `/api/v1/chat/stream` 请求，点击

### 5. 檢查 Response

在请求的 **Response** 或 **Preview** 标签中，查看返回内容：

**需要確認的關鍵資訊：**

```
1. session_id 是否每次都一樣？
2. messages 陣列中是否有 user 和 assistant 兩條消息？
3. assistant 的 content 是否正確？
```

---

## Console 診斷命令

在 Console 中粘貼以下命令：

### 查看當前任務的 messages

```javascript
JSON.parse(localStorage.getItem('ai-box-task-' + localStorage.getItem('currentTaskId'))).messages
```

### 查看特定任務的 messages

```javascript
JSON.parse(localStorage.getItem('ai-box-task-1771844445294')).messages
```

### 展開查看 messages 內容

```javascript
JSON.parse(localStorage.getItem('ai-box-task-1771844445294')).messages.map(m => ({role: m.role, content: m.content?.substring(0, 200)}))
```

---

## 需要蒐集的資訊

請按順序完成以下診斷，並記錄結果：

### 診斷 1：確認 session_id

在 Network 中點擊 `/api/v1/chat/stream` 請求

在 **Payload** 或 **Request Payload** 中找到 `session_id`：

```json
{
  "session_id": "xxx-xxx-xxx",
  ...
}
```

**記錄**：第一次的 session_id = __________
**記錄**：第二次的 session_id = __________

### 診斷 2：確認 Response 內容

在 Network 中點擊 `/api/v1/chat/stream` 請求

在 **Response/Preview** 中查看返回的 JSON：

```json
{
  "success": true,
  "data": {
    "messages": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}  // <-- 這裡的內容是什麼？
    ]
  }
}
```

**記錄**：第二次查詢時，assistant 的 content = __________

### 診斷 3：確認 localStorage

在 Console 中運行：

```javascript
JSON.parse(localStorage.getItem('ai-box-task-1771844445294')).messages.map(m => m.role)
```

**記錄**：返回的 role 陣列 = __________

---

## 常見問題原因

| 原因                      | 症狀                     | 解決方案              |
| ------------------------- | ------------------------ | --------------------- |
| **Ollama 緩存**     | 相同 prompt 返回相同結果 | 關閉 `use_cache`    |
| **LLM 緩存**        | 意圖解析結果被緩存       | 禁用 `_llm_cache`   |
| **session_id 問題** | 會話沒有正確隔離         | 檢查 session_id 傳遞  |
| **流式響應問題**    | 響應沒有正確返回         | 檢查 stream 處理      |
| **前端顯示問題**    | 請求正確但顯示錯誤       | 檢查 message 更新邏輯 |

---

## 已執行的修改

### 1. MM-Agent (mm_agent_chain.py)

```python
# 關閉 Ollama 緩存
provider=LLMProvider.OLLAMA, use_cache=False
```

### 2. Data-Agent (parser.py)

```python
# 禁用 LLM 緩存
_llm_cache = None
```

---

## 2026-02-23 最新發現

### 測試結果

通過直接調用 MM-Agent API 測試：

```bash
curl -X POST http://localhost:8003/api/v1/chat/stream ...
```

**結果**：返回了 workflow 步驟，但**沒有返回實際的查詢結果**！

### 問題分析

1. **MM-Agent 返回 workflow 步驟** - 說明意圖分類是正確的
2. **但沒有返回最終結果** - 可能是 chain 執行問題
3. **後端返回重複響應** - 不是前端緩存問題

### 已確認的事實

| 測試                     | 結果        |
| ------------------------ | ----------- |
| 關閉 Ollama 緩存         | ✅ 已完成   |
| 禁用 Data-Agent LLM 緩存 | ✅ 已完成   |
| session_id 傳遞          | ✅ 正確     |
| messages 包含歷史        | ✅ 正確     |
| 後端返回錯誤響應         | ❌ 問題在此 |

### 下一步

需要檢查：

1. MM-Agent chain 執行邏輯
2. React Executor 是否正確執行步驟
3. 為什麼沒有返回最終結果

---

## 2026-02-23 診斷 - 全新 Session 測試

### 測試方法

在瀏覽器 Console 中粘貼以下代碼：

```javascript
// 發送一個全新的查詢（使用全新 session_id）
fetch('https://iee.sunlyc.com/api/v1/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    agent_id: "-h0tjyh",
    session_id: "test-" + Date.now(),  // 全新 session_id
    task_id: "test-" + Date.now(),
    messages: [{"role": "user", "content": "你好"}],
    instruction: "你好"  // 添加 instruction 字段
  })
}).then(r => r.text()).then(console.log)
```

### 預期結果

- 返回問候語回覆（如「你好！請問有什麼可以幫您？」）

### 測試不同內容

```javascript
// 測試庫存查詢
fetch('https://iee.sunlyc.com/api/v1/chat/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    agent_id: "-h0tjyh",
    session_id: "test-inv-" + Date.now(),
    task_id: "test-inv-" + Date.now(),
    model_id: "Olllama-Local",
    model_selector: {"mode": "manual", "model_id": "Ollama-Local"},
    messages: [{"role": "user", "content": "查詢ZPLJ002PX_2A料號的庫存"}],
    instruction: "查詢ZPLJ002PX_2A料號的庫存"
  })
}).then(r => r.text()).then(console.log)
```

### 需要記錄的結果

1. 測試「你好」的返回內容
2. 測試庫存查詢的返回內容
3. 兩次測試的返回是否正確不同

---

**文檔版本**: v1.2
**最後更新**: 2026-02-23
