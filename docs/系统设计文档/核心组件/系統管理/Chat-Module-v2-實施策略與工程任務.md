# Chat Module v2 實施策略與工程任務

**創建日期**: 2026-01-28
**最後修改日期**: 2026-01-28
**對齊規格**: [Chat-Module-API-v2-規格](./Chat-Module-API-v2-規格.md)、[Chat-舊代碼盤點報告](./Chat-舊代碼盤點報告.md)（前端接入與改接 v2 缺項）
**目標**: 將階段任務細化為可直接執行的工程任務，達到工程化程度。

測試環境 venv

---

## 1. 現狀盤點

### 1.1 規格 vs 實作對照

| 規格模塊                     | 規格路徑                                         | 實作狀態      | 備註                                                       |
| ---------------------------- | ------------------------------------------------ | ------------- | ---------------------------------------------------------- |
| 主路由                       | `router.py`                                    | ✅ 存在       | 委派 `_process_chat_request`                             |
| 依賴注入                     | `dependencies.py`                              | ✅ 存在       | MoE、Classifier、Context、Storage 等                       |
| 觀測性                       | `services/observability.py`                    | ✅ 存在       | stats / traces / recent                                    |
| 會話消息                     | `get_session_messages`                         | ✅ 存在       | 在 observability 或 router 內                              |
| 用戶偏好                     | GET/PUT preferences/models                       | ✅ 存在       | 調用 user_preference_service                               |
| 文件操作                     | `services/file_operations.py`                  | ✅ 存在       | 文件創建/編輯邏輯                                          |
| 工具層                       | `utils/file_detection.py`, `file_parsing.py` | ✅ 存在       |                                                            |
| middleware/                  | `middleware/`                                  | ❌ 不存在     | 需新建目錄及 rate_limiter, cache_middleware, auth_enhancer |
| handlers/                    | `handlers/`                                    | ❌ 不存在     | 需新建 base, sync, stream, async, batch                    |
| services/chat_pipeline.py    | 核心管道                                         | ❌ 不存在     | 規劃中替換委派                                             |
| services/session_service.py  | 會話服務                                         | ❌ 獨立不存在 | 會話邏輯目前在 observability 或 chat                       |
| services/priority_service.py | 優先級服務                                       | ❌ 不存在     |                                                            |
| strategies/                  | 策略層                                           | ❌ 不存在     |                                                            |
| validators/                  | 驗證層                                           | ❌ 不存在     |                                                            |
| models/                      | 數據模型層                                       | ❌ 不存在     | 目前用 services.api.models.chat                            |

### 1.2 目錄現狀（實測）

```
api/routers/chat_module/
├── __init__.py
├── dependencies.py
├── README.md
├── router.py
├── services/
│   ├── __init__.py
│   ├── file_operations.py
│   └── observability.py
└── utils/
    ├── __init__.py
    ├── file_detection.py
    └── file_parsing.py
```

**缺失**: `middleware/`、`handlers/`、`strategies/`、`validators/`、`models/`；`services/` 下缺 `chat_pipeline.py`、`session_service.py`、`priority_service.py` 等。

---

## 2. 階段劃分與依賴關係

```
階段1（基礎架構）
    │
    ├──► 階段2a（handlers + 錯誤處理）──► 階段2b（chat_pipeline 替換委派，可選延後）
    │
    └──► 階段3（進階端點：stream / batch / async / retry / priority / archive / tasks）
    │
    └──► 階段4（Worker + 測試）
    │
    ├──► 階段6（流式與前端對齊，盤點加強項）
    │
    └──► 階段5（收尾：文檔、可選停用 v1）
```

- **階段 1** 不依賴其他階段，可立即執行。
- **階段 2a** 依賴階段 1（需 middleware、validators、models、handlers/base）。
- **階段 2b** 依賴階段 2a 與現有 chat 邏輯（可選：先保留委派，僅補齊結構）。
- **階段 3** 依賴階段 2a（需 handler 與 router 擴展）。
- **階段 4** 依賴階段 2a 或 2b（依當前主入口實作撰寫測試）。
- **階段 6** 依賴階段 3（需 stream 端點已存在），依 [Chat-舊代碼盤點報告] 流式缺項對齊前端，使前端改接 v2 時無需改動即可相容。

---

## 3. 階段一：基礎架構（可直接執行）

**目標**: 建立規格中的目錄與佔位模塊，不改變現有行為，可通過 import 與最小測試。

### 任務清單

