# 庫管員-Agent 註冊配置指南

**創建日期**: 2026-01-13
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13

---

## 📋 概述

本文檔說明如何在 AI-Box 系統中註冊和配置外部 Agent（物管員-Agent）。

AI-Box 支持兩種方式連接外部 Agent：

- ✅ **HTTP API**：標準 REST API 方式
- ✅ **MCP (Model Context Protocol)**：MCP 協議方式（**推薦，符合規格書**）

根據[庫管員-Agent-規格書](./庫管員-Agent-規格書.md)，物管員-Agent 應該使用 **MCP Protocol** 方式註冊。

---

## 🔑 前置準備

### 1. 獲取 Secret ID 和 Secret Key

外部 Agent 註冊前，需要先從 AI-Box 獲取 Secret ID 和 Secret Key 進行身份驗證。

#### 方式一：通過 API 生成（推薦）

```bash
# 生成新的 Secret ID/Key 對
curl -X POST http://localhost:8000/api/v1/agents/secrets/generate \
  -H "Content-Type: application/json"
```

**響應示例**：

```json
{
  "success": true,
  "data": {
    "secret_id": "aibox-warehouse-agent-1234567890-abc123",
    "secret_key": "sk_live_<YOUR_SECRET_KEY_HERE>",
    "expires_at": null
  },
  "message": "Secret generated successfully"
}
```

**⚠️ 重要**：

- `secret_key` **只會顯示一次**，請妥善保存
- 保存 `secret_id` 和 `secret_key` 用於後續註冊

#### 方式二：通過環境變量（開發/測試環境）

在 AI-Box 服務器中設置環境變量：

```bash
export AGENT_SECRET_ID="aibox-warehouse-agent-1234567890-abc123"
export AGENT_SECRET_KEY="sk_live_<YOUR_SECRET_KEY_HERE>"
```

重啟 AI-Box 服務後，系統會自動載入這些 Secret。

### 2. 驗證 Secret（註冊前必須執行）

在註冊 Agent 前，必須先驗證 Secret ID 和 Secret Key：

```bash
curl -X POST http://localhost:8000/api/v1/agents/secrets/verify \
  -H "Content-Type: application/json" \
  -d '{
    "secret_id": "aibox-warehouse-agent-1234567890-abc123",
    "secret_key": "sk_live_<YOUR_SECRET_KEY_HERE>"
  }'
```

**響應示例**：

```json
{
  "success": true,
  "data": {
    "valid": true,
    "is_bound": false,
    "status": "active"
  },
  "message": "Secret verified successfully"
}
```

**驗證要求**：

- ✅ `valid` 必須為 `true`
- ✅ `is_bound` 必須為 `false`（未綁定到其他 Agent）

---

## 🔧 註冊配置

### 方式一：通過前端界面註冊（推薦）

1. **打開 Agent 註冊界面**

   - 在 AI-Box 前端界面點擊「註冊新 Agent」按鈕
2. **填寫基本資訊**

   - **Agent 名稱**：`物管員 Agent` 或 `Warehouse Manager Agent`
   - **Agent 類型**：選擇 `Execution (執行)`
   - **描述**：`庫存管理業務 Agent，負責料號查詢、庫存查詢、缺料分析和採購單生成`
   - **能力列表**：`query_part`, `query_stock`, `analyze_shortage`, `generate_purchase_order`
   - **圖標**：選擇合適的圖標（例如：`FaWarehouse`）
3. **配置端點（關鍵步驟）**

   - **取消勾選**「內部 Agent」
   - **協議類型**：選擇 `MCP (Model Context Protocol)`
   - **MCP 端點 URL**：`http://your-warehouse-agent-host:8003/mcp`
     - 例如：`http://localhost:8003/mcp`（本地開發）
     - 或：`http://192.168.1.100:8003/mcp`（內網部署）
     - 或：`https://warehouse-agent.example.com/mcp`（公網部署）
