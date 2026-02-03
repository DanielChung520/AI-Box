# AI-Box API 接入點造冊

**創建日期**: 2026-01-28  
**最後修改日期**: 2026-01-28  
**用途**: 彙整所有 API 路由／接入點，含代碼位置、說明、是否可由 curl 等工具調用。

---

## 1. 概述

### 1.1 基礎 URL 與前綴

| 項目 | 值 |
|------|-----|
| **API 基礎 URL** | 預設 `http://localhost:8000`（可由 `API_GATEWAY_HOST`、`API_GATEWAY_PORT` 配置） |
| **v1 前綴** | `/api/v1`（`api/core/version.py` 之 `API_PREFIX`） |
| **v2 前綴** | `/api/v2`（僅 Chat 模塊，`api/main.py` 單獨註冊） |
| **無前綴路由** | `/health`、`/ready`、`/version`、`/metrics`（健康與監控） |

### 1.2 造冊欄位說明

| 欄位 | 說明 |
|------|------|
| **方法** | HTTP 方法（GET / POST / PUT / PATCH / DELETE） |
| **完整路徑** | 實際請求路徑（含前綴） |
| **代碼位置** | 定義該端點的文件與行號（或模塊路徑） |
| **說明** | 端點用途簡述 |
| **curl 可調用** | ✅ 可直接用 curl；⚠️ 需認證（Bearer Token）；🔶 流式/SSE（需 `-N` 等）；❌ 僅內部/特殊 |

### 1.3 使用 curl 的通用方式

```bash
# 基礎 URL（依環境替換）
BASE="http://localhost:8000"

# 無需認證（健康檢查、版本）
curl -s "${BASE}/health"
curl -s "${BASE}/version"

# 需認證：先登入取得 token，再帶入請求
TOKEN=$(curl -s -X POST "${BASE}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}' | jq -r '.access_token')
curl -s -H "Authorization: Bearer ${TOKEN}" "${BASE}/api/v1/auth/me"

# 流式/SSE：使用 -N 禁用緩衝
curl -sN -X POST "${BASE}/api/v2/chat/stream" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"hi"}],"model_selector":{"mode":"auto"}}'
```

**完整 OpenAPI 規格**：啟動服務後訪問 `GET /docs`（Swagger UI）或 `GET /openapi.json` 可導出所有端點與參數。

---

## 2. 路由註冊對照（main.py）

以下為 `api/main.py` 中註冊的路由模塊與其**完整路徑前綴**（應用級 prefix + 模塊自身 prefix）。

