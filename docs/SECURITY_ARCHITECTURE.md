# AI-Box 安全認證架構說明

**代碼功能說明**: 系統安全認證架構文檔  
**創建日期**: 2025-12-08  
**創建人**: Daniel Chung  
**最後修改日期**: 2025-12-08

## 目錄

1. [概述](#概述)
2. [認證架構圖](#認證架構圖)
3. [前端認證流程](#前端認證流程)
4. [後端API認證](#後端api認證)
5. [數據庫連接認證](#數據庫連接認證)
6. [完整認證流程示例](#完整認證流程示例)
7. [安全最佳實踐](#安全最佳實踐)
8. [開發模式與生產模式](#開發模式與生產模式)
9. [相關文件](#相關文件)

---

## 概述

AI-Box 系統採用**分層認證架構**，確保各層級的安全性和職責分離：

- **前端層**: 使用 JWT Token 進行用戶身份認證
- **API層**: 驗證 JWT Token 並解析用戶信息
- **數據庫層**: 使用環境變數中的憑證進行系統級連接

這種設計確保：
- ✅ 前端不接觸數據庫憑證
- ✅ 用戶身份與系統憑證分離
- ✅ 符合安全最佳實踐

---

## 認證架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                        用戶瀏覽器                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  前端應用 (React/Vite)                                 │   │
│  │  - localStorage: access_token (JWT)                  │   │
│  │  - API 請求: Authorization: Bearer <JWT_TOKEN>      │   │
│  └───────────────────┬──────────────────────────────────┘   │
└──────────────────────┼──────────────────────────────────────┘
                       │ HTTPS/HTTP
                       │ JWT Token 認證
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 後端服務器                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API 路由層                                           │   │
│  │  - Depends(get_current_user)                         │   │
│  │  - 驗證 JWT Token                                    │   │
│  │  - 解析用戶信息 (user_id, username, email, etc.)     │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼──────────────────────────────────┐   │
│  │  業務邏輯層                                           │   │
│  │  - UserTaskService                                   │   │
│  │  - FileMetadataService                               │   │
│  │  - 使用 current_user.user_id 進行數據操作            │   │
│  └───────────────────┬──────────────────────────────────┘   │
└──────────────────────┼──────────────────────────────────────┘
                       │ 系統級連接
                       │ 環境變數憑證
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    數據庫層                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ArangoDB                                            │   │
│  │  - 使用 .env 中的 ARANGODB_PASSWORD                 │   │
│  │  - 系統級連接（非用戶級）                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 前端認證流程

### 1. 登錄流程

```typescript
// ai-bot/src/pages/LoginPage.tsx
1. 用戶輸入用戶名和密碼
2. 調用 POST /api/v1/auth/login
3. 後端驗證憑證並返回 JWT token
4. 前端將 token 存儲到 localStorage
   localStorage.setItem('access_token', token)
```

### 2. API 請求認證

```typescript
// ai-bot/src/lib/api.ts
export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // 1. 從 localStorage 獲取 JWT token
  const token = localStorage.getItem('access_token');
  
  // 2. 在請求頭中添加 Authorization
  const fetchOptions: RequestInit = {
    ...options,
    headers: {
      ...apiConfig.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  };
  
  // 3. 發送請求
  const response = await fetch(url, fetchOptions);
  return response.json();
}
```

### 3. 前端認證要點

- ✅ **JWT Token 存儲**: 使用 `localStorage` 存儲 `access_token`
- ✅ **自動添加認證頭**: 所有 API 請求自動添加 `Authorization: Bearer <token>`
- ✅ **不接觸數據庫憑證**: 前端永遠不會接觸 ArangoDB 的用戶名和密碼
- ✅ **Token 過期處理**: 當 token 過期時，需要重新登錄

---

## 後端API認證

### 1. 認證依賴注入

```python
# api/routers/user_tasks.py
@router.delete("/{task_id}")
async def delete_user_task(
    task_id: str,
    current_user: User = Depends(get_current_user),  # ← 認證依賴
) -> JSONResponse:
    # current_user 包含從 JWT token 解析的用戶信息
    # - current_user.user_id
    # - current_user.username
    # - current_user.email
    # - current_user.roles
    # - current_user.permissions
    ...
```

### 2. JWT Token 驗證流程

```python
# system/security/dependencies.py
async def get_current_user(request: Request) -> User:
    # 1. 從請求頭提取 token
    token = await extract_token_from_request(request)
    #    - Authorization: Bearer <token>
    #    - X-API-Key: <api_key>
    
    # 2. 驗證 token
    user = await authenticate_request(request)
    
    # 3. 解析 JWT payload
    #    - sub / user_id: 用戶ID
    #    - username: 用戶名
    #    - email: 郵箱
    #    - roles: 角色列表
    #    - permissions: 權限列表
    
    # 4. 返回 User 對象
    return user
```

### 3. Token 提取邏輯

```python
# system/security/auth.py
async def extract_token_from_request(request: Request) -> Optional[str]:
    # 優先檢查 Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # 移除 "Bearer " 前綴
    
    # 備選：檢查 X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    return None
```

### 4. JWT Token 驗證

```python
# system/security/auth.py
async def verify_jwt_token(token: str) -> Optional[User]:
    # 1. 使用 JWT Service 驗證 token
    jwt_service = get_jwt_service()
    payload = jwt_service.verify_token(token, token_type="access")
    
    # 2. 從 payload 構建 User 對象
    user_id = payload.get("sub") or payload.get("user_id")
    user = User(
        user_id=str(user_id),
        username=payload.get("username"),
        email=payload.get("email"),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        is_active=payload.get("is_active", True),
    )
    
    return user
```

### 5. 後端認證要點

- ✅ **依賴注入**: 使用 FastAPI 的 `Depends(get_current_user)` 進行認證
- ✅ **自動驗證**: 所有需要認證的路由自動驗證 JWT token
- ✅ **用戶信息解析**: 從 JWT payload 中解析用戶信息
- ✅ **權限檢查**: 可選的權限檢查（`require_permission`）

---

## 數據庫連接認證

### 1. ArangoDB 連接配置

```python
# database/arangodb/client.py
class ArangoDBClient:
    def __init__(self, ...):
        # 從環境變數讀取憑證
        self.username = username or os.getenv(
            self.settings.credentials.username,  # "ARANGODB_USERNAME"
            "root"  # 默認值
        )
        self.password = password or os.getenv(
            self.settings.credentials.password,  # "ARANGODB_PASSWORD"
            "ai_box_arangodb_password"  # 默認值
        )
        
        # 連接 ArangoDB
        self.db = self.client.db(
            self.settings.database,
            username=self.username,
            password=self.password,
        )
```

### 2. 環境變數配置

```bash
# .env
ARANGODB_HOST=localhost
ARANGODB_PORT=8529
ARANGODB_USERNAME=root
ARANGODB_PASSWORD=changeme
ARANGODB_DATABASE=ai_box_kg
```

### 3. 數據庫連接要點

- ✅ **系統級連接**: ArangoDB 連接使用系統級憑證，不是用戶級
- ✅ **環境變數管理**: 憑證存儲在 `.env` 文件中，不提交到版本控制
- ✅ **服務層使用**: 業務邏輯層（Service）使用 `ArangoDBClient` 連接數據庫
- ✅ **用戶隔離**: 通過 `user_id` 字段在應用層實現數據隔離

---

## 完整認證流程示例

### 示例：Sidebar 刪除任務

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 前端 Sidebar (Sidebar.tsx)                               │
│    handleConfirmDelete()                                    │
│    ↓                                                         │
│    deleteUserTask(taskId)                                   │
│    ↓                                                         │
│    apiDelete('/user-tasks/${taskId}')                        │
│    ↓                                                         │
│    apiRequest() 添加 Authorization: Bearer <JWT_TOKEN>     │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP Request
                    │ Authorization: Bearer <JWT_TOKEN>
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 後端 API (user_tasks.py)                                 │
│    @router.delete("/{task_id}")                            │
│    Depends(get_current_user)                                │
│    ↓                                                         │
│    extract_token_from_request()                             │
│    ↓                                                         │
│    verify_jwt_token(token)                                  │
│    ↓                                                         │
│    解析 JWT payload → User 對象                              │
│    current_user.user_id = "daniel@test.com"                 │
└───────────────────┬─────────────────────────────────────────┘
                    │ 業務邏輯
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 業務邏輯層 (UserTaskService)                             │
│    service.get(user_id=current_user.user_id, task_id=...)  │
│    ↓                                                         │
│    使用 current_user.user_id 查詢任務                       │
│    （確保用戶只能刪除自己的任務）                            │
└───────────────────┬─────────────────────────────────────────┘
                    │ 數據庫操作
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 數據庫層 (ArangoDBClient)                               │
│    ArangoDBClient()                                         │
│    ↓                                                         │
│    從 .env 讀取 ARANGODB_PASSWORD                           │
│    ↓                                                         │
│    使用系統憑證連接 ArangoDB                                │
│    ↓                                                         │
│    執行 AQL 查詢（使用 user_id 過濾）                       │
└─────────────────────────────────────────────────────────────┘
```

### 關鍵安全點

1. **用戶身份驗證**: 前端使用 JWT token，後端驗證 token 獲取 `user_id`
2. **數據隔離**: 所有數據庫查詢都使用 `current_user.user_id` 進行過濾
3. **系統憑證分離**: 數據庫連接使用系統級憑證，與用戶身份分離
4. **權限檢查**: 可選的權限檢查確保用戶只能執行授權的操作

---

## 安全最佳實踐

### 1. JWT Token 安全

- ✅ **HTTPS 傳輸**: 生產環境必須使用 HTTPS
- ✅ **Token 存儲**: 使用 `localStorage`（可考慮 `httpOnly` cookie）
- ✅ **Token 過期**: 設置合理的過期時間
- ✅ **Token 刷新**: 實現 refresh token 機制（待實現）

### 2. 數據庫憑證安全

- ✅ **環境變數**: 憑證存儲在 `.env` 文件中
- ✅ **版本控制**: `.env` 文件不提交到 Git
- ✅ **默認值**: 避免使用弱默認密碼
- ✅ **定期輪換**: 定期更換數據庫密碼

### 3. API 安全

- ✅ **輸入驗證**: 所有輸入都進行驗證
- ✅ **SQL 注入防護**: 使用參數化查詢（AQL）
- ✅ **CORS 配置**: 正確配置 CORS 策略
- ✅ **速率限制**: 實施 API 速率限制（待實現）

### 4. 用戶數據隔離

- ✅ **user_id 過濾**: 所有查詢都使用 `user_id` 過濾
- ✅ **權限檢查**: 實施基於角色的訪問控制（RBAC）
- ✅ **審計日誌**: 記錄所有敏感操作（已實現）

---

## 開發模式與生產模式

### 開發模式 (`SECURITY_ENABLED=false` 或 `SECURITY_MODE=development`)

```python
# system/security/dependencies.py
if settings.should_bypass_auth:
    # 1. 嘗試從 JWT token 解析用戶信息
    user = await authenticate_request(request)
    if user:
        return user  # 使用解析到的用戶
    
    # 2. 如果沒有 token，返回開發用戶
    return User.create_dev_user()  # user_id="dev_user"
```

**特點**:
- ✅ 允許從 JWT token 解析真實用戶信息（便於開發測試）
- ✅ 如果沒有 token，返回默認開發用戶
- ✅ 不強制要求認證（便於開發）

### 生產模式 (`SECURITY_ENABLED=true` 且 `SECURITY_MODE=production`)

```python
# system/security/dependencies.py
# 生產模式下進行真實認證
user = await authenticate_request(request)
if not user:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )
```

**特點**:
- ✅ 強制要求認證
- ✅ 必須提供有效的 JWT token 或 API Key
- ✅ 未認證的請求返回 401 錯誤

---

## 相關文件

### 前端文件

- `ai-bot/src/lib/api.ts` - API 請求封裝，JWT token 處理
- `ai-bot/src/lib/jwtUtils.ts` - JWT token 解析工具
- `ai-bot/src/pages/LoginPage.tsx` - 登錄頁面
- `ai-bot/src/components/Sidebar.tsx` - 任務管理（使用認證 API）

### 後端文件

- `system/security/auth.py` - JWT token 驗證邏輯
- `system/security/dependencies.py` - FastAPI 依賴注入（認證）
- `system/security/jwt_service.py` - JWT 服務（簽發、驗證）
- `system/security/models.py` - User 模型定義
- `api/routers/auth.py` - 登錄 API
- `api/routers/user_tasks.py` - 任務管理 API（使用認證）
- `api/routers/file_management.py` - 文件管理 API（使用認證）

### 數據庫文件

- `database/arangodb/client.py` - ArangoDB 客戶端（連接管理）
- `database/arangodb/settings.py` - ArangoDB 配置（憑證讀取）
- `services/api/services/user_task_service.py` - 任務服務（使用 ArangoDBClient）

---

## 總結

AI-Box 系統採用**三層認證架構**：

1. **前端層**: JWT Token 認證（用戶身份）
2. **API層**: JWT Token 驗證（用戶授權）
3. **數據庫層**: 環境變數憑證（系統連接）

這種設計確保：
- ✅ **安全性**: 各層級職責分離，憑證不洩露
- ✅ **可維護性**: 清晰的認證流程，易於維護
- ✅ **可擴展性**: 支持多種認證方式（JWT、API Key）
- ✅ **合規性**: 符合安全最佳實踐

---

**最後更新**: 2025-12-08  
**維護者**: Daniel Chung
