# MM-Agent（庫管員 Agent）

**版本**：1.0.0
**創建日期**：2026-01-13
**創建人**：Daniel Chung
**最後修改日期**：2026-01-31

## 概述

**datalake-system 為獨立示範系統**。Data-Agent、Dashboard、Datalake、MM-Agent 均使用 `datalake-system/venv`。

MM-Agent（庫管員 Agent）是一個外部業務Agent，作為獨立服務註冊到AI-Box，負責庫存管理業務邏輯：

- **料號查詢**：查詢物料編號、規格、單位等基本信息
- **庫存查詢**：查詢當前庫存數量、庫存位置、庫存狀態
- **缺料分析**：分析庫存是否缺料，計算缺料數量
- **採購單生成**：當庫存缺料時，生成採購單（虛擬動作，用於測試）
- **庫存管理**：其他庫存相關工作（庫存調整、庫存盤點等）

## 架構位置

```
┌─────────────────────────────────────────────────────────┐
│  AI-Box（AI 操作系統）                                   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  第一層：協調層（Agent Orchestrator）              │   │
│  │  - 接收用戶指令：「查詢料號 ABC-123 的庫存」      │   │
│  │  - 任務分析與路由                                 │   │
│  │  - 通過 MCP Client 調用庫管員 Agent               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ MCP Protocol
┌─────────────────────────────────────────────────────────┐
│  庫管員 Agent（外部服務，端口 8003）                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  MCP Server                                       │   │
│  │  - 接收來自 AI-Box 的調用                        │   │
│  │  - 語義分析與職責理解                             │   │
│  │  - 通過 Orchestrator 調用 Data Agent              │   │
│  │  - 結果判斷與業務邏輯處理                         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        ↓ 通過 AI-Box Orchestrator
┌─────────────────────────────────────────────────────────┐
│  Data Agent（Datalake 外部服務，端口 8004）              │
│  ┌──────────────────────────────────────────────────┐   │
│  │  - 查詢外部 Datalake（SeaweedFS）                │   │
│  │  - 返回料號和庫存數據                             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 項目結構

```
mm_agent/
├── __init__.py
├── agent.py                   # MMAgent 主類
├── models.py                  # 數據模型
├── mcp_server.py              # MCP Server實現
├── main.py                    # FastAPI服務主程序
├── orchestrator_client.py     # AI-Box Orchestrator客戶端
├── services/                  # 業務服務模塊
│   ├── __init__.py
│   ├── semantic_analyzer.py  # 語義分析服務（正則+LLM）
│   ├── prompt_manager.py     # 提示詞管理服務
│   ├── context_manager.py     # 上下文管理服務
│   ├── responsibility_analyzer.py # 職責理解服務
│   ├── part_service.py        # 料號查詢服務
│   ├── stock_service.py      # 庫存查詢服務
│   ├── shortage_analyzer.py   # 缺料分析服務
│   └── purchase_service.py   # 採購單生成服務
└── validators/                # 驗證器模塊
    ├── __init__.py
    ├── result_validator.py   # 結果驗證器
    └── data_validator.py     # 數據驗證器
```

## 快速開始

### 1. 環境配置

在AI-Box項目的`.env`文件中添加：

```bash
# MM-Agent Service 配置
MM_AGENT_SERVICE_HOST=localhost
MM_AGENT_SERVICE_PORT=8003
AI_BOX_API_URL=http://localhost:8000
AI_BOX_API_KEY=your-api-key
```

### 2. 啟動服務

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
./scripts/mm_agent/start.sh
```

或使用快速啟動：

```bash
./scripts/mm_agent/quick_start.sh
```

### 3. 查看狀態

```bash
./scripts/mm_agent/status.sh
```

### 4. 查看日誌

```bash
# 查看所有日誌
./scripts/mm_agent/view_logs.sh

# 查看錯誤日誌
./scripts/mm_agent/view_logs.sh error
```

### 5. 停止服務

```bash
./scripts/mm_agent/stop.sh
```

## API端點

### 健康檢查

```bash
curl http://localhost:8003/health
```

### 獲取服務能力

```bash
curl http://localhost:8003/capabilities
```

### 執行任務

```bash
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-task",
    "task_data": {
      "instruction": "查詢料號 ABC-123 的庫存"
    },
    "metadata": {
      "user_id": "user-123",
      "tenant_id": "tenant-123",
      "session_id": "session-123"
    }
  }'
```

## 支持的操作

### 1. 查詢料號信息

**指令示例**：

- "查詢料號 ABC-123 的信息"
- "查詢物料 ABC-123"

### 2. 查詢庫存

**指令示例**：

- "查詢料號 ABC-123 的庫存"
- "ABC-123 的庫存是多少？"

### 3. 缺料分析

**指令示例**：

- "檢查料號 ABC-123 是否需要補貨"
- "ABC-123 缺料嗎？"

### 4. 生成採購單

**指令示例**：

- "為料號 ABC-123 生成採購單，數量 100 件"
- "生成 ABC-123 的採購單，需要 50 個"

### 5. 上下文支持

**指令示例**：

- "剛才查的那個料號，幫我生成採購單"
- "它缺料嗎？"

## 測試

運行測試：

```bash
cd /Users/daniel/GitHub/AI-Box/datalake-system
pytest tests/mm_agent/ -v
```

## 相關文檔

- [MM-Agent 規格書](../.ds-docs/MM-Agent/庫管員-Agent-規格書.md)
- [Agent-開發規範](../../docs/系统设计文档/核心组件/Agent平台/Agent-開發規範.md)
- [Data-Agent-規格書](../../docs/系统设计文档/核心组件/Agent平台/Data-Agent-規格書.md)
