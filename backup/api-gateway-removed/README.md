# API Gateway 目錄備份說明

## 備份信息

- **備份日期**：2025-01-27
- **備份原因**：功能重複，統一使用 `services/api/` 作為唯一 API Gateway 實現
- **備份位置**：`backup/api-gateway-removed/`

## 刪除原因

`api_gateway/` 目錄與 `services/api/` 目錄功能重複，且 `services/api/` 版本更完整，包含：

1. **更多功能**：20+ 路由（vs api_gateway 的 4 個基本路由）
2. **版本管理**：動態版本信息（vs api_gateway 的固定版本 1.0.0）
3. **安全中間件**：SecurityMiddleware（api_gateway 無）
4. **Request ID 中間件**：RequestIDMiddleware（api_gateway 無）
5. **Prometheus metrics**：完整的 metrics 支持（vs api_gateway 的簡化版）
6. **完整的錯誤處理和日誌記錄**

## 差異對比

### api_gateway 版本（簡化版）

- 只有 4 個基本路由：health, agents, task_analyzer, orchestrator
- 無版本管理
- 無安全中間件
- 無 Request ID 中間件
- 固定版本號 1.0.0
- 簡化的健康檢查（無 Prometheus metrics）

### services/api 版本（完整版）

- 20+ 路由（包含所有 api_gateway 功能 + 額外功能）
- 版本管理（`core/version.py`）
- 安全中間件（`SecurityMiddleware`）
- Request ID 中間件（`RequestIDMiddleware`）
- 動態版本信息
- Prometheus metrics 支持
- 完整的錯誤處理和日誌記錄

## 備份內容

本備份包含完整的 `api_gateway/` 目錄結構：

```
api_gateway/
├── __init__.py
├── main.py
├── core/
│   ├── __init__.py
│   └── response.py
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py
│   └── logging.py
├── routers/
│   ├── __init__.py
│   ├── agents.py
│   ├── health.py
│   ├── orchestrator.py
│   └── task_analyzer.py
└── models/
    └── __init__.py
```

## 恢復方法

如果需要恢復此備份，可以：

1. 將 `backup/api-gateway-removed/api_gateway/` 目錄複製回專案根目錄
2. 注意：恢復後需要更新所有 import 語句，因為專案已統一使用 `services/api/`

## 注意事項

- 此備份僅用於歷史記錄，不建議恢復使用
- 所有功能已由 `services/api/` 完整覆蓋
- 如有 CI/CD 配置引用 `api_gateway`，需要更新為 `services.api.main:app`