| 應用前綴 | 模塊 | 模塊 prefix | 完整前綴 | 代碼位置 |
|----------|------|-------------|----------|----------|
| （無） | health | （無） | `/health`, `/ready` | `api/routers/health.py` |
| （無） | metrics | （無） | `/metrics` | `api/routers/metrics.py` |
| （無） | app 直掛 | - | `/version` | `api/main.py` |
| `/api/v1` | auth | `/auth` | `/api/v1/auth` | `api/routers/auth.py` |
| `/api/v1` | data_consent | `/consent` | `/api/v1/consent` | `api/routers/data_consent.py` |
| `/api/v1` | audit_log | `/audit-logs` | `/api/v1/audit-logs` | `api/routers/audit_log.py` |
| `/api/v1` | system_admin | `/admin/system-users` | `/api/v1/admin/system-users` | `api/routers/system_admin.py` |
| `/api/v1` | service_monitor | `/admin/services` | `/api/v1/admin/services` | `api/routers/service_monitor.py` |
| `/api/v1` | service_alert | `/admin/service-alerts` | `/api/v1/admin/service-alerts` | `api/routers/service_alert.py` |
| `/api/v1` | alert_webhook | `/admin/alerts` | `/api/v1/admin/alerts` | `api/routers/alert_webhook.py` |
| `/api/v1` | prometheus_compat | `/admin/services` | `/api/v1/admin/services` | `api/routers/prometheus_compat.py` |
| `/api/v1` | security_group | `/admin/security-groups` | `/api/v1/admin/security-groups` | `api/routers/security_group.py` |
| `/api/v1` | system_config | `/admin/system-configs` | `/api/v1/admin/system-configs` | `api/routers/system_config.py` |
| `/api/v1` | user_account | `/admin/users` | `/api/v1/admin/users` | `api/routers/user_account.py` |
| `/api/v1` | user_sessions | `/admin/sessions` | `/api/v1/admin/sessions` | `api/routers/user_sessions.py` |
| `/api/v1` | user_tasks | `/user-tasks` | `/api/v1/user-tasks` | `api/routers/user_tasks.py` |
| `/api/v1` | agents | （各端點自帶路徑） | `/api/v1/agents/...` | `api/routers/agents.py` |
| `/api/v1` | agent_registry | （自帶） | `/api/v1/...` | `api/routers/agent_registry.py` |
| `/api/v1` | agent_catalog | （自帶） | `/api/v1/...` | `api/routers/agent_catalog.py` |
| `/api/v1` | agent_category | （自帶） | `/api/v1/...` | `api/routers/agent_category.py` |
| `/api/v1` | agent_display_config | （自帶） | `/api/v1/...` | `api/routers/agent_display_config.py` |
| `/api/v1` | agent_auth | （自帶） | `/api/v1/...` | `api/routers/agent_auth.py` |
| `/api/v1` | oauth2_router | `/oauth2` | `/api/v1/oauth2` | `api/routers/oauth2_router.py` |
| `/api/v1` | monitoring_proxy | `/monitoring` | `/api/v1/monitoring` | `api/routers/monitoring_proxy_router.py` |
| `/api/v1` | agent_secret | （自帶） | `/api/v1/...` | `api/routers/agent_secret.py` |
| `/api/v1` | task_analyzer | （自帶） | `/api/v1/task-analyzer/...` | `api/routers/task_analyzer.py` |
| `/api/v1` | agent_registration (public) | `/agent-registration` | `/api/v1/agent-registration` | `api/routers/agent_registration.py` |
| `/api/v1` | agent_registration (admin) | `/admin/agent-requests` | `/api/v1/admin/agent-requests` | `api/routers/agent_registration.py` |
| `/api/v1` | orchestrator | （自帶） | `/api/v1/orchestrator/...` | `api/routers/orchestrator.py` |
| `/api/v1` | planning | （自帶） | `/api/v1/agents/planning/...` | `api/routers/planning.py` |
| `/api/v1` | execution | （自帶） | `/api/v1/...` | `api/routers/execution.py` |
| `/api/v1` | review | （自帶） | `/api/v1/agents/review/...` | `api/routers/review.py` |
| `/api/v1` | mcp | `/mcp` | `/api/v1/mcp` | `api/routers/mcp.py` |
| `/api/v1` | file_metadata | `/files` | `/api/v1/files` | `api/routers/file_metadata.py` |
| `/api/v1` | file_management | `/files` | `/api/v1/files` | `api/routers/file_management.py` |
| `/api/v1` | file_upload | `/files` | `/api/v1/files` | `api/routers/file_upload.py` |
| `/api/v1` | agent_files | （自帶） | `/api/v1/...` | `api/routers/agent_files.py` |
| `/api/v1` | reports | （自帶） | `/api/v1/reports/...` | `api/routers/reports.py` |
| `/api/v1` | chat | `/chat` | `/api/v1/chat` | `api/routers/chat.py` |
| `/api/v2` | chat_module | `/chat` | `/api/v2/chat` | `api/routers/chat_module/router.py` |
| `/api/v1` | config_definitions | `/config/definitions` | `/api/v1/config/definitions` | `api/routers/config_definitions.py` |
| `/api/v1` | ontology | `/ontologies` | `/api/v1/ontologies` | `api/routers/ontology.py` |
| `/api/v1` | llm_models | `/models` | `/api/v1/models` | `api/routers/llm_models.py` |
| `/api/v1` | moe | `/moe` | `/api/v1/moe` | `api/routers/moe.py` |
| `/api/v1` | moe_metrics | `/moe/metrics` | `/api/v1/moe/metrics` | `api/routers/moe_metrics.py` |
| `/api/v1` | rq_monitor | `/rq` | `/api/v1/rq` | `api/routers/rq_monitor.py` |

