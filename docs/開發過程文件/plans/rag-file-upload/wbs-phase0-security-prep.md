# WBS-階段零：安全準備

**文檔功能說明**: 安全準備階段實施工作分解結構（必須在階段一開始前完成）
**創建日期**: 2025-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2025-01-27
**優先級**: 🔴 P0 - 關鍵路徑，阻塞後續階段

## 1. 工作分解結構

### 1.1 JWT認證系統實現 (2-3天)

#### 1.1.1 JWT服務實現 (1-2天)

- [x] **任務 1.1.1.1**: 實現JWT Token簽發
  - 位置: `system/security/jwt_service.py` (新建)
  - 功能: 生成JWT Token，包含用戶信息
  - 預計時間: 4小時

- [x] **任務 1.1.1.2**: 實現JWT Token驗證
  - 位置: `system/security/auth.py`
  - 功能: 驗證Token簽名、過期時間
  - 預計時間: 4小時

- [x] **任務 1.1.1.3**: 實現Token刷新機制
  - 功能: Refresh Token生成和驗證
  - 預計時間: 3小時

- [x] **任務 1.1.1.4**: 實現Token黑名單
  - 功能: 登出時將Token加入黑名單
  - 使用Redis存儲黑名單
  - 預計時間: 3小時

#### 1.1.2 認證中間件實現 (1天)

- [x] **任務 1.1.2.1**: 實現認證依賴注入
  - 位置: `system/security/dependencies.py`
  - 功能: `get_current_user` 依賴函數
  - 預計時間: 3小時

- [x] **任務 1.1.2.2**: 實現認證中間件
  - 位置: `system/security/middleware.py`
  - 功能: 自動驗證請求中的Token
  - 預計時間: 4小時

- [x] **任務 1.1.2.3**: 更新文件上傳API
  - 位置: `api/routers/file_upload.py`
  - 功能: 強制要求認證，從Token獲取user_id
  - 預計時間: 2小時

- [x] **任務 1.1.2.4**: 實現開發模式繞過機制
  - 功能: 開發環境可選認證，生產環境強制認證
  - 預計時間: 1小時

### 1.2 數據使用同意機制 (1天)

#### 1.2.1 同意模型設計 (0.3天)

- [x] **任務 1.2.1.1**: 設計數據使用同意數據模型
  - 位置: `services/api/models/data_consent.py` (新建)
  - 字段: user_id, consent_type, purpose, granted, timestamp
  - 預計時間: 2小時

- [x] **任務 1.2.1.2**: 實現同意類型定義
  - 類型: file_upload, ai_processing, data_sharing, training
  - 預計時間: 1小時

#### 1.2.2 同意流程實現 (0.5天)

- [x] **任務 1.2.2.1**: 實現同意API
  - 位置: `api/routers/data_consent.py` (新建)
  - 功能: 記錄用戶同意狀態
  - 預計時間: 3小時

- [x] **任務 1.2.2.2**: 實現同意檢查中間件
  - 功能: 在文件上傳前檢查用戶同意
  - 預計時間: 2小時

- [x] **任務 1.2.2.3**: 實現前端同意UI
  - 位置: `ai-bot/src/components/ConsentModal.tsx` (新建)
  - 功能: 顯示同意條款，記錄用戶選擇
  - 預計時間: 3小時

#### 1.2.3 同意追蹤 (0.2天)

- [x] **任務 1.2.3.1**: 實現同意狀態查詢
  - 功能: 查詢用戶的同意狀態
  - 預計時間: 1小時

- [x] **任務 1.2.3.2**: 實現同意撤銷功能
  - 功能: 允許用戶撤銷同意
  - 預計時間: 1小時

### 1.3 審計日誌系統 (1-2天)

#### 1.3.1 日誌模型設計 (0.3天)

- [x] **任務 1.3.1.1**: 設計審計日誌數據模型
  - 位置: `services/api/models/audit_log.py` (新建)
  - 字段: user_id, action, resource_type, resource_id, timestamp, ip_address, details
  - 預計時間: 2小時

- [x] **任務 1.3.1.2**: 定義審計事件類型
  - 類型: file_upload, file_access, file_delete, data_process, model_call
  - 預計時間: 1小時

#### 1.3.2 日誌記錄實現 (0.5天)

- [x] **任務 1.3.2.1**: 實現審計日誌服務
  - 位置: `services/api/services/audit_log_service.py` (新建)
  - 功能: 記錄審計日誌到數據庫
  - 預計時間: 3小時

- [x] **任務 1.3.2.2**: 實現審計日誌裝飾器
  - 功能: 自動記錄API調用
  - 預計時間: 2小時

- [x] **任務 1.3.2.3**: 在關鍵操作中添加日誌
  - 位置: `api/routers/file_upload.py`
  - 功能: 記錄文件上傳操作
  - 預計時間: 2小時