4. **Secret 身份驗證**

   - 輸入從 AI-Box 獲取的 `Secret ID`
   - 輸入對應的 `Secret Key`
   - 點擊「驗證 Secret」按鈕
   - **等待驗證成功**（顯示綠色成功提示）
5. **權限配置（可選）**

   - **認證方式**：可選 API Key、mTLS 證書、IP 白名單等（額外安全層）
   - **資源訪問權限**：
     - Memory 命名空間：可留空或填寫允許訪問的命名空間
     - 允許使用的工具：可留空或填寫允許的工具列表
     - LLM Provider：可留空或填寫允許的 LLM 提供商
6. **提交註冊**

   - 檢查所有必填項是否已填寫
   - 點擊「註冊 Agent」按鈕
   - 等待註冊完成
7. **管理員核准**

   - 註冊後，Agent 狀態為「註冊中」（`REGISTERING`）
   - 需要管理員核准後，狀態才會變為「在線」（`ONLINE`）
   - 核准方式：

     ```bash
     curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/approve?approved=true \
       -H "Content-Type: application/json"
     ```

### 方式二：通過 API 直接註冊

#### MCP 協議註冊（推薦）

```bash
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "warehouse-manager-agent",
    "agent_type": "execution",
    "name": "物管員 Agent",
    "endpoints": {
      "http": null,
      "mcp": "http://localhost:8003/mcp",
      "protocol": "mcp",
      "is_internal": false
    },
    "capabilities": [
      "query_part",
      "query_stock",
      "analyze_shortage",
      "generate_purchase_order"
    ],
    "metadata": {
      "version": "2.2",
      "description": "庫存管理業務 Agent，負責料號查詢、庫存查詢、缺料分析和採購單生成",
      "tags": ["warehouse", "inventory", "purchase"],
      "icon": "FaWarehouse"
    },
    "permissions": {
      "read": true,
      "write": false,
      "execute": true,
      "admin": false,
      "secret_id": "aibox-warehouse-agent-1234567890-abc123",
      "allowed_memory_namespaces": [],
      "allowed_tools": [],
      "allowed_llm_providers": []
    }
  }'
```

#### HTTP 協議註冊（備選方案）

如果物管員-Agent 也提供 HTTP API，可以使用 HTTP 方式註冊：

```bash
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "warehouse-manager-agent",
    "agent_type": "execution",
    "name": "物管員 Agent",
    "endpoints": {
      "http": "http://localhost:8003/api",
      "mcp": null,
      "protocol": "http",
      "is_internal": false
    },
    "capabilities": [
      "query_part",
      "query_stock",
      "analyze_shortage",
      "generate_purchase_order"
    ],
    "metadata": {
      "version": "2.2",
      "description": "庫存管理業務 Agent",
      "tags": ["warehouse", "inventory"],
      "icon": "FaWarehouse"
    },
    "permissions": {
      "read": true,
      "write": false,
      "execute": true,
      "admin": false,
      "secret_id": "aibox-warehouse-agent-1234567890-abc123",
      "api_key": "your-api-key-here",
      "allowed_memory_namespaces": [],
      "allowed_tools": [],
      "allowed_llm_providers": []
    }
  }'
```

---

## ✅ 註冊後驗證

### 1. 檢查註冊狀態

```bash
curl http://localhost:8000/api/v1/agents/warehouse-manager-agent
```

**響應示例**：

```json
{
  "success": true,
  "data": {
    "agent_id": "warehouse-manager-agent",
    "name": "物管員 Agent",
    "status": "registering",
    "is_internal": false,
    "protocol": "mcp",
    "endpoints": {
      "mcp": "http://localhost:8003/mcp",
      "protocol": "mcp",
      "is_internal": false
    },
    "capabilities": [
      "query_part",
      "query_stock",
      "analyze_shortage",
      "generate_purchase_order"
    ]
  }
}
```

### 2. 管理員核准（將狀態從 `registering` 轉為 `online`）

```bash
curl -X POST "http://localhost:8000/api/v1/agents/warehouse-manager-agent/approve?approved=true" \
  -H "Content-Type: application/json"
```

