# LLM 響應為空（EMPTY_RESPONSE）問題定位說明

**最後更新**: 2026-01-28  
**相關測試**: P1 KA-TEST-008（多關鍵詞查詢）等

---

## 1. 錯誤觸發位置

- **文件**: `api/routers/chat.py`
- **函數**: `_process_chat_request`
- **邏輯**: 在構建 `ChatResponse` 前檢查 `content`；若為空則拋出 `HTTPException`，`error_code="EMPTY_RESPONSE"`，`original_error="Content extracted from LLM result is empty"`。
- **代碼位置**: 約 2578–2605 行（`if not content:` 分支）。

---

## 2. 數據流（從 LLM 到 content）

```
moe.chat(...) 
  → client.chat(...)  [llm/moe/moe_manager.py]
    → 各 LLM client（如 llm/clients/ollama.py）返回 dict
  → result 帶 _routing，且應含 content / message / text
  → _extract_content(result)  [api/routers/chat.py]
    → 取 result["content"] 或 result["message"] 或 result["text"]
    → 或 OpenAI 風格 result["choices"][0]["message"]["content"]
  → content 為空則觸發 EMPTY_RESPONSE
```

因此「空」可能來自：

1. **LLM 實際返回空字串**（模型未生成內容、超時、被截斷等）。
2. **Client 返回結構與預期不符**（content 不在 `content`/`message`/`text`，或 key 不同）。
3. **僅有空白**：`_extract_content` 已對頂層內容做 `.strip()`，若只剩空白會當作空。

---

## 3. 已加診斷日誌

### 3.1 Chat 層（api/routers/chat.py）

- **觸發時機**: 當 `content` 為空、即將拋出 `EMPTY_RESPONSE` 時。
- **日誌關鍵字**: `EMPTY_RESPONSE diagnostic`
- **內容**:  
  `request_id`、`result_type`、`result_keys`、`content`/`message` 的類型與長度、`_routing`、`usage`、`result_preview`（前 300 字）。

**如何用**：在日誌中搜 `EMPTY_RESPONSE diagnostic`，看該請求的 `result_keys` 和 `content_type`/`message_type`，判斷是沒有這些 key，還是值為空。

### 3.2 Ollama Client 層（llm/clients/ollama.py）

- **觸發時機**: Ollama `/api/chat` 返回後，若提取出的 `content` 為空。
- **日誌關鍵字**: `Ollama chat returned empty content`
- **內容**:  
  `model`、`response_keys`、`has_message`、`message_keys`、`message_content_type`、`message_content_len`。

**如何用**：若底層是 Ollama，搜 `Ollama chat returned empty content`，看 `response` 是否含 `message`、`message` 裡是否有 `content`，以及長度是否為 0。

---

## 4. 定位步驟建議

1. **復現**  
   用失敗用例（如 KA-TEST-008：「查找關於「API 開發」和「性能優化」的文檔」）打 `POST /api/v2/chat`，觸發一次 EMPTY_RESPONSE。

2. **查 Chat 層日誌**  
   - 搜 `EMPTY_RESPONSE diagnostic`，記下該請求的 `request_id`。  
   - 看 `result_keys` 是否包含 `content`/`message`/`text`。  
   - 看 `content_type`/`message_type` 和對應 `_len`：若為 0，表示上游給的就是空。

3. **查 LLM 層日誌**  
   - 若使用 Ollama：搜 `Ollama chat returned empty content`，對照同一時間或同一請求。  
   - 看 `response_keys`、`message_keys`、`message_content_len`：  
     - 若 `message` 無 `content` 或 `content` 長度為 0，則為 **Ollama 返回空內容**（模型行為、超時、max_tokens 等）。  
     - 若有 content 但 Chat 層仍空，則可能是 **MoE/failover 後結構不同** 或 **其他 client 返回格式不同**。

4. **根據結果處理**  
   - **Ollama 返回空**：檢查模型、超時、max_tokens、該查詢是否易觸發空輸出；必要時換模型或加重試。  
   - **result 無 content/message/text**：檢查 MoE 使用的 client 及 failover 路徑，確認返回格式並在 `_extract_content` 或對應 client 中支援該格式。  
   - **content 為純空白**：已在 `_extract_content` 中 strip，若仍觸發表示上游就是空字串；需回到 LLM/client 層查原因。

---

## 5. _extract_content 支持格式（api/routers/chat.py）

- 頂層：`result["content"]`、`result["message"]`、`result["text"]`（取首個非空並 strip）。
- OpenAI 風格：`result["choices"][0]["message"]["content"]`。
- 若為 `None` 或僅空白，返回 `""`，從而觸發 EMPTY_RESPONSE。

若某 client 使用其他 key（例如 `response`、`output`），需在 `_extract_content` 中增加對應分支，或在該 client 內統一轉成 `content`/`message`/`text` 再返回。