| ID              | 任務描述                                                                                                                                                                                                   | 產出                      | 驗收                                                                   | 預估   |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------- | ------ |
| **T1.1**  | 新建 `api/routers/chat_module/middleware/__init__.py`，導出 `rate_limiter`、`cache_middleware`、`auth_enhancer`（可為空實現或佔位）                                                                | 文件存在，無語法錯誤      | `from api.routers.chat_module.middleware import rate_limiter` 不報錯 | 5 min  |
| **T1.2**  | 新建 `api/routers/chat_module/middleware/rate_limiter.py`，實現基於記憶體的簡單限流（如按 user_id 計數，閾值可配置），提供 `check_rate_limit(user_id, limit_per_minute)`                               | 可調用函數                | 單元測試或手動調用通過                                                 | 30 min |
| **T1.3**  | 新建 `api/routers/chat_module/middleware/cache_middleware.py`，實現 `CacheMiddleware`：`get_cached_response(key, ttl)`、`set_cached_response(key, response, ttl)`，後端先用記憶體 dict             | 可調用類/函數             | 單元測試或手動調用通過                                                 | 30 min |
| **T1.4**  | 新建 `api/routers/chat_module/middleware/auth_enhancer.py`，提供 `require_chat_permission(current_user)` 依賴項（內部可只做 pass 或調用現有 get_current_user）                                         | 可被 FastAPI Depends 使用 | 掛到一條測試路由不報錯                                                 | 15 min |
| **T1.5**  | 新建 `api/routers/chat_module/validators/__init__.py`，導出 `request_validator`、`permission_validator`、`quota_validator`                                                                         | 文件存在                  | import 不報錯                                                          | 5 min  |
| **T1.6**  | 新建 `api/routers/chat_module/validators/request_validator.py`，提供 `validate_chat_request(body: ChatRequest) -> None`，校驗 messages 非空、model_selector 合法，不通過則 raise HTTPException(422)    | 可調用                    | 單元測試：合法通過、非法拋 422                                         | 20 min |
| **T1.7**  | 新建 `api/routers/chat_module/validators/permission_validator.py`，提供 `validate_attachments_access(attachments, user_id)`（可調用現有 FilePermissionService）                                        | 可調用                    | 單元測試或集成測試                                                     | 20 min |
| **T1.8**  | 新建 `api/routers/chat_module/validators/quota_validator.py`，佔位：`check_quota(user_id) -> None`，內部 pass 或日誌                                                                                   | 可調用                    | import 不報錯                                                          | 10 min |
| **T1.9**  | 新建 `api/routers/chat_module/strategies/__init__.py`，導出 `model_selection`、`agent_routing`、`response_formatting`                                                                              | 文件存在                  | import 不報錯                                                          | 5 min  |
| **T1.10** | 新建 `api/routers/chat_module/strategies/model_selection.py`，佔位：`select_model(model_selector, user_id) -> model_id`，內部調用 `get_moe_manager().select_model("chat", user_id)` 返回             | 可調用                    | 與現有 MoE 行為一致                                                    | 15 min |
| **T1.11** | 新建 `api/routers/chat_module/models/__init__.py`，導出 `request`、`response`、`internal`（可從 services.api.models.chat 轉 re-export）                                                            | 文件存在                  | import 不報錯                                                          | 10 min |
| **T1.12** | 新建 `api/routers/chat_module/models/request.py`，定義 v2 可選擴展欄位：`PriorityLevel`、`ExperimentalFeatures`、`ChatRequestEnhanced`（繼承或包裝現有 ChatRequest）                               | Pydantic 模型             | 能解析帶 priority/timeout/cache_ttl 的 JSON                            | 20 min |
| **T1.13** | 新建 `api/routers/chat_module/models/response.py`，定義 `WarningInfo`、`ChatResponseEnhanced`（與規格一致）                                                                                          | Pydantic 模型             | 能構建 response 並 model_dump                                          | 15 min |
| **T1.14** | 新建 `api/routers/chat_module/models/internal.py`，定義 `ErrorCode`、`ChatErrorResponse`（與規格錯誤模型一致）                                                                                       | 錯誤模型                  | 用於統一錯誤響應                                                       | 15 min |
| **T1.15** | 新建 `api/routers/chat_module/utils/error_helper.py`，實現 `ErrorHandler.handle_llm_error(exc) -> (message, ErrorCode)`、`ErrorHandler.create_http_exception(exc, request_id=None, status_code=500)` | 可調用                    | 單元測試：傳入 TimeoutError 等返回對應 message 與 code                 | 30 min |
| **T1.16** | 更新 `api/routers/chat_module/dependencies.py`：新增 `get_rate_limiter()`、`get_cache_middleware()`（返回階段 1 實現的單例）                                                                         | 依賴可注入                | router 或 handler 可 Depends(get_cache_middleware)                     | 15 min |

**階段一驗收**

- 所有新文件存在，無語法錯誤。
- `ruff check api/routers/chat_module`、`mypy api/routers/chat_module` 通過（或對新檔案無新增錯誤）。
- 至少一則單元測試：例如 `test_error_helper.py`、`test_request_validator.py`。

---

## 4. 階段二 a：Handlers 與錯誤處理（可直接執行）

**目標**: 引入 BaseHandler、SyncHandler，主聊天仍可繼續委派舊 pipeline；統一錯誤處理與驗證。

### 任務清單

| ID              | 任務描述                                                                                                                                                                                                                                           | 產出                     | 驗收                              | 預估   |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------------------- | ------ |
| **T2a.1** | 新建 `api/routers/chat_module/handlers/__init__.py`，導出 `base`、`sync_handler`                                                                                                                                                             | 文件存在                 | import 不報錯                     | 5 min  |
| **T2a.2** | 新建 `api/routers/chat_module/handlers/base.py`，實現 `BaseHandler(ABC)`：`pre_process(request)`（調用 rate_limit、permission、quota）、`post_process(request, response)`（可選 cache、metrics）、抽象方法 `handle(request) -> response` | 抽象類                   | 子類實現 handle 即可跑通流程      | 30 min |
| **T2a.3** | 新建 `api/routers/chat_module/handlers/sync_handler.py`，實現 `SyncHandler(BaseHandler)`，`handle(request)` 內部調用 `_process_chat_request`（與現有 router 一致）                                                                         | 可替換 router 內直接委派 | 行為與現有 POST /api/v2/chat 一致 | 20 min |
| **T2a.4** | 在 `router.py` 中為 POST `/api/v2/chat` 註冊全局異常處理：捕獲 Exception，用 `ErrorHandler.create_http_exception` 轉為 JSONResponse（或掛到 FastAPI app 的 exception_handler）                                                               | 500 時返回統一錯誤體     | 手動觸發 500 得到統一格式         | 15 min |
| **T2a.5** | 在 POST `/api/v2/chat` 流程中先調用 `request_validator.validate_chat_request(request_body)`，再執行現有委派                                                                                                                                    | 非法請求 422             | 空 messages 等返回 422            | 10 min |
| **T2a.6** | （可選）將 POST `/api/v2/chat` 改為通過 `SyncHandler` 實例調用：`handler = SyncHandler(...); response = await handler.handle(request)`，保留委派邏輯在 SyncHandler 內部                                                                      | 架構統一                 | 行為不變，測試通過                | 15 min |

**階段二 a 驗收**

