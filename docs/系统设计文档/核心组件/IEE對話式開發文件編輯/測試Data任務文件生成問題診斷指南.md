# 測試Data任務文件生成問題診斷指南

**版本**: 1.0
**創建日期**: 2026-01-06
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-06

---

## 📋 問題描述

「測試Data任務」最近2輪對話中，用戶已指示生成文件，但系統仍然返回一般對話回復，沒有觸發文件創建。

---

## 🔍 診斷步驟

### Step 1: 檢查任務對話記錄

#### 方法 1: 通過前端界面檢查

1. 打開前端應用
2. 找到「測試Data任務」
3. 查看最近2輪對話：
   - 用戶消息內容
   - AI 回復內容
   - 時間戳

#### 方法 2: 通過 API 查詢任務

```bash
# 查詢任務列表
curl -X GET "https://iee.k84.org/api/v1/user-tasks?limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查找任務 ID（假設為 1767704748805）
# 查看任務詳情（包含 messages）
curl -X GET "https://iee.k84.org/api/v1/user-tasks/1767704748805" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 方法 3: 直接查詢 ArangoDB

```python
from database.arangodb import ArangoDBClient
from services.api.services.user_task_service import get_user_task_service

# 查詢任務
service = get_user_task_service()
task = service.get(user_id="daniel@test.com", task_id="1767704748805")

# 查看消息
if task and task.messages:
    print(f"總消息數：{len(task.messages)}")
    print("\n最後2輪對話：")
    for msg in task.messages[-4:]:  # 最後4條消息（2輪對話）
        print(f"\n[{msg.sender}] {msg.timestamp}")
        print(msg.content[:200])
```

---

### Step 2: 檢查後端日誌

#### 關鍵日誌關鍵字

在後端日誌中查找以下關鍵字，按時間順序檢查：

**1. 接收請求和工具配置**

```bash
grep "chat_request_tools_received\|chat_request_tools" logs/app.log | tail -10
```

**預期日誌**:

```
chat_request_tools_received: {
  "allowed_tools": ["document_editing", ...],  # ✅ 應該包含 document_editing
  "has_web_search": false,
  "allowed_tools_count": 1
}
```

**如果 `allowed_tools` 為空或不包含 `document_editing`**:

- ❌ 問題：前端未正確傳遞 Assistant 的 `allowedTools`
- ✅ 解決：確認 Assistant 已啟用「文件編輯」功能，並檢查前端代碼修復是否生效

---

**2. Task Analyzer 調用**

```bash
grep "task_analyzer_result_assigned\|task_analyzer.*analyze" logs/app.log | tail -10
```

**預期日誌**:

```
task_analyzer_result_assigned: {
  "has_task_analyzer_result": true,
  "has_decision_result": true,
  ...
}
```

**如果 `has_task_analyzer_result=false`**:

- ❌ 問題：Task Analyzer 未返回結果
- ✅ 解決：檢查 Task Analyzer 的錯誤日誌

---

**3. Router LLM 判斷**

```bash
grep "Router LLM: Router decision\|RouterDecision\|router_decision" logs/app.log | tail -10
```

**預期日誌**:

```
Router LLM: Router decision: {
  "intent_type": "execution",  # ✅ 應該是 "execution"
  "needs_tools": true,  # ✅ 應該是 true
  "needs_agent": false,
  "confidence": 0.85,  # ✅ 應該 >= 0.6
  ...
}
```

**如果 `needs_tools=false`**:

- ❌ 問題：Router LLM 未識別文件生成意圖
- ✅ 解決：
  - 檢查用戶指令是否明確表達文件生成意圖
  - 使用更明確的指令，如「生成文件」、「幫我產生Data Agent文件」
  - 檢查 Router LLM 的 System Prompt 是否包含文件生成示例

**如果 `intent_type` 不是 "execution"**:

- ❌ 問題：Router LLM 將意圖分類為其他類型（如 "conversation"）
- ✅ 解決：使用更明確的執行類指令

**如果 `confidence < 0.6`**:

- ❌ 問題：Router LLM 信心度太低，可能使用 Safe Fallback
- ✅ 解決：使用更明確的指令

---

**4. Capability Matcher 匹配**

```bash
grep "Matched tools for router decision\|document_editing.*match\|has_file_editing_enabled" logs/app.log | tail -10
```

**預期日誌**:

```
Matched tools for router decision: {
  "tool_name": "document_editing",
  "name_category_match": 1.0,  # ✅ 應該是 1.0（完美匹配）
  "total_score": 0.95,  # ✅ 應該 >= 0.5
  ...
}
```

**如果未匹配到 `document_editing`**:

- ❌ 問題：Capability Matcher 未匹配到文件編輯工具
- ✅ 解決：
  - 檢查 `has_file_editing_enabled` 是否為 `True`
  - 檢查 `allowed_tools` 是否包含 `document_editing`
  - 檢查 Router LLM 的 `needs_tools` 和 `intent_type`

---

**5. Decision Engine 選擇**

```bash
grep "Decision Engine: Selected tool\|chosen_tools.*document_editing" logs/app.log | tail -10
```

**預期日誌**:

```
Decision Engine: Selected tool: document_editing (score: 0.95)
```

**如果未選擇 `document_editing`**:

- ❌ 問題：Decision Engine 未選擇文件編輯工具
- ✅ 解決：
  - 檢查工具評分是否 >= 0.5
  - 檢查是否有其他工具評分更高

---

**6. System Prompt 增強**

```bash
grep "document_generation_intent_detected_via_task_analyzer" logs/app.log | tail -10
```

**預期日誌**:

```
document_generation_intent_detected_via_task_analyzer: {
  "user_text": "...",
  "filename": "...",
  "chosen_tools": ["document_editing"],
  ...
}
```

**如果未增強 System Prompt**:

- ❌ 問題：System Prompt 未被增強
- ✅ 解決：檢查 `chosen_tools` 是否包含 `document_editing`

---

**7. 文件創建檢查**

```bash
grep "checking_file_creation_intent\|document_editing_tool_detected_for_file_creation\|file_created_from_stream\|file_creation_returned_none" logs/app.log | tail -20
```

**預期日誌**:

```
checking_file_creation_intent: {
  "has_task_analyzer_result": true,
  "task_id": "1767704748805",
  ...
}