其餘模塊（workflows、streaming、docs_editing、editing_session、modular_documents、governance、rbac、tools_registry、langgraph、document_editing_v2、chromadb、file_audit、file_lookup、data_quality、model_usage、genai_*、crewai 等）若已在 main 中註冊，其前綴依 `include_router(..., prefix=API_PREFIX)` 或各自 prefix 組成完整路徑。

---

## 3. 按模塊造冊（代表端點）

以下每模塊列出**代表端點**；完整清單請以 **OpenAPI**（`/docs` 或 `/openapi.json`）為準。

### 3.1 健康與版本（無前綴）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/health` | `api/routers/health.py:18` | 健康檢查 | ✅ 可 |
| GET | `/ready` | `api/routers/health.py:37` | 就緒檢查 | ✅ 可 |
| GET | `/version` | `api/main.py` | API 版本資訊 | ✅ 可 |
| GET | `/metrics` | `api/routers/metrics.py:20` | Prometheus 指標 | ✅ 可（若啟用） |

### 3.2 認證（/api/v1/auth）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| POST | `/api/v1/auth/login` | `api/routers/auth.py:174` | 登入，取得 token | ✅ 可 |
| POST | `/api/v1/auth/refresh` | `api/routers/auth.py:257` | 刷新 token | ⚠️ 需 refresh token |
| POST | `/api/v1/auth/logout` | `api/routers/auth.py:317` | 登出 | ⚠️ 需認證 |
| GET | `/api/v1/auth/me` | `api/routers/auth.py:350` | 當前用戶資訊 | ⚠️ 需認證 |
| PUT | `/api/v1/auth/me` | `api/routers/auth.py:375` | 更新當前用戶 | ⚠️ 需認證 |
| POST | `/api/v1/auth/change-password` | `api/routers/auth.py:480` | 修改密碼 | ⚠️ 需認證 |

### 3.3 Chat v1（/api/v1/chat）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| POST | `/api/v1/chat` | `api/routers/chat.py:4593` | 產品級同步 Chat | ⚠️ 需認證 |
| POST | `/api/v1/chat/stream` | `api/routers/chat.py:2701` | 產品級流式 Chat（SSE） | 🔶 SSE，需 -N |
| POST | `/api/v1/chat/requests` | `api/routers/chat.py:5188` | 異步聊天請求 | ⚠️ 需認證 |
| GET | `/api/v1/chat/requests/{request_id}` | `api/routers/chat.py:5262` | 查詢異步請求狀態 | ⚠️ 需認證 |
| GET | `/api/v1/chat/observability/stats` | `api/routers/chat.py:5331` | Chat 統計 | ⚠️ 需認證 |
| GET | `/api/v1/chat/preferences/models` | `api/routers/chat.py:5416` | 收藏模型列表 | ⚠️ 需認證 |
| PUT | `/api/v1/chat/preferences/models` | `api/routers/chat.py:5435` | 設置收藏模型 | ⚠️ 需認證 |

### 3.4 Chat v2（/api/v2/chat）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| POST | `/api/v2/chat` | `api/routers/chat_module/router.py:85` | 產品級同步 Chat（v2） | ⚠️ 需認證 |
| POST | `/api/v2/chat/stream` | `api/routers/chat_module/router.py:120` | 流式 Chat（SSE，與前端對齊） | 🔶 SSE，需 -N |
| POST | `/api/v2/chat/batch` | `api/routers/chat_module/router.py:151` | 批處理 Chat | ⚠️ 需認證 |
| POST | `/api/v2/chat/requests` | `api/routers/chat_module/router.py:181` | 異步請求 | ⚠️ 需認證 |
| GET | `/api/v2/chat/requests/{request_id}` | `api/routers/chat_module/router.py:211` | 查詢異步狀態 | ⚠️ 需認證 |
| GET | `/api/v2/chat/observability/stats` | `api/routers/chat_module/router.py:371` | 觀測統計 | ⚠️ 需認證 |
| GET | `/api/v2/chat/preferences/models` | `api/routers/chat_module/router.py:426` | 收藏模型 | ⚠️ 需認證 |
| PUT | `/api/v2/chat/preferences/models` | `api/routers/chat_module/router.py:455` | 設置收藏模型 | ⚠️ 需認證 |

