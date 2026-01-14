# 庫管員 Agent 服務啟動診斷報告

**創建日期**: 2026-01-14
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-14

---

## ✅ 已完成的修復

### 1. 服務啟動問題

**問題**: 服務未啟動，端口 8003 沒有監聽

**解決方案**:

- ✅ 已成功啟動服務
- ✅ 服務正在監聽端口 8003
- ✅ 健康檢查端點正常：`http://localhost:8003/health`

**驗證**:

```bash
$ lsof -i :8003
Python  13691 daniel   14u  IPv6 ... TCP localhost:8003 (LISTEN)

$ curl http://localhost:8003/health
{"status":"healthy","agent_status":"available"}
```

### 2. MCP 端點缺失問題

**問題**: `main.py` 中沒有 `/mcp` 端點，導致 Gateway 無法訪問

**解決方案**:

- ✅ 已在 `main.py` 中添加 `/mcp` 端點
- ✅ 集成 MCP Server 到 FastAPI 應用
- ✅ `/mcp` 端點可以正常響應

**驗證**:

```bash
$ curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"warehouse_execute_task",...}]}}
```

### 3. 工具名稱匹配問題

**問題**: 工具名稱 `execute_warehouse_agent_task` 不匹配 Gateway 路由規則 `warehouse_*`

**解決方案**:

- ✅ 已將工具名稱改為 `warehouse_execute_task`
- ✅ 現在可以匹配 `warehouse_*` 路由規則

**驗證**:

```bash
$ curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | jq '.result.tools[].name'

"warehouse_execute_task"
```

---

## ⚠️ 當前問題：522 錯誤

### 問題描述

通過 Cloudflare Gateway 調用時仍然返回 522 錯誤：

```bash
$ curl -X POST https://mcp.k84.org \
  -H "X-Gateway-Secret: ..." \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

error code: 522
```

### 根本原因

**Cloudflare Workers 無法訪問 localhost**

- Cloudflare Workers 運行在 Cloudflare 的邊緣網絡（全球分佈的服務器）
- `localhost:8003` 在 Workers 環境中指向 Workers 服務器本身，而不是您的本地機器
- 即使服務正在運行，Cloudflare Gateway 也無法連接到它

### 解決方案

#### 方案 1: 使用 ngrok（開發/測試環境，推薦）

**步驟**:

1. **安裝 ngrok**（如果還沒安裝）:

   ```bash
   brew install ngrok/ngrok/ngrok
   ```

2. **啟動 ngrok**（在另一個終端）:

   ```bash
   ngrok http 8003
   ```

3. **獲取公網 URL**:
   ngrok 會顯示：

   ```
   Forwarding  https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:8003
   ```

4. **更新 Gateway 路由配置**:

   編輯 `mcp/gateway/wrangler.toml`:

   ```toml
   {
     "pattern": "warehouse_*",
     "target": "https://xxxx-xxxx-xxxx.ngrok.io/mcp"  # 使用 ngrok URL
   }
   ```

5. **部署更新**:

   ```bash
   cd /Users/daniel/GitHub/AI-Box/mcp/gateway
   wrangler deploy
   ```

6. **測試**:

   ```bash
   curl -X POST https://mcp.k84.org \
     -H "X-Gateway-Secret: ..." \
     -H "X-Tool-Name: warehouse_execute_task" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
   ```

#### 方案 2: 使用 Cloudflare Tunnel（生產環境推薦）

**步驟**:

1. **安裝 Cloudflare Tunnel**:

   ```bash
   brew install cloudflare/cloudflare/cloudflared
   ```

2. **登錄**:

   ```bash
   cloudflared tunnel login
   ```

3. **運行 Tunnel**:

   ```bash
   cloudflared tunnel --url http://localhost:8003
   ```

4. **獲取公網 URL** 並更新 Gateway 配置（同方案 1）

---

## 📊 當前狀態總結

### 服務狀態

| 項目 | 狀態 | 詳情 |
|------|------|------|
| **服務運行** | ✅ 正常 | 端口 8003 正在監聽 |
| **健康檢查** | ✅ 正常 | `/health` 端點正常 |
| **MCP 端點** | ✅ 正常 | `/mcp` 端點已添加並正常響應 |
| **工具註冊** | ✅ 正常 | `warehouse_execute_task` 已註冊 |
| **本地測試** | ✅ 正常 | 本地調用 `/mcp` 端點成功 |
| **Gateway 路由** | ✅ 已配置 | `warehouse_*` 路由規則已部署 |
| **Gateway 連接** | ❌ 失敗 | 522 錯誤（Cloudflare 無法訪問 localhost） |

### 配置狀態

| 配置項目 | 狀態 | 詳情 |
|---------|------|------|
| **Gateway 路由** | ✅ 已完成 | `warehouse_*` → `http://localhost:8003/mcp` |
| **Gateway 認證** | ✅ 已完成 | 無認證配置 |
| **工具名稱** | ✅ 已修復 | `warehouse_execute_task`（匹配路由規則） |
| **MCP 端點** | ✅ 已修復 | `/mcp` 端點已添加 |

---

## 🧪 測試結果

### 測試 1: 本地服務測試

**測試命令**:

```bash
curl -X POST http://localhost:8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**結果**: ✅ **成功**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "warehouse_execute_task",
        "description": "執行庫存管理任務...",
        ...
      }
    ]
  }
}
```

### 測試 2: Gateway 路由測試

**測試命令**:

```bash
curl -X POST https://mcp.k84.org \
  -H "X-Gateway-Secret: ..." \
  -H "X-Tool-Name: warehouse_execute_task" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

**結果**: ❌ **522 錯誤**（Cloudflare 無法訪問 localhost）

**分析**:

- ✅ 路由匹配成功（Gateway 識別了 `warehouse_*` 工具）
- ✅ 認證通過（Gateway Secret 正確）
- ❌ 無法連接到目標服務（Cloudflare 無法訪問 localhost）

---

## 🎯 下一步操作

### 立即執行（必須）

1. **使用 ngrok 暴露服務**:

   ```bash
   # 在另一個終端運行
   ngrok http 8003
   ```

2. **更新 Gateway 路由配置**:
   - 將 `target` 改為 ngrok 提供的 HTTPS URL
   - 部署更新

3. **重新測試 Gateway 調用**

### 可選操作

1. **配置 Cloudflare Tunnel**（生產環境）
2. **在 AI-Box 中註冊 Agent**（端點指向 Gateway）

---

## 📝 修改記錄

### 2026-01-14

1. ✅ **添加 `/mcp` 端點** - 在 `main.py` 中集成 MCP Server
2. ✅ **修復工具名稱** - 將 `execute_warehouse_agent_task` 改為 `warehouse_execute_task`
3. ✅ **驗證服務啟動** - 確認服務正常運行並響應請求

---

## 📚 相關文檔

- [庫管員-Agent-522錯誤排查指南](./庫管員-Agent-522錯誤排查指南.md) - 522 錯誤詳細說明
- [庫管員-Agent-Cloudflare-測試指南](./庫管員-Agent-Cloudflare-測試指南.md) - 測試方法
- [庫管員-Agent-規格書](./庫管員-Agent-規格書.md) - Agent 規格說明

---

**版本**: 1.0
**最後更新日期**: 2026-01-14
**維護人**: Daniel Chung