document_editing_tool_detected_for_file_creation: {
  "chosen_tools": ["document_editing"],
  "note": "Attempting to create file",
  ...
}

file_created_from_stream: {
  "file_id": "...",
  "filename": "...",
  ...
}
```

**如果看到 `file_creation_returned_none`**:

- ❌ 問題：文件創建函數返回 `None`
- ✅ 解決：檢查以下日誌：
  - `try_create_file_no_task_id` - task_id 為空
  - `try_create_file_invalid_extension` - 文件擴展名不支持
  - `try_create_file_permission_check_failed` - 權限檢查失敗
  - `try_create_file_storage_save_failed` - 存儲保存失敗
  - `try_create_file_metadata_creation_failed` - 元數據創建失敗

---

### Step 3: 檢查 Assistant 配置

#### 方法 1: 通過前端界面檢查

1. 打開 Assistant 維護界面
2. 找到「測試Data任務」使用的 Assistant
3. 檢查「資源配置」標籤：
   - ✅ 「啟用文件編輯」是否勾選
   - ✅ 「可使用的工具類別」是否包含文件編輯相關類別

#### 方法 2: 通過 API 查詢

```bash
# 查詢 Assistant 配置
curl -X GET "https://iee.k84.org/api/v1/assistants/{assistant_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**檢查項目**:

- `allowedTools` 是否包含 `document_editing`
- `enableFileEditing` 是否為 `true`

---

### Step 4: 檢查前端傳遞的 `allowedTools`

#### 方法 1: 檢查瀏覽器控制台

打開瀏覽器開發者工具（F12），查看 Console 日誌：

```javascript
// 應該看到：
[ChatInput] 📤 Sending message with tools: {
  allowedTools: ["document_editing", ...],  // ✅ 應該包含 document_editing
  ...
}

[Home] Calling chatProductStream with tools: {
  allowedTools: ["document_editing", ...],  // ✅ 應該包含 document_editing
  ...
}
```

#### 方法 2: 檢查 Network 請求

1. 打開瀏覽器開發者工具（F12）
2. 切換到「Network」標籤
3. 發送一條消息
4. 找到 `/api/v1/chat/stream` 請求
5. 查看「Payload」或「Request」：
   - `allowed_tools` 是否包含 `document_editing`

---

## 🐛 常見問題與解決方案

### 問題 1: `allowed_tools` 為空或不包含 `document_editing`

**原因**:

- Assistant 未啟用「文件編輯」功能
- 前端未正確傳遞 `allowedTools`

**解決方案**:

1. ✅ 確認 Assistant 已啟用「文件編輯」功能
2. ✅ 確認前端代碼修復已生效（重新編譯前端）
3. ✅ 清除瀏覽器緩存並刷新頁面
4. ✅ 檢查 `localStorage` 中是否有 Assistant 的 `allowedTools` 配置

---

### 問題 2: Router LLM 判斷 `needs_tools=false`

**原因**:

- 用戶指令不夠明確
- Router LLM 的 System Prompt 缺少相關示例

**解決方案**:

1. ✅ 使用更明確的指令：
   - 「生成文件」
   - 「幫我產生Data Agent文件」
   - 「生成 Data Agent.md 文件」
2. ✅ 檢查 Router LLM 的 System Prompt 是否包含文件生成示例
3. ✅ 檢查 Router LLM 的 `confidence` 是否 >= 0.6

---

### 問題 3: Capability Matcher 未匹配到 `document_editing`

**原因**:

- `has_file_editing_enabled=False`
- Router LLM 的 `intent_type` 不是 `"execution"`
- Router LLM 的 `needs_tools=False`

**解決方案**:

1. ✅ 確認 Assistant 已啟用「文件編輯」功能
2. ✅ 確認 Router LLM 判斷 `needs_tools=True` 和 `intent_type="execution"`
3. ✅ 檢查 `allowed_tools` 是否正確傳遞給 Task Analyzer