### 3.5 用戶任務（/api/v1/user-tasks）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/api/v1/user-tasks` | `api/routers/user_tasks.py:42` | 列表用戶任務 | ⚠️ 需認證 |
| GET | `/api/v1/user-tasks/{task_id}` | `api/routers/user_tasks.py:147` | 取得單一任務 | ⚠️ 需認證 |
| POST | `/api/v1/user-tasks` | `api/routers/user_tasks.py:227` | 創建任務 | ⚠️ 需認證 |
| PUT | `/api/v1/user-tasks/{task_id}` | `api/routers/user_tasks.py:343` | 更新任務 | ⚠️ 需認證 |
| DELETE | `/api/v1/user-tasks/{task_id}` | `api/routers/user_tasks.py:442` | 刪除任務 | ⚠️ 需認證 |
| POST | `/api/v1/user-tasks/sync` | `api/routers/user_tasks.py:785` | 同步任務 | ⚠️ 需認證 |

### 3.6 文件管理（/api/v1/files）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/api/v1/files` | `api/routers/file_management.py:205` | 文件列表 | ⚠️ 需認證 |
| GET | `/api/v1/files/search` | `api/routers/file_management.py:339` | 搜索文件 | ⚠️ 需認證 |
| GET | `/api/v1/files/tree` | `api/routers/file_management.py:390` | 文件樹 | ⚠️ 需認證 |
| GET | `/api/v1/files/{file_id}/download` | `api/routers/file_management.py:717` | 下載文件 | ⚠️ 需認證 |
| GET | `/api/v1/files/{file_id}/preview` | `api/routers/file_management.py:1033` | 預覽 | ⚠️ 需認證 |
| POST | `/api/v1/files/v2/upload` | `api/routers/file_upload.py:2210` | 上傳文件 | ⚠️ 需認證（multipart） |
| GET | `/api/v1/files/upload/{file_id}/progress` | `api/routers/file_upload.py:2751` | 上傳進度 | ⚠️ 需認證 |

### 3.7 系統管理員（/api/v1/admin/*）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/api/v1/admin/users` | `api/routers/user_account.py:66` | 用戶列表 | ⚠️ 需管理員 |
| GET | `/api/v1/admin/users/{user_id}` | `api/routers/user_account.py:128` | 用戶詳情 | ⚠️ 需管理員 |
| GET | `/api/v1/admin/system-configs` | `api/routers/system_config.py:61` | 系統配置列表 | ⚠️ 需認證 |
| GET | `/api/v1/admin/services` | `api/routers/service_monitor.py:137` | 服務監控列表 | ⚠️ 需認證 |
| GET | `/api/v1/admin/services/{service_name}` | `api/routers/service_monitor.py:251` | 單一服務狀態 | ⚠️ 需認證 |
| GET | `/api/v1/admin/system-configs/{scope}` | `api/routers/system_config.py:143` | 依 scope 取得配置 | ⚠️ 需認證 |

### 3.8 LLM / MoE（/api/v1/models、/api/v1/moe）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/api/v1/models` | `api/routers/llm_models.py:32` | LLM 模型列表 | ⚠️ 需認證 |
| GET | `/api/v1/models/scenes` | `api/routers/llm_models.py:143` | MoE 場景列表 | ⚠️ 需認證 |
| GET | `/api/v1/moe/scenes` | `api/routers/moe.py:48` | MoE 場景配置 | ⚠️ 需認證 |
| POST | `/api/v1/moe/select` | `api/routers/moe.py:120` | MoE 選模型 | ⚠️ 需認證 |

