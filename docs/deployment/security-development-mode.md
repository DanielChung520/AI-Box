# 安全模組開發模式使用指南

## 概述

本文件說明如何在開發環境中使用 AI-Box 安全模組的開發模式繞過機制。開發模式允許開發者專注於功能開發，無需處理複雜的認證和授權邏輯。

## 開發模式特點

### 自動繞過認證

在開發模式下，所有需要認證的端點會自動使用開發用戶（`dev_user`），無需提供 JWT Token 或 API Key。

### 自動通過權限檢查

所有權限檢查在開發模式下會自動通過，無論用戶實際權限如何。

### 安全中間件繞過

安全中間件在開發模式下會繞過大部分檢查，僅設置基本的安全頭。

## 配置方式

### 方式 1: 使用 config.json

在 `config/config.json` 中配置：

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

### 方式 2: 使用環境變數

在 `.env` 文件或環境中設置：

```bash
SECURITY_ENABLED=false
SECURITY_MODE=development
```

或在命令行中：

```bash
export SECURITY_ENABLED=false
export SECURITY_MODE=development
```

### 方式 3: Docker Compose

在 `docker-compose.yml` 中設置：

```yaml
services:
  api:
    environment:
      - SECURITY_ENABLED=false
      - SECURITY_MODE=development
```

## 使用示例

### 基本認證依賴

```python
from fastapi import Depends
from services.security.dependencies import get_current_user
from services.security.models import User

@router.get("/api/v1/protected")
async def protected_endpoint(user: User = Depends(get_current_user)):
    """
    此端點在開發模式下無需認證即可訪問。
    會自動使用開發用戶 (dev_user)。
    """
    return {
        "message": "This is a protected endpoint",
        "user_id": user.user_id,
        "mode": user.metadata.get("mode", "unknown")
    }
```

在開發模式下，訪問此端點無需提供認證信息：

```bash
curl http://localhost:8000/api/v1/protected
```

返回結果：

```json
{
  "message": "This is a protected endpoint",
  "user_id": "dev_user",
  "mode": "development"
}
```

### 權限檢查依賴

```python
from services.security.dependencies import require_permission
from services.security.models import Permission

@router.delete("/api/v1/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(require_permission(Permission.TASK_DELETE.value))
):
    """
    此端點在開發模式下會自動通過權限檢查。
    """
    return {"message": f"Task {task_id} deleted", "deleted_by": user.user_id}
```

在開發模式下，即使沒有 `TASK_DELETE` 權限，此端點也可以正常訪問。

### 多權限檢查

```python
from services.security.dependencies import require_any_permission, require_all_permissions

# 需要任意一個權限
@router.get("/api/v1/data")
async def get_data(
    user: User = Depends(require_any_permission("read:data", "admin"))
):
    ...

# 需要所有權限
@router.post("/api/v1/admin/action")
async def admin_action(
    user: User = Depends(require_all_permissions("admin", "write:data"))
):
    ...
```

## 開發用戶信息

在開發模式下，自動使用的開發用戶信息如下：

```python
{
    "user_id": "dev_user",
    "username": "development_user",
    "email": "dev@ai-box.local",
    "roles": ["admin"],
    "permissions": ["*"],  # 所有權限
    "is_active": True,
    "metadata": {
        "mode": "development",
        "bypass_auth": True
    }
}
```

此用戶擁有所有角色和權限，可以用於開發和測試。

## 切換到生產模式

當準備部署到生產環境時，需要：

1. **啟用安全模組**：

   ```bash
   export SECURITY_ENABLED=true
   export SECURITY_MODE=production
   ```

2. **配置 JWT 或 API Key**：
   根據實際需求配置對應的認證方式。

3. **配置 RBAC**：
   設置適當的角色和權限策略。

詳細的生產環境配置請參考 [WBS 1.6 基礎安全模組子計劃](../plans/phase1/wbs-1.6-security-module.md)。

## 注意事項

### 開發環境安全

雖然開發模式繞過了認證檢查，但仍需注意：

- ⚠️ **不要**在生產環境中使用開發模式
- ⚠️ **不要**將包含開發用戶信息的日誌輸出到公開位置
- ⚠️ 開發模式下仍會設置基本的安全頭，但不會進行嚴格的檢查

### 測試考量

在編寫測試時：

- 可以使用 `get_current_user()` 依賴來測試認證邏輯
- 可以使用 `User.create_dev_user()` 來創建開發用戶進行測試
- 生產模式下的測試需要使用真實的 JWT Token 或 API Key

### 中間件行為

開發模式下，安全中間件會：

- ✅ 設置基本的 HTTP 安全頭（如 `X-Content-Type-Options`）
- ✅ 記錄請求日誌（debug 級別）
- ❌ 跳過速率限制檢查
- ❌ 跳過 IP 白名單/黑名單檢查
- ❌ 跳過請求大小驗證

## 故障排除

### 問題：端點仍然要求認證

**可能原因**：

- `SECURITY_ENABLED` 設置為 `true`
- `SECURITY_MODE` 設置為 `production`

**解決方案**：
檢查環境變數和 `config.json` 配置，確保：

```bash
SECURITY_ENABLED=false
SECURITY_MODE=development
```

### 問題：權限檢查失敗

**可能原因**：

- RBAC 被啟用且權限檢查邏輯已實施

**解決方案**：
在開發模式下，確保：

```bash
SECURITY_RBAC_ENABLED=false
```

或確保 `config.json` 中：

```json
{
  "services": {
    "security": {
      "rbac": {
        "enabled": false
      }
    }
  }
}
```

## 相關文檔

- [安全模組 README](../../services/security/README.md)
- [WBS 1.6 基礎安全模組子計劃](../plans/phase1/wbs-1.6-security-module.md)
- [配置管理說明](../../config/README.md)