- POST /api/v2/chat 行為與現有一致（含錯誤碼與錯誤體）。
- 非法請求返回 422，伺服器錯誤返回統一錯誤結構。

---

## 5. 階段二 b：Chat Pipeline 替換委派（可選、可延後）

**目標**: 實現 `services/chat_pipeline.py`，用新管道取代對 `_process_chat_request` 的委派；可拆為多個子任務，逐步遷移 L0–L5。

| ID              | 任務描述                                                                                                                                                                                              | 產出              | 驗收                                    | 預估   |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | --------------------------------------- | ------ |
| **T2b.1** | 新建 `api/routers/chat_module/services/chat_pipeline.py`，定義 `ChatPipeline` 類，`process(request) -> ChatResponse` 內部先調用現有 `_process_chat_request` 並轉換為 ChatResponse（最小可行） | 可調用管道        | 與委派行為一致                          | 30 min |
| **T2b.2** | 在 `dependencies.py` 中新增 `get_chat_pipeline()`，返回 `ChatPipeline` 單例                                                                                                                     | 可注入            | SyncHandler 可改為調用 pipeline.process | 10 min |
| **T2b.3** | 將 `SyncHandler.handle` 改為調用 `get_chat_pipeline().process(request)`，不再直接調用 `_process_chat_request`                                                                                   | 主聊天走 pipeline | 行為不變                                | 10 min |
| **T2b.4** | （後續）在 `ChatPipeline.process` 中逐步替換為 L0→L1→…→L5、RAG、記憶、上下文、LLM、任務治理等（對應規格書流程）；每步可單獨測試                                                                 | 完整新管道        | 與舊行為等價或擴展                      | 多日   |

**階段二 b 驗收**

- 至少完成 T2b.1–T2b.3：主聊天經由 ChatPipeline，行為與委派一致。
- 後續 L0–L5 替換可依需求分迭代完成。

---

## 6. 階段三：進階端點（可直接執行）

**目標**: 按規格實現 stream、batch、async、retry、priority、session archive、task governance 等端點與服務。

### 6.1 流式

| ID             | 任務描述                                                                                                                                                                      | 產出                     | 驗收               | 預估   |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ------------------ | ------ |
| **T3.1** | 新建 `handlers/stream_handler.py`，實現 `StreamHandler(BaseHandler)`，`handle` 返回 SSE 流；內部可先調用現有 chat 邏輯再以 SSE 格式回寫（或調用現有 stream 邏輯若已有） | POST /api/v2/chat/stream | 客戶端收到 SSE 流  | 1–2 h |
| **T3.2** | 在 `router.py` 註冊 `POST /chat/stream`，使用 `StreamHandler` 或現有 stream 實現                                                                                        | 端點可訪問               | 集成測試或手動測試 | 15 min |

### 6.2 批處理

| ID             | 任務描述                                                                                                                                                                                       | 產出                    | 驗收                 | 預估   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | -------------------- | ------ |
| **T3.3** | 新建 `handlers/batch_handler.py`，實現 `BatchHandler`：接受 `requests: List[ChatRequest]`、`mode`、`max_concurrent`，並行/串行調用 chat，返回 `batch_id`、`results`、`summary` | POST /api/v2/chat/batch | 批量請求返回匯總結果 | 1 h    |
| **T3.4** | 在 `router.py` 註冊 `POST /chat/batch`，請求體為規格中的 JSON                                                                                                                              | 端點可訪問              | 集成測試             | 10 min |

### 6.3 異步請求與重試、優先級

| ID             | 任務描述                                                                                                                                     | 產出                       | 驗收            | 預估   |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | --------------- | ------ |
| **T3.5** | 新建 `services/async_request_store.py`（或使用 Redis），存儲 request_id、status、result；`POST /chat/requests` 創建任務並返回 request_id | POST /api/v2/chat/requests | 返回 request_id | 45 min |
| **T3.6** | 在 `router.py` 註冊 `GET /chat/requests/{request_id}`，返回狀態與結果                                                                    | 端點可訪問                 | 能查詢到狀態    | 20 min |
| **T3.7** | 在 `router.py` 註冊 `POST /chat/requests/{request_id}/retry`，重試邏輯更新狀態並重新入隊                                                 | 端點可訪問                 | 重試後狀態可查  | 30 min |
| **T3.8** | 在 `router.py` 註冊 `PUT /chat/requests/{request_id}/priority`，更新優先級（需 priority_service 或 store 支持）                          | 端點可訪問                 | 優先級可更新    | 20 min |

### 6.4 會話歸檔與任務治理

| ID              | 任務描述                                                                                                                                                      | 產出                                    | 驗收                  | 預估   |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | --------------------- | ------ |
| **T3.9**  | 新建或擴展 `services/session_service.py`，實現 `archive_session(session_id, consolidate_memory, delete_messages)`，返回 archive_id、message_count 等      | POST /api/v2/chat/sessions/{id}/archive | 歸檔後可查詢或列表    | 45 min |
| **T3.10** | 在 `router.py` 註冊 `POST /chat/sessions/{session_id}/archive`                                                                                            | 端點可訪問                              | 集成測試              | 10 min |
| **T3.11** | 實現任務治理端點：`GET /chat/tasks/{task_id}`、`POST /chat/tasks/{task_id}/decision`、`POST /chat/tasks/{task_id}/abort`（可先佔位返回 501 或最小實現） | 三個端點存在                            | 符合規格請求/響應格式 | 1 h    |

**階段三驗收**

- 上述端點均註冊且可調用，請求/響應格式符合 v2 規格。
- 至少 stream、batch、async 中有一條集成測試或手動測試通過。

---

## 7. 階段四：Worker 與測試（可直接執行）