### 3. 驗證 Agent 可用性

核准後，Agent 狀態應為 `online`：

```bash
curl http://localhost:8000/api/v1/agents/warehouse-manager-agent
```

**期望響應**：

```json
{
  "success": true,
  "data": {
    "agent_id": "warehouse-manager-agent",
    "status": "online",
    ...
  }
}
```

---

## 📝 配置參數說明

### Agent ID

- **格式**：小寫字母、數字、連字符（`warehouse-manager-agent`）
- **唯一性**：必須在整個系統中唯一
- **建議**：使用有意義的名稱，如 `warehouse-manager-agent`

### Agent 類型

- **planning**：規劃型 Agent
- **execution**：執行型 Agent（**物管員-Agent 使用此類型**）
- **review**：審查型 Agent

### 協議類型

- **http**：HTTP REST API
- **mcp**：Model Context Protocol（**推薦，符合規格書**）

### MCP 端點格式

- **標準格式**：`http://host:port/mcp`
- **示例**：
  - `http://localhost:8003/mcp`（本地）
  - `http://192.168.1.100:8003/mcp`（內網 IP）
  - `https://warehouse-agent.example.com/mcp`（HTTPS）

### 權限配置

#### Secret ID（必須）

- 外部 Agent **必須提供** Secret ID
- 在註冊前必須先驗證 Secret ID 和 Secret Key
- Secret ID 會自動綁定到 Agent ID

#### 資源訪問權限（可選）

- **allowed_memory_namespaces**：允許訪問的 Memory 命名空間列表
- **allowed_tools**：允許使用的工具列表
- **allowed_llm_providers**：允許使用的 LLM 提供商列表

---

## 🔍 常見問題

### Q1: Secret ID 和 Secret Key 在哪裡獲取？

**A**: 通過 API 生成：

```bash
curl -X POST http://localhost:8000/api/v1/agents/secrets/generate
```

或聯繫 AI-Box 管理員申請。

### Q2: 註冊後狀態一直是 `registering`，無法使用？

**A**: 需要管理員核准。執行：

```bash
curl -X POST "http://localhost:8000/api/v1/agents/{agent_id}/approve?approved=true"
```

### Q3: 可以使用 HTTP 協議還是必須使用 MCP？

**A**: 兩種都可以，但根據規格書，**推薦使用 MCP 協議**。

### Q4: MCP 端點 URL 格式是什麼？

**A**: 標準格式為 `http://host:port/mcp`，例如：

- `http://localhost:8003/mcp`
- `https://warehouse-agent.example.com/mcp`

### Q5: 如何更新 Agent 配置？

**A**: 目前需要先取消註冊，然後重新註冊。未來版本將支持更新接口。

---

## 📚 相關文檔

- [庫管員-Agent-規格書](./庫管員-Agent-規格書.md) - 完整的 Agent 規格說明
- [AI-Box-Agent-架構規格書](./AI-Box-Agent-架構規格書.md) - Agent 架構總體設計
- [Agent-開發規範.md](./Agent-開發規範.md) - Agent 開發指南
- [Agent-部署方式建議.md](./Agent-部署方式建議.md) - Agent 部署方式建議

---

## 🎯 總結

1. ✅ **支持兩種協議**：HTTP 和 MCP（**推薦 MCP**）
2. ✅ **必須提供 Secret ID/Key**：用於外部 Agent 身份驗證
3. ✅ **註冊前驗證 Secret**：通過 `/agents/secrets/verify` 端點
4. ✅ **管理員核准**：註冊後需要管理員核准才能使用
5. ✅ **MCP 端點格式**：`http://host:port/mcp`

**推薦配置流程**：

1. 生成 Secret ID/Key
2. 驗證 Secret
3. 通過前端界面註冊（選擇 MCP 協議）
4. 管理員核准
5. 驗證 Agent 可用性

---

**版本**: 1.0
**最後更新日期**: 2026-01-13
**維護人**: Daniel Chung
