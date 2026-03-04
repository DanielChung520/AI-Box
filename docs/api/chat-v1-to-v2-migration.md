# Chat API V1 → V2 遷移計劃

**版本**: 1.0.0  
**創建日期**: 2026-03-02  
**作者**: Daniel Chung

---

## 1. 概述

本文檔描述 Chat API 從 V1 遷移到 V2 的計劃。V2 基於 OrchestratorIntentRAG 提供更統一的意圖分類和路由。

### 1.1 遷移目標

- 將所有 V1 Chat API 端點遷移到 V2
- 使用 OrchestratorService 統一處理流程
- 確保向後兼容性

### 1.2 遷移範圍

| 類別 | 數量 | 說明 |
|------|------|------|
| 完全對應 | 9 個 | 可直接遷移 |
| V2 增強 | 7 個 | V2 獨有功能 |
| 需要適配 | 1 個 | 請求格式差異 |

---

## 2. 端點對應表

### 2.1 主入口

| V1 | V2 | 狀態 |
|-----|-----|-------|
| `POST /api/chat` | `POST /api/v2/chat/unified` | ✅ 遷移 |
| `POST /api/chat/stream` | `POST /api/v2/chat/unified/stream` | ✅ 遷移 |

### 2.2 異步請求

| V1 | V2 | 狀態 |
|-----|-----|-------|
| `POST /api/chat/requests` | `POST /api/v2/chat/requests` | ✅ 遷移 |
| `GET /api/chat/requests/{id}` | `GET /api/v2/chat/requests/{id}` | ✅ 遷移 |
| `POST /api/chat/requests/{id}/abort` | `POST /api/v2/chat/tasks/{id}/abort` | 🔵 V2 更好 |
| - | `POST /api/v2/chat/requests/{id}/retry` | 🔵 新增 |
| - | `PUT /api/v2/chat/requests/{id}/priority` | 🔵 新增 |

### 2.3 觀測

| V1 | V2 | 狀態 |
|-----|-----|-------|
| `GET /api/chat/observability/stats` | `GET /api/v2/chat/observability/stats` | ✅ 遷移 |
| `GET /api/chat/observability/traces/{id}` | `GET /api/v2/chat/observability/traces/{id}` | ✅ 遷移 |
| `GET /api/chat/observability/recent` | `GET /api/v2/chat/observability/recent` | ✅ 遷移 |

### 2.4 會話

| V1 | V2 | 狀態 |
|-----|-----|-------|
| `GET /api/chat/sessions/{id}/messages` | `GET /api/v2/chat/sessions/{id}/messages` | ✅ 遷移 |
| - | `POST /api/v2/chat/sessions/{id}/archive` | 🔵 新增 |

### 2.5 偏好

| V1 | V2 | 狀態 |
|-----|-----|-------|
| `GET /api/chat/preferences/models` | `GET /api/v2/chat/preferences/models` | ✅ 遷移 |
| `PUT /api/chat/preferences/models` | `PUT /api/v2/chat/preferences/models` | ✅ 遷移 |

### 2.6 V2 獨有

| V2 | 說明 |
|-----|-------|
| `POST /api/v2/chat` | SyncHandler 版本 |
| `POST /api/v2/chat/batch` | 批處理 |
| `GET /api/v2/chat/tasks/{id}` | 任務治理 |
| `POST /api/v2/chat/tasks/{id}/decision` | 任務決策 |
| `POST /api/v2/chat/tasks/{id}/abort` | 任務中止 |

---

## 3. 遷移步驟

### Phase 1: 準備階段

- [ ] 1.1 部署 V2 API 到測試環境
- [ ] 1.2 更新測試用例覆蓋 V2 端點
- [ ] 1.3 驗證 OrchestratorService 功能正常

### Phase 2: 前端遷移

- [ ] 2.1 修改前端 API URL 配置
- [ ] 2.2 測試 `/unified` 端點
- [ ] 2.3 測試流式 `/unified/stream` 端點
- [ ] 2.4 測試其他端點

### Phase 3: 觀測和監控

- [ ] 3.1 監控 V2 API 錯誤率
- [ ] 3.2 監控延遲
- [ ] 3.3 收集用戶反饋

### Phase 4: 切換

- [ ] 4.1 切換正式環境
- [ ] 4.2 監控正式環境
- [ ] 4.3 保留 V1 一段時間作為回退

### Phase 5: 棄用

- [ ] 5.1 標記 V1 為 deprecated
- [ ] 5.2 移除 V1 路由註冊
- [ ] 5.3 清理相關代碼

---

## 4. 前端改動

### 4.1 URL 配置

```javascript
// V1 配置
const API_BASE = 'http://localhost:8000/api';
const CHAT_URL = `${API_BASE}/chat`;
const CHAT_STREAM_URL = `${API_BASE}/chat/stream`;

// V2 配置
const API_BASE = 'http://localhost:8000/api/v2';
const CHAT_URL = `${API_BASE}/chat/unified`;
const CHAT_STREAM_URL = `${API_BASE}/chat/unified/stream`;
```

### 4.2 請求格式

V1 和 V2 的請求格式相同：

```json
{
  "messages": [
    { "role": "user", "content": "查詢料號庫存" }
  ],
  "session_id": "session-123",
  "model_selector": { "mode": "auto" }
}
```

### 4.3 響應格式

V1 和 V2 的響應格式相同：

```json
{
  "success": true,
  "data": {
    "content": "這是回覆內容",
    "session_id": "session-123",
    "routing": { "provider": "...", "model": "..." }
  }
}
```

---

## 5. 回退計劃

如果遷移出現問題：

1. **回退 URL**: 將前端 URL 改回 V1
2. **保留 V1**: V1 路由保持可用直到 V2 穩定
3. **監控**: 及時發現問題

---

## 6. 時間表

| Phase | 工作 | 預計時間 |
|-------|------|----------|
| Phase 1 | 準備 | 1 天 |
| Phase 2 | 前端遷移 | 2-3 天 |
| Phase 3 | 觀測 | 3-5 天 |
| Phase 4 | 切換 | 1 天 |
| Phase 5 | 棄用 | 1 週觀察後 |

---

## 7. 風險

| 風險 | 影響 | 緩解 |
|------|------|------|
| OrchestratorIntentRAG 不穩定 | 可能無法正確分類 | 保持 V1 可用 |
| 外部服務調用失敗 | 回覆失敗 | 添加重試邏輯 |
| 前端改動遺漏 | 功能異常 | 全面測試 |

---

## 8. 驗收標準

- [ ] 所有 V1 端點功能在 V2 中可用
- [ ] 流式輸出正常工作
- [ ] 錯誤率不超過 1%
- [ ] 延遲不增加

---

## 9. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| 1.0.0 | 2026-03-02 | 初始版本 |