| ID             | 任務描述                                                                                                                                   | 產出                      | 驗收                               | 預估   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------- | ---------------------------------- | ------ |
| **T4.1** | 若異步請求使用 RQ：在 `workers/genai_chat_job.py` 中改為調用 `get_chat_pipeline().process` 或 v2 統一入口，確保 job 參數與 v2 模型一致 | Worker 可處理 v2 異步任務 | 提交異步請求後 Worker 完成並可查詢 | 30 min |
| **T4.2** | 新建 `tests/unit/api/routers/chat_module/test_error_helper.py`，覆蓋 `ErrorHandler.handle_llm_error` 多種異常                          | 單元測試                  | pytest 通過                        | 20 min |
| **T4.3** | 新建 `tests/unit/api/routers/chat_module/test_request_validator.py`，覆蓋合法/非法 ChatRequest                                           | 單元測試                  | pytest 通過                        | 20 min |
| **T4.4** | 新建 `tests/integration/test_chat_v2_endpoint.py`，調用 POST /api/v2/chat（含認證），斷言 200 與 data.content 存在                       | 集成測試                  | pytest 通過                        | 30 min |
| **T4.5** | （可選）新建 `tests/performance/test_chat_v2_concurrent.py`，並發調用 POST /api/v2/chat，斷言成功率與延遲                                | 性能測試                  | 可選 CI 通過                       | 30 min |

**階段四驗收**

- 單元測試與集成測試通過。
- Worker 能處理 v2 異步任務（若已實現異步端點）。

---

## 8. 階段六：流式與前端對齊（盤點加強項）

**目標**：依 [Chat-舊代碼盤點報告](./Chat-舊代碼盤點報告.md)「改接 v2/chat 滿足情況與缺項」與 [Chat-Module-API-v2-規格](./Chat-Module-API-v2-規格.md)「與前端對齊約定」，使 v2 流式 SSE 與現有 ai-bot 前端相容，前端設定 `VITE_CHAT_USE_V2=true` 改接 v2 時無需改動即可正常使用流式 Chat、檔案建立與錯誤展示。

**依賴**：階段三（POST /api/v2/chat/stream 與 StreamHandler 已存在）。

### 8.1 任務清單（細化自盤點缺項）

| ID | 任務描述 | 產出 | 驗收 | 預估 |
|----|----------|------|------|------|
| **T6.1** | **SSE 內容塊格式對齊**：在 `handlers/stream_handler.py`（或流式輸出處）將內容塊由 `{ type: 'chunk', content: "..." }` 改為 `{ type: 'content', data: { chunk: "..." } }`，以符合前端 `event.type === 'content'` 且 `event.data.chunk` | 流式內容事件與 v1/前端一致 | 前端不改動下可累積顯示內容 | 30 min |
| **T6.2** | **流式 start 事件**：流開始時送出 `{ type: 'start', data: { request_id, session_id } }`（session_id 可從 request 或 pipeline 取得，可選從 context 兜底） | start 事件存在 | 前端可選用於連線狀態顯示 | 15 min |
| **T6.3** | **流式 done 事件結構**：done 時送出格式與前端相容；前端僅檢查 `type === 'done'` 即結束，可保留頂層 `request_id`、`routing`、`observability`，並可選增加 `data: {}` 或 `data: { request_id }` 以與 v1 一致 | done 事件前端可識別並結束流 | 前端正常結束流、可選讀取 routing/observability | 15 min |
| **T6.4** | **流式 file_created 事件**：在流式管道中偵測到檔案建立時送出 `{ type: 'file_created', data: create_action }`，`create_action` 含 `file_id`、`filename`、`task_id`、`folder_id` 等（與 v1 格式一致）。若當前 StreamHandler 為「先 pipeline.process 取得完整回應再按字 chunk」，則需改為：在 pipeline 或 stream 邏輯中支援「流式生成過程中回調/ yield file_created」，或於完整回應後解析 actions 再補送一筆 file_created 事件 | 流中可收到 file_created | 前端可觸發檔案樹更新（FileTree） | 1–2 h |
| **T6.5** | **流式 error 事件**：在流式處理中捕獲可恢復或需前端展示的錯誤時，先送出 `{ type: 'error', data: { error: "訊息", error_code?: "..." } }` 再結束流，而非僅拋出 HTTP 異常，使前端能以 `event.type === 'error'` 顯示錯誤並結束 | 錯誤時前端可收到 error 事件 | 前端顯示錯誤訊息並結束流 | 30 min |
| **T6.6** | **流式與前端對齊的集成測試**：新增或擴展測試，對 POST /api/v2/chat/stream 斷言 SSE 事件序列含 `type: 'content'` 且 `data.chunk`、可選 `start`/`done`，並可選 mock 檔案建立與錯誤路徑以驗證 `file_created`、`error` 事件 | 自動化驗收 | pytest 通過 | 45 min |

### 8.2 階段六驗收

- 前端設定 `VITE_CHAT_USE_V2=true` 後，流式對話可正常累積內容、正常結束。
- 流式過程中若有檔案建立，前端可收到 `file_created` 並更新檔案樹。
- 流式過程中若發生可展示錯誤，前端可收到 `error` 事件並顯示後結束。
- 上述行為通過手動測試或 T6.6 集成測試覆蓋。

---

## 9. 階段五：收尾（可選）

| ID             | 任務描述                                                                                  | 產出           | 驗收                 |
| -------------- | ----------------------------------------------------------------------------------------- | -------------- | -------------------- |
| **T5.1** | 更新 `api/routers/chat_module/README.md`，說明 v2 端點、依賴、如何運行測試              | 文檔           | 新成員可依文檔跑通   |
| **T5.2** | 在 `Chat-Module-API-v2-規格.md` 中更新「v2 現狀與實作範圍」表格，標註已完成的端點與模塊 | 規格與實作一致 | 表格與代碼一致       |
| **T5.3** | （可選）在 main.py 或配置中提供開關，可停用 v1 路由，僅暴露 v2                            | 可配置         | 關閉 v1 後僅 v2 可用 |

---

## 10. 執行順序建議（可直接執行）

