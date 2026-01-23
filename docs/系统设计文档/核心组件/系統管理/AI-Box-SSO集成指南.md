# 代碼功能說明: AI-Box SSO 配置指南

# 創建日期: 2026-01-18 14:09 UTC+8

# 創建人: Daniel Chung

# 最後修改日期: 2026-01-18 14:09 UTC+8

# AI-Box SSO 集成指南 - Grafana 和 Prometheus

## 概述

本指南說明如何配置 AI-Box、Grafana 和 Prometheus 的 SSO（單點登錄）集成，確保只有擁有 `system_admin` 角色的用戶才能訪問監控工具。

---

## 架構設計

### 1. 系統架構

```
用戶瀏覽器
    ↓
┌─────────────────────────────────────────┐
│  AI-Box (FastAPI)                  │
│  - JWT 認證                         │
│  - OAuth2 授權服務器                │
│  - /oauth2/* 端點                  │
│  - /monitoring/* 代理端點             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  oauth2-proxy (反向代理)             │
│  - 端口: 4180                      │
│  - 保護 Grafana 和 Prometheus        │
│  - 使用 AI-Box 作為 IdP             │
└─────────────────────────────────────────┘
    ↓
┌─────────────┬──────────────────────────┐
│ Grafana     │ Prometheus             │
│ (OAuth2)    │ (API Token)           │
│ 端口: 3001  │ 端口: 9090            │
└─────────────┴──────────────────────────┘
```

### 2. 認證流程

1. **用戶登錄 AI-Box**
   - 用戶輸入用戶名/密碼
   - AI-Box 返回 JWT access_token

2. **用戶訪問監控工具**
   - 前端導航到 `/admin/monitoring-tools`
   - 選擇 Grafana 或 Prometheus

3. **OAuth2 授權流程**
   - 前端調用 `/oauth2/authorize?client_id=ai-box-oauth2-client`
   - AI-Box 驗證用戶是否是 system_admin
   - 如果是，生成授權碼並重定向回來

4. **oauth2-proxy 驗證**
   - oauth2-proxy 用授權碼換取 JWT token
   - 驗證 JWT token 的 system_admin 角色
   - 放行用戶訪問 Grafana/Prometheus

5. **訪問監控工具**
   - 用戶可以訪問 Grafana（OAuth2 認證）
   - 用戶可以訪問 Prometheus（oauth2-proxy 保護）

---

## 配置步驟

### 步驟 1：環境變量配置

在 `.env` 文件中添加：

```bash
# OAuth2 配置
OAUTH2_CLIENT_ID=ai-box-oauth2-client
OAUTH2_CLIENT_SECRET=change-this-secret-in-production
OAUTH2_COOKIE_SECRET=change-this-cookie-secret-in-production

# JWT 配置
JWT_SECRET=your-secret-key-here-change-in-production

# 監控服務 URL
GRAFANA_URL=http://localhost:3001
PROMETHEUS_URL=http://localhost:9090
```

### 步驟 2：Docker Compose 配置

已經在 `docker-compose.monitoring.yml` 中添加了 oauth2-proxy 服務：

```yaml
oauth2-proxy:
  image: quay.io/oauth2-proxy/oauth2-proxy:v7.5.1
  container_name: aibox-oauth2-proxy
  restart: unless-stopped
  ports:
    - "4180:4180"
  volumes:
    - ./monitoring/oauth2-proxy/oauth2-proxy.cfg:/etc/oauth2-proxy.cfg
  environment:
    - OAUTH2_PROXY_CLIENT_ID=ai-box-oauth2-client
    - OAUTH2_PROXY_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET}
    - OAUTH2_PROXY_COOKIE_SECRET=${OAUTH2_COOKIE_SECRET}
```

### 步驟 3：Grafana 配置

Grafana 配置已經更新為使用 OAuth2：

- **配置文件**: `monitoring/grafana/provisioning/datasources/oauth2-grafana.ini`
- **認證方式**: Generic OAuth2
- **授權 URL**: `http://oauth2-proxy:4180/oauth2/start`

### 步驟 4：啟動監控服務

```bash
# 啟動所有監控服務
docker-compose -f docker-compose.monitoring.yml up -d

# 檢查服務狀態
docker-compose -f docker-compose.monitoring.yml ps

# 查看日誌
docker-compose -f docker-compose.monitoring.yml logs -f oauth2-proxy
```

### 步驟 5：測試 SSO

1. **登錄 AI-Box**

   ```
   http://localhost:5173/login
   ```

2. **訪問監控工具入口**

   ```
   http://localhost:5173/admin/monitoring-tools
   ```

3. **選擇 Grafana**
   - 應該自動重定向到 OAuth2 授權
   - 成功後訪問 Grafana

4. **選擇 Prometheus**
   - 應該自動重定向到 OAuth2 授權
   - 成功後訪問 Prometheus

---

## 權限說明

### 系統管理員 (system_admin)

- ✅ 可以訪問 Grafana
- ✅ 可以訪問 Prometheus
- ✅ 可以查看所有監控數據
- ✅ 可以配置告警規則

### 普通用戶 (user/guest)

- ❌ 無法訪問監控工具
- ❌ 會看到 403 Forbidden 錯誤

---

## 故障排查

### 問題 1：無法訪問 Grafana

**症狀**: 重定向後顯示 403 Forbidden

**解決方法**:

```bash
# 檢查 AI-Box 日誌
docker logs aibox-grafana

# 檢查用戶角色
curl -H "Authorization: Bearer <your_token>" \
  http://localhost:8000/api/v1/users/me

# 確認用戶有 system_admin 角色
```

### 問題 2：oauth2-proxy 配置錯誤

**症狀**: oauth2-proxy 容器無法啟動

**解決方法**:

```bash
# 檢查配置文件
cat monitoring/oauth2-proxy/oauth2-proxy.cfg

# 查看日誌
docker logs aibox-oauth2-proxy

# 驗證配置
docker-compose -f docker-compose.monitoring.yml config oauth2-proxy
```

### 問題 3：JWT token 驗證失敗

**症狀**: Token verification failed

**解決方法**:

```bash
# 確保 JWT_SECRET 一致
# AI-Box 和 oauth2-proxy 必須使用相同的 JWT_SECRET

# 檢查 token 有效性
python -c "
import jwt
import sys

token = sys.argv[1]
try:
    payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
    print('Token is valid')
    print(payload)
except Exception as e:
    print(f'Token is invalid: {e}')
" <your_jwt_token>
```

---

## 安全建議

1. **生產環境必須修改的秘密**
   - `OAUTH2_CLIENT_SECRET`
   - `OAUTH2_COOKIE_SECRET`
   - `JWT_SECRET`
   - `GRAFANA_ADMIN_PASSWORD`

2. **啟用 HTTPS**
   - 生產環境必須使用 HTTPS
   - 配置 SSL/TLS 證書

3. **定輪換密碼**
   - 定期更新 JWT secret
   - 定期更新 OAuth2 client secret

4. **限制訪問**
   - 使用防火牆限制 Prometheus/Grafana 訪問
   - 只允許通過 oauth2-proxy 訪問

---

## 技術文檔

- [OAuth2 Proxy 文檔](https://oauth2-proxy.github.io/oauth2-proxy/)
- [Grafana OAuth2 認證](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/generic-oauth/)
- [FastAPI OAuth2](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

---

**最後更新**: 2026-01-18 14:09 UTC+8
**維護者**: Daniel Chung