#### 1.3.3 日誌查詢API (0.4天)

- [x] **任務 1.3.3.1**: 實現日誌查詢API
  - 位置: `api/routers/audit_log.py` (新建)
  - 功能: 按用戶、時間、操作類型查詢
  - 預計時間: 3小時

- [x] **任務 1.3.3.2**: 實現日誌導出功能
  - 功能: 導出審計日誌為CSV/JSON
  - 預計時間: 1小時

### 1.4 安全配置和測試 (0.5天)

#### 1.4.1 安全配置 (0.2天)

- [x] **任務 1.4.1.1**: 配置JWT密鑰管理
  - 功能: 從環境變數讀取密鑰，生產環境使用強密鑰
  - 預計時間: 1小時

- [x] **任務 1.4.1.2**: 配置CORS和安全頭
  - 功能: 設置適當的CORS策略和安全HTTP頭
  - 預計時間: 1小時

#### 1.4.2 安全測試 (0.3天)

- [ ] **任務 1.4.2.1**: 認證功能測試
  - 功能: 測試Token生成、驗證、刷新
  - 預計時間: 2小時

- [ ] **任務 1.4.2.2**: 未授權訪問測試
  - 功能: 測試未認證請求被拒絕
  - 預計時間: 1小時

## 2. 技術規格

### 2.1 JWT配置

```python
# JWT配置示例
{
  "algorithm": "HS256",
  "secret_key": "從環境變數讀取",
  "expiration_hours": 24,
  "refresh_expiration_days": 7
}
```

### 2.2 數據使用同意模型

```python
class DataConsent(BaseModel):
    user_id: str
    consent_type: ConsentType  # file_upload, ai_processing, etc.
    purpose: str  # 使用目的描述
    granted: bool
    timestamp: datetime
    expires_at: Optional[datetime]  # 可選過期時間
```

### 2.3 審計日誌模型

```python
class AuditLog(BaseModel):
    user_id: str
    action: AuditAction  # file_upload, file_access, etc.
    resource_type: str  # file, task, etc.
    resource_id: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]  # 額外詳情
```

### 2.4 API端點

#### 登錄

```
POST /api/auth/login
Request: { "username": "...", "password": "..." }
Response: { "access_token": "...", "refresh_token": "..." }
```

#### 刷新Token

```
POST /api/auth/refresh
Request: { "refresh_token": "..." }
Response: { "access_token": "..." }
```

#### 記錄同意

```
POST /api/consent
Request: { "consent_type": "file_upload", "granted": true }
Response: { "success": true }
```

#### 查詢審計日誌

```
GET /api/audit-logs?user_id={user_id}&action={action}&start_date={date}
Response: { "logs": [...], "total": 100 }
```

## 3. 驗收標準

### 3.1 功能驗收

- ✅ JWT Token可以正常生成和驗證
- ✅ 未認證請求被正確拒絕
- ✅ 用戶同意狀態正確記錄和檢查
- ✅ 所有關鍵操作都有審計日誌
- ✅ 審計日誌可以查詢和導出

### 3.2 安全驗收

- ✅ Token使用強密鑰簽名
- ✅ Token過期時間合理
- ✅ 黑名單機制正常工作
- ✅ 敏感信息不在日誌中記錄

### 3.3 性能驗收

- Token驗證響應時間 < 10ms
- 審計日誌記錄不影響API性能（異步記錄）

## 4. 依賴關係

### 4.1 前置條件

- 用戶數據庫/認證系統可用
- Redis可用（用於Token黑名單）

### 4.2 後續任務

- 階段一：必須在階段零完成後才能開始

## 5. 風險與緩解

### 5.1 技術風險

- **風險**: JWT實現複雜，可能出現安全漏洞
- **緩解**: 使用成熟的JWT庫，進行安全審查

### 5.2 時間風險

- **風險**: 安全準備階段可能延遲項目開始
- **緩解**: 這是必要的，不能跳過。可以並行開發部分功能

## 6. 交付物

- [x] JWT認證系統完整實現
- [x] 數據使用同意機制
- [x] 審計日誌系統
- [ ] 安全配置文檔
- [ ] 安全測試報告
- [ ] API文檔更新

## 7. 時間估算

| 任務 | 預計時間 | 實際時間 | 狀態 |
|------|---------|---------|------|
| JWT認證系統 | 2-3天 | - | ⏸️ 待開始 |
| 數據使用同意機制 | 1天 | - | ⏸️ 待開始 |
| 審計日誌系統 | 1-2天 | - | ⏸️ 待開始 |
| 安全配置和測試 | 0.5天 | - | ⏸️ 待開始 |
| **總計** | **3-5天** | - | - |

## 8. 更新日誌

| 日期 | 版本 | 更新內容 | 更新人 |
|------|------|---------|--------|
| 2025-01-27 | 1.0 | 初始版本創建 | Daniel Chung |