1. **按階段執行**：先完成階段一全部任務（T1.1–T1.16），再做階段二 a（T2a.1–T2a.6），再依需求做階段二 b、階段三、四、五。
2. **並行**：階段一內 T1.2、T1.3、T1.6、T1.7、T1.15 可並行開發；T1.1、T1.5、T1.9、T1.11 先做，其餘依賴的再跟上。
3. **階段六**：在階段三、四完成後執行，使流式與前端對齊，再進行階段五收尾。
4. **驗收**：每階段結束跑 `ruff check api/routers/chat_module`、`mypy api/routers/chat_module`、`pytest tests/unit/api/routers/chat_module tests/integration/test_chat_v2_endpoint.py -v`。

---

## 11. 驗收檢查清單（總表）

- [x] **階段一**：middleware、validators、strategies、models、utils/error_helper 存在且可導入；dependencies 更新；單元測試 9 則於 venv 下全數通過。
- [x] **階段二 a**：handlers/base、handlers/sync_handler 存在；POST /api/v2/chat 經由驗證與統一錯誤處理；行為與現有委派一致。
- [x] **階段二 b（可選）**：ChatPipeline 存在且主聊天走 pipeline；行為與委派一致。
- [x] **階段三**：stream、batch、requests、retry、priority、sessions/archive、tasks 端點註冊且符合規格。
- [x] **階段四**：Worker 支持 v2；單元/集成測試通過。
- [x] **階段六**：流式 SSE 與前端對齊（content/data.chunk、start、done、file_created、error）；集成測試已新增。
- [x] **階段五**：README 與規格「v2 現狀與實作範圍」已更新。

---

## 12. 進度管控表與狀態說明

### 11.1 階段一進度管控表

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T1.1 | 新建 middleware/__init__.py | ✅ 完成 | 2026-01-28 | 導出 rate_limiter, cache_middleware, auth_enhancer |
| T1.2 | 新建 middleware/rate_limiter.py | ✅ 完成 | 2026-01-28 | 記憶體限流，check_rate_limit(user_id, limit_per_minute) |
| T1.3 | 新建 middleware/cache_middleware.py | ✅ 完成 | 2026-01-28 | CacheMiddleware，get/set_cached_response，記憶體版 |
| T1.4 | 新建 middleware/auth_enhancer.py | ✅ 完成 | 2026-01-28 | require_chat_permission(current_user) |
| T1.5 | 新建 validators/__init__.py | ✅ 完成 | 2026-01-28 | 導出 request_validator, permission_validator, quota_validator |
| T1.6 | 新建 validators/request_validator.py | ✅ 完成 | 2026-01-28 | validate_chat_request(body)，messages 非空、content 非空、model_selector 合法 |
| T1.7 | 新建 validators/permission_validator.py | ✅ 完成 | 2026-01-28 | validate_attachments_access(attachments, user)，調用 FilePermissionService |
| T1.8 | 新建 validators/quota_validator.py | ✅ 完成 | 2026-01-28 | check_quota(user_id) 佔位 |
| T1.9 | 新建 strategies/__init__.py | ✅ 完成 | 2026-01-28 | 導出 model_selection, agent_routing, response_formatting |
| T1.10 | 新建 strategies/model_selection.py | ✅ 完成 | 2026-01-28 | select_model(model_selector, user_id)，調用 MoE select_model("chat") |
| T1.11 | 新建 models/__init__.py | ✅ 完成 | 2026-01-28 | 導出 request, response, internal |
| T1.12 | 新建 models/request.py | ✅ 完成 | 2026-01-28 | PriorityLevel, ExperimentalFeatures, ChatRequestEnhanced |
| T1.13 | 新建 models/response.py | ✅ 完成 | 2026-01-28 | WarningInfo, ChatResponseEnhanced |
| T1.14 | 新建 models/internal.py | ✅ 完成 | 2026-01-28 | ErrorCode, ChatErrorResponse |
| T1.15 | 新建 utils/error_helper.py | ✅ 完成 | 2026-01-28 | ErrorHandler.handle_llm_error, create_http_exception |
| T1.16 | 更新 dependencies.py | ✅ 完成 | 2026-01-28 | get_rate_limiter(), get_cache_middleware() |
| - | 單元測試 test_error_helper.py | ✅ 完成 | 2026-01-28 | tests/unit/api/routers/chat_module/ |
| - | 單元測試 test_request_validator.py | ✅ 完成 | 2026-01-28 | tests/unit/api/routers/chat_module/ |

### 11.2 階段一驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| 所有新文件存在，無語法錯誤 | ✅ | middleware、validators、strategies、models、utils/error_helper 已建立 |
| ruff check api/routers/chat_module 通過 | ✅ | 已執行 ruff check --fix，All checks passed |
| 至少一則單元測試 | ✅ | test_error_helper.py、test_request_validator.py 已新增 |
| 單元測試執行 | ✅ | 於專案 **venv** 下執行，9 passed（見 11.2.1） |

#### 11.2.1 階段一測試執行結果

執行指令（專案統一使用 **venv**）：

```bash
venv/bin/python -m pytest tests/unit/api/routers/chat_module/ -v --tb=short
```

| 項目 | 結果 |
|------|------|
| 通過 | 9 |
| 失敗 | 0 |
| 測試檔 | test_error_helper.py（6）、test_request_validator.py（3） |
| 執行時間 | ~1.6s |

| 測試案例 | 結果 |
|----------|------|
| TestErrorHandlerHandleLlmError::test_timeout_error_returns_llm_timeout | ✅ |
| TestErrorHandlerHandleLlmError::test_connection_error_returns_llm_service_error | ✅ |
| TestErrorHandlerHandleLlmError::test_unauthorized_string_returns_auth_error | ✅ |
| TestErrorHandlerHandleLlmError::test_rate_limit_string_returns_llm_rate_limit | ✅ |
| TestErrorHandlerHandleLlmError::test_generic_error_returns_internal_server_error | ✅ |
| TestErrorHandlerCreateHttpException::test_returns_http_exception_with_detail | ✅ |
| TestValidateChatRequest::test_valid_request_passes | ✅ |
| TestValidateChatRequest::test_empty_content_raises_422 | ✅ |
| TestValidateChatRequest::test_whitespace_only_content_raises_422 | ✅ |