### 3.9 協調器與 Agent（/api/v1/orchestrator、/api/v1/agents）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| POST | `/api/v1/orchestrator/agents/register` | `api/routers/orchestrator.py:46` | 註冊 Agent | ⚠️ 需認證 |
| GET | `/api/v1/orchestrator/agents` | `api/routers/orchestrator.py:80` | Agent 列表 | ⚠️ 需認證 |
| GET | `/api/v1/orchestrator/agents/discover` | `api/routers/orchestrator.py:112` | 發現 Agent | ⚠️ 需認證 |
| POST | `/api/v1/orchestrator/tasks/submit` | `api/routers/orchestrator.py:144` | 提交任務 | ⚠️ 需認證 |
| GET | `/api/v1/orchestrator/health` | `api/routers/orchestrator.py:351` | 協調器健康 | ✅ 可（或 ⚠️ 依實作） |

### 3.10 任務分析（/api/v1/task-analyzer）

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| POST | `/api/v1/task-analyzer/analyze` | `api/routers/task_analyzer.py:33` | 任務分析 | ⚠️ 需認證 |
| GET | `/api/v1/task-analyzer/health` | `api/routers/task_analyzer.py:67` | 健康檢查 | ✅ 可 |

### 3.11 MCP、審計、配置定義等

| 方法 | 完整路徑 | 代碼位置 | 說明 | curl 可調用 |
|------|-----------|----------|------|-------------|
| GET | `/api/v1/mcp/status` | `api/routers/mcp.py:74` | MCP 狀態 | ⚠️ 需認證 |
| POST | `/api/v1/mcp/tools/call` | `api/routers/mcp.py:154` | 調用 MCP 工具 | ⚠️ 需認證 |
| GET | `/api/v1/audit-logs` | `api/routers/audit_log.py` | 審計日誌 | ⚠️ 需認證 |
| GET | `/api/v1/ontologies` | `api/routers/ontology.py:69` | Ontology 列表 | ⚠️ 需認證 |
| GET | `/api/v1/config/definitions` | `api/routers/config_definitions.py` | 配置定義 | ⚠️ 需認證 |
| GET | `/api/v1/rq/queues` | `api/routers/rq_monitor.py:30` | RQ 隊列列表 | ⚠️ 需認證 |

---

## 4. curl 可調用標記說明

| 標記 | 含義 | 範例 |
|------|------|------|
| **✅ 可** | 無需認證或僅需一般 Header，可直接 `curl <url>` | `/health`、`/version`、部分 health 端點 |
| **⚠️ 需認證** | 需 `Authorization: Bearer <token>`，先 POST 登入取得 token | 大部分 `/api/v1/*`、`/api/v2/*` |
| **🔶 SSE/流式** | 響應為 Server-Sent Events 或流式，建議 `curl -N` 或相應客戶端 | `/api/v1/chat/stream`、`/api/v2/chat/stream` |
| **❌ 僅內部/特殊** | 僅供內部或特殊協議使用，不建議直接用 curl 當常規 API | 依實作標註 |

---

## 5. 如何取得完整端點清單

1. **Swagger UI**：啟動服務後訪問 `http://localhost:8000/docs`，可查看並試用所有已註冊端點。
2. **OpenAPI JSON**：`curl -s http://localhost:8000/openapi.json` 可導出完整規格，含路徑、方法、參數、說明。
3. **本造冊**：以「模塊 + 代表端點」為主；新增或變更路由請同步更新本文件與對應模塊表。

---

## 6. 維護說明

- **新增路由**：在對應模塊小節新增一列，填寫方法、完整路徑、代碼位置、說明、curl 可調用。
- **變更前綴**：同步更新「2. 路由註冊對照」與各表「完整路徑」。
- **代碼位置**：建議填寫 `api/routers/<模塊>.py:行號`，以便快速定位。

---

**文檔版本**: 1.0  
**維護**: 與 `api/main.py` 及 `api/routers/*` 同步更新。
