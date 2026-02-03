# AI-Box SSO 實現總結

**項目名稱**: AI-Box SSO 集成
**完成日期**: 2026-01-18 14:09 UTC+8
**創建人**: Daniel Chung

---

## ✅ 已完成的實現

### 1. 後端實現

#### 新增監控工具入口頁面

- **文件**: `ai-bot/src/pages/MonitoringTools.tsx`
- **功能**:
  - 統一監控工具入口
  - 只對 system_admin 角色可訪問
  - 提供 Grafana 和 Prometheus 快捷入口
- **訪問路徑**: `/admin/monitoring-tools`

#### 更新應用路由

- **文件**: `ai-bot/src/App.tsx`
- **改動**:
  - 添加 `MonitoringTools` 組件導入
  - 添加 `/admin/monitoring-tools` 路由

### 2. 後端 API 實現

#### OAuth2 認證路由

- **文件**: `api/routers/oauth2.py`
- **功能**:
  - `/oauth2/authorize` - OAuth2 授權端點（只有 system_admin）
  - `/oauth2/token` - JWT token 發行端點
  - `/oauth2/userinfo` - 用戶信息端點
  - `/oauth2/jwks` - JWKS 端點
  - `/oauth2/logout` - 登出端點
- **權限控制**:
  - 只有 system_admin 角色可以獲得授權碼
  - JWT token 包含 system_admin 角色

#### 監控代理路由

- **文件**: `api/routers/monitoring_proxy.py`
- **功能**:
  - `/monitoring/grafana/{path:path}` - Grafana 代理
  - `/monitoring/prometheus/{path:path}` - Prometheus 代理
  - `/monitoring/health` - 健康檢查端點
- **權限控制**:
  - 只有 system_admin 角色可以訪問代理
  - 自動轉發請求到上游服務

#### 更新主應用

- **文件**: `api/main.py`
- **改動**:
  - 添加 OAuth2 和監控代理路由註冊

### 3. Docker 配置

#### 更新監控服務配置

- **文件**: `docker-compose.monitoring.yml`
- **新增服務**:

  ```yaml
  oauth2-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:v7.5.1
    ports:
      - "4180:4180"
    volumes:
      - ./monitoring/oauth2-proxy/oauth2-proxy.cfg:/etc/oauth2-proxy.cfg
  ```

#### OAuth2 Proxy 配置

- **文件**: `monitoring/oauth2-proxy/oauth2-proxy.cfg`
- **配置**:
  - 提供者: OIDC (OpenID Connect)
  - 使用 AI-Box 作為 IdP
  - 保護 Grafana 和 Prometheus
  - Cookie 認證
  - 角色檢查 (system_admin)

#### Grafana OAuth2 配置

- **文件**: `monitoring/grafana/provisioning/datasources/oauth2-grafana.ini`
- **配置**:
  - Generic OAuth2 認證
  - 使用 oauth2-proxy 作為認證提供者
  - 角色映射: system_admin → Grafana Admin

### 4. 文檔和工具

#### SSO 集成指南

- **文件**: `docs/系統設計文檔/核心組件/系統管理/AI-Box-SSO集成指南.md`
- **內容**:
  - 架構設計說明
  - 配置步驟
  - 認證流程
  - 權限說明
  - 故障排查

#### 環境變量示例

- **文件**: `.env.sso.example`
- **內容**: SSO 相關環境變量模板

#### 快速設置腳本

- **文件**: `scripts/setup_sso.sh`
- **功能**:
  - 自動生成隨機密鑰
  - 更新 .env 文件
  - 創建必要目錄
  - 生成 Grafana admin 密碼
  - 啟動監控服務
  - 顯示摘要和使用說明

---

## 🎯 SSO 流程說明

### 完整認證流程

```
1. 用戶登入 AI-Box
   ↓
   AI-Box 驗證用戶名/密碼
   ↓
   AI-Box 返回 JWT access_token (包含 system_admin 角色)
   ↓

2. 用戶訪問監控工具
   ↓
   前端導航到 /admin/monitoring-tools
   ↓
   選擇 Grafana 或 Prometheus
   ↓

3. OAuth2 授權流程
   ↓
   AI-Box 檢查用戶是否是 system_admin
   ↓
   如果是，生成授權碼 (authorization code)
   ↓
   重定向回來 (帶授權碼)
   ↓

4. oauth2-proxy 驗證
   ↓
   使用授權碼換取 JWT token
   ↓
   驗證 JWT token 中的 system_admin 角色
   ↓

5. 訪問監控工具
   ↓
   用戶可以訪問 Grafana (OAuth2 認證)
   ↓
   用戶可以訪問 Prometheus (oauth2-proxy 保護)
```

### 權限檢查

| 系統 | 權限檢查 | 檢查位置 |
|------|----------|---------|
| AI-Box OAuth2 端點 | system_admin 角色 | AI-Box: `get_current_user()` |
| oauth2-proxy | system_admin 角色 | JWT token 中 `roles` claim |
| Grafana | system_admin 角色 | OAuth2 group mapping |
| 監控代理路由 | system_admin 角色 | AI-Box: `get_current_user()` |

