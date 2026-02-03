# LLM 響應為空（EMPTY_RESPONSE）診斷結果

**診斷時間**: 2026-01-28 17:32-17:34  
**測試用例**: KA-TEST-010, KA-TEST-020  
**相關測試**: KA-TEST-008（本次通過）

---

## 🔍 診斷發現

### 1. 問題定位

從日誌 `logs/fastapi.log` 中發現：

```
2026-01-28 17:32:58 - llm.clients.ollama - WARNING - Ollama chat returned empty content: 
model=gpt-oss:20b, 
response_keys=['model', 'created_at', 'message', 'done', 'done_reason', 'total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration'], 
has_message=True, 
message_keys=['role', 'content', 'thinking', 'tool_calls'], 
message_content_type=str, 
message_content_len=0
```

### 2. 關鍵信息

| 項目 | 值 | 說明 |
|------|-----|------|
| **模型** | `gpt-oss:20b` | 使用的 Ollama 模型 |
| **Response 結構** | ✅ 完整 | Ollama 返回了完整的 response，包含 `message` 對象 |
| **Message 結構** | ✅ 完整 | `message` 包含 `role`, `content`, `thinking`, `tool_calls` |
| **Content 長度** | **0** | `message_content_len=0`，即 `content` 為空字串 `""` |
| **特殊字段** | `thinking`, `tool_calls` | 模型可能使用了 thinking 模式或 tool calling |

### 3. 問題分析

**根本原因**：Ollama 模型 `gpt-oss:20b` 在某些查詢下返回的 `message.content` 為空字串，但同時返回了 `thinking` 和 `tool_calls` 字段。

**可能原因**：
1. **Tool Calling 模式**：模型使用了 tool calling，只返回了 `tool_calls`，沒有返回 `content` 文本
2. **Thinking 模式**：模型使用了 thinking 模式，將內容放在 `thinking` 字段，`content` 為空
3. **模型行為**：某些查詢下，模型確實沒有生成文本內容（可能是模型本身的限制或配置問題）

---

## 📋 診斷日誌分析

### Ollama Client 層日誌（已記錄）

✅ **已記錄**：`llm.clients.ollama` 在 content 為空時記錄了詳細信息：
- Response 結構（keys）
- Message 結構（keys）
- Content 類型與長度

### Chat 層日誌（未找到）

❌ **未找到**：`api.routers.chat` 中的 `EMPTY_RESPONSE diagnostic` 日誌未出現在日誌文件中。

**可能原因**：
- 日誌級別設置（ERROR 級別可能被過濾）
- 日誌尚未刷新到文件
- 異常在到達該檢查點前已被處理

---

## 💡 解決方案建議

### 方案 1：從 `thinking` 字段提取內容（✅ 已實施）

已在 `llm/clients/ollama.py` 的 `chat` 方法中實施：
- 優先使用 `message.content`；若為空則從 `message.thinking` 提取（字串或 list/dict 轉字串）
- 使用 thinking 時會記錄 INFO 日誌：`Ollama chat: content empty, using thinking as fallback`
- 僅當 content 與 thinking 均無有效內容時才記錄 WARNING 診斷日誌

### 方案 2：處理 Tool Calling

如果模型返回了 `tool_calls` 但沒有 `content`，可以：
- 提取 tool_calls 信息並格式化為文本
- 或記錄 tool_calls 並返回友好的提示消息

### 方案 3：模型配置調整

檢查 `gpt-oss:20b` 模型的配置：
- 是否啟用了 tool calling 或 thinking 模式
- 是否可以調整參數以確保返回 `content`

### 方案 4：Fallback 到其他模型

當檢測到空內容時，自動 fallback 到其他可用的模型。

---

## 🔧 下一步行動

1. ~~**增強內容提取邏輯**~~：✅ 已實施方案 1（從 thinking 提取）
2. **驗證修復**：重啟 API 後運行 P1 測試進行比較（見下方「測試比較」）
3. 可選：檢查 Ollama 模型配置、或實施方案 2（tool_calls）若仍出現空響應

---

## 📊 測試結果對比（修復前）

| 測試用例 | 修復前結果 | 說明 |
|---------|-----------|------|
| KA-TEST-008 | ❌→✅ 間歇 | 多關鍵詞查詢，曾失敗（EMPTY_RESPONSE） |
| KA-TEST-010 | ❌ 失敗 | 技術領域查詢，Ollama content 空、有 thinking |
| KA-TEST-020 | ❌ 失敗 | 系統錯誤處理，Ollama content 空、有 thinking |

---

## 📋 方案 1 實施後：測試比較說明

**實施內容**：`llm/clients/ollama.py` 中當 `message.content` 為空時，從 `message.thinking` 提取內容作為 fallback。

**如何比較**：

1. **重啟 API** 以載入新代碼。
2. **運行完整 P1 測試**：
   ```bash
   python3 docs/系统设计文档/核心组件/Agent平台/KA-Agent/測試/代碼/test_p1_chat_module_with_auth.py
   ```
3. **或僅運行 EMPTY_RESPONSE 相關用例**（KA-TEST-008 / 010 / 020）：
   ```bash
   EMPTY_RESPONSE_ONLY=1 python3 docs/系统设计文档/核心组件/Agent平台/KA-Agent/測試/代碼/test_p1_chat_module_with_auth.py
   ```
4. **對比**：
   - 修復前：KA-TEST-010、KA-TEST-020 常因 EMPTY_RESPONSE 失敗。
   - 修復後：若模型有返回 `thinking`，應改為通過；日誌中可見 `using thinking as fallback`。

**預期**：曾因 `content` 為空但 `thinking` 有值的請求，改為使用 thinking 作為回應內容，EMPTY_RESPONSE 應減少或消失。

---

## 📊 方案 1 實施後測試比較（2026-01-28 17:41）

**執行**：完整 P1 測試（9 用例），端點 `/api/v2/chat`。

| 項目 | 修復前（參考） | 方案 1 實施後（本次） |
|------|----------------|----------------------|
| **總數** | 9 | 9 |
| **通過** | 8（第 2 輪）/ 2（第 1 輪） | **5** |
| **失敗** | 1 / 7 | **4** |
| **通過率** | 88.9% / 22.2% | **55.6%** |

**本次失敗用例**（均為 EMPTY_RESPONSE）：
- KA-TEST-008（多關鍵詞查詢）
- KA-TEST-010（技術領域查詢）
- KA-TEST-017（未找到結果）
- KA-TEST-020（系統錯誤處理）

**說明**：
- 日誌中未出現 `using thinking as fallback`，表示本次失敗請求可能未走 Ollama，或 Ollama 返回的 `thinking` 也為空。
- 可能原因：MoE 路由選了其他 provider（如 Qwen），該 provider 返回空 content 且無 thinking 欄位；或 Ollama 在部分請求中 content 與 thinking 皆空。
- **建議**：對失敗請求在日誌中確認 `_routing.provider`，若多為非 Ollama，可考慮在 chat 層對空 content 做統一 fallback（例如重試或替換為友好提示）。

---

**診斷完成時間**: 2026-01-28 17:35 UTC+8  
**方案 1 實施時間**: 2026-01-28 17:40 UTC+8  
**方案 1 實施後測試**: 2026-01-28 17:41 UTC+8
