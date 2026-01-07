# 安全模組 (Security Module)

## 概述

這是 AI-Box 專案的安全模組，提供身份驗證、授權和安全相關功能。此模組為 **WBS 1.6 最小先行開發版本**，提供開發模式繞過機制，完整功能將在後續 WBS 1.6 子任務中逐步實施。

## 當前狀態

### 已實現功能

- ✅ 安全配置管理（`config.py`）
- ✅ 開發模式繞過機制
- ✅ 基礎用戶模型（`models.py`）
- ✅ 認證依賴函數骨架（`dependencies.py`）
- ✅ 安全中間件骨架（`middleware.py`）
- ✅ 配置集成（`config.json` 和環境變數支援）

### 預留接口（待實施）

以下功能已在代碼中預留接口，將在後續 WBS 1.6 子任務中實施：

1. **WBS 1.6.1 - JWT Token 服務**
   - JWT Token 簽發、驗證、刷新
   - Token 黑名單管理
   - Token 過期處理
   - 相關文件：`services/security/auth.py` 中的 `verify_jwt_token()` 函數

2. **WBS 1.6.2 - API Key 管理**
   - API Key 生成和驗證
   - API Key 輪換機制
   - API Key 限流功能
   - 相關文件：`services/security/auth.py` 中的 `verify_api_key()` 函數

3. **WBS 1.6.3 - RBAC 權限系統**
   - 角色和權限策略文件解析
   - 複雜權限組合（AND、OR、NOT）
   - 權限審計日誌
   - 動態權限分配
   - 相關文件：`services/security/dependencies.py` 中的權限檢查函數

4. **WBS 1.6.6 - 輸入驗證框架**
   - 請求速率限制（Rate Limiting）
   - IP 白名單/黑名單檢查
   - 請求大小驗證
   - 安全頭設置（CSP、HSTS 等）
   - 相關文件：`services/security/middleware.py`

## 目錄結構

```
services/security/
├── __init__.py           # 模組初始化
├── config.py             # 安全配置管理
├── models.py             # 用戶、角色、權限模型
├── auth.py               # 認證相關功能（JWT/API Key 接口預留）
├── dependencies.py       # FastAPI 依賴注入函數
├── middleware.py         # 安全中間件
└── README.md             # 本文檔
```

## 快速開始

### 開發模式（預設）

在開發模式下，所有認證檢查會被繞過，無需提供認證信息即可訪問 API。

確保 `config/config.json` 中安全模組配置為：

```json
{
  "services": {
    "security": {
      "enabled": false,
      "mode": "development"
    }
  }
}
```

或在環境變數中設置：

```bash
export SECURITY_ENABLED=false
export SECURITY_MODE=development
```

### 在路由中使用認證

```python
from fastapi import Depends
from services.security.dependencies import get_current_user
from services.security.models import User

@router.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"user_id": user.user_id, "message": "This is a protected route"}
```

在開發模式下，此端點會自動使用開發用戶（`dev_user`），無需提供認證信息。

### 使用權限檢查

```python
from services.security.dependencies import require_permission
from services.security.models import Permission

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(require_permission(Permission.TASK_DELETE.value))
):
    # 用戶必須擁有 TASK_DELETE 權限才能執行此操作
    ...
```

## 配置說明

### 環境變數

- `SECURITY_ENABLED`: 是否啟用安全檢查（`true`/`false`，預設 `false`）
- `SECURITY_MODE`: 安全模式（`development`/`production`，預設 `development`）
- `SECURITY_JWT_ENABLED`: 是否啟用 JWT（預設 `false`）
- `SECURITY_JWT_SECRET_KEY`: JWT 密鑰（從環境變數或 `.env` 讀取）
- `SECURITY_API_KEY_ENABLED`: 是否啟用 API Key（預設 `false`）
- `SECURITY_RBAC_ENABLED`: 是否啟用 RBAC（預設 `false`）

### config.json 配置

在 `config/config.json` 中配置：

```json
{
  "services": {
    "security": {
      "enabled": false,
      "mode": "development",
      "jwt": {
        "enabled": false,
        "secret_key": "SECURITY_JWT_SECRET_KEY",
        "algorithm": "HS256",
        "expiration_hours": 24
      },
      "api_key": {
        "enabled": false
      },
      "rbac": {
        "enabled": false
      }
    }
  }
}
```

## 模組組件說明

### config.py - 配置管理

提供 `SecuritySettings` 類和 `get_security_settings()` 函數，用於讀取和管理安全相關配置。

配置來源優先級：

1. 環境變數
2. `config.json` 中的 `services.security` 區塊
3. 預設值

### models.py - 數據模型

定義了以下數據模型：

- `User`: 用戶模型，包含用戶信息、角色和權限
- `Role`: 角色枚舉（admin, user, guest, developer）
- `Permission`: 權限枚舉（預定義常用權限）

### auth.py - 認證功能

提供認證相關的函數接口，目前僅提供骨架，實際驗證邏輯將在 WBS 1.6.1 和 WBS 1.6.2 中實施。

### dependencies.py - FastAPI 依賴

提供以下 FastAPI 依賴函數：

- `get_current_user()`: 獲取當前認證用戶
- `require_permission()`: 檢查用戶是否擁有指定權限
- `require_any_permission()`: 檢查用戶是否擁有任意一個指定權限
- `require_all_permissions()`: 檢查用戶是否擁有所有指定權限

### middleware.py - 安全中間件

提供 `SecurityMiddleware` 類，用於在請求級別進行安全檢查。目前僅提供骨架，實際功能將在 WBS 1.6.6 中實施。

## 開發模式行為

當 `SECURITY_ENABLED=false` 或 `SECURITY_MODE=development` 時：

- ✅ 所有認證依賴返回 mock 用戶（`dev_user`）
- ✅ 所有權限檢查自動通過
- ✅ 安全中間件繞過大部分檢查
- ✅ 無需提供 JWT Token 或 API Key

## 後續開發計劃

完整的安全功能將在以下 WBS 1.6 子任務中實施：

1. **WBS 1.6.1** (1.5 天): JWT Token 服務
2. **WBS 1.6.2** (1 天): API Key 管理
3. **WBS 1.6.3** (1.5 天): RBAC 權限系統
4. **WBS 1.6.4** (1 天): Secret 管理服務
5. **WBS 1.6.5** (1 天): TLS/SSL 配置
6. **WBS 1.6.6** (1 天): 輸入驗證框架

每個子任務完成後，對應的功能將自動啟用。

## 相關文檔

- [開發模式使用指南](../../docs/deployment/security-development-mode.md)
- [WBS 1.6 基礎安全模組子計劃](../../docs/plans/phase1/wbs-1.6-security-module.md)