---

## 📋 實現清單

- [x] 前端監控工具入口頁面
- [x] 前端路由更新
- [x] OAuth2 認證 API (/oauth2/*)
- [x] 監控代理 API (/monitoring/*)
- [x] oauth2-proxy Docker 配置
- [x] oauth2-proxy 配置文件
- [x] Grafana OAuth2 配置
- [x] docker-compose.monitoring.yml 更新
- [x] api/main.py 路由註冊
- [x] 環境變量示例文件
- [x] 快速設置腳本
- [x] SSO 集成指南文檔
- [x] 權限控制實現 (system_admin only)

---

## 🚀 使用方式

### 快速開始

1. **運行設置腳本**:

   ```bash
   bash scripts/setup_sso.sh
   ```

2. **啟動 AI-Box**:

   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **登入 AI-Box** (使用 system_admin 賬號)

4. **訪問監控工具**:
   - <http://localhost:5173/admin/monitoring-tools>

### 手動設置

如果快速設置腳本無法使用，請參考以下步驟：

1. **復制環境變量示例**:

   ```bash
   cp .env.sso.example .env
   ```

2. **生成隨機密鑰**:

   ```bash
   # 生成 OAuth2 client secret
   openssl rand -hex 32

   # 生成 JWT secret
   openssl rand -hex 32

   # 生成 cookie secret
   openssl rand -hex 32
   ```

3. **更新 .env 文件**:
   - 填入生成的密鑰

4. **啟動監控服務**:

   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

5. **創建 system_admin 用戶**:

   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "system_admin",
       "password": "YourPassword",
       "email": "admin@ai-box.local",
       "roles": ["system_admin"]
     }'
   ```

---

## ⚠️ 重要說明

### 安全注意

1. **生產環境必須修改密碼**:
   - `OAUTH2_CLIENT_SECRET`
   - `OAUTH2_COOKIE_SECRET`
   - `JWT_SECRET`
   - `GRAFANA_ADMIN_PASSWORD`

2. **啟用 HTTPS**:
   - 生產環境必須使用 HTTPS
   - 配置 SSL/TLS 證書

3. **權限控制**:
   - 只有 system_admin 角色可以訪問監控工具
   - 其他角色會看到 403 Forbidden 錯誤

### 配置注意

1. **端口分配**:
   - Grafana: 3001
   - Prometheus: 9090
   - oauth2-proxy: 4180
   - AI-Box API: 8000

2. **域名配置**:
   - 開發環境: `http://localhost:*`
   - 生產環境: 實際域名

3. **Cookie 設置**:
   - 生產環境: `cookie_secure = true`
   - 生產環境: `cookie_same_site = "strict"`

---

## 🔍 故障排查

### 問題 1: oauth2-proxy 無法啟動

**症狀**: 容器啟動失敗

**解決方法**:

```bash
# 查看容器日誌
docker logs aibox-oauth2-proxy

# 檢查配置文件
cat monitoring/oauth2-proxy/oauth2-proxy.cfg

# 驗證配置
docker-compose -f docker-compose.monitoring.yml config oauth2-proxy
```

### 問題 2: 無法訪問 Grafana

**症狀**: 訪問 Grafana 時看到 403 Forbidden

**解決方法**:

```bash
# 檢查用戶角色
curl -H "Authorization: Bearer <your_token>" \
  http://localhost:8000/api/v1/users/me

# 查看 JWT payload
python3 -c "
import jwt
token = '<your_token>'
payload = jwt.decode(token, 'your-jwt-secret', algorithms=['HS256'])
print(payload)
"
```

### 問題 3: Grafana OAuth2 配置無效

**症狀**: Grafana 顯示 "OAuth2 not configured"

**解決方法**:

```bash
# 重啟 Grafana
docker-compose -f docker-compose.monitoring.yml restart grafana

# 查看 Grafana 日誌
docker logs aibox-grafana

# 檢查配置文件
cat monitoring/grafana/provisioning/datasources/oauth2-grafana.ini
```

---

## 📊 技術棧

| 組件 | 版本 | 用途 |
|------|------|------|
| oauth2-proxy | v7.5.1 | OAuth2/OIDC 反向代理 |
| Grafana | latest | 監控可視化 |
| Prometheus | latest | 時序數據庫 |
| FastAPI | - | AI-Box 後端框架 |
| JWT | PyJWT | OAuth2 token 簽發/驗證 |

---

## 📚 相關文檔

- [AI-Box SSO 集成指南](docs/系統設計文檔/核心組件/系統管理/AI-Box-SSO集成指南.md)
- [OAuth2 Proxy 文檔](https://oauth2-proxy.github.io/oauth2-proxy/)
- [Grafana OAuth2 文檔](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/)
- [系統安全架構說明](docs/系統設計文檔/安全架構說明.md)

---

**完成日期**: 2026-01-18 14:09 UTC+8
**狀態**: ✅ 實現完成，待測試