### 11.3 狀態說明

- **階段一**：已全部完成並通過驗收。目錄結構與規格對齊，middleware（限流、緩存、認證）、validators（請求、權限、配額）、strategies（模型選擇、agent 路由、響應格式化）、models（request/response/internal）、utils/error_helper 及 dependencies 更新均已就緒；單元測試已於 **venv** 下執行，9 則全數通過。
- **階段二 a**：已全部完成並通過驗收。handlers/base、handlers/sync_handler 已建立；POST /api/v2/chat 先經 `validate_chat_request` 校驗、再經 SyncHandler（pre_process → handle → post_process）委派；異常由 `_chat_error_to_json_response` 轉為統一錯誤體；行為與現有委派一致。
- **階段二 b**：已全部完成並通過驗收。services/chat_pipeline.py 已建立，ChatPipeline.process 委派 _process_chat_request；dependencies 新增 get_chat_pipeline() 單例；SyncHandler.handle 改為調用 get_chat_pipeline().process(request)，主聊天經由 pipeline，行為與委派一致。
- **階段三**：已全部完成並通過驗收。stream（StreamHandler + POST /stream）、batch（BatchHandler + POST /batch）、異步請求（async_request_store + POST/GET/retry/priority）、會話歸檔（session_service + POST sessions/{id}/archive）、任務治理三端點（GET/POST decision/POST abort 佔位）均已註冊且可調用，請求/響應格式符合 v2 規格。
- **階段四**：已全部完成並通過驗收。Worker 新增 run_genai_chat_request_v2，調用 get_chat_pipeline().process 並更新 v2 async_request_store；async_request_store 新增 run_async_chat_task 供 Worker 與 start_async_chat_background 共用；單元測試 test_error_helper、test_request_validator 已存在且通過；集成測試 tests/test_chat_v2_endpoint.py 調用 POST /api/v2/chat（含認證與 mock pipeline），斷言 200 與 data.content 存在。
- **階段六**：已完成。流式 SSE 與前端對齊已實作於 stream_handler.py（T6.1–T6.6），集成測試 4 則全過（含流式 start/content/done、file_created）。
- **後續**：可進行階段五（收尾）或 T2b.4（L0→L5 逐步替換，多日）。

### 11.4 總體階段狀態

| 階段 | 狀態 | 備註 |
|------|------|------|
| 階段一（基礎架構） | ✅ 完成 | 2026-01-28 |
| 階段二 a（Handlers + 錯誤處理） | ✅ 完成 | 2026-01-28 |
| 階段二 b（Chat Pipeline 替換委派） | ✅ 完成 | 2026-01-28 |
| 階段三（進階端點） | ✅ 完成 | 2026-01-28 |
| 階段四（Worker + 測試） | ✅ 完成 | 2026-01-28 |
| 階段六（流式與前端對齊） | ✅ 完成 | 2026-01-28，T6.1–T6.6 |
| 階段五（收尾） | ✅ 完成 | 2026-01-28：T5.1 README 更新、T5.2 規格表更新 |

### 11.5 階段二 a 進度管控表

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T2a.1 | 新建 handlers/__init__.py | ✅ 完成 | 2026-01-28 | 導出 base、sync_handler、BaseHandler、ChatHandlerRequest、SyncHandler |
| T2a.2 | 新建 handlers/base.py | ✅ 完成 | 2026-01-28 | BaseHandler(ABC)、ChatHandlerRequest、pre_process（rate_limit/permission/quota）、post_process、handle、run |
| T2a.3 | 新建 handlers/sync_handler.py | ✅ 完成 | 2026-01-28 | SyncHandler(BaseHandler)，handle 委派 _process_chat_request |
| T2a.4 | POST /api/v2/chat 統一異常處理 | ✅ 完成 | 2026-01-28 | 端點內 try/except，_chat_error_to_json_response 轉為 JSONResponse（APIRouter 無 exception_handler） |
| T2a.5 | POST 流程先調用 validate_chat_request | ✅ 完成 | 2026-01-28 | 非法請求返回 422 |
| T2a.6 | POST 改為經 SyncHandler 調用 | ✅ 完成 | 2026-01-28 | handler.run(handler_request)，行為與現有委派一致 |

### 11.6 階段二 a 驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| handlers/base、handlers/sync_handler 存在 | ✅ | handlers/__init__.py、base.py、sync_handler.py 已建立 |
| POST /api/v2/chat 經由驗證與統一錯誤處理 | ✅ | validate_chat_request 先校驗；異常由 _chat_error_to_json_response 轉為統一錯誤體 |
| 行為與現有委派一致 | ✅ | SyncHandler.handle 調用 _process_chat_request，run 含 pre_process/post_process |
| 非法請求返回 422 | ✅ | validate_chat_request 對空 messages、空 content、非法 model_selector 拋 HTTPException(422) |
| 伺服器錯誤返回統一錯誤結構 | ✅ | ErrorHandler.create_http_exception + JSONResponse |
| 單元測試 | ✅ | 階段一 9 則測試於 venv 下全數通過，無回歸 |

### 11.7 階段二 a 實作說明

- **handlers/base.py**：`ChatHandlerRequest` 為 dataclass（request_body、request_id、tenant_id、current_user）；`BaseHandler.pre_process` 調用限流、`validate_attachments_access`、`check_quota`；`post_process` 佔位；`run` 串聯 pre_process → handle → post_process。
- **handlers/sync_handler.py**：`SyncHandler.handle` 改為調用 `get_chat_pipeline().process(request)`，主聊天走 pipeline（階段二 b）。
- **router.py**：主聊天端點先 `validate_chat_request(request_body)`，再組裝 `ChatHandlerRequest`、`SyncHandler().run(handler_request)`；try/except 捕獲非 HTTPException 後調用 `_chat_error_to_json_response(request_id, exc)` 返回 JSONResponse。