---

### 問題 4: Decision Engine 未選擇 `document_editing`

**原因**:

- 工具評分 < 0.5
- 有其他工具評分更高

**解決方案**:

1. ✅ 檢查工具評分是否 >= 0.5
2. ✅ 檢查是否有其他工具被優先選擇

---

### 問題 5: 文件創建函數返回 `None`

**原因**:

- `task_id` 為空
- 文件擴展名不支持
- 權限檢查失敗
- 存儲保存失敗

**解決方案**:

1. ✅ 確認 `task_id` 不為空
2. ✅ 確認文件擴展名為 `.md`, `.txt`, `.json`
3. ✅ 確認用戶有文件上傳權限
4. ✅ 檢查存儲服務是否正常

---

## 📊 完整診斷檢查清單

請按順序檢查以下項目：

### 前端檢查

- [ ] Assistant 已啟用「文件編輯」功能
- [ ] 瀏覽器控制台顯示 `allowedTools` 包含 `document_editing`
- [ ] Network 請求中 `allowed_tools` 包含 `document_editing`
- [ ] 用戶消息明確表達文件生成意圖

### 後端檢查

- [ ] 日誌顯示 `chat_request_tools_received` 且 `allowed_tools` 包含 `document_editing`
- [ ] 日誌顯示 `task_analyzer_result_assigned` 且 `has_task_analyzer_result=true`
- [ ] 日誌顯示 Router LLM 判斷 `needs_tools=true`, `intent_type="execution"`, `confidence >= 0.6`
- [ ] 日誌顯示 Capability Matcher 匹配到 `document_editing` 工具（評分 >= 0.5）
- [ ] 日誌顯示 Decision Engine 選擇了 `document_editing` 工具
- [ ] 日誌顯示 System Prompt 被增強（`document_generation_intent_detected_via_task_analyzer`）
- [ ] 日誌顯示文件創建檢查（`checking_file_creation_intent`）
- [ ] 日誌顯示文件創建成功（`file_created_from_stream`）或失敗原因

---

## 🔧 快速診斷命令

### 檢查最近的文件創建相關日誌

```bash
# 查找所有文件創建相關日誌
grep -E "checking_file_creation_intent|document_editing_tool_detected|file_created_from_stream|file_creation_returned_none|try_create_file" logs/app.log | tail -50

# 查找 Task Analyzer 相關日誌
grep -E "task_analyzer|Router LLM|Decision Engine|Capability Matcher" logs/app.log | tail -50

# 查找 allowed_tools 相關日誌
grep -E "allowed_tools|chat_request_tools" logs/app.log | tail -20
```

---

## 📝 日誌分析範例

### 成功案例日誌序列

```
1. chat_request_tools_received: {"allowed_tools": ["document_editing"], ...}
2. task_analyzer_result_assigned: {"has_task_analyzer_result": true, ...}
3. Router LLM: Router decision: {"needs_tools": true, "intent_type": "execution", ...}
4. Matched tools for router decision: {"tool_name": "document_editing", "total_score": 0.95, ...}
5. Decision Engine: Selected tool: document_editing (score: 0.95)
6. document_generation_intent_detected_via_task_analyzer: {...}
7. checking_file_creation_intent: {...}
8. document_editing_tool_detected_for_file_creation: {...}
9. try_create_file_start: {...}
10. file_created_from_stream: {"file_id": "...", "filename": "...", ...}
```

### 失敗案例日誌序列（Router LLM 未識別）

```
1. chat_request_tools_received: {"allowed_tools": ["document_editing"], ...}
2. task_analyzer_result_assigned: {"has_task_analyzer_result": true, ...}
3. Router LLM: Router decision: {"needs_tools": false, "intent_type": "conversation", ...}  # ❌
4. document_editing_tool_not_detected: {"note": "Task Analyzer did not select document_editing tool"}
```

### 失敗案例日誌序列（Capability Matcher 未匹配）

```
1. chat_request_tools_received: {"allowed_tools": ["document_editing"], ...}
2. Router LLM: Router decision: {"needs_tools": true, "intent_type": "execution", ...}
3. Matched tools for router decision: {"tool_name": "document_editing", "total_score": 0.3, ...}  # ❌ 評分太低
4. Decision Engine: No tools selected (all scores < 0.5)
```

---

## 🎯 下一步行動

根據診斷結果，採取相應的修復措施：

1. **如果 `allowed_tools` 為空**：
   - 確認 Assistant 配置
   - 重新編譯前端代碼
   - 清除瀏覽器緩存

2. **如果 Router LLM 判斷錯誤**：
   - 使用更明確的指令
   - 檢查 Router LLM 的 System Prompt

3. **如果 Capability Matcher 未匹配**：
   - 確認 Assistant 已啟用文件編輯
   - 檢查 `allowed_tools` 傳遞

4. **如果文件創建失敗**：
   - 檢查具體失敗原因（權限、存儲、擴展名等）

---

**最後更新日期**: 2026-01-06
**文檔版本**: 1.0
**維護人**: Daniel Chung
