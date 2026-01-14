# 庫管員 Agent - ngrok 配置指南

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## ngrok 認證配置

ngrok 現在需要註冊帳號並配置 authtoken 才能使用。

### 步驟 1: 註冊 ngrok 帳號

1. 訪問：<https://dashboard.ngrok.com/signup>
2. 註冊免費帳號（使用 GitHub、Google 或 Email）

### 步驟 2: 獲取 Authtoken

1. 登錄後訪問：<https://dashboard.ngrok.com/get-started/your-authtoken>
2. 複製您的 authtoken（類似：`2abc123def456ghi789jkl012mno345pqr678stu901vwx234yz_5A6B7C8D9E0F1G2H3I4J5K`）

### 步驟 3: 配置 Authtoken

在終端中運行：

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

將 `YOUR_AUTHTOKEN` 替換為您從 dashboard 複製的實際 token。

### 步驟 4: 啟動 ngrok

```bash
ngrok http 8003
```

### 步驟 5: 複製 URL 並更新 Gateway

ngrok 會顯示：

```
Forwarding  https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:8003
```

複製 `https://xxxx-xxxx-xxxx.ngrok.io` 並告訴我，我會更新 Gateway 配置。

---

## 替代方案：修復 Cloudflare Tunnel

如果不想註冊 ngrok，我們可以嘗試修復 Cloudflare Tunnel 的問題。

### 檢查 Tunnel 狀態

請檢查運行 Tunnel 的終端，看看是否有錯誤訊息或連接成功的日誌。

### 重新啟動 Tunnel

1. 停止當前 Tunnel（在終端按 `Ctrl+C`）
2. 重新啟動：

   ```bash
   cloudflared tunnel --url http://localhost:8003
   ```

3. 等待連接建立（通常需要 1-2 分鐘）
4. 測試新的 URL

---

## 推薦方案

### 方案 A: 使用 ngrok（如果已註冊）

- ✅ 通常更穩定
- ✅ 免費版可用
- ❌ 需要註冊帳號

### 方案 B: 修復 Cloudflare Tunnel

- ✅ 無需額外註冊
- ✅ 已安裝
- ⚠️ 可能需要調試

### 方案 C: 使用 Cloudflare 命名 Tunnel（長期方案）

- ✅ 最穩定
- ✅ 支持固定域名
- ❌ 需要 Cloudflare 帳號和域名

---

## 快速決策

**如果您想快速解決**：

1. 註冊 ngrok 帳號（約 2 分鐘）
2. 配置 authtoken
3. 啟動 ngrok
4. 告訴我 URL，我來更新配置

**如果您想繼續使用 Cloudflare**：

1. 檢查 Tunnel 終端的日誌
2. 重新啟動 Tunnel
3. 等待連接建立
4. 測試新的 URL

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