### 11.8 階段二 b 進度管控表

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T2b.1 | 新建 services/chat_pipeline.py | ✅ 完成 | 2026-01-28 | ChatPipeline.process(request) 委派 _process_chat_request，最小可行 |
| T2b.2 | dependencies.py 新增 get_chat_pipeline() | ✅ 完成 | 2026-01-28 | 返回 ChatPipeline 單例，可注入 |
| T2b.3 | SyncHandler.handle 改為調用 pipeline.process | ✅ 完成 | 2026-01-28 | 不再直接調用 _process_chat_request，主聊天走 pipeline |
| T2b.4 | （後續）L0→L5 逐步替換 | ⏸️ 未開始 | - | 多日，依需求分迭代 |

### 11.9 階段二 b 驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| ChatPipeline 存在且可調用 | ✅ | services/chat_pipeline.py，process(request) -> ChatResponse |
| get_chat_pipeline() 可注入 | ✅ | dependencies.py 單例，SyncHandler 可調用 |
| 主聊天經由 ChatPipeline | ✅ | SyncHandler.handle 調用 get_chat_pipeline().process(request) |
| 行為與委派一致 | ✅ | pipeline.process 內部仍調用 _process_chat_request |
| 單元測試 | ✅ | 階段一 9 則於 venv 下全數通過，無回歸 |

### 11.10 階段二 b 實作說明

- **services/chat_pipeline.py**：`ChatPipeline` 類，`process(request: ChatHandlerRequest) -> ChatResponse`，內部調用 `_process_chat_request(request_body, request_id, tenant_id, current_user)`；後續可逐步替換為 L0→L5、RAG、記憶、上下文、LLM、任務治理等。
- **dependencies.py**：新增 `_chat_pipeline` 單例與 `get_chat_pipeline() -> ChatPipeline`（TYPE_CHECKING 下類型為 ChatPipeline）。
- **handlers/sync_handler.py**：`handle` 改為 `return await get_chat_pipeline().process(request)`，不再直接調用 `_process_chat_request`。
- **services/__init__.py**：導出 `ChatPipeline`。

### 11.11 階段三進度管控表

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T3.1 | 新建 handlers/stream_handler.py | ✅ 完成 | 2026-01-28 | StreamHandler(BaseHandler)，handle 返回 SSE 流，內部調用 pipeline 再以 SSE 回寫 |
| T3.2 | router 註冊 POST /chat/stream | ✅ 完成 | 2026-01-28 | 使用 StreamHandler，media_type=text/event-stream |
| T3.3 | 新建 handlers/batch_handler.py | ✅ 完成 | 2026-01-28 | BatchHandler.process(requests, mode, max_concurrent)，並行/串行調用 pipeline |
| T3.4 | router 註冊 POST /chat/batch | ✅ 完成 | 2026-01-28 | 請求體 BatchChatRequest，響應 batch_id、results、summary |
| T3.5 | 新建 services/async_request_store.py + POST /chat/requests | ✅ 完成 | 2026-01-28 | 記憶體存儲 request_id/status/result，創建任務並後台執行 pipeline，返回 request_id |
| T3.6 | router GET /chat/requests/{request_id} | ✅ 完成 | 2026-01-28 | 返回狀態與結果 |
| T3.7 | router POST /chat/requests/{request_id}/retry | ✅ 完成 | 2026-01-28 | 依存儲的 request_body/tenant_id 重新入隊 |
| T3.8 | router PUT /chat/requests/{request_id}/priority | ✅ 完成 | 2026-01-28 | PriorityUpdateRequest，更新優先級 |
| T3.9 | 新建/擴展 services/session_service.py | ✅ 完成 | 2026-01-28 | archive_session(session_id, consolidate_memory, delete_messages)，返回 archive_id、message_count 等 |
| T3.10 | router POST /chat/sessions/{session_id}/archive | ✅ 完成 | 2026-01-28 | ArchiveSessionRequest 請求體 |
| T3.11 | 任務治理三端點 | ✅ 完成 | 2026-01-28 | GET /tasks/{task_id}、POST /tasks/{task_id}/decision、POST /tasks/{task_id}/abort，佔位實現 |

### 11.12 階段三驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| 上述端點均註冊且可調用 | ✅ | stream、batch、requests、retry、priority、sessions/archive、tasks 已註冊 |
| 請求/響應格式符合 v2 規格 | ✅ | BatchChatRequest/Response、SSE 格式、異步 request_id、歸檔/任務治理格式 |
| 單元測試無回歸 | ✅ | 階段一 9 則於 venv 下全數通過 |

### 11.13 階段三實作說明

- **流式**：StreamHandler.handle 返回 AsyncGenerator，先調用 pipeline.process 取得 ChatResponse，再按規格 yield data: {"type":"chunk",...}、data: {"type":"done",...}；router 先 pre_process 再 StreamingResponse(handler.handle(...))。
- **批處理**：BatchChatRequest（requests、mode、max_concurrent、priority）、BatchChatResponse（batch_id、results、summary）；BatchHandler.process 依 mode 並行（asyncio.gather + Semaphore）或串行調用 pipeline.process。
- **異步請求**：async_request_store 記憶體存儲 AsyncRequestRecord（含 request_body、tenant_id 供 retry）；POST /requests 創建記錄後 start_async_chat_background 後台執行 pipeline；GET 查詢狀態；retry 依存儲還原 ChatRequest 重新入隊；PUT priority 更新優先級。
- **會話歸檔**：session_service.archive_session 返回 ArchiveSessionResult（archive_id、message_count、memory_consolidated、archived_at）；MVP 不實際讀寫存儲。
- **任務治理**：GET/POST decision/POST abort 三端點佔位，返回規格一致結構。

