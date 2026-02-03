# Chat Module v2（模塊化架構）

**創建日期**: 2026-01-28  
**最後修改日期**: 2026-01-28  
**對齊**: [Chat-Module-API-v2-規格](../../../docs/系统设计文档/核心组件/Agent平台/KA-Agent/Chat-Module-API-v2-規格.md)、[Chat-Module-v2-實施策略與工程任務](../../../docs/系统设计文档/核心组件/Agent平台/KA-Agent/Chat-Module-v2-實施策略與工程任務.md)

---

## 📋 概述

本模塊為 **v2 Chat API** 實作，路徑前綴 `/api/v2/chat`，與 v1（`api/routers/chat.py`）並存。主聊天經 **SyncHandler → ChatPipeline** 委派既有 `_process_chat_request`，其餘端點（流式、批處理、異步請求、會話歸檔、任務治理）為本模塊實作。

**註冊方式**（`api/main.py`）：

```python
from api.routers import chat_module
app.include_router(chat_module.router, prefix="/api/v2", tags=["Chat V2"])
```

---

## 📁 目錄結構

```
api/routers/chat_module/
├── __init__.py
├── router.py                # 主路由（/chat、/chat/stream、/chat/batch、/chat/requests、sessions、tasks）
├── dependencies.py          # 依賴注入（MoE、Pipeline、限流、緩存等）
├── middleware/              # 限流、緩存、認證增強
│   ├── __init__.py
│   ├── rate_limiter.py
│   ├── cache_middleware.py
│   └── auth_enhancer.py
├── handlers/                # 處理器
│   ├── __init__.py
│   ├── base.py              # BaseHandler、ChatHandlerRequest
│   ├── sync_handler.py      # POST /api/v2/chat
│   ├── stream_handler.py    # POST /api/v2/chat/stream
│   └── batch_handler.py     # POST /api/v2/chat/batch
├── services/
│   ├── __init__.py
│   ├── chat_pipeline.py     # 核心管道（委派 _process_chat_request）
│   ├── async_request_store.py  # 異步請求存儲（POST/GET/retry/priority）
│   ├── session_service.py   # 會話歸檔
│   ├── file_operations.py
│   └── observability.py
├── strategies/              # 模型選擇、Agent 路由、響應格式化
├── validators/              # 請求、權限、配額驗證
├── models/                  # request、response、internal（含 Batch、Error 等）
└── utils/
    ├── error_helper.py      # ErrorHandler（LLM 錯誤 → HTTP 錯誤體）
    ├── file_detection.py
    └── file_parsing.py
```

---

## 🔌 v2 端點一覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/api/v2/chat` | 主聊天（SyncHandler → ChatPipeline） |
| POST | `/api/v2/chat/stream` | 流式聊天（SSE，start/content/file_created/error/done） |
| POST | `/api/v2/chat/batch` | 批處理（並行/串行） |
| POST | `/api/v2/chat/requests` | 創建異步請求，返回 request_id |
| GET | `/api/v2/chat/requests/{request_id}` | 查詢異步請求狀態與結果 |
| POST | `/api/v2/chat/requests/{request_id}/retry` | 重試異步請求 |
| PUT | `/api/v2/chat/requests/{request_id}/priority` | 更新優先級 |
| POST | `/api/v2/chat/sessions/{session_id}/archive` | 會話歸檔 |
| GET | `/api/v2/chat/tasks/{task_id}` | 任務治理（佔位） |
| POST | `/api/v2/chat/tasks/{task_id}/decision` | 任務決策（佔位） |
| POST | `/api/v2/chat/tasks/{task_id}/abort` | 任務中止（佔位） |
| GET | `/api/v2/chat/observability/stats` | 觀測統計 |
| GET | `/api/v2/chat/observability/traces` | 觀測追蹤 |
| GET | `/api/v2/chat/observability/recent` | 最近事件 |
| GET | `/api/v2/chat/sessions/{session_id}/messages` | 會話消息 |
| GET/PUT | `/api/v2/chat/preferences/models` | 用戶偏好（收藏模型） |

---

## 🔧 依賴注入（dependencies.py）

| 函數 | 說明 |
|------|------|
| `get_moe_manager()` | MoE 模型選擇 |
| `get_task_classifier()` | 任務分類 |
| `get_task_analyzer()` | 任務分析 |
| `get_context_manager()` | 上下文管理 |
| `get_storage()` | 文件存儲 |
| `get_metadata_service()` | 文件元數據 |
| `get_arango_client()` | ArangoDB |
| `get_file_permission_service()` | 文件權限 |
| `get_chat_pipeline()` | ChatPipeline 單例（主聊天入口） |
| `get_rate_limiter()` | 限流（記憶體） |
| `get_cache_middleware()` | 緩存中間件（記憶體） |

---

## ✅ 如何運行測試

**單元測試**（chat_module 內 error_helper、request_validator 等）：

```bash
# 專案根目錄，使用 venv
venv/bin/python -m pytest tests/unit/api/routers/chat_module/ -v --tb=short
```

**集成測試**（POST /api/v2/chat、流式 SSE 等）：

```bash
venv/bin/python -m pytest tests/test_chat_v2_endpoint.py -v --tb=short
```

**一併執行**：

```bash
venv/bin/python -m pytest tests/unit/api/routers/chat_module/ tests/test_chat_v2_endpoint.py -v --tb=short
```

**代碼檢查**（實施策略要求）：

```bash
ruff check api/routers/chat_module
mypy api/routers/chat_module
```

---

## 📚 相關文檔

- [Chat-Module-API-v2-規格](../../../docs/系统设计文档/核心组件/Agent平台/KA-Agent/Chat-Module-API-v2-規格.md) — v2 規格與端點詳情
- [Chat-Module-v2-實施策略與工程任務](../../../docs/系统设计文档/核心组件/Agent平台/KA-Agent/Chat-Module-v2-實施策略與工程任務.md) — 階段一～六任務與驗收
- [Chat-舊代碼盤點報告](../../../docs/系统设计文档/核心组件/Agent平台/KA-Agent/Chat-舊代碼盤點報告.md) — 前端改接 v2 缺項與對齊

---

## 📅 更新日誌

- **2026-01-28**: 階段五收尾 — README 更新為 v2 端點、依賴、測試說明，與規格及實作一致
