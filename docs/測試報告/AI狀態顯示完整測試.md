# AI 執行狀態顯示 - 完整測試

## 測試目標

確認以下環節是否正常：
1. 前端是否正確發送消息
2. 後端是否生成 request_id
3. 後端是否調用 start_status_tracking
4. SSE 連接是否建立
5. 後端是否發送狀態事件
6. 前端是否收到並顯示

## 測試步驟

### 步驟 1：確認後端日誌監控

在後端終端執行：
```bash
cd /home/daniel/ai-box
tail -f api.log 2>/dev/null | grep -E "SSE|status|request_id"
```

或者監控 stderr：
```bash
cd /home/daniel/ai-box
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | grep -E "SSE|\[SSE\]|request_id"
```

### 步驟 2：直接測試後端 SSE

**測試 A：直接發送狀態事件**
```bash
# 1. 啟動追蹤
curl -X POST "http://localhost:8000/api/v1/agent-status/start" -H "Content-Type: application/json" -d '{"request_id": "test-001"}'

# 2. 監控 SSE (5秒)
timeout 5 curl -N "http://localhost:8000/api/v1/agent-status/stream/test-001"

# 3. 在另一終端發送事件
curl -X POST "http://localhost:8000/api/v1/agent-status/event" -H "Content-Type: application/json" -d '{"request_id": "test-001", "step": "語義理解", "status": "processing", "message": "正在分析用戶意圖", "progress": 0.3}'
```

**測試 B：通過外部域名測試**
```bash
# 1. 啟動追蹤
curl -X POST "https://iee.sunlyc.com/api/v1/agent-status/start" -H "Content-Type: application/json" -d '{"request_id": "test-002"}'

# 2. 監控 SSE
timeout 5 curl -N "https://iee.sunlyc.com/api/v1/agent-status/stream/test-002"

# 3. 發送事件
curl -X POST "https://iee.sunlyc.com/api/v1/agent-status/event" -H "Content-Type: application/json" -d '{"request_id": "test-002", "step": "語義理解", "status": "processing", "message": "正在分析用戶意圖", "progress": 0.3}'
```

### 步驟 3：前端瀏覽器測試

1. 打開瀏覽器開發者工具 (F12)
2. 打開 AI 狀態窗口
3. 發送消息給 AI
4. 觀察 Console 中的日誌：
   - `[Home] 生成 request_id: ...`
   - `[Home] 📡 調用 /api/v1/agent-status/start...`
   - `[SSE] connect() targetRequestId: ...`
   - `[SSE] onopen`
   - `[SSE] onmessage: ...`

### 步驟 4：檢查 Home.tsx 代碼

確認 `handleMessageSend` 函數中：
- 是否正確生成 request_id
- 是否調用 `/api/v1/agent-status/start`
- 是否調用 `connectAIStatus()`

## 預期流程

```
用戶發送消息
    ↓
Home.tsx 生成 request_id
    ↓
Home.tsx 調用 /api/v1/agent-status/start (POST)
    ↓
Home.tsx 調用 connectAIStatus() → useAIStatusSSE.connect()
    ↓
SSE 連接到 /api/v1/agent-status/stream/{request_id}
    ↓
後端 chat.py 處理消息時調用 _publish_status_internal
    ↓
SSE stream 收到事件
    ↓
前端 onmessage 解析並更新 store
    ↓
AIStatusWindow 顯示狀態
```

## 問題診斷

### 問題 1：沒有 request_id
- 檢查 Home.tsx 中 `handleMessageSend` 是否執行
- 檢查 Console 是否有 `[Home] 生成 request_id:` 日誌

### 問題 2：沒有調用 start
- 檢查 Console 是否有 `[Home] 📡 調用 /api/v1/agent-status/start...` 日誌
- 檢查後端是否收到請求

### 問題 3：SSE 沒有連接
- 檢查 Console 是否有 `[SSE] connect()` 日誌
- 檢查是否有 `[SSE] onopen` 日誌
- 檢查 Network 標籤中是否有 SSE 請求

### 問題 4：後端沒有發送狀態
- 檢查後端日誌是否有 `[SSE] yield:` 日誌
- 檢查 chat.py 是否正確調用 `_publish_status_internal`