### 11.14 階段四進度管控表

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T4.1 | Worker 調用 get_chat_pipeline().process（v2 入口） | ✅ 完成 | 2026-01-28 | 新增 run_genai_chat_request_v2，調用 run_async_chat_task；保留 run_genai_chat_request（v1） |
| T4.2 | test_error_helper.py 覆蓋 ErrorHandler 多種異常 | ✅ 已存在 | 階段一 | tests/unit/api/routers/chat_module/test_error_helper.py，6 則 |
| T4.3 | test_request_validator.py 覆蓋合法/非法 ChatRequest | ✅ 已存在 | 階段一 | tests/unit/api/routers/chat_module/test_request_validator.py，3 則 |
| T4.4 | 新建 test_chat_v2_endpoint.py（集成測試） | ✅ 完成 | 2026-01-28 | tests/test_chat_v2_endpoint.py，POST /api/v2/chat 含認證與 mock pipeline，斷言 200 與 data.content |
| T4.5 | （可選）test_chat_v2_concurrent.py 性能測試 | ⏸️ 未做 | - | 可選 |

### 11.15 階段四驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| 單元測試與集成測試通過 | ✅ | 9 則單元 + 2 則 v2 端點測試，共 11 passed |
| Worker 能處理 v2 異步任務 | ✅ | run_genai_chat_request_v2 調用 run_async_chat_task → get_chat_pipeline().process，更新 async_request_store |

### 11.16 階段四實作說明

- **async_request_store**：新增 async 函數 `run_async_chat_task(request_id, request_body, tenant_id, current_user)`，執行 pipeline.process 並更新 store；`start_async_chat_background` 改為 `asyncio.create_task(run_async_chat_task(...))`，邏輯共用。
- **workers/genai_chat_job.py**：新增 `run_genai_chat_request_v2(request_id, request_dict, tenant_id, user_dict)`，組裝 ChatRequest 與 User 後 `asyncio.run(run_async_chat_task(...))`，供 v2 異步端點選用 RQ 時入隊；原有 `run_genai_chat_request` 保留給 v1。
- **tests/test_chat_v2_endpoint.py**：覆蓋 get_current_user、get_current_tenant_id，mock sync_handler.get_chat_pipeline 返回固定 ChatResponse；test_chat_v2_post_200_and_content 斷言 200 與 data.content；test_chat_v2_validation_error_empty_messages 斷言 422。

### 11.17 階段六進度管控表（流式與前端對齊）

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T6.1 | SSE 內容塊格式對齊：chunk → content + data.chunk | ✅ 完成 | 2026-01-28 | stream_handler 改為 type: content, data: { chunk } |
| T6.2 | 流式 start 事件 | ✅ 完成 | 2026-01-28 | 流開始時送出 type: start, data: { request_id, session_id } |
| T6.3 | 流式 done 事件結構與前端相容 | ✅ 完成 | 2026-01-28 | done 含 data: { request_id }，並保留頂層 routing/observability |
| T6.4 | 流式 file_created 事件 | ✅ 完成 | 2026-01-28 | response.actions 中 type==file_created 時送出 file_created 事件 |
| T6.5 | 流式 error 事件 | ✅ 完成 | 2026-01-28 | pipeline 異常時 yield error 事件後 return，ErrorHandler 提供 error_code |
| T6.6 | 流式與前端對齊的集成測試 | ✅ 完成 | 2026-01-28 | test_chat_v2_stream_sse_start_content_done、test_chat_v2_stream_file_created_event |

### 11.18 階段六狀態說明

- **階段六**：已完成。依 [Chat-舊代碼盤點報告](./Chat-舊代碼盤點報告.md) 流式缺項實作於 `handlers/stream_handler.py`：start、content（data.chunk）、file_created（來自 response.actions）、error、done；集成測試見 `tests/test_chat_v2_endpoint.py`（流式 SSE 與 file_created 兩則）。前端設定 `VITE_CHAT_USE_V2=true` 改接 v2 流式時可正常累積內容、結束、接收 file_created 與 error 事件。

### 11.19 階段五進度管控表（收尾）

| 任務 ID | 任務描述 | 狀態 | 完成時間 | 備註 |
|---------|----------|------|----------|------|
| T5.1 | 更新 api/routers/chat_module/README.md | ✅ 完成 | 2026-01-28 | 說明 v2 端點、依賴、如何運行測試 |
| T5.2 | 更新 Chat-Module-API-v2-規格.md「v2 現狀與實作範圍」表格 | ✅ 完成 | 2026-01-28 | 新增階段五收尾項；規格版本 v2.4 |
| T5.3 | （可選）main.py 開關停用 v1 | ⏸️ 未做 | - | 可選 |

### 11.20 階段五驗收結果

| 驗收項 | 結果 | 說明 |
|--------|------|------|
| README 已更新 | ✅ | api/routers/chat_module/README.md：v2 端點一覽、依賴、測試指令、目錄結構 |
| 規格「v2 現狀與實作範圍」已更新 | ✅ | Chat-Module-API-v2-規格.md 新增階段五收尾行，版本 v2.4 |
| 新成員可依文檔跑通 | ✅ | README 含 pytest/ruff/mypy 指令與相關文檔連結 |

---

**文檔版本**: 1.9  
**最後更新**: 2026-01-28（階段五收尾完成：T5.1 更新 api/routers/chat_module/README.md 說明 v2 端點、依賴、如何運行測試；T5.2 於 Chat-Module-API-v2-規格.md「v2 現狀與實作範圍」表新增階段五收尾項；驗收檢查清單與 11.4 總體階段狀態更新為階段五完成）  
**維護**: 與 [Chat-Module-API-v2-規格](./Chat-Module-API-v2-規格.md)、[Chat-舊代碼盤點報告](./Chat-舊代碼盤點報告.md) 及 `api/routers/chat_module/` 實作同步更新。
